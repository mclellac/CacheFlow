import sys
import os
import unittest
from unittest.mock import MagicMock

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

from src.analysis.analyzer import HeaderAnalyzer

class TestTraceIdAnalysis(unittest.TestCase):
    def setUp(self):
        self.analyzer = HeaderAnalyzer()

    def test_trace_id_modification(self):
        upstream = {
            "name": "Upstream",
            "headers": {
                "x-request-id": "req-123",
                "content-type": "application/json"
            }
        }
        current = {
            "name": "Current",
            "headers": {
                "x-request-id": "req-456", # Changed
                "content-type": "application/json"
            }
        }

        report = self.analyzer.analyze_layer(current, upstream)

        # Find x-request-id item
        trace_item = next((item for item in report.items if item.key == "x-request-id"), None)
        self.assertIsNotNone(trace_item)
        self.assertEqual(trace_item.change_type, "MODIFIED")

        # Check for warning
        self.assertIn("Trace ID changed", trace_item.warning)

    def test_trace_id_removal(self):
        upstream = {
            "name": "Upstream",
            "headers": {
                "x-request-id": "req-123",
                "content-type": "application/json"
            }
        }
        current = {
            "name": "Current",
            "headers": {
                "content-type": "application/json"
                # x-request-id removed
            }
        }

        report = self.analyzer.analyze_layer(current, upstream)

        # Find x-request-id item
        trace_item = next((item for item in report.items if item.key == "x-request-id"), None)
        self.assertIsNotNone(trace_item)
        self.assertEqual(trace_item.change_type, "REMOVED")

        # Check for warning
        self.assertIn("Trace ID dropped", trace_item.warning)

if __name__ == '__main__':
    unittest.main()
