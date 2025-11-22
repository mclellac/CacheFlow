import gi
import threading
import os
import pathlib
from gi.repository import Gtk, Adw, Gio, GObject

try:
    from .inspector import HeaderInspector
    from .preferences import DEFAULT_CONFIG
except ImportError:
    from inspector import HeaderInspector
    from preferences import DEFAULT_CONFIG

@Gtk.Template(resource_path='/com/github/mclellac/CacheFlow/ui/window.ui')
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

        val = self.settings.get_value(env_key)
        layers = val.unpack()

        if not layers:
            return DEFAULT_CONFIG
        return layers

    def on_run_clicked(self, button):
        layers = self.get_active_config()

        # Construct the config object for Inspector
        # Inspector expects { 'layers': [...], ... }
        config_data = {
            'layers': layers,
            'user_agent': self.ua_row.get_text(),
            'test_path': self.path_row.get_text(),
            'dns_servers': self.settings.get_string('dns-servers')
        }

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
