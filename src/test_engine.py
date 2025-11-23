import unittest
from unittest.mock import MagicMock, patch
import yaml
import os
from engine import CacheFlowEngine

class TestCacheFlowEngine(unittest.TestCase):
    def setUp(self):
        self.config = {
            'user_agent': 'TestAgent',
            'test_path': '/default',
            'layers': [
                {
                    'name': 'Layer1',
                    'host_url': 'http://layer1.com',
                    'custom_headers': {'H1': 'V1'}
                },
                {
                    'name': 'Layer2',
                    'host_url': 'http://layer2.com',
                    'host_overrides': [
                        {
                            'path_pattern': '/override*',
                            'host_header': 'override.com'
                        }
                    ]
                }
            ]
        }
        # No need to write config file anymore, passing dict directly

    def tearDown(self):
        pass

    @patch('engine.requests.get')
    def test_run_inspection_default(self, mock_get):
        # Mock response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {'Server': 'TestServer'}
        mock_get.return_value = mock_resp

        # Initialize with dict
        engine = CacheFlowEngine(self.config)
        results = engine.run_inspection()

        self.assertEqual(len(results), 2)

        # Check first layer call
        # It should use default path /default
        self.assertEqual(mock_get.call_args_list[0].args[0], 'http://layer1.com/default')
        headers1 = mock_get.call_args_list[0].kwargs['headers']
        self.assertEqual(headers1['User-Agent'], 'TestAgent')
        self.assertEqual(headers1['H1'], 'V1')

        # Check second layer call
        self.assertEqual(mock_get.call_args_list[1].args[0], 'http://layer2.com/default')

    @patch('engine.requests.get')
    def test_run_inspection_override(self, mock_get):
        # Mock response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {}
        mock_get.return_value = mock_resp

        engine = CacheFlowEngine(self.config)
        results = engine.run_inspection('/override/test')

        self.assertEqual(len(results), 2)

        # Check second layer call for host override
        # URL construction: http://layer2.com/override/test
        self.assertEqual(mock_get.call_args_list[1].args[0], 'http://layer2.com/override/test')
        headers2 = mock_get.call_args_list[1].kwargs['headers']
        self.assertEqual(headers2['Host'], 'override.com')

    @patch('engine.dns.resolver.Resolver')
    @patch('engine.requests.get')
    def test_dns_resolution(self, mock_get, mock_resolver):
        # Configure DNS
        self.config['dns_servers'] = '8.8.8.8'

        # Mock DNS response
        mock_answer = MagicMock()
        mock_answer.__str__.return_value = '1.2.3.4'

        mock_inst = mock_resolver.return_value
        mock_inst.resolve.return_value = [mock_answer]

        # Mock HTTP response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        engine = CacheFlowEngine(self.config)
        results = engine.run_inspection()

        # Check that DNS resolver was called
        mock_inst.resolve.assert_any_call('layer1.com', 'A')

        # Check that request used the IP
        # URL for Layer1 should be http://1.2.3.4/default with Host: layer1.com
        self.assertEqual(mock_get.call_args_list[0].args[0], 'http://1.2.3.4/default')
        headers = mock_get.call_args_list[0].kwargs['headers']
        self.assertEqual(headers['Host'], 'layer1.com')

if __name__ == '__main__':
    unittest.main()
