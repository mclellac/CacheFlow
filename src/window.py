import gi
import yaml
import threading
import os

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GObject

from inspector import HeaderInspector

# Resolve UI file path relative to this file
ui_path = os.path.join(os.path.dirname(__file__), 'ui', 'window.ui')

if not os.path.exists(ui_path):
    # Fallback to try and find it if running from a different context
    # This is just a safety measure.
    print(f"Warning: UI file not found at {ui_path}")

@Gtk.Template(filename=ui_path)
class Window(Adw.ApplicationWindow):
    __gtype_name__ = 'HeaderInspectorWindow'

    env_dropdown = Gtk.Template.Child()
    path_row = Gtk.Template.Child()
    ua_row = Gtk.Template.Child()
    run_btn = Gtk.Template.Child()
    spinner = Gtk.Template.Child()
    result_view = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Initialize Settings
        self.settings = Gio.Settings.new('com.github.mclellac.CacheFlow')

        # Bind Settings
        self.settings.bind('test-path', self.path_row, 'text', Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('user-agent', self.ua_row, 'text', Gio.SettingsBindFlags.DEFAULT)

        # Load Active Environment
        active_env = self.settings.get_string('active-environment')
        env_map = {'production': 0, 'staging': 1, 'qa': 2, 'dev': 3}
        self.env_dropdown.set_selected(env_map.get(active_env, 0))
        self.env_dropdown.connect('notify::selected-item', self.on_env_changed)

        # Connect Run
        self.run_btn.connect('clicked', self.on_run_clicked)

        # Apply Theme immediately
        self.apply_theme()

        # Listen for theme changes from preferences
        self.settings.connect('changed::theme', lambda s, k: self.apply_theme())

    def apply_theme(self):
        theme = self.settings.get_string('theme')
        style_manager = Adw.StyleManager.get_default()
        if theme == 'light':
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        elif theme == 'dark':
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)

    def on_env_changed(self, dropdown, param):
        selected = dropdown.get_selected()
        envs = ['production', 'staging', 'qa', 'dev']
        if 0 <= selected < len(envs):
            self.settings.set_string('active-environment', envs[selected])

    def get_active_config(self):
        selected = self.env_dropdown.get_selected()
        envs = ['production', 'staging', 'qa', 'dev']
        if 0 <= selected < len(envs):
            env_key = f'config-{envs[selected]}'
        else:
            env_key = 'config-production'

        config_str = self.settings.get_string(env_key)
        if not config_str or config_str.strip() == "":
            # If empty, use default template from preferences module (simulated)
            from preferences import DEFAULT_CONFIG_YAML
            return DEFAULT_CONFIG_YAML
        return config_str

    def on_run_clicked(self, button):
        config_text = self.get_active_config()

        try:
            # Parse YAML
            config_data = yaml.safe_load(config_text)
            if not isinstance(config_data, dict) or 'layers' not in config_data:
                if config_data is None:
                     config_data = {}

            # Merge runtime settings
            config_data['user_agent'] = self.ua_row.get_text()
            config_data['test_path'] = self.path_row.get_text()

            # Pass DNS settings from GSettings
            dns_servers = self.settings.get_string('dns-servers')
            config_data['dns_servers'] = dns_servers

        except yaml.YAMLError as e:
            self.show_error(f"Configuration Parse Error for active environment:\n{e}")
            return

        self.result_view.get_buffer().set_text("")
        self.run_btn.set_sensitive(False)
        self.spinner.start()

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
