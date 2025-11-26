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
        upstream_layer_for_analysis = None  # Stores the dict format for the analyzer

        for result in results:
            node_data = NodeData(**result)

            if upstream_layer_for_analysis:
                # Compare with the previous layer to get diff-annotated headers.
                formatted_headers = self.analyzer.compare_headers(
                    upstream_layer_for_analysis,
                    {'name': node_kwargs.get('name'), 'headers': raw_headers}
                )
                node_kwargs['upstream_layer'] = upstream_layer_for_analysis
            else:
                # First layer: just convert the raw dict to the standard tuple format.
                formatted_headers = [(k, v, False, '') for k, v in raw_headers.items()]

            # Create the NodeData object with correctly formatted headers.
            node_data = NodeData(name=node_kwargs.pop('name', 'Unnamed'),
                                 headers=formatted_headers,
                                 **node_kwargs)
            processed_nodes.append(node_data)

            # Prepare the upstream layer for the next iteration's analysis.
            upstream_layer_for_analysis = {
                'name': node_data.name,
                'headers': raw_headers  # Use original raw headers for the next comparison.
            }

        return processed_nodes
