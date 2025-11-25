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

    log.warning(
        "Failed to parse GSettings color string '%s'. Using default.",
        variant.get_string() if variant else "None",
    )
    rgba.parse("rgba(0,0,0,0)")
    return GObject.Value(Gdk.RGBA, rgba)


def rgba_to_setting(gdk_rgba, _user_data=None):
    """
    Maps a Gdk.RGBA from the widget to a GVariant(string).
    Returning None tells the binding to NOT update the setting.
    """
    if gdk_rgba:
        log.debug("Mapping Gdk.RGBA '%s' to GSettings string.", gdk_rgba.to_string())
        return GLib.Variant("s", gdk_rgba.to_string())
    log.debug("Widget provided a None RGBA. No setting will be saved.")
    return None


def _pack_as_variant(data):
    """Recursively packs a dict into a GLib.Variant."""
    variant_dict = {}
    for key, value in data.items():
        if isinstance(value, dict):
            variant_dict[key] = GLib.Variant("a{sv}", _pack_as_variant(value))
        elif isinstance(value, list):
            # Assuming list of strings for now
            variant_dict[key] = GLib.Variant("as", value)
        else:
            variant_dict[key] = GLib.Variant("s", str(value))
    return variant_dict


DEFAULT_LAYERS = [
    {
        "name": "CDN_Edge",
        "description": "Akamai (External View)",
        "layer_type": "CDN",
        "provider": "Akamai",
        "host_url": "https://www.example.com",
        "default_backend_host": "cache.examplefarm.com",
        "default_backend_host_header": "origin.example.com",
        "custom_headers": {
            "Pragma": "akamai-x-get-request-id, akamai-x-cache-on, akamai-x-cache-key"
        },
        "host_overrides": [],
        "path_match_only": [],
        "origin_rules": [],
    },
    {
        "name": "Infra_Cache",
        "description": "Varnish (Internal Cache Layer)",
        "layer_type": "Cache Proxy",
        "provider": "Varnish",
        "host_url": "http://cache.examplefarm.com",
        "default_backend_host": "",
        "default_backend_host_header": "",
        "custom_headers": {
            "X-Varnish-Debug": "true",
            "X-Origin-Auth": "secret-token-123",
        },
        "host_overrides": [
            {"path_pattern": "/api/*", "host_header": "api-internal.example.com"}
        ],
        "path_match_only": [],
        "origin_rules": [],
        "varnish_backends": [],
    },
]


