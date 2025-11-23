import gi
import requests
import logging

from gi.repository import Gtk, Adw, Gio, GObject, GLib
from .node_graph import NodeGraph
from .engine import CacheFlowEngine

log = logging.getLogger(__name__)


@Gtk.Template(filename='src/ui/main.ui')
class Window(Adw.ApplicationWindow):
    __gtype_name__ = 'Window'

    path_entry = Gtk.Template.Child()
    inspect_button = Gtk.Template.Child()
    node_graph = Gtk.Template.Child()
    env_switcher = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        log.debug("Main window initialized.")
        self.settings = Gio.Settings.new('com.github.mclellac.CacheFlow')
        self.environments = ["production", "staging", "qa", "dev"]

        self.setup_actions()
        self.setup_env_switcher()

        self.inspect_button.connect('clicked', self.on_inspect_clicked)
        self.path_entry.set_text(self.settings.get_string('test-path'))

    def setup_actions(self):
        """Setup application-wide actions."""
        action_group = Gio.SimpleActionGroup()
        self.insert_action_group("win", action_group)

        def add_action(name, callback):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            action_group.add_action(action)

        add_action("inspect", self.on_inspect_clicked)

        active_env_action = Gio.SimpleAction.new_stateful(
            "active_environment",
            GLib.VariantType.new("s"),
            GLib.Variant("s", self.settings.get_string('active-environment'))
        )
        active_env_action.connect("change-state", self.on_env_change)
        action_group.add_action(active_env_action)

    def setup_env_switcher(self):
        """Sets up the environment selection menu button."""
        menu = Gio.Menu.new()

        for env in self.environments:
            menu.append(env.capitalize(), f"win.active_environment::{env}")

        self.env_switcher.set_menu_model(menu)
        self.env_switcher.action_name = "win.active_environment"

    def on_env_change(self, action, value):  # noqa
        """Handles state change for the active environment."""
        new_env = value.get_string()
        action.set_state(value)
        self.settings.set_string('active-environment', new_env)
        # Optionally, clear the graph or re-inspect
        self.node_graph.set_data([])

    def on_inspect_clicked(self, _):
        """Handler for the 'Inspect' button click."""
        log.info("Inspect button clicked.")
        path = self.path_entry.get_text()
        if not path or not path.startswith('/'):
            log.error(f"Invalid path for inspection: '{path}'")
            
        self.settings.set_string('test-path', path)

        active_env = self.settings.get_string('active-environment')
        config_key = f'config-{active_env}'
        layers_config = self.settings.get_value(config_key).unpack()
        if not layers_config:
            log.error(f"No layers configured for '{active_env}' environment.")
            return
        self.run_inspection(layers_config, path)
        self.last_run_layers = layers_config

    def run_inspection(self, layers, path):
        """Performs HTTP requests and updates the node graph."""
        config = {
            'layers': layers,
            'user_agent': self.settings.get_string('user-agent'),
            'dns_servers': self.settings.get_string('dns-servers')
        }
        engine = CacheFlowEngine(config)
        results = engine.run_inspection(test_path=path)

        self.process_and_display_results(results, layers)

    def process_and_display_results(self, results, layer_config):
        """Compares headers and prepares data for the node graph."""
        log.debug("Processing inspection results for display.")
        processed_nodes = []

        if not results:
            self.node_graph.set_data([])
            return

        origin_headers = results[-1].get('headers', {})

        for i, result in enumerate(results):
            original_layer = next((layer for layer in layer_config if layer.get('name') == result.get('name')), {})
            body_color = original_layer.get('body_color', '')
            header_color = original_layer.get('header_color', '')
            text_color = original_layer.get('text_color', '')
            diff_text_color = original_layer.get('diff_text_color', '')
            headers_list = []
            if 'error' in result:
                headers_list.append(('Error', result['error'], True))
            elif i == len(results) - 1:
                for key, value in result.get('headers', {}).items():
                    headers_list.append((key, value, False))
            else:
                for key, value in result.get('headers', {}).items():
                    is_diff = key not in origin_headers or origin_headers[key] != value
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