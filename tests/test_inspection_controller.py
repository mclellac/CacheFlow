import sys
import os
import unittest
from unittest.mock import MagicMock

# Mock gi before importing modules that use it
sys.modules["gi"] = MagicMock()
sys.modules["gi.repository"] = MagicMock()

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.inspection_controller import InspectionController

class TestInspectionController(unittest.TestCase):
    def test_process_results_logic(self):
        controller = InspectionController(lambda x: None, lambda x: None)
        controller.config = {"layers": [{}, {}, {}]} # Mock config

        # Mock results: Akamai -> Webfarm -> Origin
        # Origin (Base) has "Server: Nginx"
        # Webfarm (Proxy) has "Server: Nginx" and "X-Webfarm: 1"
        # Akamai (CDN) has "Server: Akamai" and "X-Webfarm: 1"

        results = [
            {
                "name": "Akamai",
                "headers": {"Server": "Akamai", "X-Webfarm": "1"}
            },
            {
                "name": "Webfarm",
                "headers": {"Server": "Nginx", "X-Webfarm": "1"}
            },
            {
                "name": "Origin",
                "headers": {"Server": "Nginx"}
            }
        ]

        nodes = controller._process_results(results)

        # Verify Origin (Last Node)
        # Should compare vs None. All headers ADDED/Original.
        origin = nodes[2]
        self.assertEqual(origin.name, "Origin")
        # Find header tuple: (key, value, change_type, note)
        server_header = next(h for h in origin.headers if h[0] == "Server")
        self.assertEqual(server_header[2], "ADDED") # Change type

        # Verify Webfarm (Middle Node)
        # Should compare vs Origin.
        # Server: Nginx vs Nginx -> UNCHANGED
        # X-Webfarm: 1 vs (Missing) -> ADDED
        webfarm = nodes[1]
        self.assertEqual(webfarm.name, "Webfarm")
        server_header = next(h for h in webfarm.headers if h[0] == "Server")
        self.assertEqual(server_header[2], "UNCHANGED")
        x_header = next(h for h in webfarm.headers if h[0] == "X-Webfarm")
        self.assertEqual(x_header[2], "ADDED")

        # Verify Akamai (First Node)
        # Should compare vs Webfarm.
        # Server: Akamai vs Nginx -> MODIFIED
        # X-Webfarm: 1 vs 1 -> UNCHANGED
        akamai = nodes[0]
        self.assertEqual(akamai.name, "Akamai")
        server_header = next(h for h in akamai.headers if h[0] == "Server")
        self.assertEqual(server_header[2], "MODIFIED")
        x_header = next(h for h in akamai.headers if h[0] == "X-Webfarm")
        self.assertEqual(x_header[2], "UNCHANGED")

if __name__ == '__main__':
    unittest.main()
