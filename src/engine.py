"""
This module contains the CacheFlowEngine, which is responsible for executing
HTTP requests across the configured infrastructure layers.
"""

import logging
import fnmatch
import re
import warnings
from typing import List, Dict, Optional, Tuple, Any, NamedTuple
from urllib.parse import urlparse

import requests
import dns.resolver
import dns.exception
from urllib3.exceptions import InsecureRequestWarning

from .dns_adapter import DNSAdapter
from .routing import RouteCalculator

warnings.simplefilter('ignore', InsecureRequestWarning)

log = logging.getLogger(__name__)

ERR_SSL = "SSL Error. The certificate may be invalid."
ERR_TIMEOUT = "Connection timed out to {}."
ERR_CONNECTION = "Connection refused by {}."


class RequestParams(NamedTuple):
    """Encapsulates parameters for executing a layer request."""
    url: str
    headers: Dict[str, str]
    target_ip: str
    layer: Dict[str, Any]
    original_url: str


class CacheFlowEngine:
    """
    The core engine for CacheFlow. Handles DNS resolution and HTTP requests
    for each layer in the configuration.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize with a configuration dictionary.
        Config includes 'layers', 'user_agent', 'test_path',
        optional 'dns_servers' and 'verify_ssl'.
        """
        self.config = config
        self.dns_servers = []
        self.verify_ssl = config.get('verify_ssl', False)
        log.debug("CacheFlowEngine initialized.")

        dns_config = self.config.get('dns_servers', '')
        if dns_config:
            self.dns_servers = [s.strip() for s in dns_config.split(',') if s.strip()]
            log.debug("Using custom DNS servers: %s", self.dns_servers)

        self.session = requests.Session()
        self.dns_map = {}
        adapter = DNSAdapter(dns_map=self.dns_map)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)

    def resolve_host(self, hostname: str) -> Tuple[str, Optional[Any]]:
        """
        Resolves a hostname to an IP address using custom DNS servers if configured.
        """
        if not self.dns_servers:
            return hostname, None

        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = self.dns_servers
            answers = resolver.resolve(hostname, 'A')
            if answers:
                ip = str(answers[0])
                log.debug("Resolved '%s' to '%s'", hostname, ip)
                return ip, None
            raise dns.resolver.NoAnswer(f"No A records found for {hostname}")
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer,
                dns.resolver.Timeout) as e:
            log.error("Custom DNS resolution failed for %s: %s", hostname, e)
            return hostname, e

    def _process_layer_dynamic(self, layer_config: Dict[str, Any],
                               target_base: str, target_path: str,
                               target_host_header: Optional[str],
                               user_agent: str) -> Tuple[Dict[str, Any], str, str, Optional[str]]:
        """
        Processes a layer and determines the next hop.
        Returns (Result, NextBase, NextPath, NextHostHeader)
        """
        exec_layer = layer_config.copy()
        exec_layer['host_url'] = target_base
        if target_host_header:
            # If a host header is passed from the previous layer, it takes precedence.
            exec_layer['host_header'] = target_host_header

        result = self._process_layer(exec_layer, target_path, user_agent)

        next_base, next_path, next_host_header = RouteCalculator.calculate_next_hop(
            layer_config, target_path
        )

        return result, next_base, next_path, next_host_header

    def run_inspection(self, test_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Executes the inspection run using dynamic routing.
        """
        log.info("Starting inspection run (Dynamic).")
        test_path = test_path or self.config.get('test_path', '/')
        if not test_path.startswith('/'):
            test_path = f'/{test_path}'

        user_agent = self.config.get('user_agent', 'CacheFlow/0.1.0')
        layers_config = list(self.config.get('layers', []))

        if not layers_config:
            return []

        results = []
        entry_point = self.config.get('entry_point') or layers_config[0].get('host_url', 'localhost')

        parsed_entry = urlparse(f'https://{entry_point}' if '://' not in entry_point else entry_point)
        current_base = f'{parsed_entry.scheme}://{parsed_entry.netloc}'
        current_path = test_path
        current_host_header = None

        processed_layers = 0
        while processed_layers < len(layers_config):
            layer = layers_config[processed_layers]

            result, next_base, next_path, next_hh = self._process_layer_dynamic(
                layer, current_base, current_path, current_host_header, user_agent
            )
            results.append(result)

            is_last_layer = processed_layers == len(layers_config) - 1

            if next_base:
                current_base = next_base
                current_path = next_path
                current_host_header = next_hh

                if is_last_layer:
                    # If the last configured layer points to another backend, add a dynamic layer to represent it
                    dynamic_layer = {
                        'name': 'Backend',
                        'description': 'Dynamically routed backend',
                        'layer_type': 'Application Backend',
                        'provider': 'Unknown',
                        'host_url': next_base,
                    }
                    layers_config.append(dynamic_layer)

            elif not is_last_layer:
                # If there's no next hop but more layers are configured, try to fall back to the next layer's URL
                log.warning("Layer '%s' did not define a next hop. Falling back to next layer's host.", layer['name'])
                next_layer = layers_config[processed_layers + 1]
                fallback_url = next_layer.get('host_url')
                if fallback_url:
                    parsed_fallback = urlparse(f'https://{fallback_url}' if '://' not in fallback_url else fallback_url)
                    current_base = f'{parsed_fallback.scheme}://{parsed_fallback.netloc}'
                    current_path = test_path # Reset path on fallback? Maybe not. Let's keep it.
                    current_host_header = None
                else:
                    log.error("Next layer '%s' has no host_url to fall back to. Stopping inspection.", next_layer['name'])
                    break # Stop processing
            else:
                # Last layer and no next hop, we're done.
                break

            processed_layers += 1

        return results

    def _should_process_layer(self, layer: Dict[str, Any], test_path: str) -> bool:
        """Determines if a layer should be processed based on path matching."""
        path_match_patterns = layer.get('path_match_only', [])
        if not path_match_patterns:
            return True

        for pattern in path_match_patterns:
            if fnmatch.fnmatch(test_path, pattern):
                return True
        return False

    def _process_layer(self, layer: Dict[str, Any], test_path: str,
                       user_agent: str) -> Dict[str, Any]:
        """Processes a single layer."""
        if not self._should_process_layer(layer, test_path):
            return {
                'name': layer['name'],
                'skipped': True
            }

        host_header_override = layer.get('host_header')
        if 'host_overrides' in layer:
            for override in layer['host_overrides']:
                if fnmatch.fnmatch(test_path, override.get('path_pattern', '')):
                    host_header_override = override.get('host_header')
                    break

        base_url = layer.get('host_url', '').rstrip('/')
        if not base_url:
            return {
                'name': layer['name'],
                'error': 'Host URL is not configured for this layer.',
                'error_type': 'config_error'
            }

        parsed_url = urlparse(base_url)
        hostname = parsed_url.hostname

        target_ip, dns_error = self._resolve_dns_for_layer(hostname)
        if dns_error:
            return {
                'name': layer['name'],
                'error': f"DNS Error: {dns_error}",
                'error_type': 'dns'
            }

        url = base_url + test_path
        headers = layer.get('custom_headers', {}).copy()
        headers['User-Agent'] = user_agent
        if host_header_override:
            headers['Host'] = host_header_override

        params = RequestParams(
            url=url,
            headers=headers,
            target_ip=target_ip,
            layer=layer,
            original_url=base_url + test_path
        )

        return self._execute_request(params)

    def _resolve_dns_for_layer(self, hostname: str) -> Tuple[str, Optional[Any]]:
        """Resolves DNS and updates the adapter map."""
        target_ip = hostname
        dns_error = None
        if self.dns_servers:
            target_ip, dns_error = self.resolve_host(hostname)
            if not dns_error and target_ip != hostname:
                self.dns_map[hostname] = target_ip
        return target_ip, dns_error

    def _execute_request(self, params: RequestParams) -> Dict[str, Any]:
        """Executes the HTTP request and handles errors."""
        log.debug("Executing request: URL=%s, Headers=%s", params.url, params.headers)

        layer_result = {
            'name': params.layer['name'],
            'provider': params.layer.get('provider'),
            'layer_type': params.layer.get('layer_type'),
            'description': params.layer.get('description', ''),
            'url': params.url,
            'original_url': params.original_url,
            'sent_host_header': params.headers.get('Host'),
            'method': 'GET'  # Hardcoded for now, can be a parameter later
        }

        try:
            response = self.session.get(
                params.url, headers=params.headers, timeout=10,
                allow_redirects=False, verify=self.verify_ssl
            )
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

            layer_result.update({
                'status_code': response.status_code,
                'headers': dict(response.headers)
            })
            log.debug("Request successful. Status: %s", response.status_code)

        except requests.exceptions.SSLError as e:
            self._handle_error(layer_result, ERR_SSL, e, 'ssl')
        except requests.exceptions.Timeout as e:
            self._handle_error(layer_result, ERR_TIMEOUT.format(params.target_ip), e, 'timeout')
        except requests.exceptions.ConnectionError as e:
            self._handle_error(layer_result, ERR_CONNECTION.format(params.target_ip), e, 'connection')
        except requests.exceptions.HTTPError as e:
            # For 4xx/5xx errors, we still want to record the response
            layer_result.update({
                'status_code': e.response.status_code,
                'headers': dict(e.response.headers)
            })
            self._handle_error(layer_result, f"HTTP Error: {e.response.status_code}", e, 'http_error')
        except requests.exceptions.RequestException as e:
            # Catch any other `requests` specific exceptions
            self._handle_error(layer_result, f"Request Error: {e}", e, 'request_error')

        return layer_result

    def _handle_error(self, result: Dict[str, Any], message: str,
                      exception: Exception, error_type: str) -> None:
        """Helper to update result with error info."""
        log.error("Request failed for '%s': %s (%s)",
                  result.get('name'), message, exception)
        result['error'] = message
        result['error_type'] = error_type
