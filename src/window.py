import logging
import threading

import gi
from gi.repository import Gtk, Adw, Gio, GLib

from .node_graph import NodeGraph
from .header_dialog import HeaderDialog
from .node_data import NodeData

log = logging.getLogger(__name__)


@Gtk.Template(filename='src/ui/main.ui')
class Window(Adw.ApplicationWindow):
    __gtype_name__ = 'Window'

    path_entry = Gtk.Template.Child()
    inspect_button = Gtk.Template.Child()
    node_graph = Gtk.Template.Child()
    spinner = Gtk.Template.Child()
    env_switcher = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        log.debug("Main window initialized.")
        self.settings = Gio.Settings.new('com.github.mclellac.CacheFlow')
        self.environments = ["production", "staging", "qa", "dev"]

        self.setup_actions()
        self.setup_env_switcher()
        self.setup_window_size()

        self.inspect_button.connect('clicked', self.on_inspect_clicked)
        self.path_entry.set_text(self.settings.get_string('test-path'))

        self.connect("close-request", self.on_close_request)
        self.node_graph.connect('node-double-clicked', self._on_node_double_clicked)

    def setup_window_size(self):
        width = self.settings.get_int('window-width')
        height = self.settings.get_int('window-height')

        if width > 0 and height > 0:
            self.set_default_size(width, height)

    def on_close_request(self, window):
        width = self.get_width()
        height = self.get_height()
        self.settings.set_int('window-width', width)
        self.settings.set_int('window-height', height)
        return False

    def _on_header_dialog_close(self, dialog):
        width = dialog.get_width()
        height = dialog.get_height()
        self.settings.set_int('header-dialog-width', width)
        self.settings.set_int('header-dialog-height', height)

    def _on_node_double_clicked(self, _, node):
        dialog = HeaderDialog(
            headers=node.get_property('headers'),
            heading=node.get_property('name'),
            transient_for=self,
            modal=True
        )
        dialog.set_default_size(self.settings.get_int('header-dialog-width'), self.settings.get_int('header-dialog-height'))
        dialog.set_resizable(True)
        dialog.connect('close-request', self._on_header_dialog_close)
        dialog.present()

    def setup_actions(self):
        self.win_action_group = Gio.SimpleActionGroup()
        self.insert_action_group("win", self.win_action_group)

        self.add_action("inspect", self.on_inspect_clicked)

    def add_action(self, name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.win_action_group.add_action(action)

    def setup_env_switcher(self):
        self.env_model = Gtk.StringList.new(self.environments)
        self.env_switcher.set_model(self.env_model)

        active_env = self.settings.get_string('active-environment')
        if active_env in self.environments:
            self.env_switcher.set_selected(self.environments.index(active_env))
        else:
            self.env_switcher.set_selected(0)

        self.env_switcher.connect('notify::selected', self.on_env_selected)

    def on_env_selected(self, dropdown, _):
        selected_idx = dropdown.get_selected()
        new_env = self.environments[selected_idx]
        self.settings.set_string('active-environment', new_env)
        self.node_graph.set_data([])

    def on_inspect_clicked(self, _):
        log.info("Inspect button clicked.")
        path = self.path_entry.get_text()
        self.set_inspection_in_progress(True)
        if not path or not path.startswith('/'):
            error_msg = f"Invalid path for inspection: '{path}'"
            log.error(error_msg)
            self.show_error_dialog("Invalid Input", "Path must not be empty and must start with '/'.")
            self.set_inspection_in_progress(False)
            return

        self.settings.set_string('test-path', path)

        active_env = self.settings.get_string('active-environment')
        config_key = f'config-{active_env}'
        layers_config = self.settings.get_value(config_key).unpack()
        if not layers_config:
            self.show_error_dialog("Configuration Error", f"No layers configured for '{active_env}' environment.")
            self.set_inspection_in_progress(False)
            return

        config = {
            'layers': layers_config,
            'user_agent': self.settings.get_string('user-agent'),
            'dns_servers': self.settings.get_string('dns-servers'),
            'verify_ssl': self.settings.get_boolean('verify-ssl')
        }
        
        thread = threading.Thread(target=self.do_inspection_thread, args=(config, path))
        thread.daemon = True
        thread.start()

    def do_inspection_thread(self, config, path):
        from .engine import CacheFlowEngine
        log.debug("Starting inspection in background thread.")
        try:
            engine = CacheFlowEngine(config)
            results = engine.run_inspection(test_path=path)
            GLib.idle_add(self.on_inspection_succeeded, results, config['layers'])
        except Exception as e:
            log.error(f"Exception in inspection thread: {e}", exc_info=True)
            GLib.idle_add(self.on_inspection_failed, e)

    def on_inspection_succeeded(self, results, layer_config):
        log.debug("Inspection succeeded, processing results.")
        self.process_and_display_results(results, layer_config)
        self.set_inspection_in_progress(False)
        return GLib.SOURCE_REMOVE

    def on_inspection_failed(self, exception):
        log.error(f"Inspection task failed: {exception}")
        self.show_error_dialog("Inspection Failed", str(exception))
        self.set_inspection_in_progress(False)
        return GLib.SOURCE_REMOVE

    def process_and_display_results(self, results, layer_config):
        log.debug("Processing inspection results for display.")
        processed_nodes = []

        if not results:
            self.node_graph.set_data([])
            return

        for i, result in enumerate(results):
            node_data = self._create_node_data(result, i, results, layer_config)
            processed_nodes.append(node_data)

        self.node_graph.set_data(processed_nodes)

    def _create_node_data(self, result, index, all_results, layer_config):
        original_layer = next((layer for layer in layer_config if layer.get('name') == result.get('name')), {})

        headers_list = []
        if 'error' in result:
            error_type = result.get('error_type', 'unknown').capitalize()
            error_message = result['error']
            headers_list.append((f"Error ({error_type})", error_message, True, ""))
            log.warning(f"Layer '{result.get('name')}' resulted in an error: {result['error']}")
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

    def _compare_headers(self, result, index, all_results):
        headers_list = []
        upstream_headers = None
        upstream_name = ""

        if index < len(all_results) - 1:
            upstream_result = all_results[index+1]
            upstream_name = upstream_result.get('name', 'Unknown')
            if 'headers' in upstream_result:
                upstream_headers = {k.lower(): v for k, v in upstream_result.get('headers', {}).items()}

        for key, value in result.get('headers', {}).items():
            lower_key = key.lower()
            is_diff = False
            note = ""

            if upstream_headers is not None:
                if lower_key not in upstream_headers:
                    is_diff = True
                    note = f"New header set by {result.get('name')}"
                elif upstream_headers[lower_key] != value:
                    is_diff = True
                    prev_val = upstream_headers[lower_key]
                    if len(prev_val) > 20:
                        prev_val = prev_val[:20] + "..."
                    note = f"Changed from '{prev_val}' ({upstream_name})"

            headers_list.append((key, value, is_diff, note))

        return headers_list

    def set_inspection_in_progress(self, in_progress):
        self.inspect_button.set_sensitive(not in_progress)
        self.spinner.set_spinning(in_progress)
        self.spinner.set_visible(in_progress)

    def show_error_dialog(self, primary_text, secondary_text):
        dialog = Adw.MessageDialog.new(self, primary_text, secondary_text)
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.set_close_response("ok")
        dialog.present()
