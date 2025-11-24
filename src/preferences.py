"""
This module handles the application preferences, including the PreferencesWindow
and configuration management via GSettings.
"""

import logging
import uuid
from gi.repository import Gtk, Adw, Gio, GObject, GLib, Gdk

from .layer_widgets import LayerRow
from .exporters import ConfigExporter

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


DEFAULT_LAYERS = [
    {
        "name": "CDN_Edge",
        "description": "Akamai (External View)",
        "layer_type": "CDN",
        "provider": "Akamai",
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
        "layer_type": "Cache Proxy",
        "provider": "Varnish",
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
    }
]


class ConfigManager:
    """Handles all GSettings interactions for layer configurations."""

    def __init__(self, settings):
        self.settings = settings
        log.debug("ConfigManager initialized.")

    def get_configurations(self):
        """Returns the list of configurations (list of dicts)."""
        val = self.settings.get_value('configurations')
        configs = val.unpack()
        if not configs:
            # If empty, create a default one
            default_id = str(uuid.uuid4())
            default_config = {
                'id': GLib.Variant('s', default_id),
                'name': GLib.Variant('s', 'Example Domain'),
                'entry_point': GLib.Variant('s', 'www.example.com'),
                'layers': self._pack_layers(DEFAULT_LAYERS)
            }
            self.settings.set_value('configurations', GLib.Variant('aa{sv}', [default_config]))
            self.settings.set_string('active-config-id', default_id)
            return [{
                'id': default_id,
                'name': 'Example Domain',
                'entry_point': 'www.example.com',
                'layers': DEFAULT_LAYERS
            }]

        # Unpack layers recursively
        unpacked_configs = []
        for c in configs:
            c_dict = dict(c) # c is a dict from aa{sv}
            layers_variant = c_dict.get('layers')
            layers = layers_variant.unpack() if layers_variant else []
            unpacked_configs.append({
                'id': c_dict.get('id', ''),
                'name': c_dict.get('name', ''),
                'entry_point': c_dict.get('entry_point', ''),
                'layers': layers
            })
        return unpacked_configs

    def get_configuration(self, conf_id):
        """Returns a single configuration by ID."""
        configs = self.get_configurations()
        for c in configs:
            if c['id'] == conf_id:
                return c
        return None

    def add_configuration(self, name, entry_point):
        """Adds a new configuration."""
        configs = self.get_configurations()
        new_id = str(uuid.uuid4())
        new_conf = {
            'id': new_id,
            'name': name,
            'entry_point': entry_point,
            'layers': []
        }
        configs.append(new_conf)
        self._save_configs(configs)
        return new_id

    def delete_configuration(self, conf_id):
        """Deletes a configuration."""
        configs = self.get_configurations()
        configs = [c for c in configs if c['id'] != conf_id]
        self._save_configs(configs)

    def save_configuration(self, conf_id, data):
        """Updates a configuration."""
        configs = self.get_configurations()
        for i, c in enumerate(configs):
            if c['id'] == conf_id:
                configs[i] = data
                break
        self._save_configs(configs)

    def _save_configs(self, configs):
        """ packs and saves list of configs to GSettings."""
        variant_data = []
        for c in configs:
            c_dict = {
                'id': GLib.Variant('s', c['id']),
                'name': GLib.Variant('s', c['name']),
                'entry_point': GLib.Variant('s', c['entry_point']),
                'layers': self._pack_layers(c['layers'])
            }
            variant_data.append(c_dict)

        try:
            self.settings.set_value('configurations', GLib.Variant('aa{sv}', variant_data))
        except Exception as e:
            log.error("Error saving configurations: %s", e)

    def _pack_layers(self, layers_data):
        """Packs list of layer dicts into Variant."""
        variant_data = []
        for l_data in layers_data:
            layer_dict = {
                'name': GLib.Variant('s', l_data.get('name', '')),
                'description': GLib.Variant('s', l_data.get('description', '')),
                'layer_type': GLib.Variant('s', l_data.get('layer_type', 'CDN')),
                'provider': GLib.Variant('s', l_data.get('provider', 'Akamai')),
                'host_url': GLib.Variant('s', l_data.get('host_url', '')),
                'default_backend_host': GLib.Variant('s', l_data.get('default_backend_host', '')),
                'default_backend_host_header': GLib.Variant('s', l_data.get('default_backend_host_header', '')),
                'header_color': GLib.Variant('s', l_data.get('header_color', '')),
                'body_color': GLib.Variant('s', l_data.get('body_color', '')),
                'text_color': GLib.Variant('s', l_data.get('text_color', '')),
                'diff_text_color': GLib.Variant('s', l_data.get('diff_text_color', '')),
                'custom_headers': GLib.Variant('a{ss}', l_data.get('custom_headers', {})),
                'host_overrides': GLib.Variant('aa{ss}', l_data.get('host_overrides', [])),
                'path_match_only': GLib.Variant('as', l_data.get('path_match_only', [])),
                'routing_rules': GLib.Variant('aa{ss}', l_data.get('routing_rules', []))
            }
            variant_data.append(layer_dict)
        return GLib.Variant('aa{sv}', variant_data)


