import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock gi
sys.modules['gi'] = MagicMock()
sys.modules['gi.repository'] = MagicMock()
sys.modules['gi.repository.GLib'] = MagicMock()
sys.modules['gi.repository.GObject'] = MagicMock()
sys.modules['gi.repository.Adw'] = MagicMock()
sys.modules['gi.repository.Gtk'] = MagicMock()
sys.modules['gi.repository.Gio'] = MagicMock()
sys.modules['gi.repository.Gdk'] = MagicMock()
sys.modules['cairo'] = MagicMock()

from src.engine import CacheFlowEngine

class TestCookies(unittest.TestCase):
    def setUp(self):
        self.config = {
            'layers': [
                {'name': 'Layer1', 'host_url': 'example.com'}
            ]
        }
        self.engine = CacheFlowEngine(self.config)

    @patch('requests.Session')
    def test_cookie_extraction(self, mock_session):
        # Create a mock response with cookies
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}

        # Mock cookies
        cookie1 = MagicMock()
        cookie1.name = "session_id"
        cookie1.value = "12345"
        cookie1.domain = "example.com"
        cookie1.path = "/"
        cookie1.secure = True
        cookie1.expires = 1234567890
        # Mock get_nonstandard_attr
        def get_attr(name):
            if name == "SameSite": return "Strict"
            return None
        cookie1.get_nonstandard_attr.side_effect = get_attr

        # Mock has_nonstandard_attr
        def has_attr(name):
            if name == "HttpOnly": return True
            return False
        cookie1.has_nonstandard_attr.side_effect = has_attr

        mock_response.cookies = [cookie1]

        mock_session.return_value.get.return_value = mock_response
        self.engine.session = mock_session.return_value

        results = self.engine.run_inspection('/test')

        self.assertEqual(len(results), 1)
        cookies = results[0]['cookies']
        self.assertEqual(len(cookies), 1)
        self.assertEqual(cookies[0]['name'], 'session_id')
        self.assertEqual(cookies[0]['value'], '12345')
        self.assertEqual(cookies[0]['secure'], True)
        self.assertEqual(cookies[0]['http_only'], True)
        self.assertEqual(cookies[0]['same_site'], 'Strict')

if __name__ == '__main__':
    unittest.main()
