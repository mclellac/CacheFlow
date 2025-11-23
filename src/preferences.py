import gi
import logging
from gi.repository import Gtk, Adw, Gio, GObject, GLib, Gdk

from .layer_widgets import LayerRow

log = logging.getLogger(__name__)


def setting_to_rgba(variant, _user_data=None):
    """Maps a GSettings GVariant(string) to a GObject.Value(Gdk.RGBA)."""
    rgba = Gdk.RGBA()
    if variant:
        # The binding system passes a GVariant here. We must unpack it.
        rgba_string = variant.get_string()
        # Ensure the string is not empty before parsing.
        if rgba_string and rgba.parse(rgba_string):
            log.debug(f"Mapping GSettings string '{rgba_string}' to Gdk.RGBA.")
            return GObject.Value(Gdk.RGBA, rgba)

    log.warning(f"Failed to parse GSettings color string '{variant.get_string() if variant else 'None'}'. Using default.")
    rgba.parse('rgba(0,0,0,0)')
    return GObject.Value(Gdk.RGBA, rgba)


def rgba_to_setting(gdk_rgba, _user_data=None):
    """
    Maps a Gdk.RGBA from the widget to a GVariant(string).
    Returning None tells the binding to NOT update the setting.
    """
    if gdk_rgba:
        log.debug(f"Mapping Gdk.RGBA '{gdk_rgba.to_string()}' to GSettings string.")
        return GLib.Variant('s', gdk_rgba.to_string())
    # If the widget's color is None (e.g., on init), do not save anything.
    log.debug("Widget provided a None RGBA. No setting will be saved.")
    return None


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


class ConfigManager:
    """Handles all GSettings interactions for layer configurations."""

    def __init__(self, settings):
        self.settings = settings
        log.debug("ConfigManager initialized.")

    def get_layers(self, key):
        """Gets and unpacks layers for a given config key."""
        val = self.settings.get_value(key)
        layers = val.unpack()
        if not layers:
            return DEFAULT_CONFIG
        return layers

    def save_layers(self, key, layer_rows):
        """Constructs a GVariant from a list of LayerRow widgets and saves it."""
        log.info(f"Saving configuration for key '{key}'.")
        layers_data = [row.get_data() for row in layer_rows]

        variant_data = []
        for l_data in layers_data:
            layer_dict = {
                'name': GLib.Variant('s', l_data.get('name', '')),
                'description': GLib.Variant('s', l_data.get('description', '')),
                'host_url': GLib.Variant('s', l_data.get('host_url', '')),
                'header_color': GLib.Variant('s', l_data.get('header_color', '')),
                'body_color': GLib.Variant('s', l_data.get('body_color', '')),
                'custom_headers': GLib.Variant('a{ss}', l_data.get('custom_headers', {})),
                'host_overrides': GLib.Variant('aa{ss}', l_data.get('host_overrides', [])),
                'path_match_only': GLib.Variant('as', l_data.get('path_match_only', []))
            }
            variant_data.append(layer_dict)

        try:
            variant = GLib.Variant('aa{sv}', variant_data)
            self.settings.set_value(key, variant)
        except Exception as e:
            log.error(f"Error saving config for key '{key}': {e}")

    def ensure_default_config(self, key):
        """
        If no configuration exists for a key, this creates one from the
        default and saves it.
        """
        val = self.settings.get_value(key)
        if not val.unpack():
            variant_data = []
            for l_data in DEFAULT_CONFIG:
                layer_dict = {
                    'name': GLib.Variant('s', l_data.get('name', '')),
                    'description': GLib.Variant('s', l_data.get('description', '')),
                    'host_url': GLib.Variant('s', l_data.get('host_url', '')),
                    'header_color': GLib.Variant('s', l_data.get('header_color', '')),
                    'body_color': GLib.Variant('s', l_data.get('body_color', '')),
                    'custom_headers': GLib.Variant('a{ss}', l_data.get('custom_headers', {})),
                    'host_overrides': GLib.Variant('aa{ss}', l_data.get('host_overrides', [])),
                    'path_match_only': GLib.Variant('as', l_data.get('path_match_only', []))
                }
                variant_data.append(layer_dict)
            try:
                variant = GLib.Variant('aa{sv}', variant_data)
                self.settings.set_value(key, variant)
            except Exception as e:
                log.error(f"Error creating default config for key '{key}': {e}")
            log.info(f"No config found for '{key}'. Saved default configuration.")


