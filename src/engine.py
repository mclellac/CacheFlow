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
        self.config = config
        self.dns_servers = []

        dns_config = self.config.get('dns_servers', '')
        if dns_config:
            self.dns_servers = [s.strip() for s in dns_config.split(',') if s.strip()]

    def resolve_host(self, hostname):
        if not self.dns_servers:
            return hostname

        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = self.dns_servers
            answers = resolver.resolve(hostname, 'A')
            if answers:
                return str(answers[0])
        except Exception as e:
            print(f"Custom DNS resolution failed for {hostname}: {e}")
        return hostname

    def run_inspection(self, test_path=None):
        if test_path is None:
            test_path = self.config.get('test_path', '/')

        if not test_path.startswith('/'):
            test_path = '/' + test_path

        results = []
        user_agent = self.config.get('user_agent', 'CacheFlow/0.1.0')

        layers_to_inspect = self.config.get('layers', [])
        for i, layer in enumerate(layers_to_inspect):
            path_match_patterns = layer.get('path_match_only', []) if i < len(layers_to_inspect) - 1 else []
            if path_match_patterns:
                matched = False
                for pattern in path_match_patterns:
                    if fnmatch.fnmatch(test_path, pattern):
                        matched = True
                        break
                if not matched:
                    continue

            host_header_override = layer.get('host_header')
            if 'host_overrides' in layer:
                for override in layer['host_overrides']:
                    if fnmatch.fnmatch(test_path, override['path_pattern']):
                        host_header_override = override['host_header']
                        break

            base_url = layer['host_url'].rstrip('/')
            parsed_url = urlparse(base_url)
            hostname = parsed_url.hostname
            scheme = parsed_url.scheme
            port = parsed_url.port

            # Calculate final Host header
            # 1. If explicitly overridden, use that.
            # 2. Else, use the hostname from the URL.
            final_host_header = host_header_override or hostname

            target_ip = hostname
            if self.dns_servers:
                target_ip = self.resolve_host(hostname)

            if target_ip != hostname:
                netloc = target_ip
                if port:
                    netloc += f":{port}"
                url_parts = list(parsed_url)
                url_parts[1] = netloc
                url_parts[2] = test_path
                url = urlunparse(url_parts)
            else:
                url = base_url + test_path

            headers = layer.get('custom_headers', {}).copy()
            headers['User-Agent'] = user_agent

            if target_ip != hostname or host_header_override:
                headers['Host'] = final_host_header

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
