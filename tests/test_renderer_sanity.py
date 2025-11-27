
import unittest
from unittest.mock import MagicMock
from src.graph_renderer import GraphRenderer

class TestRendererSanity(unittest.TestCase):
    def test_methods_exist(self):
        node_graph = MagicMock()
        renderer = GraphRenderer(node_graph)

        self.assertTrue(hasattr(renderer, '_draw_inactive_node'))
        self.assertTrue(hasattr(renderer, '_draw_connection_label'))

    def test_inactive_node_logic(self):
        # Just check we can call it without error (mocking cairo)
        renderer = GraphRenderer(MagicMock())
        cr = MagicMock()
        node = {
            "x": 10, "y": 10, "width": 100, "height": 100,
            "data": MagicMock(header_color="rgba(0,0,0,0)", name="test", provider="test")
        }
        try:
            renderer._draw_inactive_node(cr, node, 10, 10, 100, 100, False)
        except Exception as e:
            self.fail(f"_draw_inactive_node raised exception: {e}")

if __name__ == '__main__':
    unittest.main()