class ConfigManager:
    """Handles all GSettings interactions for layer configurations."""

    def __init__(self, settings):
        self.settings = settings
        log.debug("ConfigManager initialized.")

    def get_configurations(self):
        """Returns the list of configurations (list of dicts)."""
        val = self.settings.get_value("configurations")
        configs_list = val.unpack()
        if not configs_list or not configs_list[0]:
            # If empty, create a default one
            default_id = str(uuid.uuid4())
            default_config = {
                "id": GLib.Variant("s", default_id),
                "name": GLib.Variant("s", "Example Domain"),
                "layers": self._pack_layers(DEFAULT_LAYERS),
            }
            # The schema is aa{sv}, so we wrap our list of configs in another list
            self.settings.set_value(
                "configurations", GLib.Variant("aa{sv}", [[default_config]])
            )
            self.settings.set_string("active-config-id", default_id)
            return [
                {"id": default_id, "name": "Example Domain", "layers": DEFAULT_LAYERS}
            ]

        # Data migration: Check for old a{sv} format vs new aa{sv}
        configs = []
        configs_updated = False
        if configs_list and isinstance(configs_list[0], dict):
            # This is the old format, a{sv}, which unpacks to a list of dicts.
            configs = configs_list
            configs_updated = True
        elif configs_list and isinstance(configs_list[0], list):
            # This is the new format, aa{sv}, which unpacks to a list containing one list of dicts.
            configs = configs_list[0]
        else:
            # The configuration is empty or corrupted.
            configs_updated = True # Force a re-save to default

        if not configs:
            # Handle case where configs is `[[]]` or corrupted
            default_id = str(uuid.uuid4())
            default_config_dict = {
                "id": default_id,
                "name": "Example Domain",
                "layers": DEFAULT_LAYERS,
            }
            self._save_configs([default_config_dict])
            self.settings.set_string("active-config-id", default_id)
            return [default_config_dict]

        # Unpack layers recursively
        unpacked_configs = []
        for c in configs:
            c_dict = {k: v for k, v in c.items()}
            layers_variant = c_dict.get("layers")
            if isinstance(layers_variant, GLib.Variant):
                layers = layers_variant.unpack()
            else:
                layers = layers_variant if layers_variant else []

            # Data migration from routing_rules to origin_rules
            for layer in layers:
                if "routing_rules" in layer:
                    configs_updated = True
                    routing_rules = layer.pop("routing_rules")
                    layer["origin_rules"] = []

                    # Group rules by origin
                    grouped_origins = {}
                    for rule in routing_rules:
                        origin_key = (
                            rule.get("backend_host", ""),
                            rule.get("backend_host_header", ""),
                        )
                        if origin_key not in grouped_origins:
                            grouped_origins[origin_key] = {
                                "origin_host": origin_key[0],
                                "origin_host_header": origin_key[1],
                                "path_matches": [],
                                "domain_matches": [],
                            }
                        grouped_origins[origin_key]["path_matches"].append(
                            rule.get("path_match", "")
                        )

                    layer["origin_rules"] = list(grouped_origins.values())

            # entry_point is deprecated/removed, use name (Domain Name)
            unpacked_configs.append(
                {
                    "id": c_dict.get("id", ""),
                    "name": c_dict.get("name", ""),
                    "entry_point": c_dict.get("name", ""),
                    "layers": layers,
                }
            )

        if configs_updated:
            self._save_configs(unpacked_configs)

        return unpacked_configs

    def get_configuration(self, conf_id):
        """Returns a single configuration by ID."""
        configs = self.get_configurations()
        for c in configs:
            if c["id"] == conf_id:
                return c
        return None

    def add_configuration(self, name, entry_point, layers=None):
        """Adds a new configuration."""
        configs = self.get_configurations()
        new_id = str(uuid.uuid4())
        new_conf = {
            "id": new_id,
            "name": name,
            "entry_point": entry_point,
            "layers": layers if layers else [],
        }
        configs.append(new_conf)
        self._save_configs(configs)
        return new_id

    def delete_configuration(self, conf_id):
        """Deletes a configuration."""
        configs = self.get_configurations()
        configs = [c for c in configs if c["id"] != conf_id]
        self._save_configs(configs)

    def save_configuration(self, conf_id, data):
        """Updates a configuration."""
        configs = self.get_configurations()
        for i, c in enumerate(configs):
            if c["id"] == conf_id:
                configs[i] = data
                break
        self._save_configs(configs)

    def _save_configs(self, configs):
        """packs and saves list of configs to GSettings."""
        variant_data = []
        for c in configs:
            c_dict = {
                "id": GLib.Variant("s", c["id"]),
                "name": GLib.Variant("s", c["name"]),
                # entry_point is duplicate of name (Domain Name), so we don't save it anymore
                "layers": self._pack_layers(c["layers"]),
            }
            variant_data.append(c_dict)

        try:
            # The schema is aa{sv}, so we wrap our list of configs in another list
            self.settings.set_value(
                "configurations", GLib.Variant("aa{sv}", [variant_data])
            )
        except GLib.Error as e:
            log.error("Error saving configurations to GSettings: %s", e)

    def _pack_layers(self, layers_data):
        """Packs list of layer dicts into Variant."""
        variant_data = []
        for l_data in layers_data:
            layer_dict = {
                "name": GLib.Variant("s", l_data.get("name", "")),
                "description": GLib.Variant("s", l_data.get("description", "")),
                "layer_type": GLib.Variant("s", l_data.get("layer_type", "CDN")),
                "provider": GLib.Variant("s", l_data.get("provider", "Akamai")),
                "host_url": GLib.Variant("s", l_data.get("host_url", "")),
                "default_backend_host": GLib.Variant(
                    "s", l_data.get("default_backend_host", "")
                ),
                "default_backend_host_header": GLib.Variant(
                    "s", l_data.get("default_backend_host_header", "")
                ),
                "header_color": GLib.Variant("s", l_data.get("header_color", "")),
                "body_color": GLib.Variant("s", l_data.get("body_color", "")),
                "text_color": GLib.Variant("s", l_data.get("text_color", "")),
                "diff_text_color": GLib.Variant("s", l_data.get("diff_text_color", "")),
                "custom_headers": GLib.Variant(
                    "a{ss}", l_data.get("custom_headers", {})
                ),
                "host_overrides": GLib.Variant(
                    "a{ss}", l_data.get("host_overrides", [])
                ),
                "path_match_only": GLib.Variant(
                    "as", l_data.get("path_match_only", [])
                ),
                "origin_rules": GLib.Variant(
                    "a{sv}",
                    [
                        {
                            "origin_host": GLib.Variant("s", r.get("origin_host", "")),
                            "origin_host_header": GLib.Variant(
                                "s", r.get("origin_host_header", "")
                            ),
                            "path_matches": GLib.Variant(
                                "as", r.get("path_matches", [])
                            ),
                            "domain_matches": GLib.Variant(
                                "as", r.get("domain_matches", [])
                            ),
                        }
                        for r in l_data.get("origin_rules", [])
                    ],
                ),
                "varnish_backends": GLib.Variant(
                    "aa{sv}", l_data.get("varnish_backends", [])
                ),
            }
            variant_data.append(layer_dict)

        return GLib.Variant("a{sv}", variant_data)

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
                    "name": GLib.Variant("s", l_data.get("name", "")),
                    "description": GLib.Variant("s", l_data.get("description", "")),
                    "layer_type": GLib.Variant("s", l_data.get("layer_type", "CDN")),
                    "provider": GLib.Variant("s", l_data.get("provider", "Akamai")),
                    "host_url": GLib.Variant("s", l_data.get("host_url", "")),
                    "default_backend_host": GLib.Variant(
                        "s", l_data.get("default_backend_host", "")
                    ),
                    "default_backend_host_header": GLib.Variant(
                        "s", l_data.get("default_backend_host_header", "")
                    ),
                    "header_color": GLib.Variant("s", l_data.get("header_color", "")),
                    "body_color": GLib.Variant("s", l_data.get("body_color", "")),
                    "text_color": GLib.Variant("s", l_data.get("text_color", "")),
                    "diff_text_color": GLib.Variant(
                        "s", l_data.get("diff_text_color", "")
                    ),
                    "custom_headers": GLib.Variant(
                        "a{ss}", l_data.get("custom_headers", {})
                    ),
                    "host_overrides": GLib.Variant(
                        "aa{ss}", l_data.get("host_overrides", [])
                    ),
                    "path_match_only": GLib.Variant(
                        "as", l_data.get("path_match_only", [])
                    ),
                    "origin_rules": GLib.Variant(
                        "aa{sv}", l_data.get("origin_rules", [])
                    ),
                    "varnish_backends": GLib.Variant(
                        "aa{sv}", l_data.get("varnish_backends", [])
                    ),
                }
                variant_data.append(layer_dict)
            try:
                variant = GLib.Variant("aa{sv}", variant_data)
                self.settings.set_value(key, variant)
            except Exception as e:  # pylint: disable=broad-exception-caught
                log.error("Error creating default config for key '%s': %s", key, e)
            log.info("No config found for '%s'. Saved default configuration.", key)


