"""
This module handles the application preferences, including the PreferencesWindow
and configuration management via GSettings.
"""

import logging
import yaml
from gi.repository import Gtk, Adw, Gio, GObject, GLib, Gdk

from .layer_widgets import LayerRow

log = logging.getLogger(__name__)


def setting_to_rgba(variant, _user_data=None):
    """Maps a GSettings GVariant(string) to a GObject.Value(Gdk.RGBA)."""
    rgba = Gdk.RGBA()
    if variant:
        rgba_string = variant.get_string()
        if rgba_string and rgba.parse(rgba_string):
            log.debug("Mapping GSettings string '%s' to Gdk.RGBA.", rgba_string)
            return GObject.Value(Gdk.RGBA, rgba)

    log.warning("Failed to parse GSettings color string '%s'. Using default.",
                variant.get_string() if variant else 'None')
    rgba.parse('rgba(0,0,0,0)')
    return GObject.Value(Gdk.RGBA, rgba)


def rgba_to_setting(gdk_rgba, _user_data=None):
    """
    Maps a Gdk.RGBA from the widget to a GVariant(string).
    Returning None tells the binding to NOT update the setting.
    """
    if gdk_rgba:
        log.debug("Mapping Gdk.RGBA '%s' to GSettings string.", gdk_rgba.to_string())
        return GLib.Variant('s', gdk_rgba.to_string())
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
        log.info("Saving configuration for key '%s'.", key)
        layers_data = [row.get_data() for row in layer_rows]
        self.save_layers_data(key, layers_data)

    def save_layers_data(self, key, layers_data):
        """Constructs a GVariant from a list of layer data dicts and saves it."""
        variant_data = []
        for l_data in layers_data:
            layer_dict = {
                'name': GLib.Variant('s', l_data.get('name', '')),
                'description': GLib.Variant('s', l_data.get('description', '')),
                'host_url': GLib.Variant('s', l_data.get('host_url', '')),
                'header_color': GLib.Variant('s', l_data.get('header_color', '')),
                'body_color': GLib.Variant('s', l_data.get('body_color', '')),
                'text_color': GLib.Variant('s', l_data.get('text_color', '')),
                'diff_text_color': GLib.Variant('s', l_data.get('diff_text_color', '')),
                'custom_headers': GLib.Variant('a{ss}', l_data.get('custom_headers', {})),
                'host_overrides': GLib.Variant('aa{ss}', l_data.get('host_overrides', [])),
                'path_match_only': GLib.Variant('as', l_data.get('path_match_only', []))
            }
            variant_data.append(layer_dict)

        try:
            variant = GLib.Variant('aa{sv}', variant_data)
            self.settings.set_value(key, variant)
        except Exception as e:  # pylint: disable=broad-exception-caught
            log.error("Error saving config for key '%s': %s", key, e)

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
                    'text_color': GLib.Variant('s', l_data.get('text_color', '')),
                    'diff_text_color': GLib.Variant('s', l_data.get('diff_text_color', '')),
                    'custom_headers': GLib.Variant('a{ss}', l_data.get('custom_headers', {})),
                    'host_overrides': GLib.Variant('aa{ss}', l_data.get('host_overrides', [])),
                    'path_match_only': GLib.Variant('as', l_data.get('path_match_only', []))
                }
                variant_data.append(layer_dict)
            try:
                variant = GLib.Variant('aa{sv}', variant_data)
                self.settings.set_value(key, variant)
            except Exception as e:  # pylint: disable=broad-exception-caught
                log.error("Error creating default config for key '%s': %s", key, e)
            log.info("No config found for '%s'. Saved default configuration.", key)


