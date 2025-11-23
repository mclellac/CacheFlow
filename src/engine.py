import requests
import fnmatch
import dns.resolver
from urllib.parse import urlparse, urlunparse

class CacheFlowEngine:
    def __init__(self, config):
        """
        Initialize with a configuration dictionary.
        Config includes 'layers', 'user_agent', 'test_path', and optional 'dns_servers'.
        """
        print(f"[DEBUG] CacheFlowEngine.__init__: Initializing with config: {config}")
        self.config = config
        self.dns_servers = []

        dns_config = self.config.get('dns_servers', '')
        if dns_config:
            # Parse comma separated list
            self.dns_servers = [s.strip() for s in dns_config.split(',') if s.strip()]

    def resolve_host(self, hostname):
        if not self.dns_servers:
            print(f"[DEBUG] CacheFlowEngine.resolve_host: No custom DNS servers. Returning original hostname '{hostname}'.")
            return hostname # Use system resolution (handled by requests)

        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = self.dns_servers
            answers = resolver.resolve(hostname, 'A')
            if answers:
                ip = str(answers[0])
                print(f"[DEBUG] CacheFlowEngine.resolve_host: Resolved '{hostname}' to '{ip}' using servers {self.dns_servers}.")
                return ip
        except Exception as e:
            # Fallback or raise? Let's return hostname to let requests fail naturally or use system
            print(f"[DEBUG] CacheFlowEngine.resolve_host: Custom DNS resolution failed for {hostname}: {e}")
        return hostname

    def run_inspection(self, test_path=None):
        print("[DEBUG] CacheFlowEngine.run_inspection: Starting inspection run.")
        if test_path is None:
            test_path = self.config.get('test_path', '/')

        if not test_path.startswith('/'):
            test_path = '/' + test_path
        print(f"[DEBUG] CacheFlowEngine.run_inspection: Using test path: '{test_path}'")

        results = []
        user_agent = self.config.get('user_agent', 'CacheFlow/0.1.0')

        layers_to_inspect = self.config.get('layers', [])
        for i, layer in enumerate(layers_to_inspect):
            print(f"\n[DEBUG] CacheFlowEngine.run_inspection: --- Processing layer: {layer.get('name')} ---")
            # Check path match, but ALWAYS check the last layer (origin)
            path_match_patterns = layer.get('path_match_only', []) if i < len(layers_to_inspect) - 1 else []
            if path_match_patterns:
                print(f"[DEBUG] CacheFlowEngine.run_inspection: Checking path against patterns: {path_match_patterns}")
                matched = False
                for pattern in path_match_patterns:
                    if fnmatch.fnmatch(test_path, pattern):
                        print(f"[DEBUG] CacheFlowEngine.run_inspection: Path '{test_path}' matched pattern '{pattern}'.")
                        matched = True
                        break
                if not matched:
                    print(f"[DEBUG] CacheFlowEngine.run_inspection: Path '{test_path}' did not match any patterns. Skipping layer.")
                    continue

            # Determine Host header
            host_header_override = layer.get('host_header')
            if 'host_overrides' in layer:
                for override in layer['host_overrides']:
                    if fnmatch.fnmatch(test_path, override['path_pattern']):
                        host_header_override = override['host_header']
                        break
            print(f"[DEBUG] CacheFlowEngine.run_inspection: Host header override is: '{host_header_override}'")

            # Prepare Request
            base_url = layer['host_url'].rstrip('/')
            parsed_url = urlparse(base_url)
            print(f"[DEBUG] CacheFlowEngine.run_inspection: Parsed base URL: {parsed_url}")
            hostname = parsed_url.hostname
            scheme = parsed_url.scheme
            port = parsed_url.port

            # Calculate final Host header
            # 1. If explicitly overridden, use that.
            # 2. Else, use the hostname from the URL.
            final_host_header = host_header_override if host_header_override else hostname
            print(f"[DEBUG] CacheFlowEngine.run_inspection: Final Host header will be: '{final_host_header}'")

            # Resolve DNS if needed
            target_ip = hostname
            if self.dns_servers:
                target_ip = self.resolve_host(hostname)
            print(f"[DEBUG] CacheFlowEngine.run_inspection: Target IP for connection is: '{target_ip}'")

            # Construct actual URL to hit
            # If we resolved to an IP, replace hostname in URL with IP
            # AND ensure Host header is set.

            if target_ip != hostname:
                netloc = target_ip
                if port:
                    netloc += f":{port}"
                # Reconstruct URL with IP
                url_parts = list(parsed_url)
                url_parts[1] = netloc # netloc
                url_parts[2] = test_path # path
                url = urlunparse(url_parts)
            else:
                url = base_url + test_path
            print(f"[DEBUG] CacheFlowEngine.run_inspection: Final request URL: '{url}'")

            headers = layer.get('custom_headers', {}).copy()
            headers['User-Agent'] = user_agent

            # Always set Host header if we messed with the URL (DNS override)
            # OR if there is an explicit override
            if target_ip != hostname or host_header_override:
                headers['Host'] = final_host_header
            print(f"[DEBUG] CacheFlowEngine.run_inspection: Final request headers: {headers}")

            # Make Request
            try:
                print(f"[DEBUG] CacheFlowEngine.run_inspection: Making GET request to {url}...")
                response = requests.get(url, headers=headers, timeout=10, stream=True, allow_redirects=False, verify=False)
                response.close()

                layer_result = {
                    'name': layer['name'],
                    'description': layer.get('description', ''),
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'url': url, # Show the actual URL hit (with IP if resolved)
                    'original_url': base_url + test_path,
                    'sent_host_header': headers.get('Host')
                }
                print(f"[DEBUG] CacheFlowEngine.run_inspection: Request successful. Status: {response.status_code}")
            except Exception as e:
                layer_result = {
                    'name': layer['name'],
                    'description': layer.get('description', ''),
                    'error': str(e),
                    'url': url,
                    'sent_host_header': headers.get('Host')
                }
                print(f"[DEBUG] CacheFlowEngine.run_inspection: Request FAILED. Error: {e}")

            results.append(layer_result)

        return results
