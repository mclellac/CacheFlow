import gi
import requests
import logging
import threading

from gi.repository import Gtk, Adw, Gio, GObject, GLib, Pango, Gdk
from .node_graph import NodeGraph

log = logging.getLogger(__name__)


class HeaderDialog(Adw.MessageDialog):
    """A dialog to display key-value headers from a node."""

    def __init__(self, headers, **kwargs):
        super().__init__(**kwargs)
        self._clipboard_provider = None # To hold a reference

        heading = self.get_heading()
        self.set_heading(f"Headers for {heading}")

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_min_content_height(400)
        scrolled_window.set_vexpand(True)

        # Create the model (key, value, is_diff)
        store = Gtk.ListStore(str, str, bool)
        headers_to_split = ['x-akamai-session-info', 'content-security-policy']

        for header, value, is_diff in headers:
            # Check if the header is one of the long ones we want to split
            if header.lower() in headers_to_split and ';' in value:
                parts = [p.strip() for p in value.split(';') if p.strip()]
                if not parts:
                    store.append([header, '', is_diff])
                    continue
                # Add the first part with the header key
                store.append([header, parts[0] + ';', is_diff])
                # Add subsequent parts without the header key for alignment
                for part in parts[1:]:
                    store.append(['', part + (';' if not part == parts[-1] else ''), is_diff])
            else:
                store.append([header, value, is_diff])

        # Create the view
        treeview = Gtk.TreeView(model=store)
        treeview.set_hexpand(True)
        treeview.set_can_focus(True)
        treeview.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.treeview = treeview # Store for later use

        # Create columns
        renderer_key = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END)
        column_key = Gtk.TreeViewColumn("Header", renderer_key)
        column_key.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column_key.set_min_width(150)
        column_key.set_resizable(True)

        renderer_value = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END)
        column_value = Gtk.TreeViewColumn("Value", renderer_value, text=1)
        column_value.set_expand(True)
        column_value.set_resizable(True)

        # Make text selectable for copying
        renderer_key.set_property('editable', True)
        renderer_value.set_property('editable', True)

        def style_header_cell(column, cell, model, iter, data):
            key = model.get_value(iter, 0)
            escaped_key = GLib.markup_escape_text(key)
            markup = f"<b>{escaped_key}</b>"
            cell.set_property("markup", markup)

        def style_value_cell(column, cell, model, iter, data):
            is_diff = model.get_value(iter, 2)
            if is_diff:
                # Using a bold weight to indicate a difference.
                cell.set_property("weight", Pango.Weight.BOLD)
            else:
                cell.set_property("weight", Pango.Weight.NORMAL)

        column_key.set_cell_data_func(renderer_key, style_header_cell)
        column_value.set_cell_data_func(renderer_value, style_value_cell)

        treeview.append_column(column_key)
        treeview.append_column(column_value)

        scrolled_window.set_child(treeview)

        self.set_extra_child(scrolled_window)
        self.add_response("close", "Close")
        self.set_default_response("close")
        self.set_close_response("close")

        # Setup context menu for copying
        self._setup_context_menu()

    def _setup_context_menu(self):
        """Creates and attaches the right-click context menu."""
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
        """Shows the popover menu on right-click."""
        self.popover.set_pointing_to(Gdk.Rectangle(x, y, 1, 1))
        self.popover.popup()

    def _on_copy_activated(self, action, param):
        """Copies the selected rows to the clipboard."""
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
            if key: # Don't copy lines that are just continuations of a value
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
        """Setup application-wide actions."""
        self.win_action_group = Gio.SimpleActionGroup()
        self.insert_action_group("win", self.win_action_group)

        self.add_action("inspect", self.on_inspect_clicked)

    def add_action(self, name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.win_action_group.add_action(action)

    def setup_env_switcher(self):
        """Sets up the environment selection dropdown."""
        self.env_model = Gtk.StringList.new(self.environments)
        self.env_switcher.set_model(self.env_model)

        # Sync dropdown with settings
        active_env = self.settings.get_string('active-environment')
        if active_env in self.environments:
            self.env_switcher.set_selected(self.environments.index(active_env))
        else:
            self.env_switcher.set_selected(0)

        self.env_switcher.connect('notify::selected', self.on_env_selected)

    def on_env_selected(self, dropdown, _):
        """Handles environment selection change."""
        selected_idx = dropdown.get_selected()
        new_env = self.environments[selected_idx]
        self.settings.set_string('active-environment', new_env)
        # Optionally, clear the graph or re-inspect
        self.node_graph.set_data([])

    def on_inspect_clicked(self, _):
        """Handler for the 'Inspect' button click."""
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
            return # Stop execution if no layers are configured
        
        # Run the inspection in a separate thread to keep the UI responsive.
        thread = threading.Thread(target=self.do_inspection_thread, args=(layers_config, path))
        thread.daemon = True
        thread.start()

    def do_inspection_thread(self, layers, path):
        """
        This function runs in a background thread and performs the blocking
        network requests.
        """
        from .engine import CacheFlowEngine
        log.debug("Starting inspection in background thread.")
        try:
            config = {
                'layers': layers,
                'user_agent': self.settings.get_string('user-agent'),
                'dns_servers': self.settings.get_string('dns-servers')
            }
            engine = CacheFlowEngine(config)
            results = engine.run_inspection(test_path=path)
            # Schedule the success callback on the main GTK thread.
            GLib.idle_add(self.on_inspection_succeeded, results, layers)
        except Exception as e:
            log.error(f"Exception in inspection thread: {e}", exc_info=True)
            # Schedule the failure callback on the main GTK thread.
            GLib.idle_add(self.on_inspection_failed, e)

    def on_inspection_succeeded(self, results, layer_config):
        """Handles successful inspection results in the main thread."""
        log.debug("Inspection succeeded, processing results.")
        self.process_and_display_results(results, layer_config)
        self.set_inspection_in_progress(False)
        return GLib.SOURCE_REMOVE

    def on_inspection_failed(self, exception):
        """Handles failed inspection in the main thread."""
        log.error(f"Inspection task failed: {exception}")
        self.show_error_dialog("Inspection Failed", str(exception))
        self.set_inspection_in_progress(False)
        return GLib.SOURCE_REMOVE

    def process_and_display_results(self, results, layer_config):
        """Compares headers and prepares data for the node graph."""
        log.debug("Processing inspection results for display.")
        processed_nodes = []

        if not results:
            self.node_graph.set_data([])
            return

        # Safely get the headers from the last layer (origin) for comparison.
        origin_result = results[-1]
        origin_headers = {k.lower(): v for k, v in origin_result.get('headers', {}).items()}

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
                # Use a tuple to display the error type and message clearly
                headers_list.append((f"Error ({error_type})", error_message, True))
                log.warning(f"Layer '{result.get('name')}' resulted in an error: {result['error']}")
            elif i == len(results) - 1:
                for key, value in result.get('headers', {}).items():
                    headers_list.append((key, value, False))
            else:
                for key, value in result.get('headers', {}).items():
                    lower_key = key.lower()
                    is_diff = lower_key not in origin_headers or origin_headers[lower_key] != value
                    log.debug(f"Comparing header '{key}': value='{value}', origin='{origin_headers.get(lower_key)}', is_diff={is_diff}")
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
        """Updates the UI to show that an inspection is running."""
        self.inspect_button.set_sensitive(not in_progress)
        self.spinner.set_spinning(in_progress)
        self.spinner.set_visible(in_progress)

    def show_error_dialog(self, primary_text, secondary_text):
        """Displays an error dialog to the user."""
        dialog = Adw.MessageDialog.new(self, primary_text, secondary_text)
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.set_close_response("ok")
        dialog.present()