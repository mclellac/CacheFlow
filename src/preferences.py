import gi
import os

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

class PreferencesWindow(Adw.PreferencesWindow):
    __gtype_name__ = 'PreferencesWindow'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Preferences")

        self.settings = Gio.Settings.new('com.github.mclellac.CacheFlow')

        # Application Page
        page_app = Adw.PreferencesPage(title="Application", icon_name="preferences-system-symbolic")
        self.add(page_app)

        # Appearance Group
        group_appearance = Adw.PreferencesGroup(title="Appearance")
        page_app.add(group_appearance)

        self.theme_row = Adw.ComboRow(title="Theme")
        model = Gtk.StringList()
        model.append("System")
        model.append("Light")
        model.append("Dark")
        self.theme_row.set_model(model)
        group_appearance.add(self.theme_row)

        # Network Group
        group_network = Adw.PreferencesGroup(title="Network")
        page_app.add(group_network)

        self.dns_row = Adw.EntryRow(title="DNS Servers")
        self.dns_row.set_tooltip_text("Comma-separated list of DNS servers (e.g., 8.8.8.8, 1.1.1.1)")
        self.dns_row.set_show_apply_button(True)
        group_network.add(self.dns_row)

        # Environments
        self.setup_env_page("Production", "network-server-symbolic", "config-production", "config_prod_view")
        self.setup_env_page("Staging", "folder-publicshare-symbolic", "config-staging", "config_staging_view")
        self.setup_env_page("QA", "user-available-symbolic", "config-qa", "config_qa_view")
        self.setup_env_page("Dev", "applications-development-symbolic", "config-dev", "config_dev_view")

        # Bind DNS
        self.settings.bind('dns-servers', self.dns_row, 'text', Gio.SettingsBindFlags.DEFAULT)

        # Handle Theme
        self.theme_row.connect('notify::selected-item', self.on_theme_changed)
        self.load_theme()

    def setup_env_page(self, title, icon, key, view_attr_name):
        page = Adw.PreferencesPage(title=title, icon_name=icon)
        self.add(page)

        group = Adw.PreferencesGroup(title="Configuration", description="Define layers and infrastructure headers.")
        page.add(group)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_height_request(400)
        group.add(box)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        box.append(scrolled)

        view = Gtk.TextView()
        view.set_monospace(True)
        view.set_top_margin(10)
        view.set_bottom_margin(10)
        view.set_left_margin(10)
        view.set_right_margin(10)
        view.set_wrap_mode(Gtk.WrapMode.WORD)
        scrolled.set_child(view)

        # Set attribute on self so we can reference it if needed, though mostly for debugging
        setattr(self, view_attr_name, view)

        # Load Config
        self.setup_config_view(view, key)

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
