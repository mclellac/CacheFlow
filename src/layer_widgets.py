"""
This module defines custom widgets used in the Layer configuration UI,
including the LayerRow for editing layer details.
"""

from gi.repository import Gtk, Adw, Gdk
from .providers.base import ProviderType
from .providers import get_providers_by_type

# Default Colors Constants
DEFAULT_LAYER_COLORS = {
    ProviderType.CDN: {
        "header_color": "#613583", # Purple 5
        "body_color": "#9141ac",   # Purple 4
    },
    ProviderType.LOAD_BALANCER: {
        "header_color": "#1c71d8", # Blue 4
        "body_color": "#3584e4",   # Blue 3
    },
    ProviderType.CACHE_PROXY: {
        "header_color": "#e66100", # Orange 4
        "body_color": "#ff7800",   # Orange 3
    },
    ProviderType.APP_BACKEND: {
        "header_color": "#26a269", # Green 5
        "body_color": "#2ec27e",   # Green 4
    },
}

DEFAULT_DIFF_COLORS = {
    "added_text_color": "#2ec27e",   # Green 4
    "modified_text_color": "#e66100", # Orange 4
    "removed_text_color": "#e01b24",  # Red 4
}


class ConfigRowMixin:
    """Mixin for configuration rows with change and delete handling."""

    def setup_mixin(self, on_change=None, on_delete=None):
        """Sets up the mixin with callback functions."""
        self.on_change = on_change
        self.on_delete = on_delete

        if hasattr(self, "delete_btn"):
            self.delete_btn.connect("clicked", self.on_delete_clicked)

    def notify_change(self, *_args):
        """Notifies when data changes."""
        if getattr(self, "on_change", None):
            self.on_change()

    def on_delete_clicked(self, _btn):
        """Callback for delete button."""
        if getattr(self, "on_delete", None):
            self.on_delete(self)


class BaseEntryRow(ConfigRowMixin, Adw.PreferencesRow):
    """Base class for rows with text entries."""

    __gtype_name__ = "BaseEntryRow"

    def __init__(self, on_change=None, on_delete=None, **kwargs):
        super().__init__(**kwargs)
        self.setup_mixin(on_change, on_delete)
        self.entries = []

    def setup_entries(self, texts):
        """Sets up the entries with initial texts and connects change signals."""
        for entry, text in zip(self.entries, texts):
            entry.set_text(text)
            entry.connect("changed", self.notify_change)

    def get_texts(self):
        """Returns a list of texts from the entries."""
        return [entry.get_text() for entry in self.entries]


@Gtk.Template(filename="src/ui/header_row.ui")
class HeaderRow(BaseEntryRow):
    """Row for editing a single header key-value pair."""

    __gtype_name__ = "HeaderRow"

    key_entry = Gtk.Template.Child()
    val_entry = Gtk.Template.Child()
    delete_btn = Gtk.Template.Child()

    def __init__(
        self, key="", value="", on_change=None, on_delete=None, **kwargs
    ):
        super().__init__(on_change=on_change, on_delete=on_delete, **kwargs)
        self.entries = [self.key_entry, self.val_entry]
        self.setup_entries([key, value])


@Gtk.Template(filename="src/ui/override_row.ui")
class OverrideRow(BaseEntryRow):
    """Row for editing a host override."""

    __gtype_name__ = "OverrideRow"

    pat_entry = Gtk.Template.Child()
    host_entry = Gtk.Template.Child()
    delete_btn = Gtk.Template.Child()

    def __init__(
        self, pattern="", host="", on_change=None, on_delete=None, **kwargs
    ):
        super().__init__(on_change=on_change, on_delete=on_delete, **kwargs)
        self.entries = [self.pat_entry, self.host_entry]
        self.setup_entries([pattern, host])


@Gtk.Template(filename="src/ui/path_match_row.ui")
class PathMatchRow(BaseEntryRow):
    """Row for editing a path match pattern."""

    __gtype_name__ = "PathMatchRow"

    pat_entry = Gtk.Template.Child()
    delete_btn = Gtk.Template.Child()

    def __init__(self, pattern="", on_change=None, on_delete=None, **kwargs):
        super().__init__(on_change=on_change, on_delete=on_delete, **kwargs)
        self.entries = [self.pat_entry]
        self.setup_entries([pattern])


