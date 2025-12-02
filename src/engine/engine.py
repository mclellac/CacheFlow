"""
This module contains the CacheFlowEngine, which is responsible for executing
HTTP requests across the configured infrastructure layers.
"""

import logging
import fnmatch
import warnings
from typing import List, Dict, Optional, Tuple, Any, NamedTuple
from urllib.parse import urlparse

import requests
import dns.resolver
import dns.exception
from urllib3.exceptions import InsecureRequestWarning

from .dns_adapter import DNSAdapter
from .routing import RouteCalculator

warnings.simplefilter("ignore", InsecureRequestWarning)

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
        """Initializes the CacheFlowEngine.

        Args:
            config: A dictionary containing the configuration for the engine.
                It includes 'layers', 'user_agent', 'test_path', and optional
                'dns_servers' and 'verify_ssl'.
        """
        self.config = config
        self.dns_servers = []
        self.verify_ssl = config.get("verify_ssl", False)
        log.debug("CacheFlowEngine initialized.")

        dns_config = self.config.get("dns_servers", "")
        if dns_config:
            self.dns_servers = [
                s.strip() for s in dns_config.split(",") if s.strip()
            ]
            log.debug("Using custom DNS servers: %s", self.dns_servers)

        self.session = requests.Session()
        self.dns_map = {}
        adapter = DNSAdapter(dns_map=self.dns_map)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def resolve_host(self, hostname: str) -> Tuple[str, Optional[Any]]:
        """Resolves a hostname to an IP address.

        Uses custom DNS servers if they are configured in the engine.

        Args:
            hostname: The hostname to resolve.

        Returns:
            A tuple containing the resolved IP address (or the original
            hostname if resolution fails) and an error object if one occurred.
        """
        if not self.dns_servers:
            return hostname, None

        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = self.dns_servers
            answers = resolver.resolve(hostname, "A")
            if answers:
                ip = str(answers[0])
                log.debug("Resolved '%s' to '%s'", hostname, ip)
                return ip, None
            raise dns.resolver.NoAnswer(f"No A records found for {hostname}")
        except (
            dns.resolver.NXDOMAIN,
            dns.resolver.NoAnswer,
            dns.resolver.Timeout,
            dns.exception.DNSException,
        ) as e:
            log.error("Custom DNS resolution failed for %s: %s", hostname, e)
            return hostname, str(e)
        return hostname, None

    def _select_node_from_siblings(
        self,
        siblings: List[Dict[str, Any]],
        previous_headers: Dict[str, str],
        target_base: str,
        layer_type: str,
        target_host_header: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Selects the active node from a list of siblings based on routing criteria.

        Args:
            siblings: List of sibling node configurations.
            previous_headers: Response headers from the previous layer.
            target_base: The target base URL resolved from routing rules.
            layer_type: The type of the current layer.
            target_host_header: The host header of the current request.

        Returns:
            A tuple containing the active node configuration and a list of inactive siblings.
        """
        active_node = None
        inactive_nodes = []

        for node in siblings:
            matched = False

            if layer_type == "Cache Proxy":
                matched = self._match_cache_proxy_node(
                    node, previous_headers, target_host_header
                )
            elif layer_type == "Application Backend":
                matched = self._match_backend_node(node, target_base)

            if matched and not active_node:
                active_node = node
            else:
                inactive_nodes.append(node)

        if not active_node and siblings:
            log.warning(
                "No matching node found in siblings. Defaulting to first node."
            )
            active_node = siblings[0]
            inactive_nodes = siblings[1:]

        return active_node, inactive_nodes

    def _match_cache_proxy_node(
        self,
        node: Dict[str, Any],
        previous_headers: Dict[str, str],
        target_host_header: Optional[str],
    ) -> bool:
        """Checks if a cache proxy node matches criteria."""
        match_header = node.get("match_header", "")
        match_value = node.get("match_value", "")

        if match_header and match_value:
            actual_value = previous_headers.get(match_header, "")
            if (
                not actual_value
                and match_header.lower() == "host"
                and target_host_header
            ):
                actual_value = target_host_header

            if actual_value == match_value:
                return True
            if actual_value.lower() == match_value.lower():
                return True
        return False

    def _match_backend_node(
        self, node: Dict[str, Any], target_base: str
    ) -> bool:
        """Checks if a backend node matches criteria."""
        node_url = node.get("host_url", "").rstrip("/")
        target = target_base.rstrip("/")

        if "://" in node_url:
            node_url = node_url.split("://", 1)[1]
        if "://" in target:
            target = target.split("://", 1)[1]

        return node_url == target

    def _process_layer_dynamic(
        self,
        layer_config: Dict[str, Any],
        target_base: str,
        target_path: str,
        target_host_header: Optional[str],
        user_agent: str,
        previous_headers: Dict[str, str],
    ) -> Tuple[Dict[str, Any], str, str, Optional[str]]:
        """Processes a layer and determines the next hop.

        Args:
            layer_config: The configuration for the layer to process.
            target_base: The base URL for the request.
            target_path: The path for the request.
            target_host_header: The host header to use for the request.
            user_agent: The user agent to use for the request.
            previous_headers: The headers from the previous layer response.

        Returns:
            A tuple containing the result of the layer processing, the next
            base URL, the next path, and the next host header.
        """
        exec_layer = layer_config.copy()
        siblings = []

        # Check for multiple nodes
        nodes = layer_config.get("nodes", [])
        if nodes:
            # We have multiple nodes. We need to select one.
            active_node, inactive_nodes = self._select_node_from_siblings(
                nodes,
                previous_headers,
                target_base,
                layer_config.get("layer_type", ""),
                target_host_header,
            )

            # Merge active node config into exec_layer
            # Active node attributes override layer defaults
            if active_node:
                exec_layer.update(active_node)
                # Ensure we use the active node's URL if it's a Cache Proxy (where URL is defined in node)
                # For App Backend, target_base comes from routing rules, but we matched matched it against node['host_url']
                # So we should use that.
                if exec_layer.get("layer_type") == "Cache Proxy":
                    target_base = active_node.get("host_url", target_base)

            siblings = inactive_nodes

        exec_layer["host_url"] = target_base
        if target_host_header:
            # If a host header is passed from the previous layer, it takes precedence.
            exec_layer["host_header"] = target_host_header

        result = self._process_layer(exec_layer, target_path, user_agent)

        # Attach sibling info to result for visualization
        result["siblings"] = siblings

        request_host = None
        if target_base:
            parsed_base = urlparse(target_base)
            request_host = parsed_base.hostname

        next_base, next_path, next_host_header = (
            RouteCalculator.calculate_next_hop(
                layer_config, target_path, request_host
            )
        )

        return result, next_base, next_path, next_host_header

    def run_inspection(
        self, test_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Executes the inspection run using dynamic routing.

        Args:
            test_path: The path to test. If not provided, the path from the
                config will be used.

        Returns:
            A list of dictionaries, where each dictionary represents the
            result of a layer inspection.
        """
        log.info("Starting inspection run (Dynamic).")
        test_path = test_path or self.config.get("test_path", "/")
        if not test_path.startswith("/"):
            test_path = f"/{test_path}"

        user_agent = self.config.get("user_agent", "CacheFlow/0.1.0")
        layers_config = list(self.config.get("layers", []))

        if not layers_config:
            return []

        results = []
        entry_point = self.config.get("entry_point") or layers_config[0].get(
            "host_url", "localhost"
        )

        parsed_entry = urlparse(
            f"https://{entry_point}"
            if "://" not in entry_point
            else entry_point
        )
        current_base = f"{parsed_entry.scheme}://{parsed_entry.netloc}"
        current_path = test_path
        current_host_header = None
        previous_headers = {}

        processed_layers = 0
        while processed_layers < len(layers_config):
            layer = layers_config[processed_layers]

            # Detect if this layer and subsequent layers are all "Application Backend"
            # If so, treat them as siblings (candidates) for the next hop
            backend_candidates = self._find_backend_candidates(
                layers_config, processed_layers
            )

            if len(backend_candidates) > 1:
                # We have multiple backend candidates. Select the one matching current_base.
                active_layer, inactive_layers = self._select_node_from_siblings(
                    backend_candidates,
                    previous_headers,
                    current_base,
                    "Application Backend",
                    current_host_header,
                )

                if not active_layer:
                    active_layer = backend_candidates[0]
                    inactive_layers = backend_candidates[1:]

                # Execute the active layer
                result, next_base, next_path, next_hh = (
                    self._process_layer_dynamic(
                        active_layer,
                        current_base,
                        current_path,
                        current_host_header,
                        user_agent,
                        previous_headers,
                    )
                )

                # Add inactive layers as siblings to the result
                if "siblings" not in result:
                    result["siblings"] = []
                result["siblings"].extend(inactive_layers)

                results.append(result)
                processed_layers += len(backend_candidates)
            else:
                # Normal processing
                result, next_base, next_path, next_hh = (
                    self._process_layer_dynamic(
                        layer,
                        current_base,
                        current_path,
                        current_host_header,
                        user_agent,
                        previous_headers,
                    )
                )
                results.append(result)
                processed_layers += 1

            # Update previous headers for next iteration
            previous_headers = result.get("headers", {})
            is_last_layer = processed_layers >= len(layers_config)

            if next_base:
                current_base = next_base
                current_path = next_path
                current_host_header = next_hh

                if is_last_layer:
                    # If the last configured layer points to another backend,
                    # add a dynamic layer to represent it
                    self._add_dynamic_backend_layer(layers_config, next_base)

            elif not is_last_layer:
                # Fallback to next layer's host
                fallback_base = self._get_fallback_base(
                    layers_config, processed_layers
                )
                if fallback_base:
                    current_base = fallback_base
                    current_path = test_path
                    current_host_header = None
                else:
                    log.error(
                        "Next layer '%s' has no host_url to fall back to. "
                        "Stopping inspection.",
                        layers_config[processed_layers]["name"],
                    )
                    break  # Stop processing
            else:
                # Last layer and no next hop, we're done.
                break

        return results

    def _find_backend_candidates(
        self, layers_config: List[Dict[str, Any]], start_index: int
    ) -> List[Dict[str, Any]]:
        """Identifies consecutive Application Backend layers."""
        candidates = []
        layer = layers_config[start_index]
        if layer.get("layer_type") == "Application Backend":
            candidates.append(layer)
            lookahead = start_index + 1
            while lookahead < len(layers_config):
                next_l = layers_config[lookahead]
                if next_l.get("layer_type") == "Application Backend":
                    candidates.append(next_l)
                    lookahead += 1
                else:
                    break
        return candidates

    def _add_dynamic_backend_layer(
        self, layers_config: List[Dict[str, Any]], next_base: str
    ) -> None:
        """Adds a dynamic backend layer to the configuration."""
        dynamic_layer = {
            "name": "Backend",
            "description": "Dynamically routed backend",
            "layer_type": "Application Backend",
            "provider": "Unknown",
            "host_url": next_base,
        }
        layers_config.append(dynamic_layer)

    def _get_fallback_base(
        self,
        layers_config: List[Dict[str, Any]],
        next_layer_index: int,
    ) -> Optional[str]:
        """Gets the fallback base URL from the next layer.

        Args:
            layers_config: The list of layer configurations.
            next_layer_index: The index of the next layer.

        Returns:
            The fallback base URL, or None if not available.
        """
        layer = layers_config[next_layer_index - 1]
        log.warning(
            "Layer '%s' did not define a next hop. "
            "Falling back to next layer's host.",
            layer["name"],
        )

        next_layer = layers_config[next_layer_index]
        fallback_url = next_layer.get("host_url")

        if fallback_url:
            parsed_fallback = urlparse(
                f"https://{fallback_url}"
                if "://" not in fallback_url
                else fallback_url
            )
            return f"{parsed_fallback.scheme}://{parsed_fallback.netloc}"

        return None

    def _should_process_layer(
        self, layer: Dict[str, Any], test_path: str
    ) -> bool:
        """Determines if a layer should be processed based on path matching.

        Args:
            layer: The layer configuration.
            test_path: The path to test.

        Returns:
            True if the layer should be processed, False otherwise.
        """
        path_match_patterns = layer.get("path_match_only", [])
        if not path_match_patterns:
            return True

        for pattern in path_match_patterns:
            if fnmatch.fnmatch(test_path, pattern):
                return True
        return False

    def _process_layer(
        self, layer: Dict[str, Any], test_path: str, user_agent: str
    ) -> Dict[str, Any]:
        """Processes a single layer.

        Args:
            layer: The layer configuration.
            test_path: The path to test.
            user_agent: The user agent to use for the request.

        Returns:
            A dictionary containing the result of the layer inspection.
        """
        if not self._should_process_layer(layer, test_path):
            return {"name": layer["name"], "skipped": True}

        host_header_override = layer.get("host_header")
        if "host_overrides" in layer:
            for override in layer["host_overrides"]:
                if fnmatch.fnmatch(
                    test_path, override.get("path_pattern", "")
                ):
                    host_header_override = override.get("host_header")
                    break

        base_url = layer.get("host_url", "").rstrip("/")
        if not base_url:
            return {
                "name": layer["name"],
                "error": "Host URL is not configured for this layer.",
                "error_type": "config_error",
            }

        parsed_url = urlparse(base_url)
        hostname = parsed_url.hostname

        target_ip, dns_error = self._resolve_dns_for_layer(hostname)
        if dns_error:
            return {
                "name": layer["name"],
                "error": f"DNS Error: {dns_error}",
                "error_type": "dns",
            }

        url = base_url + test_path
        headers = layer.get("custom_headers", {}).copy()
        headers["User-Agent"] = user_agent

        # Disable automatic compression to match curl behavior and avoid missing headers
        # from servers that vary responses based on Accept-Encoding.
        # Only set if not explicitly configured by the user.
        has_accept_encoding = any(
            k.lower() == "accept-encoding" for k in headers
        )
        if not has_accept_encoding:
            headers["Accept-Encoding"] = None

        if host_header_override:
            headers["Host"] = host_header_override

        params = RequestParams(
            url=url,
            headers=headers,
            target_ip=target_ip,
            layer=layer,
            original_url=base_url + test_path,
        )

        return self._execute_request(params)

    def _extract_cookies(self, response_cookies) -> List[Dict[str, Any]]:
        """Extracts cookie data from the response cookies."""
        cookies = []
        for c in response_cookies:
            cookie_data = {
                "name": c.name,
                "value": c.value,
                "domain": c.domain,
                "path": c.path,
                "secure": c.secure,
                "expires": c.expires,
                "http_only": c.has_nonstandard_attr("HttpOnly"),
                "same_site": c.get_nonstandard_attr("SameSite"),
            }
            cookies.append(cookie_data)
        return cookies

    def _resolve_dns_for_layer(
        self, hostname: str
    ) -> Tuple[str, Optional[Any]]:
        """Resolves DNS for a layer and updates the adapter map.

        Args:
            hostname: The hostname to resolve.

        Returns:
            A tuple containing the resolved IP address and any DNS error that
            occurred.
        """
        target_ip = hostname
        dns_error = None
        if self.dns_servers:
            target_ip, dns_error = self.resolve_host(hostname)
            if not dns_error and target_ip != hostname:
                self.dns_map[hostname] = target_ip
        return target_ip, dns_error

    def _execute_request(self, params: RequestParams) -> Dict[str, Any]:
        """Executes the HTTP request for a layer and handles errors.

        Args:
            params: A RequestParams object containing the request parameters.

        Returns:
            A dictionary containing the result of the request.
        """
        log.debug(
            "Executing request: URL=%s, Headers=%s", params.url, params.headers
        )

        layer_result = {
            "name": params.layer["name"],
            "provider": params.layer.get("provider"),
            "layer_type": params.layer.get("layer_type"),
            "description": params.layer.get("description", ""),
            "url": params.url,
            "original_url": params.original_url,
            "sent_host_header": params.headers.get("Host"),
            "method": "GET",  # Hardcoded for now, can be a parameter later
            "request_headers": params.headers,
            "latency": 0.0,
        }

        try:
            response = self.session.get(
                params.url,
                headers=params.headers,
                timeout=10,
                allow_redirects=False,
                verify=self.verify_ssl,
                stream=True,
            )

            # Capture TLS info
            tls_version = None
            cipher_suite = None
            if params.url.startswith("https://"):
                try:
                    # Attempt to access underlying socket for TLS info
                    # Note: This relies on internal structure of urllib3/requests
                    if hasattr(response.raw, "connection") and hasattr(
                        response.raw.connection, "sock"
                    ):
                        sock = response.raw.connection.sock
                        if sock:
                            if hasattr(sock, "version"):
                                tls_version = sock.version()
                            if hasattr(sock, "cipher"):
                                cipher = sock.cipher()
                                if cipher:
                                    cipher_suite = cipher[0]
                except Exception:  # pylint: disable=broad-exception-caught
                    log.warning("Could not extract TLS info", exc_info=True)

            # Force reading content to consume stream and release connection
            _ = response.content

            # We do NOT call response.raise_for_status() because we want to capture
            # and analyze 4xx/5xx responses as valid results from the infrastructure layer.

            layer_result.update(
                {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "cookies": self._extract_cookies(response.cookies),
                    "latency": response.elapsed.total_seconds() * 1000,
                    "tls_version": tls_version,
                    "cipher_suite": cipher_suite,
                }
            )
            log.debug("Request completed. Status: %s", response.status_code)

        except requests.exceptions.SSLError as e:
            self._handle_error(layer_result, ERR_SSL, e, "ssl")
        except requests.exceptions.Timeout as e:
            msg = ERR_TIMEOUT.format(params.target_ip)
            self._handle_error(layer_result, msg, e, "timeout")
        except requests.exceptions.ConnectionError as e:
            msg = ERR_CONNECTION.format(params.target_ip)
            self._handle_error(layer_result, msg, e, "connection")
        except requests.exceptions.RequestException as e:
            # Catch any other `requests` specific exceptions
            self._handle_error(
                layer_result, f"Request Error: {e}", e, "request_error"
            )

        return layer_result

    def _handle_error(
        self,
        result: Dict[str, Any],
        message: str,
        exception: Exception,
        error_type: str,
    ) -> None:
        """Updates a result dictionary with error information.

        Args:
            result: The result dictionary to update.
            message: The error message.
            exception: The exception that occurred.
            error_type: The type of error.
        """
        log.error(
            "Request failed for '%s': %s (%s)",
            result.get("name"),
            message,
            exception,
        )
        result["error"] = message
        result["error_type"] = error_type