@Gtk.Template(filename='src/ui/preferences.ui')
class PreferencesWindow(Adw.PreferencesWindow):
    """
    A singleton window for managing application preferences and layer configurations.
    """
    __gtype_name__ = 'PreferencesWindow'

    theme_row = Gtk.Template.Child()
    dns_row = Gtk.Template.Child()
    font_button = Gtk.Template.Child()

    config_selector = Gtk.Template.Child()
    add_config_btn = Gtk.Template.Child()
    delete_config_btn = Gtk.Template.Child()

    domain_name_row = Gtk.Template.Child()
    entry_point_row = Gtk.Template.Child()

    layers_group = Gtk.Template.Child()
    add_layer_row = Gtk.Template.Child()

    export_row = Gtk.Template.Child()
    import_row = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        log.debug("PreferencesWindow initializing.")
        self.set_destroy_with_parent(True)
        self.settings = Gio.Settings.new('com.github.mclellac.CacheFlow')
        self.config_manager = ConfigManager(self.settings)
        self.exporter = ConfigExporter(self)
        self._layer_rows = []
        self._loading = True
        self.current_config_id = None

        self.settings.bind('dns-servers', self.dns_row, 'text',
                           Gio.SettingsBindFlags.DEFAULT)

        self.theme_row.connect('notify::selected-item', self.on_theme_changed)
        self.load_theme()

        self.font_button.set_font(self.settings.get_string('node-font'))
        self.font_button.connect('font-set', self.on_font_set)

        # Setup Config Selector
        self.config_model = Gtk.StringList()
        self.config_selector.set_model(self.config_model)
        self.config_selector.connect('notify::selected', self.on_config_selected)

        self.add_config_btn.connect('clicked', self.on_add_config)
        self.delete_config_btn.connect('clicked', self.on_delete_config)

        self.domain_name_row.connect('notify::text', self.on_details_changed)
        self.entry_point_row.connect('notify::text', self.on_details_changed)

        self.add_layer_row.connect('activated', self.add_layer)

        self.export_row.connect('activated', self.do_export_config)
        self.import_row.connect('activated', self.do_import_config)

        self.refresh_config_list()
        self._loading = False

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

    def refresh_config_list(self):
        """Refreshes the config selector model."""
        self._loading = True
        configs = self.config_manager.get_configurations()

        # Keep track of IDs in order
        self.config_ids = [c['id'] for c in configs]

        # Update model
        # Clear/Splice
        if self.config_model.get_n_items() > 0:
            self.config_model.splice(0, self.config_model.get_n_items(), [])

        for c in configs:
            self.config_model.append(c['name'])

        # Select active
        active_id = self.settings.get_string('active-config-id')
        if active_id in self.config_ids:
            idx = self.config_ids.index(active_id)
            self.config_selector.set_selected(idx)
        elif configs:
            self.config_selector.set_selected(0)
            self.settings.set_string('active-config-id', configs[0]['id'])

        self._loading = False
        self.on_config_selected(self.config_selector, None)

    def on_config_selected(self, _row, _param):
        """Callback when a configuration is selected."""
        if self._loading:
            return

        idx = self.config_selector.get_selected()
        if idx < 0 or idx >= len(self.config_ids):
            return

        self.current_config_id = self.config_ids[idx]
        self.settings.set_string('active-config-id', self.current_config_id)

        config = self.config_manager.get_configuration(self.current_config_id)
        if config:
            self.load_config_ui(config)

    def load_config_ui(self, config):
        """Loads configuration into the UI fields."""
        self._loading = True
        self.domain_name_row.set_text(config.get('name', ''))
        self.entry_point_row.set_text(config.get('entry_point', ''))

        # Clear existing layers
        for row in self._layer_rows:
            self.layers_group.remove(row)
        self._layer_rows = []

        # Load layers
        layers = config.get('layers', [])
        for layer_data in layers:
            self.create_layer_row(layer_data)

        # Re-add add button at the end
        self.layers_group.remove(self.add_layer_row)
        self.layers_group.add(self.add_layer_row)

        self._loading = False

    def create_layer_row(self, data):
        """Creates a LayerRow."""
        row = LayerRow(
            layer_data=data,
            on_delete=self.remove_layer,
            on_change=self.save_current_config
        )
        self._layer_rows.append(row)
        self.layers_group.add(row)

    def on_details_changed(self, *_args):
        """Callback when domain details change."""
        if self._loading or not self.current_config_id:
            return

        # Update name in list if changed
        new_name = self.domain_name_row.get_text()
        # We can try to update the GtkStringList but it's easier to wait for refresh or save.
        self.save_current_config()

    def save_current_config(self):
        """Saves the current UI state to the configuration."""
        if self._loading or not self.current_config_id:
            return

        layers_data = [row.get_data() for row in self._layer_rows]
        data = {
            'id': self.current_config_id,
            'name': self.domain_name_row.get_text(),
            'entry_point': self.entry_point_row.get_text(),
            'layers': layers_data
        }
        self.config_manager.save_configuration(self.current_config_id, data)

    def on_add_config(self, _btn):
        """Adds a new configuration."""
        new_id = self.config_manager.add_configuration("New Domain", "www.example.com")
        # Refresh first
        self.refresh_config_list()
        # Set active to new
        self.settings.set_string('active-config-id', new_id)
        self.refresh_config_list()

    def on_delete_config(self, _btn):
        """Deletes the current configuration."""
        if not self.current_config_id:
            return

        self.config_manager.delete_configuration(self.current_config_id)
        # The refresh will pick a new one or default
        self.refresh_config_list()

    def add_layer(self, _row):
        """Adds a new layer to the current config."""
        new_data = {
            'name': 'New Layer',
            'description': '',
            'layer_type': 'CDN',
            'provider': 'Akamai',
            'host_url': 'http://localhost',
            'custom_headers': {},
            'host_overrides': [],
            'path_match_only': [],
            'routing_rules': []
        }
        self.create_layer_row(new_data)
        self.layers_group.remove(self.add_layer_row)
        self.layers_group.add(self.add_layer_row)
        self.save_current_config()

    def remove_layer(self, row):
        """Removes a layer."""
        self.layers_group.remove(row)
        self._layer_rows.remove(row)
        self.save_current_config()

    def do_export_config(self, _row):
        """Exports the current configuration."""
        if not self.current_config_id:
            return
        config = self.config_manager.get_configuration(self.current_config_id)
        # Export just layers as per previous logic, or update Exporter?
        # Let's export layers for now.
        self.exporter.export_config(config['layers'], on_success=self.on_export_success)

    def on_export_success(self, filepath):
        """Callback when configuration is exported."""
        self.add_toast(Adw.Toast.new(f"Exported to {filepath}"))

    def do_import_config(self, _row):
        """Imports the configuration."""
        self.exporter.import_config(self.on_config_imported)

    def on_config_imported(self, layers_data):
        """Callback when configuration is imported."""
        # This replaces layers of current config
        if not self.current_config_id:
            return

        # We assume import is just layers list for now
        # Update current config
        config = self.config_manager.get_configuration(self.current_config_id)
        config['layers'] = layers_data
        self.config_manager.save_configuration(self.current_config_id, config)

        # Refresh UI
        self.load_config_ui(config)
        self.add_toast(Adw.Toast.new("Configuration imported"))
