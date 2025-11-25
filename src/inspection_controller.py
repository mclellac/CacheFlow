"""
This module defines the InspectionController, which manages the inspection
process in a separate thread to avoid blocking the UI.
"""

import logging
import threading
from typing import Callable, List

from gi.repository import GLib

from .engine import CacheFlowEngine
from .node_data import NodeData
from .analyzer import HeaderAnalyzer

log = logging.getLogger(__name__)


class InspectionController:
    """
    Manages the inspection process in a separate thread.
    """

    def __init__(self, on_success: Callable, on_error: Callable):
        self.on_success = on_success
        self.on_error = on_error
        self.analyzer = HeaderAnalyzer()

    def start_inspection(self, config: dict, path: str):
        """Starts the inspection in a new thread."""
        thread = threading.Thread(target=self._run_inspection_thread,
                                  args=(config, path))
        thread.daemon = True
        thread.start()

    def _run_inspection_thread(self, config: dict, path: str):
        """The target function for the inspection thread."""
        try:
            engine = CacheFlowEngine(config)
            results = engine.run_inspection(path)
            processed_nodes = self._process_results(results)
            GLib.idle_add(self.on_success, processed_nodes)
        except Exception as e:
            log.exception("An error occurred during inspection.")
            GLib.idle_add(self.on_error, e)

    def _process_results(self, results: List[dict]) -> List[NodeData]:
        """
        Processes the raw results from the engine into a list of NodeData objects,
        including header analysis.
        """
        processed_nodes = []
        upstream_layer = None

        for result in results:
            node_data = NodeData.from_dict(result)

            if upstream_layer:
                # Compare current layer with the immediate upstream layer
                comparison_results = self.analyzer.compare_headers(
                    upstream_layer,
                    {
                        'name': node_data.name,
                        'headers': {k: v for k, v, _, _ in node_data.headers}
                    }
                )
                # Update headers in node_data with notes from the analysis
                node_data.headers = comparison_results
                node_data.upstream_layer = upstream_layer

            processed_nodes.append(node_data)

            # Update upstream_layer for the next iteration
            # Convert NodeData back to a dict format expected by analyzer
            upstream_layer = {
                'name': node_data.name,
                'headers': {k: v for k, v, _, _ in node_data.headers}
            }

        return processed_nodes
