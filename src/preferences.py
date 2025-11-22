import gi
import os
import pathlib

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GObject

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
"""

@Gtk.Template(resource_path='/com/github/mclellac/CacheFlow/ui/preferences.ui')
class PreferencesWindow(Adw.PreferencesWindow):
    __gtype_name__ = 'PreferencesWindow'

    theme_row = Gtk.Template.Child()
    dns_row = Gtk.Template.Child()

    config_prod_view = Gtk.Template.Child()
    config_staging_view = Gtk.Template.Child()
    config_qa_view = Gtk.Template.Child()
    config_dev_view = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings = Gio.Settings.new('com.github.mclellac.CacheFlow')

        # Bind DNS
        self.settings.bind('dns-servers', self.dns_row, 'text', Gio.SettingsBindFlags.DEFAULT)

        # Handle Theme
        self.theme_row.connect('notify::selected-item', self.on_theme_changed)
        self.load_theme()

        # Handle Configs
        self.setup_config_view(self.config_prod_view, 'config-production')
        self.setup_config_view(self.config_staging_view, 'config-staging')
        self.setup_config_view(self.config_qa_view, 'config-qa')
        self.setup_config_view(self.config_dev_view, 'config-dev')

    def load_theme(self):
        theme = self.settings.get_string('theme')
        if theme == 'light':
            self.theme_row.set_selected(1)
        elif theme == 'dark':
            self.theme_row.set_selected(2)
        else:
            self.theme_row.set_selected(0)

    def on_theme_changed(self, row, param):
        selected = row.get_selected()
        style_manager = Adw.StyleManager.get_default()
        if selected == 1:
            self.settings.set_string('theme', 'light')
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        elif selected == 2:
            self.settings.set_string('theme', 'dark')
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            self.settings.set_string('theme', 'system')
            style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)

    def setup_config_view(self, view, key):
        # Load
        val = self.settings.get_string(key)
        if not val or val.strip() == "":
             val = DEFAULT_CONFIG_YAML
             self.settings.set_string(key, val)

        view.get_buffer().set_text(val)

        # Connect Change
        view.get_buffer().connect("changed", lambda b: self.on_config_changed(b, key))

    def on_config_changed(self, buffer, key):
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
        self.settings.set_string(key, text)
