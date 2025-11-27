"""
This module handles the application preferences, including the PreferencesWindow
and configuration management via GSettings.
"""

import logging
from gi.repository import Gtk, Adw, Gio, GObject, Gdk, GLib

from .layer_widgets import LayerRow
from .exporters import ConfigExporter
from .config_manager import ConfigManager

log = logging.getLogger(__name__)


def setting_to_rgba(variant, _user_data=None):
    """Maps a GSettings GVariant(string) to a GObject.Value(Gdk.RGBA)."""
    rgba = Gdk.RGBA()
    if variant:
        rgba_string = variant.get_string()
        if rgba_string and rgba.parse(rgba_string):
            log.debug(
                "Mapping GSettings string '%s' to Gdk.RGBA.", rgba_string
            )
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
        log.debug(
            "Mapping Gdk.RGBA '%s' to GSettings string.", gdk_rgba.to_string()
        )
        return GLib.Variant("s", gdk_rgba.to_string())
    log.debug("Widget provided a None RGBA. No setting will be saved.")
    return None


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

    # New groups
    group_cdn = Gtk.Template.Child()
    group_lb = Gtk.Template.Child()
    group_proxy = Gtk.Template.Child()
    group_app = Gtk.Template.Child()

    # Add buttons
    add_cdn_row = Gtk.Template.Child()
    add_lb_row = Gtk.Template.Child()
    add_proxy_row = Gtk.Template.Child()
    add_app_row = Gtk.Template.Child()

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
        self.config_selector.connect(
            "notify::selected", self.on_config_selected
        )

        self.add_config_btn.connect("clicked", self.on_add_config)
        self.delete_config_btn.connect("clicked", self.on_delete_config)

        self.domain_name_row.connect("notify::text", self.on_details_changed)

        self.add_cdn_row.connect("activated", lambda *_: self.add_layer("CDN"))
        self.add_lb_row.connect(
            "activated", lambda *_: self.add_layer("Load Balancer")
        )
        self.add_proxy_row.connect(
            "activated", lambda *_: self.add_layer("Cache Proxy")
        )
        self.add_app_row.connect(
            "activated", lambda *_: self.add_layer("Application Backend")
        )

        self.export_row.connect("activated", self.do_export_config)
        self.import_row.connect("activated", self.do_import_config)

        self.refresh_config_list()
        self._loading = False

        self.connect(
            "close-request",
            lambda win: log.debug("PreferencesWindow close requested."),
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

        # Clear existing layers from all groups
        for row in self._layer_rows:
            parent = row.get_parent()
            if parent:
                parent.remove(row)
        self._layer_rows = []

        # Load layers into respective groups
        layers = config.get("layers", [])
        for layer_data in layers:
            self.create_layer_row(layer_data)

        # Ensure "Add" buttons are at the end of each group
        self._reorder_add_buttons()

        self._loading = False

    def _reorder_add_buttons(self):
        """Ensures Add buttons are at the end of their lists."""
        # No-op since buttons are now in separate static groups at the bottom.
        pass

    def create_layer_row(self, data):
        """Creates a LayerRow and adds it to the appropriate group."""
        row = LayerRow(
            layer_data=data,
            on_delete=self.remove_layer,
            on_change=self.save_current_config,
        )
        self._layer_rows.append(row)

        layer_type = data.get("layer_type", "CDN")
        if layer_type == "CDN":
            self.group_cdn.append(row)
        elif layer_type == "Load Balancer":
            self.group_lb.append(row)
        elif layer_type == "Cache Proxy" or layer_type == "Caching Proxy":
            # Handle legacy naming if any
            self.group_proxy.append(row)
        elif layer_type == "Application Backend" or layer_type == "Backend":
            self.group_app.append(row)
        else:
            # Fallback for unknown types - add to App or CDN?
            # Let's add to App for safety, or log warning.
            log.warning(
                "Unknown layer type '%s'. Defaulting to Application.",
                layer_type,
            )
            self.group_app.append(row)

    def on_details_changed(self, *_):
        """Callback when domain details change."""
        if self._loading or not self.current_config_id:
            return

        # We can try to update the GtkStringList but it's easier to wait for refresh or save.
        self.save_current_config()

    def save_current_config(self):
        """Saves the current UI state to the configuration."""
        if self._loading or not self.current_config_id:
            return

        # Collect layers in the enforced order: CDN -> LB -> Proxy -> App
        ordered_layers = []

        # Helper to get data from rows in a group
        def get_layers_from_group(group):
            layers = []
            # Iterate children. AdwPreferencesGroup children are not easily accessible via list?
            # We have self._layer_rows, we can filter by type or parent.
            # Filtering by parent is safer to respect visual order (if we allowed reordering).
            # But currently we don't support DnD reordering.
            # So just iterating self._layer_rows and sorting by type/group is enough?
            # No, user might expect the order within the group to matter (if we had multiple CDN layers).
            # Since we don't have DnD, the order is append-only.

            # Use `row.get_parent() == group`
            # But Gtk widget iteration is better.
            child = group.get_first_child()
            while child:
                if isinstance(child, LayerRow):
                    layers.append(child.get_data())
                child = child.get_next_sibling()
            return layers

        ordered_layers.extend(get_layers_from_group(self.group_cdn))
        ordered_layers.extend(get_layers_from_group(self.group_lb))
        ordered_layers.extend(get_layers_from_group(self.group_proxy))
        ordered_layers.extend(get_layers_from_group(self.group_app))

        data = {
            "id": self.current_config_id,
            "name": self.domain_name_row.get_text(),
            "entry_point": self.domain_name_row.get_text(),
            "layers": ordered_layers,
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
            # Use domain as host URL for CDN (first request)
            "host_url": domain,
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

    def add_layer(self, layer_type):
        """Adds a new layer to the current config."""

        # Determine default provider based on type
        provider = "Akamai"
        if layer_type == "Load Balancer":
            provider = "Nginx"
        elif layer_type == "Cache Proxy":
            provider = "Varnish"
        elif layer_type == "Application Backend":
            provider = "Apache"

        new_data = {
            "name": f"New {layer_type}",
            "description": "",
            "layer_type": layer_type,
            "provider": provider,
            "host_url": "http://localhost",
            "custom_headers": {},
            "host_overrides": [],
            "path_match_only": [],
            "routing_rules": [],
        }
        self.create_layer_row(new_data)
        self._reorder_add_buttons()
        self.save_current_config()

    def remove_layer(self, row):
        """Removes a layer."""
        parent = row.get_parent()
        if parent:
            parent.remove(row)
        self._layer_rows.remove(row)
        self.save_current_config()

    def do_export_config(self, _row):
        """Exports the current configuration."""
        if not self.current_config_id:
            return
        config = self.config_manager.get_configuration(self.current_config_id)
        # Export just layers as per previous logic, or update Exporter?
        # Let's export layers for now.
        self.exporter.export_config(
            config["layers"], on_success=self.on_export_success
        )

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
