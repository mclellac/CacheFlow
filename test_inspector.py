import unittest
from unittest.mock import MagicMock, patch
import yaml
import os
from inspector import HeaderInspector

class TestHeaderInspector(unittest.TestCase):
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
        with open('test_config.yaml', 'w') as f:
            yaml.dump(self.config, f)

    def tearDown(self):
        if os.path.exists('test_config.yaml'):
            os.remove('test_config.yaml')

    @patch('inspector.requests.get')
    def test_run_inspection_default(self, mock_get):
        # Mock response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {'Server': 'TestServer'}
        mock_get.return_value = mock_resp

        inspector = HeaderInspector('test_config.yaml')
        results = inspector.run_inspection()

        self.assertEqual(len(results), 2)

        # Check first layer call
        # It should use default path /default
        self.assertEqual(mock_get.call_args_list[0].args[0], 'http://layer1.com/default')
        headers1 = mock_get.call_args_list[0].kwargs['headers']
        self.assertEqual(headers1['User-Agent'], 'TestAgent')
        self.assertEqual(headers1['H1'], 'V1')

        # Check second layer call
        self.assertEqual(mock_get.call_args_list[1].args[0], 'http://layer2.com/default')

    @patch('inspector.requests.get')
    def test_run_inspection_override(self, mock_get):
        # Mock response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {}
        mock_get.return_value = mock_resp

        inspector = HeaderInspector('test_config.yaml')
        results = inspector.run_inspection('/override/test')

        self.assertEqual(len(results), 2)

        # Check second layer call for host override
        # URL construction: http://layer2.com/override/test
        self.assertEqual(mock_get.call_args_list[1].args[0], 'http://layer2.com/override/test')
        headers2 = mock_get.call_args_list[1].kwargs['headers']
        self.assertEqual(headers2['Host'], 'override.com')

if __name__ == '__main__':
    unittest.main()