@Gtk.Template(filename="src/ui/domain_match_row.ui")
class DomainMatchRow(BaseEntryRow):
    """Row for editing a domain match pattern."""

    __gtype_name__ = "DomainMatchRow"

    pat_entry = Gtk.Template.Child()
    delete_btn = Gtk.Template.Child()

    def __init__(self, pattern="", on_change=None, on_delete=None, **kwargs):
        super().__init__(on_change=on_change, on_delete=on_delete, **kwargs)
        self.entries = [self.pat_entry]
        self.setup_entries([pattern])


@Gtk.Template(filename="src/ui/node_row.ui")
class NodeRow(ConfigRowMixin, Adw.ExpanderRow):
    """Row for editing a sibling node (Proxy/Backend)."""

    __gtype_name__ = "NodeRow"

    name_entry = Gtk.Template.Child()
    host_entry = Gtk.Template.Child()
    match_group = Gtk.Template.Child()
    match_header_entry = Gtk.Template.Child()
    match_value_entry = Gtk.Template.Child()
    provider_row = Gtk.Template.Child()
    header_color_button = Gtk.Template.Child()
    body_color_button = Gtk.Template.Child()
    delete_btn = Gtk.Template.Child()

    def __init__(self, node_data=None, layer_type=ProviderType.CDN, on_change=None, on_delete=None, **kwargs):
        super().__init__(**kwargs)
        self.setup_mixin(on_change, on_delete)
        self._loading = True
        self.layer_type = layer_type

        # Setup provider model
        self.provider_model = Gtk.StringList()
        self.provider_row.set_model(self.provider_model)

        self.name_entry.connect("notify::text", self.on_name_changed)
        self.host_entry.connect("notify::text", self.notify_change)
        self.match_header_entry.connect("notify::text", self.notify_change)
        self.match_value_entry.connect("notify::text", self.notify_change)
        self.provider_row.connect("notify::selected", self.notify_change)
        self.header_color_button.connect("color-set", self.notify_change)
        self.body_color_button.connect("color-set", self.notify_change)

        self._update_visibility()

        if node_data:
            self.load_data(node_data)
        else:
            self.on_name_changed(self.name_entry) # Set initial title

            # Init default colors to transparent if not set
            if not self.header_color_button.get_rgba():
                self.header_color_button.set_rgba(Gdk.RGBA(0, 0, 0, 0))
            if not self.body_color_button.get_rgba():
                self.body_color_button.set_rgba(Gdk.RGBA(0, 0, 0, 0))

        self._loading = False

    def _update_visibility(self):
        """Update visibility of fields based on layer type."""
        is_cache_proxy = self.layer_type == ProviderType.CACHE_PROXY
        is_backend = self.layer_type == ProviderType.APP_BACKEND

        self.match_group.set_visible(is_cache_proxy)
        self.provider_row.set_visible(is_backend)

        if is_backend:
             # Populate providers if backend
            providers = get_providers_by_type(ProviderType.APP_BACKEND)
            if self.provider_model.get_n_items() == 0:
                for p in providers:
                    self.provider_model.append(p.name)
                # Static list of cloud providers as fallbacks
                known_names = [p.name for p in providers]
                for cloud in ["AWS", "Azure", "Google Cloud", "OpenShift", "VM"]:
                    if cloud not in known_names:
                        self.provider_model.append(cloud)

    def on_name_changed(self, entry, *_args):
        text = entry.get_text()
        self.set_title(text if text else "New Node")
        self.notify_change()

    def load_data(self, data):
        self.name_entry.set_text(data.get("name", ""))
        self.host_entry.set_text(data.get("host_url", ""))
        self.match_header_entry.set_text(data.get("match_header", ""))
        self.match_value_entry.set_text(data.get("match_value", ""))

        provider = data.get("provider", "")
        if provider:
            # Find index
            found = False
            for i in range(self.provider_model.get_n_items()):
                if self.provider_model.get_string(i) == provider:
                    self.provider_row.set_selected(i)
                    found = True
                    break
            if not found:
                self.provider_model.append(provider)
                self.provider_row.set_selected(self.provider_model.get_n_items() - 1)

        for key, btn in [("header_color", self.header_color_button), ("body_color", self.body_color_button)]:
            rgba = Gdk.RGBA()
            if not (data.get(key) and rgba.parse(data[key])):
                rgba.parse("rgba(0,0,0,0)")
            btn.set_rgba(rgba)

    def get_data(self):
        prov_idx = self.provider_row.get_selected()
        provider = ""
        if prov_idx != -1 and prov_idx < self.provider_model.get_n_items():
            provider = self.provider_model.get_string(prov_idx)

        return {
            "name": self.name_entry.get_text(),
            "host_url": self.host_entry.get_text(),
            "match_header": self.match_header_entry.get_text(),
            "match_value": self.match_value_entry.get_text(),
            "provider": provider,
            "header_color": self.header_color_button.get_rgba().to_string(),
            "body_color": self.body_color_button.get_rgba().to_string(),
        }