@Gtk.Template(resource_path='/com/github/mclellac/CacheFlow/ui/preferences.ui')
class PreferencesWindow(Adw.PreferencesWindow):
    __gtype_name__ = 'PreferencesWindow'

    theme_row = Gtk.Template.Child()
    dns_row = Gtk.Template.Child()
    font_button = Gtk.Template.Child()

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
        log.debug("PreferencesWindow initializing.")
        self.set_destroy_with_parent(True)
        self.settings = Gio.Settings.new('com.github.mclellac.CacheFlow')
        self.config_manager = ConfigManager(self.settings)
        self._layer_rows = {}

        self.settings.bind('dns-servers', self.dns_row, 'text', Gio.SettingsBindFlags.DEFAULT)

        self.theme_row.connect('notify::selected-item', self.on_theme_changed)
        self.load_theme()

        self.font_button.set_font(self.settings.get_string('node-font'))
        self.font_button.connect('font-set', self.on_font_set)

        env_map = {'production': self.prod_group, 'staging': self.staging_group, 'qa': self.qa_group, 'dev': self.dev_group}
        add_row_map = {'production': self.prod_add_row, 'staging': self.staging_add_row, 'qa': self.qa_add_row, 'dev': self.dev_add_row}
        for env, group in env_map.items():
            key = f'config-{env}'
            add_row_map[env].connect('activated', lambda r, g=group, k=key: self.add_layer(g, k))
            self.setup_env_config(group, key)
        
        self.connect('close-request', lambda win: log.debug("PreferencesWindow close requested."))

    def load_theme(self):
        log.debug("Loading and applying theme preference.")
        theme = self.settings.get_string('theme')
        if theme == 'light':
            self.theme_row.set_selected(1)
        elif theme == 'dark':
            self.theme_row.set_selected(2)
        else:
            self.theme_row.set_selected(0)

    def on_theme_changed(self, row, param):
        log.info(f"Theme changed to index {row.get_selected()}.")
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

    def on_font_set(self, button):
        log.info("Node font changed.")
        font_string = button.get_font()
        self.settings.set_string('node-font', font_string)

    def setup_env_config(self, group, key):
        log.debug(f"Setting up configuration for group '{group.get_title()}' with key '{key}'.")
        self._layer_rows[group] = []
        self.config_manager.ensure_default_config(key)
        layers = self.config_manager.get_layers(key)
        for layer_data in layers:
            self.create_layer_row(group, key, layer_data)

    def create_layer_row(self, group, key, data, save_on_change=True):
        """Creates a LayerRow and adds it to the UI."""
        on_change_callback = (lambda: self.config_manager.save_layers(key, self._layer_rows[group])) if save_on_change else None

        row = LayerRow(
            layer_data=data,
            on_delete=lambda r: self.remove_layer(group, key, r),
            on_change=on_change_callback
        )

        if group not in self._layer_rows:
            self._layer_rows[group] = []
        self._layer_rows[group].append(row)

        add_row_map = {
            self.prod_group: self.prod_add_row,
            self.staging_group: self.staging_add_row,
            self.qa_group: self.qa_add_row,
            self.dev_group: self.dev_add_row
        }
        add_row = add_row_map.get(group)

        if add_row:
            group.remove(add_row)
            group.add(row)
            group.add(add_row)
        else:
            group.add(row)

    def add_layer(self, group, key):
        """Handles adding a new, default layer to a group."""
        log.info(f"Adding new layer to group '{group.get_title()}'.")
        new_data = {
            'name': 'New Layer',
            'description': '',
            'host_url': 'http://localhost',
            'custom_headers': {},
            'host_overrides': [],
            'path_match_only': []
        }
        self.create_layer_row(group, key, new_data)
        self.config_manager.save_layers(key, self._layer_rows[group])

    def remove_layer(self, group, key, row):
        """Handles removing a layer from a group."""
        log.info(f"Removing layer '{row.get_title()}' from group '{group.get_title()}'.")
        group.remove(row)
        if group in self._layer_rows and row in self._layer_rows[group]:
            self._layer_rows[group].remove(row)
        self.config_manager.save_layers(key, self._layer_rows[group])
