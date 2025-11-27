"""
This module defines the InspectionController, which manages the inspection
process in a separate thread to avoid blocking the UI.
"""

import logging
import threading
from typing import Callable, List, Dict, Any, Union

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
    ) -> List[List[NodeData]]:
        """Processes the raw results from the engine into NodeData objects.

        This method merges configuration data (like colors) and performs
        header analysis.

        Args:
            results: A list of raw result dictionaries from the engine.

        Returns:
            A list of list of NodeData objects (representing layers).
        """
        processed_layers: List[List[NodeData]] = []
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
            # However, with dynamic routing and dynamic backends, indices might mismatch if not careful.
            # But run_inspection returns results roughly in order of traversal.
            layer_config = config_layers[i] if i < len(config_layers) else {}

            # Active Node Data
            active_node_args = {
                "name": result.get("name"),
                "headers": formatted_headers,
                "request_url": result.get("request_url"),
                "request_host": result.get("request_host"),
                "request_method": result.get("request_method"),
                "provider": result.get("provider"),
                "layer_type": result.get("layer_type"),
                "upstream_layer": baseline_layer,
                "is_active": True,
                # Merge color properties from the layer's configuration (which should be merged in result already by engine)
                # But engine merges config into result dict, so we can use result directly if it has them
                # Or rely on layer_config.
                # Let's prefer result properties if they exist (engine merged active node props), fall back to layer_config
                "header_color": result.get("header_color") or layer_config.get("header_color"),
                "body_color": result.get("body_color") or layer_config.get("body_color"),
                "text_color": result.get("text_color") or layer_config.get("text_color"),
                "added_text_color": result.get("added_text_color") or layer_config.get("added_text_color"),
                "removed_text_color": result.get("removed_text_color") or layer_config.get("removed_text_color"),
                "modified_text_color": result.get("modified_text_color") or layer_config.get("modified_text_color"),
            }

            nodes_in_this_layer = [NodeData(**active_node_args)]

            # Process Siblings
            siblings = result.get("siblings", [])
            for sibling in siblings:
                 # Sibling nodes are inactive and have no headers/results
                sibling_args = {
                    "name": sibling.get("name", "Unknown"),
                    "headers": [], # No headers for inactive nodes
                    "provider": sibling.get("provider"),
                    "layer_type": result.get("layer_type"), # Same type as active
                    "is_active": False,
                    "header_color": sibling.get("header_color") or layer_config.get("header_color"),
                    "body_color": sibling.get("body_color") or layer_config.get("body_color"),
                    "text_color": layer_config.get("text_color"), # Use layer default for text
                }
                nodes_in_this_layer.append(NodeData(**sibling_args))

            processed_layers.append(nodes_in_this_layer)

        return processed_layers