@Gtk.Template(filename='src/ui/preferences.ui')
class PreferencesWindow(Adw.PreferencesWindow):
    """
    A singleton window for managing application preferences and layer configurations.
    """
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

    prod_export_row = Gtk.Template.Child()
    prod_import_row = Gtk.Template.Child()
    staging_export_row = Gtk.Template.Child()
    staging_import_row = Gtk.Template.Child()
    qa_export_row = Gtk.Template.Child()
    qa_import_row = Gtk.Template.Child()
    dev_export_row = Gtk.Template.Child()
    dev_import_row = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        log.debug("PreferencesWindow initializing.")
        self.set_destroy_with_parent(True)
        self.settings = Gio.Settings.new('com.github.mclellac.CacheFlow')
        self.config_manager = ConfigManager(self.settings)
        self._layer_rows = {}

        self.settings.bind('dns-servers', self.dns_row, 'text',
                           Gio.SettingsBindFlags.DEFAULT)

        self.theme_row.connect('notify::selected-item', self.on_theme_changed)
        self.load_theme()

        self.font_button.set_font(self.settings.get_string('node-font'))
        self.font_button.connect('font-set', self.on_font_set)

        env_map = {'production': self.prod_group, 'staging': self.staging_group,
                   'qa': self.qa_group, 'dev': self.dev_group}
        add_row_map = {'production': self.prod_add_row, 'staging': self.staging_add_row,
                       'qa': self.qa_add_row, 'dev': self.dev_add_row}
        export_row_map = {
            'production': self.prod_export_row, 'staging': self.staging_export_row,
            'qa': self.qa_export_row, 'dev': self.dev_export_row
        }
        import_row_map = {
            'production': self.prod_import_row, 'staging': self.staging_import_row,
            'qa': self.qa_import_row, 'dev': self.dev_import_row
        }

        for env, group in env_map.items():
            key = f'config-{env}'
            add_row_map[env].connect('activated',
                                     lambda r, g=group, k=key: self.add_layer(g, k))
            export_row_map[env].connect('activated',
                                        lambda r, k=key: self.export_config(k))
            import_row_map[env].connect('activated',
                                        lambda r, g=group, k=key: self.import_config(g, k))
            self.setup_env_config(group, key)

        self.connect('close-request',
                     lambda win: log.debug("PreferencesWindow close requested."))

    def load_theme(self):
        """Loads the current theme setting."""
        log.debug("Loading and applying theme preference.")
        theme = self.settings.get_string('theme')
        if theme == 'light':
            self.theme_row.set_selected(1)
        elif theme == 'dark':
            self.theme_row.set_selected(2)
        else:
            self.theme_row.set_selected(0)

    def on_theme_changed(self, row, _param):
        """Callback when the theme selection changes."""
        log.info("Theme changed to index %d.", row.get_selected())
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
        """Callback when the node font changes."""
        log.info("Node font changed.")
        font_string = button.get_font()
        self.settings.set_string('node-font', font_string)

    def setup_env_config(self, group, key):
        """Populates the configuration group with layer rows."""
        log.debug("Setting up configuration for group '%s' with key '%s'.",
                  group.get_title(), key)
        self._layer_rows[group] = []
        self.config_manager.ensure_default_config(key)
        layers = self.config_manager.get_layers(key)
        for layer_data in layers:
            self.create_layer_row(group, key, layer_data)

    def create_layer_row(self, group, key, data, save_on_change=True):
        """Creates a LayerRow and adds it to the UI."""
        on_change_callback = (
            lambda: self.config_manager.save_layers(key, self._layer_rows[group])
        ) if save_on_change else None

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
        log.info("Adding new layer to group '%s'.", group.get_title())
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
        log.info("Removing layer '%s' from group '%s'.",
                 row.get_title(), group.get_title())
        group.remove(row)
        if group in self._layer_rows and row in self._layer_rows[group]:
            self._layer_rows[group].remove(row)
        self.config_manager.save_layers(key, self._layer_rows[group])

    def export_config(self, key):
        """Opens a file chooser to export the configuration."""
        dialog = Gtk.FileChooserNative(
            title="Export Configuration",
            transient_for=self,
            action=Gtk.FileChooserAction.SAVE
        )
        filter_yaml = Gtk.FileFilter()
        filter_yaml.set_name("YAML files")
        filter_yaml.add_pattern("*.yaml")
        filter_yaml.add_pattern("*.yml")
        dialog.add_filter(filter_yaml)

        dialog.connect("response", self.on_export_response, key)
        dialog.show()

    def on_export_response(self, dialog, response, key):
        """Callback for export dialog."""
        if response == Gtk.ResponseType.ACCEPT:
            file = dialog.get_file()
            path = file.get_path()
            try:
                layers = self.config_manager.get_layers(key)
                with open(path, 'w', encoding='utf-8') as f:
                    yaml.dump(layers, f, sort_keys=False)
                log.info("Configuration exported to %s", path)
            except Exception as e:  # pylint: disable=broad-exception-caught
                log.error("Failed to export configuration: %s", e)
        dialog.destroy()

    def import_config(self, group, key):
        """Opens a file chooser to import the configuration."""
        dialog = Gtk.FileChooserNative(
            title="Import Configuration",
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN
        )
        filter_yaml = Gtk.FileFilter()
        filter_yaml.set_name("YAML files")
        filter_yaml.add_pattern("*.yaml")
        filter_yaml.add_pattern("*.yml")
        dialog.add_filter(filter_yaml)

        dialog.connect("response", self.on_import_response, group, key)
        dialog.show()

    def on_import_response(self, dialog, response, group, key):
        """Callback for import dialog."""
        if response == Gtk.ResponseType.ACCEPT:
            file = dialog.get_file()
            path = file.get_path()
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    layers_data = yaml.safe_load(f)

                if not isinstance(layers_data, list):
                    raise ValueError("Imported data must be a list of layers.")

                # Save the new data
                self.config_manager.save_layers_data(key, layers_data)

                # Refresh the UI
                # Remove existing rows from the group (except the Add button row,
                # which is not tracked in _layer_rows)
                # But _layer_rows only tracks the LayerRows.
                rows_to_remove = self._layer_rows.get(group, [])[:]
                for row in rows_to_remove:
                    group.remove(row)

                # Setup again
                self.setup_env_config(group, key)

                log.info("Configuration imported from %s", path)
            except Exception as e:  # pylint: disable=broad-exception-caught
                log.error("Failed to import configuration: %s", e)
        dialog.destroy()
