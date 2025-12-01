"""
This module defines custom widgets used in the Layer configuration UI,
including the LayerRow for editing layer details.
"""

from typing import List, Any, Optional, Dict
from gi.repository import Gtk, Adw, Gdk, GObject
from ..providers.base import ProviderType
from ..providers import get_providers_by_type
from .layer_strategies import get_strategy

# Default Colors Constants
DEFAULT_LAYER_COLORS = {
    ProviderType.CDN: {
        "header_color": "#613583",  # Purple 5
        "body_color": "#9141ac",  # Purple 4
    },
    ProviderType.LOAD_BALANCER: {
        "header_color": "#1c71d8",  # Blue 4
        "body_color": "#3584e4",  # Blue 3
    },
    ProviderType.CACHE_PROXY: {
        "header_color": "#e66100",  # Orange 4
        "body_color": "#ff7800",  # Orange 3
    },
    ProviderType.APP_BACKEND: {
        "header_color": "#26a269",  # Green 5
        "body_color": "#2ec27e",  # Green 4
    },
}

DEFAULT_DIFF_COLORS = {
    "added_text_color": "#2ec27e",  # Green 4
    "modified_text_color": "#e66100",  # Orange 4
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

    def __init__(self, key="", value="", on_change=None, on_delete=None, **kwargs):
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

    def __init__(self, pattern="", host="", on_change=None, on_delete=None, **kwargs):
        super().__init__(on_change=on_change, on_delete=on_delete, **kwargs)
        self.entries = [self.pat_entry, self.host_entry]
        self.setup_entries([pattern, host])


@Gtk.Template(filename="src/ui/path_match_row.ui")
class PathMatchRow(BaseEntryRow):
    """Row for editing a path match pattern."""

    __gtype_name__ = "PathMatchRow"

    pat_entry = Gtk.Template.Child()
    type_combo = Gtk.Template.Child()
    delete_btn = Gtk.Template.Child()

    def __init__(self, pattern="", on_change=None, on_delete=None, **kwargs):
        super().__init__(on_change=on_change, on_delete=on_delete, **kwargs)
        self.entries = [self.pat_entry]

        self.type_combo.connect("changed", self.on_type_changed)

        self._set_pattern(pattern)
        self.pat_entry.connect("changed", self.notify_change)

    def _set_pattern(self, pattern):
        """Sets the UI state based on the pattern string."""
        if not pattern:
            self.type_combo.set_active_id("starts_with")
            self.pat_entry.set_text("")
            return

        # Heuristic detection
        if (
            pattern.endswith("*")
            and pattern.startswith("*")
            and len(pattern) > 1
        ):
            # Contains? *foo*
            core = pattern[1:-1]
            if "*" not in core:
                self.type_combo.set_active_id("contains")
                self.pat_entry.set_text(core)
                return

        if pattern.endswith("*") and len(pattern) > 0:
            core = pattern[:-1]
            if "*" not in core:
                self.type_combo.set_active_id("starts_with")
                self.pat_entry.set_text(core)
                return

        if pattern.startswith("*") and len(pattern) > 0:
            core = pattern[1:]
            if "*" not in core:
                self.type_combo.set_active_id("ends_with")
                self.pat_entry.set_text(core)
                return

        if "*" not in pattern:
            self.type_combo.set_active_id("exact")
            self.pat_entry.set_text(pattern)
            return

        # Fallback to Glob
        self.type_combo.set_active_id("glob")
        self.pat_entry.set_text(pattern)

    def on_type_changed(self, _combo):
        """Handles changes in the match type combo."""
        self.notify_change()

    def get_texts(self):
        """Returns the constructed pattern."""
        type_id = self.type_combo.get_active_id()
        val = self.pat_entry.get_text()

        if not val:
            return [""]

        if type_id == "starts_with":
            return [f"{val}*"]
        if type_id == "ends_with":
            return [f"*{val}"]
        if type_id == "contains":
            return [f"*{val}*"]
        if type_id == "exact":
            return [val]

        return [val]


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

    def __init__(
        self,
        node_data=None,
        layer_type=ProviderType.CDN,
        on_change=None,
        on_delete=None,
        **kwargs,
    ):
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
            self.on_name_changed(self.name_entry)  # Set initial title

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
                for cloud in [
                    "AWS",
                    "Azure",
                    "Google Cloud",
                    "OpenShift",
                    "VM",
                ]:
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

        for key, btn in [
            ("header_color", self.header_color_button),
            ("body_color", self.body_color_button),
        ]:
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
                row.get_texts()[0] for row in self.path_match_rows if row.get_texts()[0]
            ],
            "domain_matches": [
                row.get_texts()[0]
                for row in self.domain_match_rows
                if row.get_texts()[0]
            ],
        }


