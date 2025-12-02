import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock gi for headless testing
sys.modules['gi'] = MagicMock()
sys.modules['gi.repository'] = MagicMock()
sys.modules['gi.repository.GLib'] = MagicMock()
sys.modules['gi.repository.GObject'] = MagicMock()
sys.modules['gi.repository.Adw'] = MagicMock()
sys.modules['gi.repository.Gtk'] = MagicMock()
sys.modules['gi.repository.Gio'] = MagicMock()
sys.modules['gi.repository.Gdk'] = MagicMock()
sys.modules['gi.repository.Pango'] = MagicMock()
sys.modules['gi.repository.PangoCairo'] = MagicMock()
sys.modules['cairo'] = MagicMock()

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

    @patch('requests.Session')
    def test_domain_match_routing(self, mock_session):
        self.config['layers'][0]['routing_rules'] = [
            {
                'domain_match': 'custom.domain.com',
                'backend_host': 'domain-backend.com'
            }
        ]
        # We need the entry point (or previous layer host) to match the domain
        self.config['entry_point'] = 'custom.domain.com'
        self.config['layers'][0]['host_url'] = 'custom.domain.com'

        # Re-init engine with new config
        self.engine = CacheFlowEngine(self.config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.return_value.get.return_value = mock_response
        self.engine.session = mock_session.return_value

        results = self.engine.run_inspection('/foo')

        self.assertEqual(len(results), 2)
        self.assertEqual(results[1]['name'], 'Backend')
        self.assertIn('domain-backend.com', results[1]['url'])

if __name__ == '__main__':
    unittest.main()
