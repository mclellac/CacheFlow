import requests
import fnmatch
import dns.resolver
import dns.exception
import warnings
import logging
from urllib.parse import urlparse

from urllib3.exceptions import InsecureRequestWarning
from .dns_adapter import DNSAdapter
warnings.simplefilter('ignore', InsecureRequestWarning)

log = logging.getLogger(__name__)

ERR_SSL = "SSL Error. The certificate may be invalid."
ERR_TIMEOUT = "Connection timed out to {}."
ERR_CONNECTION = "Connection refused by {}."

class CacheFlowEngine:
    def __init__(self, config):
        """
        Initialize with a configuration dictionary.
        Config includes 'layers', 'user_agent', 'test_path', optional 'dns_servers' and 'verify_ssl'.
        """
        self.config = config
        self.dns_servers = []
        self.verify_ssl = config.get('verify_ssl', False)
        log.debug("CacheFlowEngine initialized.")

        dns_config = self.config.get('dns_servers', '')
        if dns_config:
            self.dns_servers = [s.strip() for s in dns_config.split(',') if s.strip()]
            log.debug(f"Using custom DNS servers: {self.dns_servers}")

        self.session = requests.Session()
        self.dns_map = {}
        adapter = DNSAdapter(dns_map=self.dns_map)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)

    def resolve_host(self, hostname):
        if not self.dns_servers:
            return hostname

        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = self.dns_servers
            answers = resolver.resolve(hostname, 'A')
            if answers:
                ip = str(answers[0])
                log.debug(f"Resolved '{hostname}' to '{ip}'")
                return ip, None
            raise dns.resolver.NoAnswer(f"No A records found for {hostname}")
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.Timeout) as e:
            log.error(f"Custom DNS resolution failed for {hostname}: {e}")
            return hostname, e

    def run_inspection(self, test_path=None):
        log.info("Starting inspection run.")
        if test_path is None:
            test_path = self.config.get('test_path', '/')

        if not test_path.startswith('/'):
            test_path = '/' + test_path
        log.debug(f"Using test path: '{test_path}'")

        results = []
        user_agent = self.config.get('user_agent', 'CacheFlow/0.1.0')

        layers_to_inspect = self.config.get('layers', [])
        for i, layer in enumerate(layers_to_inspect):
            log.info(f"Processing layer: {layer.get('name')}")
            path_match_patterns = layer.get('path_match_only', []) if i < len(layers_to_inspect) - 1 else []
            if path_match_patterns:
                for pattern in path_match_patterns:
                    if fnmatch.fnmatch(test_path, pattern):
                        break
                else:
                    log.debug(f"Path '{test_path}' did not match any patterns. Skipping layer.")
                    continue

            host_header_override = layer.get('host_header')
            if 'host_overrides' in layer:
                for override in layer['host_overrides']:
                    if fnmatch.fnmatch(test_path, override['path_pattern']):
                        host_header_override = override['host_header']
                        break
            log.debug(f"Host header override is: '{host_header_override}'")

            base_url = layer['host_url'].rstrip('/')
            parsed_url = urlparse(base_url)
            hostname = parsed_url.hostname

            final_host_header = host_header_override or hostname

            # Resolve DNS if needed and update the adapter map
            target_ip = hostname
            dns_error = None
            if self.dns_servers:
                target_ip, dns_error = self.resolve_host(hostname)
                if not dns_error and target_ip != hostname:
                    self.dns_map[hostname] = target_ip
            
            if dns_error:
                results.append({
                    'name': layer['name'],
                    'error': f"DNS Error: {dns_error}",
                    'error_type': 'dns'
                })
                continue

            # Keep the original URL to preserve SNI and SSL verification
            url = base_url + test_path

            headers = layer.get('custom_headers', {}).copy()
            headers['User-Agent'] = user_agent

            # Set Host header if overridden
            if host_header_override:
                headers['Host'] = final_host_header

            log.debug(f"Request URL: {url}")
            log.debug(f"Request Headers: {headers}")
            try:
                response = self.session.get(url, headers=headers, timeout=10, stream=True, allow_redirects=False, verify=self.verify_ssl)
                response.close()

                layer_result = {
                    'name': layer['name'],
                    'description': layer.get('description', ''),
                    'status_code': response.status_code,
                    'headers': dict(response.headers)
                }
                log.debug(f"Request successful. Status: {response.status_code}")
            except requests.exceptions.SSLError as e:
                error_message = ERR_SSL
                log.error(f"Request failed for {url}: {error_message} - {e}")
                layer_result = {'name': layer['name'], 'error': error_message, 'error_type': 'ssl'}
            except requests.exceptions.ConnectTimeout as e:
                error_message = ERR_TIMEOUT.format(target_ip)
                log.error(f"Request failed for {url}: {error_message} - {e}")
                layer_result = {'name': layer['name'], 'error': error_message, 'error_type': 'timeout'}
            except requests.exceptions.ConnectionError as e:
                error_message = ERR_CONNECTION.format(target_ip)
                log.error(f"Request failed for {url}: {error_message} - {e}")
                layer_result = {'name': layer['name'], 'error': error_message, 'error_type': 'connection'}
            except Exception as e:
                error_message = str(e)
                log.error(f"An unexpected error occurred for {url}: {e}")
                layer_result = {
                    'name': layer['name'],
                    'error': error_message,
                    'error_type': 'unknown'
                }
            
            # Add common details to the result
            layer_result.update({
                'description': layer.get('description', ''),
                'url': url,
                'original_url': base_url + test_path,
                'sent_host_header': headers.get('Host'),
                'method': 'GET'
            })

            results.append(layer_result)

        return results
