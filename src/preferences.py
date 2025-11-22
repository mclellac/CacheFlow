import gi
import os
import pathlib
from gi.repository import Gtk, Adw, Gio, GObject, GLib

from .layer_widgets import LayerRow

# Default config as a Python list of dicts
DEFAULT_CONFIG = [
    {
        "name": "CDN_Edge",
        "description": "Akamai (External View)",
        "host_url": "https://www.example.com",
        "custom_headers": {
            "Pragma": "akamai-x-get-request-id, akamai-x-cache-on, akamai-x-cache-key"
        },
        "host_overrides": [],
        "path_match_only": []
    },
    {
        "name": "Infra_Cache",
        "description": "Varnish (Internal Cache Layer)",
        "host_url": "http://cache.examplefarm.com",
        "custom_headers": {
            "X-Varnish-Debug": "true",
            "X-Origin-Auth": "secret-token-123"
        },
        "host_overrides": [
            {
                "path_pattern": "/api/*",
                "host_header": "api-internal.example.com"
            }
        ],
        "path_match_only": []
    },
    {
        "name": "Application_Backend_A",
        "description": "Openshift App Backend (mybackend.openshift.app.com)",
        "host_url": "https://mybackend.openshift.app.com",
        "custom_headers": {},
        "path_match_only": [
            "/products/*",
            "/api/v1/*"
        ],
        "host_overrides": []
    }
]

@Gtk.Template(resource_path='/com/github/mclellac/CacheFlow/ui/preferences.ui')
class PreferencesWindow(Adw.PreferencesWindow):
    __gtype_name__ = 'PreferencesWindow'

    theme_row = Gtk.Template.Child()
    dns_row = Gtk.Template.Child()

    prod_group = Gtk.Template.Child()
    staging_group = Gtk.Template.Child()
    qa_group = Gtk.Template.Child()
    dev_group = Gtk.Template.Child()

    prod_add_row = Gtk.Template.Child()
    staging_add_row = Gtk.Template.Child()
    qa_add_row = Gtk.Template.Child()
    dev_add_row = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings = Gio.Settings.new('com.github.mclellac.CacheFlow')

        # Registry for LayerRows: {group_widget: [LayerRow, ...]}
        self._layer_rows = {}

        # Bind DNS
        self.settings.bind('dns-servers', self.dns_row, 'text', Gio.SettingsBindFlags.DEFAULT)

        # Handle Theme
        self.theme_row.connect('notify::selected-item', self.on_theme_changed)
        self.load_theme()

        # Connect Add Buttons
        self.prod_add_row.connect('activated', lambda row: self.add_layer(self.prod_group, 'config-production'))
        self.staging_add_row.connect('activated', lambda row: self.add_layer(self.staging_group, 'config-staging'))
        self.qa_add_row.connect('activated', lambda row: self.add_layer(self.qa_group, 'config-qa'))
        self.dev_add_row.connect('activated', lambda row: self.add_layer(self.dev_group, 'config-dev'))

        # Handle Configs
        self.setup_env_config(self.prod_group, 'config-production')
        self.setup_env_config(self.staging_group, 'config-staging')
        self.setup_env_config(self.qa_group, 'config-qa')
        self.setup_env_config(self.dev_group, 'config-dev')

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

    def setup_env_config(self, group, key):
        # Initialize registry for this group
        self._layer_rows[group] = []

        val = self.settings.get_value(key)
        layers = val.unpack() # Returns native python types (list of dicts)

        if not layers:
             layers = DEFAULT_CONFIG
             # We might want to save this default to the settings to ensure consistency
             # But for now, we just use it to populate.

        # Populate layers
        for layer_data in layers:
            self.create_layer_row(group, key, layer_data)

    def create_layer_row(self, group, key, data):
        row = LayerRow(
            layer_data=data,
            on_delete=lambda r: self.remove_layer(group, key, r),
            on_change=lambda: self.save_config(group, key)
        )

        # Add to registry
        if group not in self._layer_rows:
            self._layer_rows[group] = []
        self._layer_rows[group].append(row)

        # Add to UI before the "Add" button
        add_row = None
        if group == self.prod_group: add_row = self.prod_add_row
        elif group == self.staging_group: add_row = self.staging_add_row
        elif group == self.qa_group: add_row = self.qa_add_row
        elif group == self.dev_group: add_row = self.dev_add_row

        if add_row:
            group.remove(add_row)
            group.add(row)
            group.add(add_row)
        else:
            group.add(row)

    def add_layer(self, group, key):
        new_data = {
            'name': 'New Layer',
            'description': '',
            'host_url': 'http://localhost',
            'custom_headers': {},
            'host_overrides': [],
            'path_match_only': []
        }
        self.create_layer_row(group, key, new_data)
        self.save_config(group, key)

    def remove_layer(self, group, key, row):
        group.remove(row)
        if group in self._layer_rows and row in self._layer_rows[group]:
            self._layer_rows[group].remove(row)
        self.save_config(group, key)

    def save_config(self, group, key):
        layers = []
        if group in self._layer_rows:
            for row in self._layer_rows[group]:
                layers.append(row.get_data())

        # Construct Variant
        # Type: aa{sv}

        # We need to ensure the data matches the strict types for GVariant
        # name: s
        # description: s
        # host_url: s
        # custom_headers: a{ss}
        # host_overrides: aa{ss}
        # path_match_only: as

        variant_data = []
        for l in layers:
            layer_dict = {
                'name': GLib.Variant('s', l.get('name', '')),
                'description': GLib.Variant('s', l.get('description', '')),
                'host_url': GLib.Variant('s', l.get('host_url', '')),
                'custom_headers': GLib.Variant('a{ss}', l.get('custom_headers', {})),
                'host_overrides': GLib.Variant('aa{ss}', l.get('host_overrides', [])),
                'path_match_only': GLib.Variant('as', l.get('path_match_only', []))
            }
            variant_data.append(layer_dict)

        # GLib.Variant('aa{sv}', variant_data)
        try:
            v = GLib.Variant('aa{sv}', variant_data)
            self.settings.set_value(key, v)
        except Exception as e:
            print(f"Error saving config: {e}")

