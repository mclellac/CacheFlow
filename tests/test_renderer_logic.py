import unittest
from unittest.mock import MagicMock
import sys

# Mock modules before importing GraphRenderer
sys.modules['gi'] = MagicMock()
sys.modules['gi.repository'] = MagicMock()
sys.modules['gi.repository.Adw'] = MagicMock()
sys.modules['gi.repository.Pango'] = MagicMock()
sys.modules['gi.repository.PangoCairo'] = MagicMock()
sys.modules['gi.repository.GLib'] = MagicMock()
sys.modules['gi.repository.Gdk'] = MagicMock()
sys.modules['cairo'] = MagicMock()

# Assuming NodeData is needed or we mock it structure
from src.nodegraph.graph_renderer import GraphRenderer

class TestGraphRenderer(unittest.TestCase):
    def test_node_matches_filter(self):
        renderer = GraphRenderer(MagicMock())

        node_data = MagicMock()
        node_data.name = "My Node"
        node_data.headers = [
            ("Content-Type", "application/json", "UNCHANGED", ""),
            ("X-Cache", "HIT", "ADDED", "")
        ]

        node = {"data": node_data}

        # Test case insensitive matching
        self.assertTrue(renderer._node_matches_filter(node, "node"))
        self.assertTrue(renderer._node_matches_filter(node, "json"))
        self.assertTrue(renderer._node_matches_filter(node, "cache"))
        self.assertTrue(renderer._node_matches_filter(node, "x-cache"))
        self.assertFalse(renderer._node_matches_filter(node, "miss"))

if __name__ == '__main__':
    unittest.main()
