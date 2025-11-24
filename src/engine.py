"""
This module contains the CacheFlowEngine, which is responsible for executing
HTTP requests across the configured infrastructure layers.
"""

import logging
import fnmatch
import warnings
from typing import List, Dict, Optional, Tuple, Any
from urllib.parse import urlparse

import requests
import dns.resolver
import dns.exception
from urllib3.exceptions import InsecureRequestWarning

from .dns_adapter import DNSAdapter

warnings.simplefilter('ignore', InsecureRequestWarning)

log = logging.getLogger(__name__)

ERR_SSL = "SSL Error. The certificate may be invalid."
ERR_TIMEOUT = "Connection timed out to {}."
ERR_CONNECTION = "Connection refused by {}."


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

    def run_inspection(self, test_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Executes the inspection run against all configured layers.
        """
        log.info("Starting inspection run.")
        if test_path is None:
            test_path = self.config.get('test_path', '/')

        if not test_path.startswith('/'):
            test_path = '/' + test_path
        log.debug("Using test path: '%s'", test_path)

        results = []
        user_agent = self.config.get('user_agent', 'CacheFlow/0.1.0')
        layers_to_inspect = self.config.get('layers', [])

        for i, layer in enumerate(layers_to_inspect):
            log.info("Processing layer: %s", layer.get('name'))

            if not self._should_process_layer(layer, test_path,
                                              i < len(layers_to_inspect) - 1):
                log.debug("Path '%s' did not match any patterns. Skipping layer.",
                          test_path)
                continue

            result = self._process_layer(layer, test_path, user_agent)
            results.append(result)

        return results

    def _should_process_layer(self, layer: Dict[str, Any], test_path: str,
                              check_match: bool) -> bool:
        """Determines if a layer should be processed based on path matching."""
        if not check_match:
            return True

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
        # Determine overrides
        host_header_override = layer.get('host_header')
        if 'host_overrides' in layer:
            for override in layer['host_overrides']:
                if fnmatch.fnmatch(test_path, override['path_pattern']):
                    host_header_override = override['host_header']
                    break
        log.debug("Host header override is: '%s'", host_header_override)

        base_url = layer['host_url'].rstrip('/')
        parsed_url = urlparse(base_url)
        hostname = parsed_url.hostname
        final_host_header = host_header_override or hostname

        # Resolve DNS
        target_ip, dns_error = self._resolve_dns_for_layer(hostname)
        if dns_error:
            return {
                'name': layer['name'],
                'error': f"DNS Error: {dns_error}",
                'error_type': 'dns'
            }

        # Prepare Request
        url = base_url + test_path
        headers = layer.get('custom_headers', {}).copy()
        headers['User-Agent'] = user_agent
        if host_header_override:
            headers['Host'] = final_host_header

        # Execute Request
        return self._execute_request(url, headers, target_ip, layer,
                                     base_url + test_path)

    def _resolve_dns_for_layer(self, hostname: str) -> Tuple[str, Optional[Any]]:
        """Resolves DNS and updates the adapter map."""
        target_ip = hostname
        dns_error = None
        if self.dns_servers:
            target_ip, dns_error = self.resolve_host(hostname)
            if not dns_error and target_ip != hostname:
                self.dns_map[hostname] = target_ip
        return target_ip, dns_error

    def _execute_request(self, url: str, headers: Dict[str, str], target_ip: str,
                         layer: Dict[str, Any], original_url: str) -> Dict[str, Any]:
        """Executes the HTTP request and handles errors."""
        # pylint: disable=too-many-arguments
        # pylint: disable=too-many-positional-arguments
        log.debug("Request URL: %s", url)
        log.debug("Request Headers: %s", headers)

        layer_result = {
            'name': layer['name'],
            'description': layer.get('description', ''),
            'url': url,
            'original_url': original_url,
            'sent_host_header': headers.get('Host'),
            'method': 'GET'
        }

        try:
            response = self.session.get(
                url, headers=headers, timeout=10, stream=True,
                allow_redirects=False, verify=self.verify_ssl
            )
            response.close()

            layer_result.update({
                'status_code': response.status_code,
                'headers': dict(response.headers)
            })
            log.debug("Request successful. Status: %s", response.status_code)

        except requests.exceptions.SSLError as e:
            self._handle_error(layer_result, ERR_SSL, e, 'ssl')
        except requests.exceptions.ConnectTimeout as e:
            self._handle_error(layer_result, ERR_TIMEOUT.format(target_ip), e,
                               'timeout')
        except requests.exceptions.ConnectionError as e:
            self._handle_error(layer_result, ERR_CONNECTION.format(target_ip), e,
                               'connection')
        except Exception as e:  # pylint: disable=broad-exception-caught
            self._handle_error(layer_result, str(e), e, 'unknown')

        return layer_result

    def _handle_error(self, result: Dict[str, Any], message: str,
                      exception: Exception, error_type: str) -> None:
        """Helper to update result with error info."""
        log.error("Request failed for %s: %s - %s",
                  result.get('url'), message, exception)
        result['error'] = message
        result['error_type'] = error_type
