"""
This module defines the main application window, managing the UI and
coordinating inspection tasks.
"""

import logging
import threading
from typing import Dict, Any, List, Tuple

from gi.repository import Gtk, Adw, Gio, GLib

from .node_graph import NodeGraph  # pylint: disable=unused-import
from .header_dialog import HeaderDialog
from .node_data import NodeData
from .analyzer import HeaderAnalyzer

log = logging.getLogger(__name__)


@Gtk.Template(filename='src/ui/main.ui')
class Window(Adw.ApplicationWindow):
    """The main application window."""
    __gtype_name__ = 'Window'

    path_entry = Gtk.Template.Child()
    env_label = Gtk.Template.Child()
    inspect_button = Gtk.Template.Child()
    node_graph = Gtk.Template.Child()
    spinner = Gtk.Template.Child()
    env_switcher = Gtk.Template.Child()
    content_stack = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        log.debug("Main window initialized.")
        self.settings = Gio.Settings.new('com.github.mclellac.CacheFlow')
        self.environments = ["production", "staging", "qa", "dev"]
        self.win_action_group = None
        self.env_model = None
        self.analyzer = HeaderAnalyzer()

        self.setup_actions()
        self.setup_env_switcher()
        self.setup_window_size()

        self.inspect_button.connect('clicked', self.on_inspect_clicked)
        self.path_entry.set_text(self.settings.get_string('test-path'))

        self.connect("close-request", self.on_close_request)
        self.node_graph.connect('node-double-clicked', self._on_node_double_clicked)

    def setup_window_size(self):
        """Restores the window size from settings."""
        width = self.settings.get_int('window-width')
        height = self.settings.get_int('window-height')

        if width > 0 and height > 0:
            self.set_default_size(width, height)

    def on_close_request(self, _window):
        """Saves window size before closing."""
        width = self.get_width()
        height = self.get_height()
        self.settings.set_int('window-width', width)
        self.settings.set_int('window-height', height)
        return False

    def _on_header_dialog_close(self, dialog):
        width = dialog.get_content_width()
        height = dialog.get_content_height()
        self.settings.set_int('header-dialog-width', width)
        self.settings.set_int('header-dialog-height', height)

    def _on_node_double_clicked(self, _, node):
        dialog = HeaderDialog(
            headers=node.get_property('headers'),
            heading=node.get_property('name')
        )
        width = self.settings.get_int('header-dialog-width')
        height = self.settings.get_int('header-dialog-height')
        if width > 0 and height > 0:
            dialog.set_content_width(width)
            dialog.set_content_height(height)
        dialog.connect('closed', self._on_header_dialog_close)
        dialog.connect('analyze-clicked', lambda d: self._on_analyze_requested(node))
        dialog.present(self)

    def _on_analyze_requested(self, node_data):
        # Extract current layer dict
        current_layer = {
            'name': node_data.name,
            'headers': {k: v for k, v, _, _ in node_data.headers}
        }

        # Find upstream layer
        nodes = [n['data'] for n in self.node_graph.nodes]
        upstream_layer = None
        try:
            idx = nodes.index(node_data)
            if idx < len(nodes) - 1:
                upstream_data = nodes[idx + 1]
                upstream_layer = {
                    'name': upstream_data.name,
                    'headers': {k: v for k, v, _, _ in upstream_data.headers}
                }
        except ValueError:
            log.warning("Node data not found in graph nodes.")

        # pylint: disable=import-outside-toplevel
        from .analysis_dialog import HeaderAnalysisDialog
        dialog = HeaderAnalysisDialog(current_layer, upstream_layer)
        dialog.present(self)

    def setup_actions(self):
        """Sets up window-scope actions."""
        self.win_action_group = Gio.SimpleActionGroup()
        self.insert_action_group("win", self.win_action_group)

        self.add_action("inspect", self.on_inspect_clicked)
        self.add_action("export-graph", self.on_export_graph_action)
        self.add_action("reset-layout", self.on_reset_layout_action)

    def on_export_graph_action(self, _action, _param):
        """Triggers the export graph dialog."""
        self.node_graph.show_export_dialog()

    def on_reset_layout_action(self, _action, _param):
        """Resets the node graph layout."""
        self.node_graph.reset_layout()

    def add_action(self, name, callback):
        """Helper to add an action to the window group."""
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.win_action_group.add_action(action)

    def setup_env_switcher(self):
        """Sets up the environment switcher dropdown."""
        self.env_model = Gtk.StringList.new(self.environments)
        self.env_switcher.set_model(self.env_model)

        active_env = self.settings.get_string('active-environment')
        if active_env in self.environments:
            self.env_switcher.set_selected(self.environments.index(active_env))
        else:
            self.env_switcher.set_selected(0)

        self.update_env_label(active_env)
        self.env_switcher.connect('notify::selected', self.on_env_selected)

    def on_env_selected(self, dropdown, _):
        """Callback when the environment selection changes."""
        selected_idx = dropdown.get_selected()
        new_env = self.environments[selected_idx]
        self.settings.set_string('active-environment', new_env)
        self.node_graph.set_data([])
        self.content_stack.set_visible_child_name("empty")
        self.update_env_label(new_env)

    def update_env_label(self, env_name):
        """Updates the environment label with the host URL."""
        config_key = f'config-{env_name}'
        layers_config = self.settings.get_value(config_key).unpack()
        if layers_config and len(layers_config) > 0:
            first_layer = layers_config[0]
            host_url = first_layer.get('host_url', 'No Host Configured')
            self.env_label.set_text(host_url)
        else:
            self.env_label.set_text("No Host Configured")

    def on_inspect_clicked(self, *_):
        """Callback for the inspect button."""
        log.info("Inspect button clicked.")
        path = self.path_entry.get_text()
        self.set_inspection_in_progress(True)
        if not path or not path.startswith('/'):
            error_msg = f"Invalid path for inspection: '{path}'"
            log.error(error_msg)
            self.show_error_dialog(
                "Invalid Input",
                "Path must not be empty and must start with '/'."
            )
            self.set_inspection_in_progress(False)
            return

        self.settings.set_string('test-path', path)

        active_env = self.settings.get_string('active-environment')
        config_key = f'config-{active_env}'
        layers_config = self.settings.get_value(config_key).unpack()
        if not layers_config:
            self.show_error_dialog(
                "Configuration Error",
                f"No layers configured for '{active_env}' environment."
            )
            self.set_inspection_in_progress(False)
            return

        config = {
            'layers': layers_config,
            'user_agent': self.settings.get_string('user-agent'),
            'dns_servers': self.settings.get_string('dns-servers'),
            'verify_ssl': self.settings.get_boolean('verify-ssl')
        }

        thread = threading.Thread(
            target=self.do_inspection_thread, args=(config, path)
        )
        thread.daemon = True
        thread.start()

    def do_inspection_thread(self, config: Dict[str, Any], path: str) -> None:
        """Executes the inspection in a background thread."""
        # pylint: disable=import-outside-toplevel
        from .engine import CacheFlowEngine
        log.debug("Starting inspection in background thread.")
        try:
            engine = CacheFlowEngine(config)
            results = engine.run_inspection(test_path=path)
            GLib.idle_add(
                self.on_inspection_succeeded, results, config['layers']
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            log.error("Exception in inspection thread: %s", e, exc_info=True)
            GLib.idle_add(self.on_inspection_failed, e)

    def on_inspection_succeeded(self, results: List[Dict[str, Any]],
                                layer_config: List[Dict[str, Any]]) -> bool:
        """Callback when inspection succeeds."""
        log.debug("Inspection succeeded, processing results.")
        self.process_and_display_results(results, layer_config)
        self.set_inspection_in_progress(False)
        return GLib.SOURCE_REMOVE

    def on_inspection_failed(self, exception: Exception) -> bool:
        """Callback when inspection fails."""
        log.error("Inspection task failed: %s", exception)
        self.show_error_dialog("Inspection Failed", str(exception))
        self.set_inspection_in_progress(False)
        return GLib.SOURCE_REMOVE

    def process_and_display_results(self, results: List[Dict[str, Any]],
                                    layer_config: List[Dict[str, Any]]) -> None:
        """Processes inspection results and updates the node graph."""
        log.debug("Processing inspection results for display.")
        processed_nodes = []

        if not results:
            self.node_graph.set_data([])
            self.content_stack.set_visible_child_name("empty")
            return

        for i, result in enumerate(results):
            node_data = self._create_node_data(result, i, results, layer_config)
            processed_nodes.append(node_data)

        self.node_graph.set_data(processed_nodes)
        self.content_stack.set_visible_child_name("graph")

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
                         all_results: List[Dict[str, Any]]) -> List[Tuple[str, str, bool, str]]:
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
            # Skip Removed and Missing for the node view
            if item.change_type in ("REMOVED", "MISSING"):
                continue

            is_diff = item.change_type in ("ADDED", "MODIFIED")
            note = item.description
            if item.warning:
                note = f"Warning: {item.warning} | {note}"

            headers_list.append((item.key, item.value, is_diff, note))

        return headers_list

    def set_inspection_in_progress(self, in_progress):
        """Toggles UI state during inspection."""
        self.inspect_button.set_sensitive(not in_progress)
        self.spinner.set_spinning(in_progress)
        self.spinner.set_visible(in_progress)

    def show_error_dialog(self, primary_text, secondary_text):
        """Displays an error dialog."""
        dialog = Adw.AlertDialog.new(primary_text, secondary_text)
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.set_close_response("ok")
        dialog.present(self)

    def show_toast(self, message: str) -> None:
        """Displays a toast notification."""
        toast = Adw.Toast.new(message)
        self.toast_overlay.add_toast(toast)
