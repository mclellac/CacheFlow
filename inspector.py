import yaml
import requests
import fnmatch
from urllib.parse import urljoin

class HeaderInspector:
    def __init__(self, config_path):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

    def run_inspection(self, test_path=None):
        if test_path is None:
            test_path = self.config.get('test_path', '/')

        # Ensure test_path starts with /
        if not test_path.startswith('/'):
            test_path = '/' + test_path

        results = []
        user_agent = self.config.get('user_agent', 'HTTP-Header-Inspector')

        for layer in self.config.get('layers', []):
            # Check path match if applicable
            if 'path_match_only' in layer:
                matched = False
                for pattern in layer['path_match_only']:
                    if fnmatch.fnmatch(test_path, pattern):
                        matched = True
                        break
                if not matched:
                    # Skip this layer
                    continue

            # Determine Host header
            host_header = layer.get('host_header') # Default for layer
            if 'host_overrides' in layer:
                for override in layer['host_overrides']:
                    if fnmatch.fnmatch(test_path, override['path_pattern']):
                        host_header = override['host_header']
                        break

            # Prepare Request
            base_url = layer['host_url'].rstrip('/')
            url = base_url + test_path

            headers = layer.get('custom_headers', {}).copy()
            headers['User-Agent'] = user_agent
            if host_header:
                headers['Host'] = host_header

            # Make Request
            try:
                # requests automatically handles redirects by default.
                # We might want to see the headers of the immediate response.
                # allow_redirects=False is probably better for inspecting specific infrastructure layers.
                response = requests.get(url, headers=headers, timeout=10, stream=True, allow_redirects=False)
                response.close()

                layer_result = {
                    'name': layer['name'],
                    'description': layer.get('description', ''),
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'url': url,
                    'sent_host_header': host_header
                }
            except Exception as e:
                layer_result = {
                    'name': layer['name'],
                    'description': layer.get('description', ''),
                    'error': str(e),
                    'url': url,
                    'sent_host_header': host_header
                }

            results.append(layer_result)

        return results