@Gtk.Template(filename="src/ui/origin_rule_row.ui")
class OriginRuleRow(ConfigRowMixin, Adw.ExpanderRow):
    """Row for editing a backend destination and its associated path matches."""

    __gtype_name__ = "OriginRuleRow"

    host_entry = Gtk.Template.Child()
    host_header_entry = Gtk.Template.Child()
    rewrite_entry = Gtk.Template.Child()
    path_match_group = Gtk.Template.Child()
    add_path_btn = Gtk.Template.Child()
    domain_match_group = Gtk.Template.Child()
    add_domain_btn = Gtk.Template.Child()
    delete_btn = Gtk.Template.Child()

    def __init__(
        self,
        origin_data=None,
        label_prefix="Backend",
        on_change=None,
        on_delete=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.setup_mixin(on_change, on_delete)
        self._loading = True
        self.label_prefix = label_prefix

        self.path_match_rows = []
        self.domain_match_rows = []

        self.host_entry.connect("changed", self.on_backend_host_changed)
        self.host_header_entry.connect("changed", self.notify_change)
        self.rewrite_entry.connect("changed", self.notify_change)
        self.add_path_btn.connect("clicked", self.on_add_path_clicked)
        self.add_domain_btn.connect("clicked", self.on_add_domain_clicked)

        if origin_data:
            self.load_data(origin_data)
        else:
            # Set initial title for new rows
            self.on_backend_host_changed(self.host_entry)

        self._loading = False

    def set_label_prefix(self, prefix):
        """Updates the label prefix and refreshes UI."""
        self.label_prefix = prefix
        self.on_backend_host_changed(self.host_entry)

    def on_backend_host_changed(self, entry):
        """Updates the row title and notifies of change."""
        host = entry.get_text()
        self.set_title(
            f"{self.label_prefix}: {host}"
            if host
            else f"{self.label_prefix}: (Not Set)"
        )
        self.domain_match_group.set_visible(self.label_prefix == "Origin")
        self.notify_change()

    def load_data(self, data):
        """Loads backend data into the UI."""
        self.host_entry.set_text(data.get("backend_host", ""))
        self.host_header_entry.set_text(data.get("backend_host_header", ""))
        self.rewrite_entry.set_text(data.get("path_rewrite", ""))
        self.on_backend_host_changed(self.host_entry)  # Update title

        for path in data.get("path_matches", []):
            self.add_path_match_row(pattern=path)

        for domain in data.get("domain_matches", []):
            self.add_domain_match_row(pattern=domain)

        self.update_subtitle()

    def on_add_path_clicked(self, _btn):
        """Callback to add a new path match row."""
        self.add_path_match_row()
        self.notify_change()

    def add_path_match_row(self, pattern=""):
        """Adds a path match entry row."""
        row = PathMatchRow(
            pattern=pattern,
            on_change=self.notify_change,
            on_delete=self.remove_path_match_row,
        )
        self.path_match_group.add(row)
        self.path_match_rows.append(row)
        self.update_subtitle()

    def remove_path_match_row(self, row):
        """Removes a path match entry row."""
        self.path_match_group.remove(row)
        self.path_match_rows.remove(row)
        self.notify_change()
        self.update_subtitle()

    def on_add_domain_clicked(self, _btn):
        """Callback to add a new domain match row."""
        self.add_domain_match_row()
        self.notify_change()

    def add_domain_match_row(self, pattern=""):
        """Adds a domain match entry row."""
        row = DomainMatchRow(
            pattern=pattern,
            on_change=self.notify_change,
            on_delete=self.remove_domain_match_row,
        )
        self.domain_match_group.add(row)
        self.domain_match_rows.append(row)
        self.update_subtitle()

    def remove_domain_match_row(self, row):
        """Removes a domain match entry row."""
        self.domain_match_group.remove(row)
        self.domain_match_rows.remove(row)
        self.notify_change()
        self.update_subtitle()

    def update_subtitle(self):
        """Updates the subtitle with the number of paths and domains."""
        p_count = len(self.path_match_rows)
        d_count = len(self.domain_match_rows)
        p_text = f"{p_count} Path{'s' if p_count != 1 else ''}"
        d_text = f"{d_count} Domain{'s' if d_count != 1 else ''}"
        self.set_subtitle(f"{p_text}, {d_text}")

    def get_data(self):
        """Returns the backend and path/domain data."""
        return {
            "backend_host": self.host_entry.get_text(),
            "backend_host_header": self.host_header_entry.get_text(),
            "path_rewrite": self.rewrite_entry.get_text(),
            "path_matches": [
                row.get_texts()[0]
                for row in self.path_match_rows
                if row.get_texts()[0]
            ],
            "domain_matches": [
                row.get_texts()[0]
                for row in self.domain_match_rows
                if row.get_texts()[0]
            ],
        }


@Gtk.Template(filename="src/ui/layer_row.ui")
class LayerRow(Adw.PreferencesGroup):
    """
    A widget representing a single configuration layer in the settings.
    Allows editing of layer properties like URL, headers, and colors.
    """

    __gtype_name__ = "LayerRow"

    type_row = Gtk.Template.Child()
    provider_row = Gtk.Template.Child()
    name_row = Gtk.Template.Child()
    desc_row = Gtk.Template.Child()
    url_row = Gtk.Template.Child()

    nodes_group = Gtk.Template.Child()
    add_node_btn = Gtk.Template.Child()

    header_color_button = Gtk.Template.Child()
    body_color_button = Gtk.Template.Child()

    text_color_button = Gtk.Template.Child()
    added_text_color_button = Gtk.Template.Child()
    removed_text_color_button = Gtk.Template.Child()
    modified_text_color_button = Gtk.Template.Child()

    headers_group = Gtk.Template.Child()
    add_header_btn = Gtk.Template.Child()

    overrides_group = Gtk.Template.Child()
    add_override_btn = Gtk.Template.Child()

    path_match_group = Gtk.Template.Child()
    add_path_match_btn = Gtk.Template.Child()

    routing_rules_group = Gtk.Template.Child()
    add_routing_rule_btn = Gtk.Template.Child()

    # Flattened Default Backend Group (Removed AdwExpanderRow)
    default_backend_host_row = Gtk.Template.Child()
    default_backend_header_row = Gtk.Template.Child()

    delete_btn = Gtk.Template.Child()

    def __init__(self, layer_data=None, on_delete=None, on_change=None):
        super().__init__()
        self._loading = True

        self.on_delete_callback = on_delete
        self.on_change_callback = on_change

        self.header_rows = []
        self.override_rows = []
        self.path_match_rows = []
        self.origin_rule_rows = []
        self.node_rows = []

        # Setup Models for Type and Provider
        self.type_model = Gtk.StringList()
        self.provider_model = Gtk.StringList()

        # Populate Type Model
        self.types_list = list(ProviderType)
        for t in self.types_list:
            self.type_model.append(t.value)

        self.type_row.set_model(self.type_model)
        self.provider_row.set_model(self.provider_model)

        self.type_row.connect("notify::selected", self.on_type_changed)
        self.provider_row.connect("notify::selected", self.on_provider_changed)

        self.delete_btn.connect("clicked", self.on_delete_clicked)

        self.name_row.connect("notify::text", self.on_changed)
        self.desc_row.connect("notify::text", self.on_changed)
        self.url_row.connect("notify::text", self.on_changed)
        self.default_backend_host_row.connect("notify::text", self.on_changed)
        self.default_backend_header_row.connect(
            "notify::text", self.on_changed
        )
        self.header_color_button.connect("color-set", self.on_changed)
        self.body_color_button.connect("color-set", self.on_changed)
        self.text_color_button.connect("color-set", self.on_changed)
        self.added_text_color_button.connect("color-set", self.on_changed)
        self.removed_text_color_button.connect("color-set", self.on_changed)
        self.modified_text_color_button.connect("color-set", self.on_changed)

        self.add_header_btn.connect("clicked", self.on_add_header)
        self.add_override_btn.connect("clicked", self.on_add_override)
        self.add_path_match_btn.connect("clicked", self.on_add_path_match)
        self.add_routing_rule_btn.connect("clicked", self.on_add_routing_rule)
        self.add_node_btn.connect("clicked", self.on_add_node)

        if layer_data:
            self.load_data(layer_data)

        # Force update provider list if empty (e.g. new layer)
        if self.provider_model.get_n_items() == 0:
            self.on_type_changed(None, None)
            # Apply defaults if new layer and no data
            if not layer_data:
                 self._apply_default_colors()

        # Ensure defaults are set if colors are transparent
        self._ensure_color_defaults()

        self._loading = False

    def _ensure_color_defaults(self):
        """Sets default colors if current ones are transparent/unset."""
        # Check if type is selected
        type_idx = self.type_row.get_selected()
        if type_idx < 0 or type_idx >= len(self.types_list):
            return

        selected_type = self.types_list[type_idx]
        defaults = DEFAULT_LAYER_COLORS.get(selected_type, {})

        # Layer Colors
        for key, btn in [
            ("header_color", self.header_color_button),
            ("body_color", self.body_color_button)
        ]:
            if not btn.get_rgba() or btn.get_rgba().alpha == 0:
                default_hex = defaults.get(key)
                if default_hex:
                    rgba = Gdk.RGBA()
                    rgba.parse(default_hex)
                    btn.set_rgba(rgba)

        # Diff Text Colors
        diff_map = {
            "added_text_color": self.added_text_color_button,
            "modified_text_color": self.modified_text_color_button,
            "removed_text_color": self.removed_text_color_button
        }
        for key, btn in diff_map.items():
            if not btn.get_rgba() or btn.get_rgba().alpha == 0:
                default_hex = DEFAULT_DIFF_COLORS.get(key)
                if default_hex:
                     rgba = Gdk.RGBA()
                     rgba.parse(default_hex)
                     btn.set_rgba(rgba)

    def _apply_default_colors(self):
        """Force apply default colors (for new layers)."""
        type_idx = self.type_row.get_selected()
        if type_idx < 0 or type_idx >= len(self.types_list):
            return
        selected_type = self.types_list[type_idx]
        defaults = DEFAULT_LAYER_COLORS.get(selected_type, {})

        for key, btn in [("header_color", self.header_color_button), ("body_color", self.body_color_button)]:
            val = defaults.get(key)
            if val:
                rgba = Gdk.RGBA()
                rgba.parse(val)
                btn.set_rgba(rgba)

        for key, btn in [
             ("added_text_color", self.added_text_color_button),
             ("modified_text_color", self.modified_text_color_button),
             ("removed_text_color", self.removed_text_color_button)
        ]:
            val = DEFAULT_DIFF_COLORS.get(key)
            if val:
                rgba = Gdk.RGBA()
                rgba.parse(val)
                btn.set_rgba(rgba)


    def on_type_changed(self, _row, _param):
        """Updates the provider list based on the selected type."""
        selected_idx = self.type_row.get_selected()
        if selected_idx < 0 or selected_idx >= len(self.types_list):
            return

        selected_type = self.types_list[selected_idx]

        # Configure Visibility and Labels based on Type
        # Logic:
        # CDN: Hide almost everything except Origins.
        # LB/Proxy/Backend: Standard visibility.

        visibility = {
            ProviderType.CDN: {
                "url": False,
                "default_backend": True,
                "routing": True,
                "overrides": False,
                "path_match": False,
                "nodes": False,
                "headers": False, # Explicitly hide for CDN
            },
            ProviderType.CACHE_PROXY: {
                "url": False,
                "default_backend": True,
                "routing": True,
                "overrides": True,
                "path_match": True,
                "nodes": True,
                "headers": True,
            },
            ProviderType.LOAD_BALANCER: {
                "url": True,
                "default_backend": True,
                "routing": True,
                "overrides": True,
                "path_match": True,
                "nodes": False,
                "headers": True,
            },
            ProviderType.APP_BACKEND: {
                "url": True,
                "default_backend": False,
                "routing": False,
                "overrides": False,
                "path_match": False,
                "nodes": False,
                "headers": True,
            },
        }
        config = visibility.get(selected_type, visibility[ProviderType.CDN])

        self.url_row.set_visible(config["url"])
        self.default_backend_host_row.set_visible(config["default_backend"])
        self.default_backend_header_row.set_visible(config["default_backend"])
        self.routing_rules_group.set_visible(config["routing"])
        self.overrides_group.set_visible(config["overrides"])
        self.path_match_group.set_visible(config["path_match"])
        self.nodes_group.set_visible(config["nodes"])
        self.headers_group.set_visible(config["headers"])

        if selected_type == ProviderType.CDN:
            self.default_backend_host_row.set_title("Default Origin Host (Fallback)")
            self.default_backend_header_row.set_title("Default Origin Host Header")
            self.routing_rules_group.set_title("Origins")
            self.routing_rules_group.set_subtitle("Configure origin servers and matching rules.")
            self.add_routing_rule_btn.set_tooltip_text("Add New Origin")
            label_prefix = "Origin"
        else:
            self.default_backend_host_row.set_title("Default Backend Host")
            self.default_backend_header_row.set_title("Default Backend Host Header")
            self.routing_rules_group.set_title("Backend Rules")
            self.routing_rules_group.set_subtitle("Define backend destinations based on request paths.")
            self.add_routing_rule_btn.set_tooltip_text("Add New Backend")
            label_prefix = "Backend"

        for row in self.origin_rule_rows:
            row.set_label_prefix(label_prefix)

        # Clear provider model
        n_items = self.provider_model.get_n_items()
        if n_items > 0:
            self.provider_model.splice(0, n_items, [])

        self.current_providers = get_providers_by_type(selected_type)

        for prov in self.current_providers:
            self.provider_model.append(prov.name)

        # Select first by default if not loading
        if not self._loading and self.current_providers:
            self.provider_row.set_selected(0)
            self.on_changed()

    def on_provider_changed(self, _row, _param):
        """Callback when provider changes."""
        # Update custom headers with debug headers for this provider if empty
        if self._loading:
            return

        prov_idx = self.provider_row.get_selected()
        if 0 <= prov_idx < len(self.current_providers):
            selected_provider_cls = self.current_providers[prov_idx]
            # Instantiate provider to get debug headers
            provider = selected_provider_cls()
            debug_headers = provider.get_debug_headers()

            # If headers are empty, populate them.
            if not self.header_rows and debug_headers:
                for key, value in debug_headers.items():
                    self.add_header_row(key, value)

        self.on_changed()

    def load_data(self, data):
        """Loads layer data into the UI widgets."""
        self._loading = True
        self.name_row.set_text(data.get("name", ""))
        self.desc_row.set_text(data.get("description", ""))
        self.url_row.set_text(data.get("host_url", ""))
        self.default_backend_host_row.set_text(
            data.get("default_backend_host", "")
        )
        self.default_backend_header_row.set_text(
            data.get("default_backend_host_header", "")
        )
        self.set_title(data.get("name", "New Layer"))
        self.name_row.connect(
            "notify::text",
            lambda *args: self.set_title(self.name_row.get_text()),
        )

        self._load_type_and_provider(data)
        self._load_colors(data)
        self._load_headers(data)
        self._load_overrides(data)
        self._load_path_matches(data)
        self._load_routing_rules(data)
        self._load_nodes(data) # New
        self._loading = False

    def _load_type_and_provider(self, data):
        """Loads the layer type and provider from data."""
        layer_type_str = data.get("layer_type", ProviderType.CDN.value)
        type_idx = next(
            (
                i
                for i, t in enumerate(self.types_list)
                if t.value == layer_type_str
            ),
            0,
        )
        self.type_row.set_selected(type_idx)
        self.on_type_changed(None, None)

        provider_str = data.get("provider", "")
        if provider_str:
            prov_idx = next(
                (
                    i
                    for i, prov in enumerate(self.current_providers)
                    if prov.name == provider_str
                ),
                0,
            )
            self.provider_row.set_selected(prov_idx)

    def _load_colors(self, data):
        """Loads color data into the UI."""
        color_buttons = {
            "header_color": self.header_color_button,
            "body_color": self.body_color_button,
            "text_color": self.text_color_button,
            "added_text_color": self.added_text_color_button,
            "removed_text_color": self.removed_text_color_button,
            "modified_text_color": self.modified_text_color_button,
        }
        for key, button in color_buttons.items():
            rgba = Gdk.RGBA()
            if not (data.get(key) and rgba.parse(data[key])):
                rgba.parse("rgba(0,0,0,0)")
            button.set_rgba(rgba)

    def _load_headers(self, data):
        """Loads custom headers."""
        for key, value in data.get("custom_headers", {}).items():
            self.add_header_row(key, value)

    def _load_overrides(self, data):
        """Loads host overrides."""
        for override in data.get("host_overrides", []):
            self.add_override_row(
                override.get("path_pattern", ""),
                override.get("host_header", ""),
            )

    def _load_path_matches(self, data):
        """Loads path matches."""
        for pattern in data.get("path_match_only", []):
            self.add_path_match_row(pattern)

    def _load_routing_rules(self, data):
        """Loads and groups routing rules."""
        routing_rules = data.get("routing_rules", [])
        if not routing_rules:
            return

        grouped_backends = {}
        for rule in routing_rules:
            backend_key = (
                rule.get("backend_host", ""),
                rule.get("backend_host_header", ""),
                rule.get("path_rewrite", ""),
            )
            if backend_key not in grouped_backends:
                grouped_backends[backend_key] = {
                    "backend_host": backend_key[0],
                    "backend_host_header": backend_key[1],
                    "path_rewrite": backend_key[2],
                    "path_matches": [],
                    "domain_matches": [],
                }
            if rule.get("path_match"):
                grouped_backends[backend_key]["path_matches"].append(
                    rule.get("path_match")
                )
            if rule.get("domain_match"):
                grouped_backends[backend_key]["domain_matches"].append(
                    rule.get("domain_match")
                )

        # Get label type based on current type if already set
        type_idx = self.type_row.get_selected()
        selected_type = (
            self.types_list[type_idx].value
            if 0 <= type_idx < len(self.types_list)
            else ProviderType.CDN.value
        )
        label_prefix = (
            "Origin" if selected_type == ProviderType.CDN.value else "Backend"
        )

        for origin_data in grouped_backends.values():
            self.add_origin_rule_row(origin_data, label_prefix=label_prefix)

    def _load_nodes(self, data):
        """Loads sibling nodes."""
        for node in data.get("nodes", []):
            self.add_node_row(node)

    def on_changed(self, *_args):
        """Callback when any data in the layer row changes."""
        if self._loading:
            return
        if self.on_change_callback:
            self.on_change_callback()

    def on_delete_clicked(self, _btn):
        """Callback for the delete button."""
        if self.on_delete_callback:
            self.on_delete_callback(self)

    def on_add_header(self, _btn):
        """Callback to add a new header row."""
        self.add_header_row()
        self.on_changed()

    def add_header_row(self, key="", value=""):
        """Adds a header entry row."""
        row = HeaderRow(
            key=key,
            value=value,
            on_change=self.on_changed,
            on_delete=self.remove_header_row,
        )
        self.headers_group.add_row(row)
        self.header_rows.append(row)

    def remove_header_row(self, row):
        """Removes a header entry row."""
        self.headers_group.remove(row)
        self.header_rows.remove(row)
        self.on_changed()

    def on_add_override(self, _btn):
        """Callback to add a new override row."""
        self.add_override_row()
        self.on_changed()

    def add_override_row(self, pattern="", host=""):
        """Adds an override entry row."""
        row = OverrideRow(
            pattern=pattern,
            host=host,
            on_change=self.on_changed,
            on_delete=self.remove_override_row,
        )
        self.overrides_group.add_row(row)
        self.override_rows.append(row)

    def remove_override_row(self, row):
        """Removes an override entry row."""
        self.overrides_group.remove(row)
        self.override_rows.remove(row)
        self.on_changed()

    def on_add_path_match(self, _btn):
        """Callback to add a new path match row."""
        self.add_path_match_row()
        self.on_changed()

    def add_path_match_row(self, pattern=""):
        """Adds a path match entry row."""
        row = PathMatchRow(
            pattern=pattern,
            on_change=self.on_changed,
            on_delete=self.remove_path_match_row,
        )
        self.path_match_group.add_row(row)
        self.path_match_rows.append(row)

    def remove_path_match_row(self, row):
        """Removes a path match entry row."""
        self.path_match_group.remove(row)
        self.path_match_rows.remove(row)
        self.on_changed()

    def on_add_routing_rule(self, _btn):
        """Callback to add a new backend rule row."""
        type_idx = self.type_row.get_selected()
        selected_type = (
            self.types_list[type_idx].value
            if 0 <= type_idx < len(self.types_list)
            else ProviderType.CDN.value
        )
        label_prefix = (
            "Origin" if selected_type == ProviderType.CDN.value else "Backend"
        )
        self.add_origin_rule_row(label_prefix=label_prefix)
        self.on_changed()

    def add_origin_rule_row(self, origin_data=None, label_prefix="Backend"):
        """Adds a backend rule entry row."""
        row = OriginRuleRow(
            origin_data=origin_data,
            label_prefix=label_prefix,
            on_change=self.on_changed,
            on_delete=self.remove_origin_rule_row,
        )
        self.routing_rules_group.add_row(row)
        self.origin_rule_rows.append(row)

    def remove_origin_rule_row(self, row):
        """Removes a backend rule entry row."""
        self.routing_rules_group.remove(row)
        self.origin_rule_rows.remove(row)
        self.on_changed()

    def on_add_node(self, _btn):
        """Callback to add a new node row."""
        self.add_node_row()
        self.on_changed()

    def add_node_row(self, node_data=None):
        """Adds a node entry row."""
        # Determine current layer type
        type_idx = self.type_row.get_selected()
        current_type = self.types_list[type_idx] if 0 <= type_idx < len(self.types_list) else ProviderType.CDN

        row = NodeRow(
            node_data=node_data,
            layer_type=current_type,
            on_change=self.on_changed,
            on_delete=self.remove_node_row,
        )
        self.nodes_group.add_row(row)
        self.node_rows.append(row)

    def remove_node_row(self, row):
        """Removes a node entry row."""
        self.nodes_group.remove(row)
        self.node_rows.remove(row)
        self.on_changed()

    def get_data(self):
        """Collects and returns the layer configuration data."""

        # Get selected Type
        type_idx = self.type_row.get_selected()
        if 0 <= type_idx < len(self.types_list):
            selected_type = self.types_list[type_idx].value
        else:
            selected_type = ProviderType.CDN.value

        # Get selected Provider
        prov_idx = self.provider_row.get_selected()
        if 0 <= prov_idx < len(self.current_providers):
            selected_provider = self.current_providers[prov_idx].name
        else:
            selected_provider = "Unknown"

        data = {
            "layer_type": selected_type,
            "provider": selected_provider,
            "name": self.name_row.get_text(),
            "description": self.desc_row.get_text(),
            "host_url": self.url_row.get_text() if self.url_row.get_visible() else "",
            "default_backend_host": self.default_backend_host_row.get_text(),
            "default_backend_host_header": self.default_backend_header_row.get_text(),
            "header_color": self.header_color_button.get_rgba().to_string(),
            "body_color": self.body_color_button.get_rgba().to_string(),
            "text_color": self.text_color_button.get_rgba().to_string(),
            "added_text_color": self.added_text_color_button.get_rgba().to_string(),
            "removed_text_color": self.removed_text_color_button.get_rgba().to_string(),
            "modified_text_color": self.modified_text_color_button.get_rgba().to_string(),
            "custom_headers": {},
            "host_overrides": [],
            "path_match_only": [],
            "routing_rules": [],
            "nodes": [], # New
        }

        for row in self.header_rows:
            k, v = row.get_texts()
            if k:
                data["custom_headers"][k] = v

        if self.overrides_group.get_visible():
            for row in self.override_rows:
                p, h = row.get_texts()
                if p and h:
                    data["host_overrides"].append(
                        {"path_pattern": p, "host_header": h}
                    )

        if self.path_match_group.get_visible():
            for row in self.path_match_rows:
                (p,) = row.get_texts()
                if p:
                    data["path_match_only"].append(p)

        # Flatten routing rules from backend rows
        if self.routing_rules_group.get_visible():
            for origin_row in self.origin_rule_rows:
                origin_data = origin_row.get_data()
                if origin_data["backend_host"]:
                    base_rule = {
                        "backend_host": origin_data["backend_host"],
                        "backend_host_header": origin_data["backend_host_header"],
                        "path_rewrite": origin_data["path_rewrite"],
                    }
                    for path_match in origin_data["path_matches"]:
                        rule = base_rule.copy()
                        rule["path_match"] = path_match
                        data["routing_rules"].append(rule)

                    for domain_match in origin_data["domain_matches"]:
                        rule = base_rule.copy()
                        rule["domain_match"] = domain_match
                        data["routing_rules"].append(rule)

        # Collect nodes
        if self.nodes_group.get_visible():
            for node_row in self.node_rows:
                data["nodes"].append(node_row.get_data())

        return data
