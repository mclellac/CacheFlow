import gi
import requests
import logging
import threading

from gi.repository import Gtk, Adw, Gio, GObject, GLib, Pango, Gdk
from .node_graph import NodeGraph

log = logging.getLogger(__name__)


@Gtk.Template(resource_path='/com/github/mclellac/CacheFlow/ui/header_dialog.ui')
class HeaderDialog(Adw.MessageDialog):
    """A dialog to display key-value headers from a node."""
    __gtype_name__ = 'HeaderDialog'

    treeview = Gtk.Template.Child()
    column_key = Gtk.Template.Child()
    renderer_key = Gtk.Template.Child()
    column_value = Gtk.Template.Child()
    renderer_value = Gtk.Template.Child()

    def __init__(self, headers, **kwargs):
        super().__init__(**kwargs)
        self._clipboard_provider = None

        heading = self.get_heading()
        if heading and heading != "Headers":
             self.set_heading(f"Headers for {heading}")

        store = Gtk.ListStore(str, str, bool)
        headers_to_split = ['x-akamai-session-info', 'content-security-policy']

        for header, value, is_diff in headers:
            if header.lower() in headers_to_split and ';' in value:
                parts = [p.strip() for p in value.split(';') if p.strip()]
                if not parts:
                    store.append([header, '', is_diff])
                    continue
                store.append([header, parts[0] + ';', is_diff])
                for part in parts[1:]:
                    store.append(['', part + (';' if not part == parts[-1] else ''), is_diff])
            else:
                store.append([header, value, is_diff])

        self.treeview.set_model(store)

        self.column_key.set_cell_data_func(self.renderer_key, self.style_header_cell)
        self.column_value.set_cell_data_func(self.renderer_value, self.style_value_cell)

        self._setup_context_menu()

    def style_header_cell(self, column, cell, model, iter, data):
        key = model.get_value(iter, 0)
        escaped_key = GLib.markup_escape_text(key)
        markup = f"<b>{escaped_key}</b>"
        cell.set_property("markup", markup)

    def style_value_cell(self, column, cell, model, iter, data):
        is_diff = model.get_value(iter, 2)
        if is_diff:
            cell.set_property("weight", Pango.Weight.BOLD)
        else:
            cell.set_property("weight", Pango.Weight.NORMAL)

    def _setup_context_menu(self):
        copy_action = Gio.SimpleAction.new("copy_selection", None)
        copy_action.connect("activate", self._on_copy_activated)

        action_group = Gio.SimpleActionGroup()
        action_group.add_action(copy_action)
        self.insert_action_group("dialog", action_group)
        menu_model = Gio.Menu()
        menu_model.append("Copy", "dialog.copy_selection")

        self.popover = Gtk.PopoverMenu.new_from_model(menu_model)
        self.popover.set_parent(self.treeview)

        click_controller = Gtk.GestureClick.new()
        click_controller.set_button(Gdk.BUTTON_SECONDARY)
        click_controller.connect("pressed", self._on_right_click)
        self.treeview.add_controller(click_controller)

    def _on_right_click(self, gesture, n_press, x, y):
        self.popover.set_pointing_to(Gdk.Rectangle(x, y, 1, 1))
        self.popover.popup()

    def _on_copy_activated(self, action, param):
        log.debug("Copy action activated.")
        selection = self.treeview.get_selection()
        model, paths = selection.get_selected_rows()
        if not paths:
            log.debug("No rows selected, nothing to copy.")
            return

        log.debug(f"Found {len(paths)} rows selected for copying.")
        clipboard_text = []
        for path in paths:
            it = model.get_iter(path)
            key = model.get_value(it, 0)
            value = model.get_value(it, 1)
            if key:
                clipboard_text.append(f"{key}: {value}")

        text_to_copy = "\n".join(clipboard_text)
        log.debug(f"Attempting to copy text to clipboard: '{text_to_copy}'")
        self._clipboard_provider = Gdk.ContentProvider.new_for_value(text_to_copy)
        clipboard = self.get_clipboard()
        clipboard.set_content(self._clipboard_provider)
        log.debug("Clipboard content set.")


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
        
        thread = threading.Thread(target=self.do_inspection_thread, args=(layers_config, path))
        thread.daemon = True
        thread.start()

    def do_inspection_thread(self, layers, path):
        from .engine import CacheFlowEngine
        log.debug("Starting inspection in background thread.")
        try:
            config = {
                'layers': layers,
                'user_agent': self.settings.get_string('user-agent'),
                'dns_servers': self.settings.get_string('dns-servers'),
                'verify_ssl': self.settings.get_boolean('verify-ssl')
            }
            engine = CacheFlowEngine(config)
            results = engine.run_inspection(test_path=path)
            GLib.idle_add(self.on_inspection_succeeded, results, layers)
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
            original_layer = next((layer for layer in layer_config if layer.get('name') == result.get('name')), {})
            body_color = original_layer.get('body_color', '')
            header_color = original_layer.get('header_color', '')
            text_color = original_layer.get('text_color', '')
            diff_text_color = original_layer.get('diff_text_color', '')
            headers_list = []
            if 'error' in result:
                error_type = result.get('error_type', 'unknown').capitalize()
                error_message = result['error']
                headers_list.append((f"Error ({error_type})", error_message, True))
                log.warning(f"Layer '{result.get('name')}' resulted in an error: {result['error']}")
            else:
                upstream_headers = None
                if i < len(results) - 1:
                    upstream_result = results[i+1]
                    if 'headers' in upstream_result:
                         upstream_headers = {k.lower(): v for k, v in upstream_result.get('headers', {}).items()}

                for key, value in result.get('headers', {}).items():
                    lower_key = key.lower()
                    is_diff = False
                    if upstream_headers is not None:
                        if lower_key not in upstream_headers or upstream_headers[lower_key] != value:
                            is_diff = True

                    log.debug(f"Comparing header '{key}': value='{value}', upstream='{upstream_headers.get(lower_key) if upstream_headers else 'None'}', is_diff={is_diff}")
                    headers_list.append((key, value, is_diff))

            processed_nodes.append({
                "name": result['name'],
                "headers": headers_list,
                "body_color": body_color,
                "header_color": header_color,
                "text_color": text_color,
                "diff_text_color": diff_text_color
            })

        self.node_graph.set_data(processed_nodes)

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
