"""
This module defines the InspectionController, which manages the inspection
process in a separate thread to avoid blocking the UI.
"""

import logging
import threading
from typing import Callable, List, Dict, Any

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
        """Initializes the InspectionController.

        Args:
            on_success: The callback function to call on success.
            on_error: The callback function to call on error.
        """
        self.on_success = on_success
        self.on_error = on_error
        self.analyzer = HeaderAnalyzer()
        self.config = None

    def start_inspection(self, config: dict, path: str):
        """Starts the inspection in a new thread.

        Args:
            config: The configuration for the inspection.
            path: The path to inspect.
        """
        self.config = config  # Store config for processing results
        thread = threading.Thread(
            target=self._run_inspection_thread, args=(config, path)
        )
        thread.daemon = True
        thread.start()

    def _run_inspection_thread(self, config: dict, path: str):
        """The target function for the inspection thread.

        Args:
            config: The configuration for the inspection.
            path: The path to inspect.
        """
        try:
            engine = CacheFlowEngine(config)
            results = engine.run_inspection(path)
            processed_nodes = self._process_results(results)
            GLib.idle_add(self.on_success, processed_nodes)
        except Exception as e:
            log.exception("An error occurred during inspection.")
            GLib.idle_add(self.on_error, e)

    def _process_results(
        self, results: List[Dict[str, Any]]
    ) -> List[NodeData]:
        """Processes the raw results from the engine into NodeData objects.

        This method merges configuration data (like colors) and performs
        header analysis.

        Args:
            results: A list of raw result dictionaries from the engine.

        Returns:
            A list of NodeData objects.
        """
        processed_nodes: List[NodeData] = []
        config_layers: List[Dict[str, Any]] = self.config.get("layers", [])

        for i, result in enumerate(results):
            # The analyzer needs the raw headers dict.
            raw_headers = result.get("headers", {})
            log.debug(
                "Processing results for layer '%s'. Headers count: %d",
                result.get("name"),
                len(raw_headers),
            )
            log.debug(
                "Raw headers for '%s': %s", result.get("name"), raw_headers
            )

            current_layer_for_analysis = {
                "name": result.get("name"),
                "headers": raw_headers,
            }

            # Identify the next layer (which is technically upstream in the request flow)
            # to serve as the baseline for comparison.
            baseline_layer = None
            if i + 1 < len(results):
                next_result = results[i + 1]
                baseline_layer = {
                    "name": next_result.get("name"),
                    "headers": next_result.get("headers", {}),
                }

            # Analyze the headers against the baseline (next) layer.
            # If baseline is None (last layer), all headers are treated as ADDED/original.
            report = self.analyzer.analyze_layer(
                current_layer=current_layer_for_analysis,
                upstream_layer=baseline_layer,
                is_edge=(i == 0),
            )

            # Convert the analysis report into the 4-tuple format required by NodeData.
            formatted_headers = [
                (item.key, item.value, item.change_type, item.description)
                for item in report.items
            ]
            log.debug(
                "Formatted headers for '%s': %d items",
                result.get("name"),
                len(formatted_headers),
            )

            # Find the corresponding layer in the original config to get UI settings.
            # This assumes the order of results matches the order of layers.
            layer_config = config_layers[i] if i < len(config_layers) else {}

            # Create the final dictionary for NodeData, merging results and config.
            node_args = {
                "name": result.get("name"),
                "headers": formatted_headers,
                "request_url": result.get("request_url"),
                "request_host": result.get("request_host"),
                "request_method": result.get("request_method"),
                "provider": result.get("provider"),
                "layer_type": result.get("layer_type"),
                "upstream_layer": baseline_layer,
                # Merge color properties from the layer's configuration
                "header_color": layer_config.get("header_color"),
                "body_color": layer_config.get("body_color"),
                "text_color": layer_config.get("text_color"),
                "added_text_color": layer_config.get("added_text_color"),
                "removed_text_color": layer_config.get("removed_text_color"),
                "modified_text_color": layer_config.get("modified_text_color"),
            }

            node_data = NodeData(**node_args)
            processed_nodes.append(node_data)

        return processed_nodes
