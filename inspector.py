import requests
import fnmatch
import dns.resolver
from urllib.parse import urlparse, urlunparse

class HeaderInspector:
    def __init__(self, config):
        """
        Initialize with a configuration dictionary.
        Config includes 'layers', 'user_agent', 'test_path', and optional 'dns_servers'.
        """
        self.config = config
        self.dns_servers = []

        dns_config = self.config.get('dns_servers', '')
        if dns_config:
            # Parse comma separated list
            self.dns_servers = [s.strip() for s in dns_config.split(',') if s.strip()]

    def resolve_host(self, hostname):
        if not self.dns_servers:
            return hostname # Use system resolution (handled by requests)

        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = self.dns_servers
            answers = resolver.resolve(hostname, 'A')
            if answers:
                return str(answers[0]) # Return first IP
        except Exception as e:
            # Fallback or raise? Let's return hostname to let requests fail naturally or use system
            print(f"Custom DNS resolution failed for {hostname}: {e}")
        return hostname

    def run_inspection(self, test_path=None):
        if test_path is None:
            test_path = self.config.get('test_path', '/')

        if not test_path.startswith('/'):
            test_path = '/' + test_path

        results = []
        user_agent = self.config.get('user_agent', 'HTTP-Header-Inspector')

        for layer in self.config.get('layers', []):
            # Check path match
            if 'path_match_only' in layer:
                matched = False
                for pattern in layer['path_match_only']:
                    if fnmatch.fnmatch(test_path, pattern):
                        matched = True
                        break
                if not matched:
                    continue

            # Determine Host header
            host_header_override = layer.get('host_header')
            if 'host_overrides' in layer:
                for override in layer['host_overrides']:
                    if fnmatch.fnmatch(test_path, override['path_pattern']):
                        host_header_override = override['host_header']
                        break

            # Prepare Request
            base_url = layer['host_url'].rstrip('/')
            parsed_url = urlparse(base_url)
            hostname = parsed_url.hostname
            scheme = parsed_url.scheme
            port = parsed_url.port

            # Calculate final Host header
            # 1. If explicitly overridden, use that.
            # 2. Else, use the hostname from the URL.
            final_host_header = host_header_override if host_header_override else hostname

            # Resolve DNS if needed
            target_ip = hostname
            if self.dns_servers:
                target_ip = self.resolve_host(hostname)

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

            headers = layer.get('custom_headers', {}).copy()
            headers['User-Agent'] = user_agent

            # Always set Host header if we messed with the URL (DNS override)
            # OR if there is an explicit override
            if target_ip != hostname or host_header_override:
                headers['Host'] = final_host_header

            # Make Request
            try:
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
            except Exception as e:
                layer_result = {
                    'name': layer['name'],
                    'description': layer.get('description', ''),
                    'error': str(e),
                    'url': url,
                    'sent_host_header': headers.get('Host')
                }

            results.append(layer_result)

        return results
