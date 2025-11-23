# SPDX-License-Identifier: MIT

import gi
import requests

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GObject, GLib
from .node_graph import NodeGraph
from .engine import CacheFlowEngine

@Gtk.Template(filename='src/ui/main.ui')
class Window(Adw.ApplicationWindow):
    __gtype_name__ = 'Window'

    path_entry = Gtk.Template.Child()
    inspect_button = Gtk.Template.Child()
    node_graph = Gtk.Template.Child()
    env_switcher = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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
        # Bind the button's state to the action
        self.env_switcher.bind_property("active-action", self.lookup_action("win.active_environment"), "state", GObject.BindingFlags.DEFAULT)

    def on_env_change(self, action, value):
        """Handles state change for the active environment."""
        new_env = value.get_string()
        action.set_state(value)
        self.settings.set_string('active-environment', new_env)
        print(f"Switched to {new_env} environment")
        # Optionally, clear the graph or re-inspect
        self.node_graph.set_data([])

    def on_inspect_clicked(self, _):
        """Handler for the 'Inspect' button click."""
        path = self.path_entry.get_text()
        if not path or not path.startswith('/'):
            print("Invalid path") # Replace with a dialog later
            return

        self.settings.set_string('test-path', path)

        active_env = self.settings.get_string('active-environment')
        print(f"[DEBUG] Window.on_inspect_clicked: Reading active environment: '{active_env}'")
        config_key = f'config-{active_env}'
        layers_config = self.settings.get_value(config_key).unpack()

        if not layers_config:
            print(f"No layers configured for '{active_env}' environment.")
            return

        self.run_inspection(layers_config, path)

    def run_inspection(self, layers, path):
        """Performs HTTP requests and updates the node graph."""
        config = {
            'layers': layers,
            'user_agent': self.settings.get_string('user-agent'),
            'dns_servers': self.settings.get_string('dns-servers')
        }
        engine = CacheFlowEngine(config)
        results = engine.run_inspection(test_path=path)

        self.process_and_display_results(results)

    def process_and_display_results(self, results):
        """Compares headers and prepares data for the node graph."""
        print("[DEBUG] Window.process_and_display_results: Processing results for display.")
        processed_nodes = []

        if not results:
            print("[DEBUG] Window.process_and_display_results: No results to process.")
            self.node_graph.set_data([])
            return

        # The last layer is the origin, our source of truth.
        origin_headers = results[-1].get('headers', {})

        for i, result in enumerate(results):
            headers_list = []
            # If there's an error, there are no headers to process.
            if 'error' in result:
                headers_list.append(('Error', result['error'], True))
            elif i == len(results) - 1: # This is the origin layer
                for key, value in result.get('headers', {}).items():
                    headers_list.append((key, value, False)) # Nothing to compare against
            else:
                for key, value in result.get('headers', {}).items():
                    # Compare against the origin
                    is_diff = key not in origin_headers or origin_headers[key] != value
                    headers_list.append((key, value, is_diff))

            processed_nodes.append({
                "name": result['name'],
                "headers": headers_list
            })
        print(f"[DEBUG] Window.process_and_display_results: Processed nodes data: {processed_nodes}")

        self.node_graph.set_data(processed_nodes)