"""
This module manages the inspection execution and result processing.
"""

import threading
import logging
from typing import Dict, Any, List, Callable
from gi.repository import GLib

from .engine import CacheFlowEngine
from .node_data import NodeData
from .analyzer import HeaderAnalyzer

log = logging.getLogger(__name__)

class InspectionController:
    """
    Coordinates inspection tasks and processes results for the UI.
    """

    def __init__(self, on_success: Callable, on_error: Callable):
        self.on_success = on_success
        self.on_error = on_error
        self.analyzer = HeaderAnalyzer()

    def start_inspection(self, config: Dict[str, Any], path: str):
        """Starts the inspection in a background thread."""
        thread = threading.Thread(
            target=self._do_inspection_thread, args=(config, path)
        )
        thread.daemon = True
        thread.start()

    def _do_inspection_thread(self, config: Dict[str, Any], path: str) -> None:
        """Executes the inspection in a background thread."""
        log.debug("Starting inspection in background thread.")
        try:
            engine = CacheFlowEngine(config)
            results = engine.run_inspection(test_path=path)

            # Process results into NodeData here?
            # Or pass raw results back to UI?
            # Passing raw results and letting UI decide presentation might be more flexible,
            # but processing here keeps Window cleaner.
            # Let's process here.

            processed_nodes = self._process_results(results, config['layers'])

            GLib.idle_add(
                self.on_success, processed_nodes
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            log.error("Exception in inspection thread: %s", e, exc_info=True)
            GLib.idle_add(self.on_error, e)

    def _process_results(self, results: List[Dict[str, Any]],
                         layer_config: List[Dict[str, Any]]) -> List[NodeData]:
        """Processes inspection results into NodeData objects."""
        log.debug("Processing inspection results.")
        processed_nodes = []

        for i, result in enumerate(results):
            node_data = self._create_node_data(result, i, results, layer_config)
            processed_nodes.append(node_data)

        return processed_nodes

    def _create_node_data(self, result: Dict[str, Any], index: int,
                          all_results: List[Dict[str, Any]],
                          layer_config: List[Dict[str, Any]]) -> NodeData:
        original_layer = next(
            (layer for layer in layer_config if layer.get('name') == result.get('name')),
            {}
        )

        headers_list = []
        if 'error' in result:
            error_type = result.get('error_type', 'unknown').capitalize()
            error_message = result['error']
            headers_list.append((f"Error ({error_type})", error_message, True, ""))
            log.warning("Layer '%s' resulted in an error: %s",
                        result.get('name'), result['error'])
        else:
            headers_list = self._compare_headers(result, index, all_results)

        return NodeData(
            name=result['name'],
            headers=headers_list,
            body_color=original_layer.get('body_color', ''),
            header_color=original_layer.get('header_color', ''),
            text_color=original_layer.get('text_color', ''),
            diff_text_color=original_layer.get('diff_text_color', ''),
            request_url=result.get('url'),
            request_host=result.get('sent_host_header'),
            request_method=result.get('method', 'GET')
        )

    def _compare_headers(self, result: Dict[str, Any], index: int,
                         all_results: List[Dict[str, Any]]) -> List[Any]:
        current_layer = {'name': result['name'], 'headers': result['headers']}
        upstream_layer = None

        if index < len(all_results) - 1:
            upstream_result = all_results[index+1]
            if 'headers' in upstream_result:
                upstream_layer = {
                    'name': upstream_result['name'],
                    'headers': upstream_result['headers']
                }

        report = self.analyzer.analyze_layer(current_layer, upstream_layer)

        headers_list = []
        for item in report.items:
            # Skip Removed and Missing for the node view (graph only shows what IS present)
            if item.change_type in ("REMOVED", "MISSING"):
                continue

            is_diff = item.change_type in ("ADDED", "MODIFIED")
            note = item.description
            if item.warning:
                note = f"Warning: {item.warning} | {note}"

            headers_list.append((item.key, item.value, is_diff, note))

        return headers_list
