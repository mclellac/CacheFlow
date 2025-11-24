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
        # Create a copy of layers to allow modification (dynamic routing)
        layers_to_inspect = list(self.config.get('layers', []))

        # Queue of (layer, path) tuples to process
        # Initial path is the test_path for all static layers unless modified
        inspection_queue = [(l, test_path) for l in layers_to_inspect]

        processed_count = 0
        while processed_count < len(inspection_queue):
            layer, current_path = inspection_queue[processed_count]
            log.info("Processing layer: %s with path %s", layer.get('name'), current_path)

            # Check if we should process this layer (legacy path matching)
            # We only check against subsequent static layers, dynamic ones are explicit
            is_last = processed_count == len(inspection_queue) - 1
            if not self._should_process_layer(layer, current_path, not is_last):
                log.debug("Path '%s' did not match any patterns. Skipping layer.",
                          current_path)
                processed_count += 1
                continue

            result = self._process_layer(layer, current_path, user_agent)
            results.append(result)

            # Check for Dynamic Routing Rules
            routing_rules = layer.get('routing_rules', [])
            if routing_rules:
                for rule in routing_rules:
                    path_match = rule.get('path_match')
                    # Simple fnmatch or regex? Let's assume fnmatch for consistency with existing features,
                    # or maybe regex if the user wants power. The requirement mentioned regsub.
                    # Let's try regex match if fnmatch fails or just use regex.
                    # The existing path_match_only uses fnmatch.
                    # But regsub implies regex. Let's use regex for matching too for flexibility.

                    try:
                        match = re.search(path_match, current_path) if path_match else None
                    except re.error as e:
                        log.error("Invalid regex in routing rule '%s': %s", path_match, e)
                        continue

                    if match:
                        log.info("Routing rule matched: %s", path_match)
                        backend_host = rule.get('backend_host')
                        backend_provider = rule.get('backend_provider', 'Unknown')
                        path_rewrite = rule.get('path_rewrite')

                        new_path = current_path
                        if path_rewrite:
                             # Parse rewrite rule: s|pattern|repl|flags
                             # Or just standard regex sub if the user provides pattern and replacement separately?
                             # The user example was: "regsub paths ... /path1 could be regsubbed to /"
                             # The UI has a single 'rewrite' field.
                             # Let's support a simple syntax or just assume the 'path_match' is the pattern to replace?
                             # But 'path_match' might be just for matching.
                             # Let's assume 'path_rewrite' contains "s/pattern/replacement/" or similar syntax,
                             # OR simpler: the user enters the replacement string and we use 'path_match' as the regex?
                             # No, Varnish regsub(req.url, regex, replacement).
                             # So we need both regex and replacement.
                             # In our UI we have 'Rewrite' entry.
                             # Let's assume the 'Rewrite' entry expects "s/find/replace/" format for flexibility.

                             if path_rewrite.startswith('s'):
                                 try:
                                     # format: s/find/replace/flags
                                     parts = path_rewrite.split(path_rewrite[1])
                                     if len(parts) >= 3:
                                         pattern = parts[1]
                                         repl = parts[2]
                                         new_path = re.sub(pattern, repl, current_path)
                                         log.debug("Rewrote path '%s' to '%s'", current_path, new_path)
                                 except Exception as e: # pylint: disable=broad-exception-caught
                                     log.error("Failed to parse rewrite rule '%s': %s", path_rewrite, e)

                        # Create Dynamic Backend Layer
                        backend_layer = {
                            'name': f"Backend ({backend_host})",
                            'description': 'Dynamically routed backend',
                            'layer_type': 'Application Backend',
                            'provider': backend_provider,
                            'host_url': f"https://{backend_host}", # Default to HTTPS
                            'custom_headers': {},
                            'host_overrides': [],
                            'path_match_only': []
                        }

                        # Add to queue
                        # We append this new layer to be processed next.
                        # IMPORTANT: Do we want to stop processing subsequent STATIC layers?
                        # If we are routing, we probably want to diverge.
                        # So we truncate the queue after the current layer and append the new one.
                        inspection_queue = inspection_queue[:processed_count+1]
                        inspection_queue.append((backend_layer, new_path))
                        break # Follow the first matching rule

            processed_count += 1

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
            headers['Host'] = final_host_header

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
        log.debug("Request URL: %s", params.url)
        log.debug("Request Headers: %s", params.headers)

        layer_result = {
            'name': params.layer['name'],
            'description': params.layer.get('description', ''),
            'layer_type': params.layer.get('layer_type', 'Unknown'),
            'provider': params.layer.get('provider', 'Unknown'),
            'url': params.url,
            'original_url': params.original_url,
            'sent_host_header': params.headers.get('Host'),
            'method': 'GET'
        }

        try:
            response = self.session.get(
                params.url, headers=params.headers, timeout=10, stream=True,
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
            self._handle_error(layer_result, ERR_TIMEOUT.format(params.target_ip), e,
                               'timeout')
        except requests.exceptions.ConnectionError as e:
            self._handle_error(layer_result, ERR_CONNECTION.format(params.target_ip), e,
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
