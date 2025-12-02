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

# Now import the class to test
from src.nodegraph.graph_renderer import GraphRenderer
from src.node_data import NodeData

class TestGraphSearch(unittest.TestCase):
    def setUp(self):
        self.mock_node_graph = MagicMock()
        self.renderer = GraphRenderer(self.mock_node_graph)

        # Create a sample NodeData object
        # headers is a list of tuples: (key, value, change_type, note)
        self.node_data = NodeData(
            name="Test Node",
            headers=[
                ("Content-Type", "application/json", "UNCHANGED", ""),
                ("X-Custom-ID", "12345", "ADDED", "New ID")
            ]
        )

        self.node = {"data": self.node_data}

    def test_search_match_name(self):
        # Match by name
        self.assertTrue(self.renderer._is_match(self.node, "Test"))
        self.assertTrue(self.renderer._is_match(self.node, "test"))
        self.assertTrue(self.renderer._is_match(self.node, "Node"))

    def test_search_match_header_key(self):
        # Match by header key
        self.assertTrue(self.renderer._is_match(self.node, "Content-Type"))
        self.assertTrue(self.renderer._is_match(self.node, "content"))
        self.assertTrue(self.renderer._is_match(self.node, "X-Custom"))

    def test_search_match_header_value(self):
        # Match by header value
        self.assertTrue(self.renderer._is_match(self.node, "application/json"))
        self.assertTrue(self.renderer._is_match(self.node, "json"))
        self.assertTrue(self.renderer._is_match(self.node, "12345"))

    def test_search_no_match(self):
        # No match
        self.assertFalse(self.renderer._is_match(self.node, "NotFound"))
        self.assertFalse(self.renderer._is_match(self.node, "XML"))

    def test_empty_query(self):
        # Empty query should match everything (or return True as per implementation logic)
        self.assertTrue(self.renderer._is_match(self.node, ""))
        self.assertTrue(self.renderer._is_match(self.node, None))

if __name__ == '__main__':
    unittest.main()
