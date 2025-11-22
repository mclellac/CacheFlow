import gi
import yaml
import threading
import json
import os

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GObject

from inspector import HeaderInspector

DEFAULT_CONFIG_YAML = """
layers:
  - name: 'CDN_Edge'
    description: 'Akamai (External View)'
    host_url: 'https://www.example.com'
    custom_headers:
      Pragma: 'akamai-x-get-request-id, akamai-x-cache-on, akamai-x-cache-key'

  - name: 'Infra_Cache'
    description: 'Varnish (Internal Cache Layer)'
    host_url: 'http://cache.examplefarm.com'
    custom_headers:
      X-Varnish-Debug: 'true'
      X-Origin-Auth: 'secret-token-123'
    host_overrides:
      - path_pattern: '/api/*'
        host_header: 'api-internal.example.com'

  - name: 'Application_Backend_A'
    description: 'Openshift App Backend (mybackend.openshift.app.com)'
    host_url: 'https://mybackend.openshift.app.com'
    custom_headers: {}
    path_match_only:
      - '/products/*'
      - '/api/v1/*'

  - name: 'Application_Backend_B'
    description: 'Secondary Backend (legacy.app.com)'
    host_url: 'https://legacy.app.com'
    custom_headers: {}
    path_match_only:
      - '/static/*'
      - '/images/*'
"""

@Gtk.Template(filename='window.ui')
class Window(Adw.ApplicationWindow):
    __gtype_name__ = 'HeaderInspectorWindow'

    path_row = Gtk.Template.Child()
    ua_row = Gtk.Template.Child()
    run_btn = Gtk.Template.Child()
    spinner = Gtk.Template.Child()
    config_view = Gtk.Template.Child()
    result_view = Gtk.Template.Child()
    stack = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Initialize Settings
        self.settings = Gio.Settings.new('org.example.headerinspector')

        # Bind Settings
        self.settings.bind('test-path', self.path_row, 'text', Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('user-agent', self.ua_row, 'text', Gio.SettingsBindFlags.DEFAULT)

        # Load Config
        self.load_config()

        # Connect Signals
        self.run_btn.connect('clicked', self.on_run_clicked)

        # Setup Menu Actions
        action_reset = Gio.SimpleAction.new("reset_config", None)
        action_reset.connect("activate", self.on_reset_config)
        self.add_action(action_reset)

        # Connect config buffer change to save
        buffer = self.config_view.get_buffer()
        buffer.connect("changed", self.on_config_changed)

    def load_config(self):
        config_str = self.settings.get_string('layers-config')
        if not config_str or config_str.strip() == "":
            # Load Default
            self.config_view.get_buffer().set_text(DEFAULT_CONFIG_YAML)
            self.save_config_to_settings()
        else:
            self.config_view.get_buffer().set_text(config_str)

    def on_config_changed(self, buffer):
        # Auto-save config to settings when text changes
        # In a real app, might want a debounce or explicit save, but GSettings is fast enough for this text size
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
        self.settings.set_string('layers-config', text)

    def save_config_to_settings(self):
        buffer = self.config_view.get_buffer()
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
        self.settings.set_string('layers-config', text)

    def on_reset_config(self, action, param):
        self.config_view.get_buffer().set_text(DEFAULT_CONFIG_YAML)

    def on_run_clicked(self, button):
        # Get current config from text view
        buffer = self.config_view.get_buffer()
        config_text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)

        try:
            # Parse YAML
            config_data = yaml.safe_load(config_text)
            if not isinstance(config_data, dict) or 'layers' not in config_data:
                # Try wrapping it if user just pasted the layers list?
                # Or assume the user messed up.
                # If the text is just the layers list, we might need to support that,
                # but the default config is a dict with 'layers' key.
                # Let's assume the user keeps the structure.
                if config_data is None: # Empty text
                     config_data = {}

            # Update global settings in the config object passed to inspector
            config_data['user_agent'] = self.ua_row.get_text()
            config_data['test_path'] = self.path_row.get_text()

        except yaml.YAMLError as e:
            self.show_error(f"Configuration Parse Error:\n{e}")
            return

        self.result_view.get_buffer().set_text("")
        self.run_btn.set_sensitive(False)
        self.spinner.start()

        # Switch to results tab
        self.stack.set_visible_child_name('results')

        thread = threading.Thread(target=self.run_inspection_thread, args=(config_data,))
        thread.start()

    def run_inspection_thread(self, config_data):
        try:
            inspector = HeaderInspector(config_data)
            results = inspector.run_inspection(config_data.get('test_path'))

            output = ""
            for res in results:
                output += f"=== Layer: {res['name']} ===\n"
                if 'description' in res and res['description']:
                    output += f"Description: {res['description']}\n"
                output += f"URL: {res['url']}\n"
                if res.get('sent_host_header'):
                    output += f"Host Override: {res['sent_host_header']}\n"

                if 'error' in res:
                    output += f"ERROR: {res['error']}\n"
                else:
                    output += f"Status: {res['status_code']}\n"
                    output += "Headers:\n"
                    for k, v in res['headers'].items():
                        output += f"  {k}: {v}\n"
                output += "\n" + "-"*40 + "\n\n"

            GObject.idle_add(self.update_ui_success, output)

        except Exception as e:
            GObject.idle_add(self.show_error, str(e))

    def update_ui_success(self, output):
        self.result_view.get_buffer().set_text(output)
        self.run_btn.set_sensitive(True)
        self.spinner.stop()

    def show_error(self, error_msg):
        self.result_view.get_buffer().set_text(f"An error occurred:\n{error_msg}")
        self.run_btn.set_sensitive(True)
        self.spinner.stop()
