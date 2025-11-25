import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.engine import CacheFlowEngine

class TestCacheFlowEngine(unittest.TestCase):
    def setUp(self):
        self.config = {
            'entry_point': 'example.com',
            'layers': [
                {
                    'name': 'CDN',
                    'host_url': 'example.com',
                    'routing_rules': [
                        {
                            'path_match': '/api/*',
                            'backend_host': 'api-backend.com',
                            'path_rewrite': 's/api/v1'
                        }
                    ]
                }
            ]
        }
        self.engine = CacheFlowEngine(self.config)

    @patch('requests.Session')
    def test_routing_rule_match(self, mock_session):
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Server': 'Mock'}
        mock_session.return_value.get.return_value = mock_response
        self.engine.session = mock_session.return_value

        results = self.engine.run_inspection('/api/test')

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['name'], 'CDN')
        self.assertEqual(results[1]['name'], 'Backend')
        self.assertIn('api-backend.com', results[1]['url'])
        self.assertIn('/v1/test', results[1]['url'])

    @patch('requests.Session')
    def test_default_backend_fallback(self, mock_session):
        self.config['layers'][0]['routing_rules'] = []
        self.config['layers'][0]['default_backend_host'] = 'default-backend.com'

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.return_value.get.return_value = mock_response
        self.engine.session = mock_session.return_value

        results = self.engine.run_inspection('/other')

        self.assertEqual(len(results), 2)
        self.assertEqual(results[1]['name'], 'Backend')
        self.assertIn('default-backend.com', results[1]['url'])
        self.assertIn('/other', results[1]['url'])

if __name__ == '__main__':
    unittest.main()
