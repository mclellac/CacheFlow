"""
This module defines the main application window, managing the UI and
coordinating inspection tasks.
"""

import logging
from typing import List

from gi.repository import Gtk, Adw, Gio, GLib

from .node_graph import NodeGraph  # pylint: disable=unused-import
from .header_dialog import HeaderDialog
from .node_data import NodeData
from .analyzer import HeaderAnalyzer
from .analysis_dialog import HeaderAnalysisDialog
from .inspection_controller import InspectionController
from .config_manager import ConfigManager

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
    config_switcher = Gtk.Template.Child()
    content_stack = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        log.debug("Main window initialized.")
        self.settings = Gio.Settings.new('com.github.mclellac.CacheFlow')
        self.config_manager = ConfigManager(self.settings)
        self.win_action_group = None
        self.config_model = None
        self.analyzer = HeaderAnalyzer()
        self.controller = InspectionController(
            on_success=self.on_inspection_succeeded,
            on_error=self.on_inspection_failed
        )

        self.setup_actions()
        self.setup_config_switcher()
        self.setup_window_size()

        self.inspect_button.connect('clicked', self.on_inspect_clicked)
        self.path_entry.set_text(self.settings.get_string('test-path'))

        self.connect("close-request", self.on_close_request)
        self.node_graph.connect('node-double-clicked', self._on_node_double_clicked)

        # Listen for setting changes (e.g. from Preferences) to refresh switcher
        self.settings.connect('changed::configurations', self.on_configurations_changed)

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

    def _on_header_window_close(self, win):
        width, height = win.get_default_size()
        self.settings.set_int('header-dialog-width', width)
        self.settings.set_int('header-dialog-height', height)

    def _on_node_double_clicked(self, _, node):
        win = HeaderDialog(
            headers=node.get_property('headers'),
            heading=node.get_property('name'),
            node_data=node,
            application=self.get_application()
        )
        width = self.settings.get_int('header-dialog-width')
        height = self.settings.get_int('header-dialog-height')
        if width > 0 and height > 0:
            win.set_default_size(width, height)

        win.connect('close-request', self._on_header_window_close)
        win.connect('analyze-clicked', self._on_analyze_clicked, node)
        win.present()

    def _on_analyze_clicked(self, header_dialog, node_data):
        """Handles the analyze-clicked signal from the HeaderDialog."""
        self._on_analyze_requested(node_data, header_dialog)

    def _on_analyze_requested(self, node_data, parent_win):
        # Extract current layer dict
        current_layer = {
            'name': node_data.name,
            'headers': {k: v for k, v, _, _ in node_data.headers}
        }

        # Upstream layer is now attached to node_data
        upstream_layer = node_data.upstream_layer

        dialog = HeaderAnalysisDialog(current_layer,
                                      upstream_layer,
                                      transient_for=parent_win,
                                      modal=True)
        dialog.present()

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

    def setup_config_switcher(self):
        """Sets up the configuration switcher dropdown."""
        configs = self.config_manager.get_configurations()
        self.config_ids = [c['id'] for c in configs]
        names = [c['name'] for c in configs]

        self.config_model = Gtk.StringList.new(names)
        self.config_switcher.set_model(self.config_model)

        active_id = self.settings.get_string('active-config-id')
        if active_id in self.config_ids:
            idx = self.config_ids.index(active_id)
            self.config_switcher.set_selected(idx)
        elif configs:
            self.config_switcher.set_selected(0)
            self.settings.set_string('active-config-id', configs[0]['id'])
            active_id = configs[0]['id']

        self.update_env_label(active_id)
        self.config_switcher.connect('notify::selected', self.on_config_selected)

    def on_configurations_changed(self, _settings, _key):
        """Callback when configurations change in GSettings."""
        # Re-setup switcher
        # We need to preserve selection if possible or respect new active ID
        # For simplicity, just re-run setup
        self.setup_config_switcher()

    def on_config_selected(self, dropdown, _):
        """Callback when the configuration selection changes."""
        idx = dropdown.get_selected()
        if idx < 0 or idx >= len(self.config_ids):
            return

        new_id = self.config_ids[idx]
        self.settings.set_string('active-config-id', new_id)
        self.node_graph.set_data([])
        self.content_stack.set_visible_child_name("empty")
        self.update_env_label(new_id)

    def update_env_label(self, config_id):
        """Updates the environment label with the entry point."""
        config = self.config_manager.get_configuration(config_id)
        if config:
            self.env_label.set_text(config.get('entry_point', 'No Host Configured'))
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

        active_id = self.settings.get_string('active-config-id')
        config_data = self.config_manager.get_configuration(active_id)

        if not config_data or not config_data.get('layers'):
            self.show_error_dialog(
                "Configuration Error",
                "No layers configured for current domain."
            )
            self.set_inspection_in_progress(False)
            return

        layers_config = config_data.get('layers', [])

        config = {
            'layers': layers_config,
            'entry_point': config_data.get('entry_point', ''),
            'user_agent': self.settings.get_string('user-agent'),
            'dns_servers': self.settings.get_string('dns-servers'),
            'verify_ssl': self.settings.get_boolean('verify-ssl')
        }

        self.controller.start_inspection(config, path)

    def on_inspection_succeeded(self, processed_nodes: List[NodeData]) -> bool:
        """Callback when inspection succeeds."""
        log.debug("Inspection succeeded, displaying results.")

        if not processed_nodes:
            self.node_graph.set_data([])
            self.content_stack.set_visible_child_name("empty")
        else:
            self.node_graph.set_data(processed_nodes)
            self.content_stack.set_visible_child_name("graph")

        self.set_inspection_in_progress(False)
        return GLib.SOURCE_REMOVE

    def on_inspection_failed(self, exception: Exception) -> bool:
        """Callback when inspection fails."""
        log.error("Inspection task failed: %s", exception)
        self.show_error_dialog("Inspection Failed", str(exception))
        self.set_inspection_in_progress(False)
        return GLib.SOURCE_REMOVE

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
