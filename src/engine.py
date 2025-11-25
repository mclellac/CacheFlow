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
        layers_to_inspect = list(self.config.get('layers', []))

        # Initial queue with the first layer (CDN) using the Domain Entry Point
        if not layers_to_inspect:
            log.warning("No layers configured for inspection.")
            return []

        # The first request is to the Entry Point (Domain Name)
        # This maps to the first layer in our list (usually CDN)
        first_layer = layers_to_inspect[0]
        entry_point = self.config.get('entry_point', '')
        if not entry_point:
            # Fallback if entry_point missing (shouldn't happen with new config)
            entry_point = first_layer.get('host_url', 'localhost')

        # Ensure entry point has protocol
        if not entry_point.startswith('http'):
            entry_point = 'https://' + entry_point

        # Queue of (layer_config, current_url, current_host_header)
        # We process layers one by one, using the previous layer's output to determine the next URL.
        # But we align with the `layers_to_inspect` list structure where possible.
        # Actually, `layers_to_inspect` defines the *expected* infrastructure.
        # The URL we *request* is calculated dynamically.
        # So:
        # 1. Request to EntryPoint. Associate with Layer 0.
        # 2. Layer 0 config determines Next URL.
        # 3. Request to Next URL. Associate with Layer 1.
        # ...

        current_url = entry_point.rstrip('/') + test_path
        current_host_header = None # Default to URL's host

        processed_count = 0
        while processed_count < len(layers_to_inspect):
            layer = layers_to_inspect[processed_count]
            log.info("Processing layer: %s. Target: %s", layer.get('name'), current_url)

            # Update layer config for execution (inject current URL)
            # We create a temporary layer dict for execution to avoid modifying the config source
            exec_layer = layer.copy()
            exec_layer['host_url'] = current_url # Overwrite with dynamic URL
            if current_host_header:
                exec_layer['host_header'] = current_host_header
                # Ensure host_overrides doesn't conflict if we force it?
                # Actually _process_layer handles overrides.
                # If we pass `host_header` here, it acts as a base.
                # But _process_layer looks for `host_overrides`.
                # If we want to FORCE the host header determined by previous hop,
                # we should probably clear `host_overrides` or make sure it respects the passed one?
                # The logic in _process_layer says:
                # final_host_header = host_header_override or hostname
                # So if we set 'host_header' key, it will be used unless an override matches.
                # But the "Previous Layer" determined the Host Header.
                # Does the "Current Layer" config override the "Previous Layer's" instruction?
                # Usually, Previous Layer (e.g. CDN) says "Go to Origin with Host Header X".
                # The Origin (Cache Proxy) shouldn't override that unless it's doing internal rewriting.
                # But `CacheFlow` simulates the request *as if* it came from the Previous Layer.
                # So we should respect the determined Host Header.
                # Let's trust `host_header` in `exec_layer`.

            result = self._process_layer(exec_layer, test_path, user_agent)
            results.append(result)

            # Determine Next Hop
            # Check Routing Rules
            routing_rules = layer.get('routing_rules', [])
            rule_matched = False

            # Helper to extract path from current_url in case it was rewritten?
            # Actually, `test_path` is passed along.
            # But wait, if previous layer rewrote the path, we should use the new path for the next request.
            # `current_url` contains the path?
            # `_process_layer` constructs URL = base_url + test_path.
            # So `test_path` is the "path to be requested".
            # If we rewrite it, we must update `test_path` for the next iteration.

            # Wait, `current_url` passed to `_process_layer` (via exec_layer['host_url'])
            # is expected to be the BASE URL (Host) or full URL?
            # `_process_layer` does: `base_url = layer['host_url'].rstrip('/')`
            # then `url = base_url + test_path`.
            # So `host_url` MUST be just the schema://hostname.
            # My logic above set `current_url = entry_point + test_path`.
            # This causes `base_url` to include the path, and then `+ test_path` doubles it.
            # FIX: `current_url` should be the BASE URL (schema://host).

            # Let's fix the initial `current_url`.
            parsed_entry = urlparse(entry_point)
            current_base = f"{parsed_entry.scheme}://{parsed_entry.netloc}"

            # If entry_point had a path, we might need to prepend it to test_path?
            # Usually entry point is just domain.

            # Re-run logic with separation of Base and Path

            if processed_count == 0:
                 # First iteration correction
                 # The loop variable `current_url` was intended to be the full target?
                 # Let's split it: `next_base_url` and `next_path`.
                 pass

            # Let's refactor the loop state variables
            if processed_count == 0:
                 # Initialize from Entry Point
                 parsed = urlparse(entry_point)
                 next_base = f"{parsed.scheme}://{parsed.netloc}"
                 next_path = test_path
                 next_host_header = None

                 # Logic correction: The request we JUST made was to `next_base` + `next_path`.
                 # The `exec_layer` setup needs to handle this.

            # To avoid confusion, let's look at the result of the Current Layer to calculate Next Layer.
            # But we need to setup `exec_layer` correctly first.
            # I will restart the loop logic mentally.

        return results

    def _process_layer_dynamic(self, layer_config: Dict[str, Any],
                               target_base: str, target_path: str,
                               target_host_header: Optional[str],
                               user_agent: str) -> Tuple[Dict[str, Any], str, str, Optional[str]]:
        """
        Processes a layer and determines the next hop.
        Returns (Result, NextBase, NextPath, NextHostHeader)
        """
        # 1. Execute Request
        # We need to inject the target into the layer config temporarily
        exec_layer = layer_config.copy()
        exec_layer['host_url'] = target_base
        if target_host_header:
            # We treat the passed host header as an override for this request
            # We add a catch-all override to ensure it's used
            overrides = exec_layer.get('host_overrides', [])
            # Prepend to ensure priority? Or append?
            # process_layer uses the FIRST match.
            # So we prepend a match-all rule with our target header.
            exec_layer['host_overrides'] = [{
                'path_pattern': '*',
                'host_header': target_host_header
            }] + overrides

            # Also set the top level for fallback
            exec_layer['host_header'] = target_host_header

        result = self._process_layer(exec_layer, target_path, user_agent)

        # 2. Determine Next Hop based on THIS layer's rules and the path used
        next_base = None
        next_path = target_path
        next_host_header = None

        # Check Routing Rules
        routing_rules = layer_config.get('routing_rules', [])
        rule_matched = False

        for rule in routing_rules:
            path_match = rule.get('path_match')
            is_match = False
            if path_match:
                is_match = fnmatch.fnmatch(target_path, path_match)

            if is_match:
                log.info("Routing rule matched: %s", path_match)
                backend_host = rule.get('backend_host') # This is the "Destination Origin"
                path_rewrite = rule.get('path_rewrite')
                backend_host_header = rule.get('backend_host_header')

                if backend_host:
                     if not backend_host.startswith('http'):
                         next_base = f"https://{backend_host}"
                     else:
                         next_base = backend_host

                if backend_host_header:
                    next_host_header = backend_host_header

                if path_rewrite:
                     # Simple rewrite logic: s/find/replace/
                     if path_rewrite.startswith('s'):
                         try:
                             parts = path_rewrite.split(path_rewrite[1])
                             if len(parts) >= 3:
                                 pattern = parts[1]
                                 repl = parts[2]
                                 next_path = re.sub(pattern, repl, target_path)
                                 log.debug("Rewrote path '%s' to '%s'", target_path, next_path)
                         except Exception as e: # pylint: disable=broad-exception-caught
                             log.error("Failed to parse rewrite rule: %s", e)

                rule_matched = True
                break

        if not rule_matched:
            # Fallback to Default Backend/Origin
            default_host = layer_config.get('default_backend_host')
            if default_host:
                log.info("Using default backend: %s", default_host)
                if not default_host.startswith('http'):
                    next_base = f"https://{default_host}"
                else:
                    next_base = default_host

                next_host_header = layer_config.get('default_backend_host_header')

        return result, next_base, next_path, next_host_header


    def run_inspection_v2(self, test_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Executes the inspection run using dynamic routing.
        """
        log.info("Starting inspection run (Dynamic).")
        if test_path is None:
            test_path = self.config.get('test_path', '/')
        if not test_path.startswith('/'):
            test_path = '/' + test_path

        user_agent = self.config.get('user_agent', 'CacheFlow/0.1.0')
        layers_config = list(self.config.get('layers', []))

        if not layers_config:
            return []

        results = []

        # Initial State
        entry_point = self.config.get('entry_point', '')
        if not entry_point:
            entry_point = layers_config[0].get('host_url', 'localhost')

        parsed = urlparse(entry_point if entry_point.startswith('http') else f"https://{entry_point}")
        current_base = f"{parsed.scheme}://{parsed.netloc}"
        current_path = test_path
        current_host_header = None

        # Loop through configured layers
        # If the chain diverges (dynamic backend not in list), we add it dynamically.

        idx = 0
        while idx < len(layers_config):
            layer = layers_config[idx]

            # Execute
            result, next_base, next_path, next_hh = self._process_layer_dynamic(
                layer, current_base, current_path, current_host_header, user_agent
            )
            results.append(result)

            # Prepare for next iteration
            if next_base:
                current_base = next_base
                current_path = next_path
                current_host_header = next_hh
            else:
                # No next hop defined.
                # If this is the last layer, that's fine.
                # If there are more layers configured but no link, we can't proceed.
                if idx < len(layers_config) - 1:
                    log.warning("Layer '%s' did not define a next hop, but more layers exist.", layer['name'])
                    # We could try to fall back to the NEXT layer's Host URL if it exists?
                    # This supports the mixed mode (Static + Dynamic).
                    next_layer = layers_config[idx+1]
                    fallback_url = next_layer.get('host_url')
                    if fallback_url:
                        current_base = fallback_url if fallback_url.startswith('http') else f"https://{fallback_url}"
                        # path and host header remain?
                        # Probably reset host header?
                        # current_host_header = None
                    else:
                        break # Cannot proceed
                else:
                    break # End of chain

            # Special Handling for Dynamic Backends
            # If `next_base` points to something that is NOT the next configured layer...
            # The user might have configured: CDN -> Cache -> Backend.
            # The CDN routing rule might point to "Cache-B" (not in list).
            # We need to detect if we should create a dynamic node.

            # But for now, we just proceed to the next layer in the list using the calculated URL.
            # What if the user intentionally wants to visualize the divergence?
            # If the calculated `next_base` doesn't match the `host_url` of `layers_config[idx+1]`,
            # it implies a divergence or just a specific resolution.
            # Given we are simulating, we treat `next_base` as the TRUTH for the next request.
            # We attach it to the next layer in the list.

            # If we run out of configured layers but `next_base` is set (e.g. CDN -> Default Origin, but no Cache Layer config),
            # we should probably create a "Dynamic Backend" node to show where it went.

            if idx == len(layers_config) - 1 and next_base:
                # We have a next hop but no more config layers.
                # Create a dynamic backend layer to visualize the final destination.
                dynamic_layer = {
                    'name': 'Backend', # Generic name
                    'description': 'Dynamically routed backend',
                    'layer_type': 'Application Backend',
                    'provider': 'Unknown',
                    'host_url': next_base, # This isn't used for routing as we are at end, but for display
                    # We don't need to actually add it to `layers_config` for saving, just for this run.
                    # But we need to iterate it.
                }
                # We append to a local list or just process it?
                # We can append to `layers_config` (it's a local list variable).
                layers_config.append(dynamic_layer)

            idx += 1

        return results

    # Replacer for run_inspection
    run_inspection = run_inspection_v2

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
