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
            # The analyzer needs the raw headers dict.
            current_layer_for_analysis = {
                'name': result.get('name'),
                'headers': result.get('headers', {})
            }

            # Analyze the headers against the previous (upstream) layer.
            report = self.analyzer.analyze_layer(
                current_layer=current_layer_for_analysis,
                upstream_layer=upstream_layer_for_analysis
            )

            # Convert the analysis report into the 4-tuple format required by NodeData.
            # The change_type string is now passed directly.
            formatted_headers = [
                (
                    item.key,
                    item.value,
                    item.change_type,
                    item.description
                )
                for item in report.items
            ]

            # Update the result with the processed headers before creating NodeData.
            result['headers'] = formatted_headers
            if upstream_layer_for_analysis:
                result['upstream_layer'] = upstream_layer_for_analysis

            node_data = NodeData(**result)
            processed_nodes.append(node_data)

            # The current layer becomes the upstream layer for the next iteration.
            upstream_layer_for_analysis = current_layer_for_analysis

        return processed_nodes