@Gtk.Template(filename="src/ui/add_config_dialog.ui")
class AddConfigDialog(Adw.Window):
    """Dialog to add a new domain configuration."""

    __gtype_name__ = "AddConfigDialog"

    domain_name_entry = Gtk.Template.Child()
    add_btn = Gtk.Template.Child()
    cancel_btn = Gtk.Template.Child()

    def __init__(self, parent_window, on_add_callback):
        super().__init__(transient_for=parent_window)
        self.on_add = on_add_callback
        self.add_btn.connect("clicked", self.on_add_clicked)
        self.cancel_btn.connect("clicked", lambda *_: self.close())

    def on_add_clicked(self, _btn):
        """Callback when Add is clicked."""
        domain = self.domain_name_entry.get_text()
        if domain:
            self.on_add(domain)
            self.close()


@Gtk.Template(filename="src/ui/preferences.ui")
class PreferencesWindow(Adw.PreferencesWindow):
    """
    A singleton window for managing application preferences and layer configurations.
    """

    __gtype_name__ = "PreferencesWindow"

    theme_row = Gtk.Template.Child()
    ssl_row = Gtk.Template.Child()
    dns_row = Gtk.Template.Child()
    font_button = Gtk.Template.Child()

    config_selector = Gtk.Template.Child()
    add_config_btn = Gtk.Template.Child()
    delete_config_btn = Gtk.Template.Child()

    domain_name_row = Gtk.Template.Child()

    layers_group = Gtk.Template.Child()
    add_layer_row = Gtk.Template.Child()

    export_row = Gtk.Template.Child()
    import_row = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        log.debug("PreferencesWindow initializing.")
        self.set_destroy_with_parent(True)
        self.settings = Gio.Settings.new("com.github.mclellac.CacheFlow")
        self.config_manager = ConfigManager(self.settings)
        self.exporter = ConfigExporter(self)
        self._layer_rows = []
        self._loading = True
        self.current_config_id = None

        self.settings.bind(
            "dns-servers", self.dns_row, "text", Gio.SettingsBindFlags.DEFAULT
        )
        self.settings.bind(
            "verify-ssl", self.ssl_row, "active", Gio.SettingsBindFlags.DEFAULT
        )

        self.theme_row.connect("notify::selected-item", self.on_theme_changed)
        self.load_theme()

        self.font_button.set_font(self.settings.get_string("node-font"))
        self.font_button.connect("font-set", self.on_font_set)

        # Setup Config Selector
        self.config_model = Gtk.StringList()
        self.config_selector.set_model(self.config_model)
        self.config_selector.connect("notify::selected", self.on_config_selected)

        self.add_config_btn.connect("clicked", self.on_add_config)
        self.delete_config_btn.connect("clicked", self.on_delete_config)

        self.domain_name_row.connect("notify::text", self.on_details_changed)

        self.add_layer_row.connect("activated", self.add_layer)

        self.export_row.connect("activated", self.do_export_config)
        self.import_row.connect("activated", self.do_import_config)

        self.refresh_config_list()
        self._loading = False

        self.connect(
            "close-request", lambda win: log.debug("PreferencesWindow close requested.")
        )

    def load_theme(self):
        """Loads the current theme setting."""
        log.debug("Loading and applying theme preference.")
        theme = self.settings.get_string("theme")
        if theme == "light":
            self.theme_row.set_selected(1)
        elif theme == "dark":
            self.theme_row.set_selected(2)
        else:
            self.theme_row.set_selected(0)

    def on_theme_changed(self, row, _param):
        """Callback when the theme selection changes."""
        log.info("Theme changed to index %d.", row.get_selected())
        selected = row.get_selected()
        style_manager = Adw.StyleManager.get_default()
        if selected == 1:
            self.settings.set_string("theme", "light")
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        elif selected == 2:
            self.settings.set_string("theme", "dark")
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            self.settings.set_string("theme", "system")
            style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)

    def on_font_set(self, button):
        """Callback when the node font changes."""
        log.info("Node font changed.")
        font_string = button.get_font()
        self.settings.set_string("node-font", font_string)

    def refresh_config_list(self):
        """Refreshes the config selector model."""
        self._loading = True
        configs = self.config_manager.get_configurations()

        # Keep track of IDs in order
        self.config_ids = [c["id"] for c in configs]

        # Update model
        # Clear/Splice
        if self.config_model.get_n_items() > 0:
            self.config_model.splice(0, self.config_model.get_n_items(), [])

        for c in configs:
            self.config_model.append(c["name"])

        # Select active
        active_id = self.settings.get_string("active-config-id")
        if active_id in self.config_ids:
            idx = self.config_ids.index(active_id)
            self.config_selector.set_selected(idx)
        elif configs:
            self.config_selector.set_selected(0)
            self.settings.set_string("active-config-id", configs[0]["id"])

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
        self.settings.set_string("active-config-id", self.current_config_id)

        config = self.config_manager.get_configuration(self.current_config_id)
        if config:
            self.load_config_ui(config)

    def load_config_ui(self, config):
        """Loads configuration into the UI fields."""
        self._loading = True
        self.domain_name_row.set_text(config.get("name", ""))

        # Clear existing layers
        for row in self._layer_rows:
            self.layers_group.remove(row)
        self._layer_rows = []

        # Load layers
        layers = config.get("layers", [])
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
            on_change=self.save_current_config,
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
            "id": self.current_config_id,
            "name": self.domain_name_row.get_text(),
            "entry_point": self.domain_name_row.get_text(),
            "layers": layers_data,
        }
        self.config_manager.save_configuration(self.current_config_id, data)

    def on_add_config(self, _btn):
        """Adds a new configuration."""
        dialog = AddConfigDialog(self, self.do_add_config)
        dialog.present()

    def do_add_config(self, domain):
        """Actually adds the config after dialog confirms."""
        # Create default CDN layer
        default_cdn_layer = {
            "name": "CDN",
            "description": "CDN Layer for " + domain,
            "layer_type": "CDN",
            "provider": "Akamai",  # Default provider
            "host_url": domain,  # Use domain as host URL for CDN (first request)
            "custom_headers": {},
            "host_overrides": [],
            "path_match_only": [],
            "routing_rules": [],
        }

        new_id = self.config_manager.add_configuration(
            domain, domain, layers=[default_cdn_layer]
        )

        # Refresh first
        self.refresh_config_list()
        # Set active to new
        self.settings.set_string("active-config-id", new_id)
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
            "name": "New Layer",
            "description": "",
            "layer_type": "CDN",
            "provider": "Akamai",
            "host_url": "http://localhost",
            "custom_headers": {},
            "host_overrides": [],
            "path_match_only": [],
            "routing_rules": [],
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
        self.exporter.export_config(config["layers"], on_success=self.on_export_success)

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
        config["layers"] = layers_data
        self.config_manager.save_configuration(self.current_config_id, config)

        # Refresh UI
        self.load_config_ui(config)
        self.add_toast(Adw.Toast.new("Configuration imported"))