class RowListManager:
    """Helper to manage dynamic lists of configuration rows."""

    def __init__(self, group, row_class, on_change):
        self.group = group
        self.row_class = row_class
        self.on_change_cb = on_change
        self.rows = []

    def add_row(self, **kwargs):
        """Adds a new row to the group."""
        row = self.row_class(
            on_change=self.on_change_cb, on_delete=self.remove_row, **kwargs
        )
        self.group.add_row(row)
        self.rows.append(row)
        return row

    def remove_row(self, row):
        """Removes a row from the group."""
        self.group.remove(row)
        if row in self.rows:
            self.rows.remove(row)
        if self.on_change_cb:
            self.on_change_cb()

    def clear(self):
        """Removes all rows."""
        for row in list(self.rows):
            self.remove_row(row)


@Gtk.Template(filename="src/ui/layer_row.ui")
class LayerRow(Adw.PreferencesGroup):
    """
    Base class for configuration layer rows.
    Now specifically refactored to support subclassing.
    """

    __gtype_name__ = "LayerRow"

    # Signals
    @GObject.Signal(arg_types=(str,))
    def type_changed_request(self, new_type_str: str):
        pass

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

    preset_btn = Gtk.Template.Child()

    routing_rules_group = Gtk.Template.Child()
    add_routing_rule_btn = Gtk.Template.Child()

    # Flattened Default Backend Group
    default_backend_host_row = Gtk.Template.Child()
    default_backend_header_row = Gtk.Template.Child()

    delete_btn = Gtk.Template.Child()

    def __init__(self, layer_data=None, on_delete=None, on_change=None):
        super().__init__()
        self._loading = True
        self.on_delete_callback = on_delete
        self.on_change_callback = on_change
        self.current_providers = []

        # Initialize Managers (Subclasses will use specific ones, but we init all for safety/Base)
        self.header_manager = RowListManager(
            self.headers_group, HeaderRow, self.on_changed
        )
        self.override_manager = RowListManager(
            self.overrides_group, OverrideRow, self.on_changed
        )
        self.path_match_manager = RowListManager(
            self.path_match_group, PathMatchRow, self.on_changed
        )
        self.origin_rule_manager = RowListManager(
            self.routing_rules_group, OriginRuleRow, self.on_changed
        )
        self.node_manager = RowListManager(self.nodes_group, NodeRow, self.on_changed)

        # Common Setup
        self._setup_types_and_providers()
        self._connect_signals()

        # Load Data
        if layer_data:
            self.load_data(layer_data)

        self._apply_strategy()

        # Post-load setup
        if self.provider_model.get_n_items() == 0:
            self.on_type_changed(None, None)
            if not layer_data:
                self._apply_default_colors()

        self._ensure_color_defaults()
        self._loading = False

    def _setup_types_and_providers(self):
        """Sets up type and provider models."""
        self.type_model = Gtk.StringList()
        self.provider_model = Gtk.StringList()
        self.types_list = list(ProviderType)
        for t in self.types_list:
            self.type_model.append(t.value)

        self.type_row.set_model(self.type_model)
        self.provider_row.set_model(self.provider_model)

        # Initialize for first type (CDN) to ensure current_providers is populated
        if self.types_list:
            self.current_providers = get_providers_by_type(self.types_list[0])

        # Enforce strict architecture: Type is fixed per slot, so hide the selector.
        self.type_row.set_visible(False)

    def _connect_signals(self):
        """Connects common signals."""
        self.type_row.connect("notify::selected", self.on_type_changed)
        self.provider_row.connect("notify::selected", self.on_provider_changed)

        if self.on_delete_callback:
            self.delete_btn.connect("clicked", self.on_delete_clicked)
        else:
            self.delete_btn.set_visible(False)

        self.name_row.connect("notify::text", self.on_changed)
        self.desc_row.connect("notify::text", self.on_changed)
        self.url_row.connect("notify::text", self.on_changed)
        self.default_backend_host_row.connect("notify::text", self.on_changed)
        self.default_backend_header_row.connect("notify::text", self.on_changed)

        for btn in [
            self.header_color_button,
            self.body_color_button,
            self.text_color_button,
            self.added_text_color_button,
            self.removed_text_color_button,
            self.modified_text_color_button,
        ]:
            btn.connect("color-set", self.on_changed)

        self.add_header_btn.connect("clicked", self.on_add_header)
        self.add_override_btn.connect("clicked", self.on_add_override)
        self.add_path_match_btn.connect("clicked", self.on_add_path_match)
        self.add_routing_rule_btn.connect("clicked", self.on_add_routing_rule)
        self.add_node_btn.connect("clicked", self.on_add_node)
        self.preset_btn.connect("clicked", self.on_preset_clicked)

    def _ensure_color_defaults(self):
        """Sets default colors if current ones are transparent/unset."""
        type_idx = self.type_row.get_selected()
        if type_idx < 0 or type_idx >= len(self.types_list):
            return

        selected_type = self.types_list[type_idx]
        defaults = DEFAULT_LAYER_COLORS.get(selected_type, {})

        for key, btn in [
            ("header_color", self.header_color_button),
            ("body_color", self.body_color_button),
        ]:
            if not btn.get_rgba() or btn.get_rgba().alpha == 0:
                default_hex = defaults.get(key)
                if default_hex:
                    rgba = Gdk.RGBA()
                    rgba.parse(default_hex)
                    btn.set_rgba(rgba)

        diff_map = {
            "added_text_color": self.added_text_color_button,
            "modified_text_color": self.modified_text_color_button,
            "removed_text_color": self.removed_text_color_button,
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

        for key, btn in [
            ("header_color", self.header_color_button),
            ("body_color", self.body_color_button),
        ]:
            val = defaults.get(key)
            if val:
                rgba = Gdk.RGBA()
                rgba.parse(val)
                btn.set_rgba(rgba)

        for key, btn in [
            ("added_text_color", self.added_text_color_button),
            ("modified_text_color", self.modified_text_color_button),
            ("removed_text_color", self.removed_text_color_button),
        ]:
            val = DEFAULT_DIFF_COLORS.get(key)
            if val:
                rgba = Gdk.RGBA()
                rgba.parse(val)
                btn.set_rgba(rgba)

    def on_type_changed(self, _row, _param):
        """Handle type change."""
        if self._loading:
            return

        selected_idx = self.type_row.get_selected()
        if selected_idx < 0 or selected_idx >= len(self.types_list):
            return

        selected_type = self.types_list[selected_idx]

        # If the type changed from what this class expects (in subclasses),
        # we might want to emit the signal.
        # But `LayerRow` (base) acts as generic.

        self._apply_strategy(selected_type)

        # Populate providers
        self.current_providers = get_providers_by_type(selected_type)
        n_items = self.provider_model.get_n_items()
        if n_items > 0:
            self.provider_model.splice(0, n_items, [])
        for prov in self.current_providers:
            self.provider_model.append(prov.name)

        if self.current_providers:
            self.provider_row.set_selected(0)

        # Notify parent to swap row if needed
        self.emit("type_changed_request", selected_type.value)
        self.on_changed()

    def _apply_strategy(self, layer_type=None):
        """Applies visibility and labels based on strategy."""
        if layer_type is None:
            # Determine from UI
            idx = self.type_row.get_selected()
            if 0 <= idx < len(self.types_list):
                layer_type = self.types_list[idx]
            else:
                layer_type = ProviderType.CDN

        strategy = get_strategy(layer_type)
        visibility = strategy.get_visibility()
        labels = strategy.get_labels()

        self.url_row.set_visible(visibility["url"])
        self.default_backend_host_row.set_visible(visibility["default_backend"])
        self.default_backend_header_row.set_visible(visibility["default_backend"])
        self.routing_rules_group.set_visible(visibility["routing"])
        self.overrides_group.set_visible(visibility["overrides"])
        self.path_match_group.set_visible(visibility["path_match"])
        self.nodes_group.set_visible(visibility["nodes"])
        self.headers_group.set_visible(visibility["headers"])

        if "url_title" in labels:
            self.url_row.set_title(labels["url_title"])
        if "default_backend_host_title" in labels:
            self.default_backend_host_row.set_title(
                labels["default_backend_host_title"]
            )
        if "default_backend_header_title" in labels:
            self.default_backend_header_row.set_title(
                labels["default_backend_header_title"]
            )
        if "routing_rules_title" in labels:
            self.routing_rules_group.set_title(labels["routing_rules_title"])
        if "routing_rules_subtitle" in labels:
            self.routing_rules_group.set_subtitle(labels["routing_rules_subtitle"])
        if "add_routing_rule_tooltip" in labels:
            self.add_routing_rule_btn.set_tooltip_text(
                labels["add_routing_rule_tooltip"]
            )

        if "nodes_title" in labels:
            self.nodes_group.set_title(labels["nodes_title"])

        label_prefix = labels.get("rule_label_prefix", "Backend")
        for row in self.origin_rule_manager.rows:
            row.set_label_prefix(label_prefix)

    def on_provider_changed(self, _row, _param):
        if self._loading:
            return
        prov_idx = self.provider_row.get_selected()
        if 0 <= prov_idx < len(self.current_providers):
            selected_provider_cls = self.current_providers[prov_idx]
            provider = selected_provider_cls()
            debug_headers = provider.get_debug_headers()
            if not self.header_manager.rows and debug_headers:
                for key, value in debug_headers.items():
                    self.add_header_row(key, value)
        self.on_changed()

    def load_data(self, data):
        self._loading = True
        self.name_row.set_text(data.get("name", ""))
        self.desc_row.set_text(data.get("description", ""))
        self.url_row.set_text(data.get("host_url", ""))
        self.default_backend_host_row.set_text(data.get("default_backend_host", ""))
        self.default_backend_header_row.set_text(
            data.get("default_backend_host_header", "")
        )
        self.set_title(data.get("name", "New Layer"))
        self.name_row.connect(
            "notify::text", lambda *args: self.set_title(self.name_row.get_text())
        )

        self._load_type_and_provider(data)
        self._load_colors(data)
        self._load_headers(data)
        self._load_overrides(data)
        self._load_path_matches(data)
        self._load_routing_rules(data)
        self._load_nodes(data)
        self._loading = False

    def _load_type_and_provider(self, data):
        layer_type_str = data.get("layer_type", ProviderType.CDN.value)
        type_idx = next(
            (i for i, t in enumerate(self.types_list) if t.value == layer_type_str), 0
        )
        self.type_row.set_selected(type_idx)

        # Don't trigger on_type_changed logic fully here, just update UI state
        # But we need provider list populated
        self.current_providers = get_providers_by_type(self.types_list[type_idx])

        n_items = self.provider_model.get_n_items()
        if n_items > 0:
            self.provider_model.splice(0, n_items, [])
        for prov in self.current_providers:
            self.provider_model.append(prov.name)

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
        for key, value in data.get("custom_headers", {}).items():
            self.add_header_row(key, value)

    def _load_overrides(self, data):
        for override in data.get("host_overrides", []):
            self.add_override_row(
                override.get("path_pattern", ""), override.get("host_header", "")
            )

    def _load_path_matches(self, data):
        for pattern in data.get("path_match_only", []):
            self.add_path_match_row(pattern)

    def _load_routing_rules(self, data):
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
        for node in data.get("nodes", []):
            self.add_node_row(node)

    def on_changed(self, *_args):
        if self._loading:
            return
        self._update_node_count_subtitle()
        if self.on_change_callback:
            self.on_change_callback()

    def _update_node_count_subtitle(self):
        """Updates the nodes group subtitle with the server count."""
        count = len(self.node_manager.rows)
        if count == 0:
            self.nodes_group.set_subtitle(
                "Configure multiple servers for this layer."
            )
        else:
            self.nodes_group.set_subtitle(
                f"{count} Server{'s' if count != 1 else ''} configured."
            )

    def on_delete_clicked(self, _btn):
        if self.on_delete_callback:
            self.on_delete_callback(self)

    def on_add_header(self, _btn):
        self.add_header_row()
        self.on_changed()

    def add_header_row(self, key="", value=""):
        self.header_manager.add_row(key=key, value=value)

    def on_add_override(self, _btn):
        self.add_override_row()
        self.on_changed()

    def add_override_row(self, pattern="", host=""):
        self.override_manager.add_row(pattern=pattern, host=host)

    def on_add_path_match(self, _btn):
        self.add_path_match_row()
        self.on_changed()

    def add_path_match_row(self, pattern=""):
        self.path_match_manager.add_row(pattern=pattern)

    def on_add_routing_rule(self, _btn):
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
        self.origin_rule_manager.add_row(
            origin_data=origin_data, label_prefix=label_prefix
        )

    def on_preset_clicked(self, btn):
        """Shows the preset selection popover."""
        popover = Gtk.Popover()
        popover.set_parent(btn)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(6)
        box.set_margin_end(6)

        # Get current available providers
        if not hasattr(self, "current_providers") or not self.current_providers:
            label = Gtk.Label(label="No presets available.")
            box.append(label)
        else:
            label = Gtk.Label(label="Load Preset")
            label.add_css_class("title-4")
            box.append(label)

            for prov_cls in self.current_providers:
                row = Adw.ActionRow(title=prov_cls.name)
                row.set_activatable(True)
                gesture = Gtk.GestureClick()
                gesture.connect(
                    "released",
                    lambda g, n, x, y, name=prov_cls.name: self._apply_preset(
                        name, popover
                    ),
                )
                row.add_controller(gesture)
                box.append(row)

        popover.set_child(box)
        popover.popup()

    def _apply_preset(self, provider_name, popover):
        """Applies the selected preset."""
        popover.popdown()
        # Find index in provider_model
        for i in range(self.provider_model.get_n_items()):
            if self.provider_model.get_string(i) == provider_name:
                self.provider_row.set_selected(i)

                # Apply headers
                for prov_cls in self.current_providers:
                    if prov_cls.name == provider_name:
                        provider = prov_cls()
                        preset_headers = provider.get_preset_headers()
                        if preset_headers:
                            for k, v in preset_headers.items():
                                self.add_header_row(k, v)
                        break
                break

    def on_add_node(self, _btn):
        """Callback for adding a new node row."""
        self.add_node_row()
        self.on_changed()

    def add_node_row(self, node_data=None):
        """Adds a new NodeRow to the UI."""
        type_idx = self.type_row.get_selected()
        current_type = (
            self.types_list[type_idx]
            if 0 <= type_idx < len(self.types_list)
            else ProviderType.CDN
        )
        self.node_manager.add_row(node_data=node_data, layer_type=current_type)

    def get_data(self):
        type_idx = self.type_row.get_selected()
        if 0 <= type_idx < len(self.types_list):
            selected_type = self.types_list[type_idx].value
        else:
            selected_type = ProviderType.CDN.value

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
            "host_url": (self.url_row.get_text() if self.url_row.get_visible() else ""),
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
            "nodes": [],
        }

        for row in self.header_manager.rows:
            k, v = row.get_texts()
            if k:
                data["custom_headers"][k] = v

        if self.overrides_group.get_visible():
            for row in self.override_manager.rows:
                p, h = row.get_texts()
                if p and h:
                    data["host_overrides"].append({"path_pattern": p, "host_header": h})

        if self.path_match_group.get_visible():
            for row in self.path_match_manager.rows:
                (p,) = row.get_texts()
                if p:
                    data["path_match_only"].append(p)

        if self.routing_rules_group.get_visible():
            for origin_row in self.origin_rule_manager.rows:
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

        if self.nodes_group.get_visible():
            for node_row in self.node_manager.rows:
                data["nodes"].append(node_row.get_data())

        return data
