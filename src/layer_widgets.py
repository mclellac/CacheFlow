"""
This module defines custom widgets used in the Layer configuration UI,
including the LayerRow for editing layer details.
"""

from gi.repository import Gtk, Adw, Gdk
from .providers.base import ProviderType
from .providers import get_providers_by_type


@Gtk.Template(filename='src/ui/header_row.ui')
class HeaderRow(Adw.PreferencesRow):
    """Row for editing a single header key-value pair."""
    __gtype_name__ = 'HeaderRow'

    key_entry = Gtk.Template.Child()
    val_entry = Gtk.Template.Child()
    delete_btn = Gtk.Template.Child()

    def __init__(self, key='', value='', on_change=None, on_delete=None, **kwargs):
        super().__init__(**kwargs)
        self.on_change = on_change
        self.on_delete = on_delete

        self.key_entry.set_text(key)
        self.val_entry.set_text(value)

        self.key_entry.connect('changed', self.notify_change)
        self.val_entry.connect('changed', self.notify_change)
        self.delete_btn.connect('clicked', self.on_delete_clicked)

    def notify_change(self, *_args):
        """Notifies when data changes."""
        if self.on_change:
            self.on_change()

    def on_delete_clicked(self, _btn):
        """Callback for delete button."""
        if self.on_delete:
            self.on_delete(self)

    def get_texts(self):
        """Returns [key, value] list."""
        return [self.key_entry.get_text(), self.val_entry.get_text()]


@Gtk.Template(filename='src/ui/override_row.ui')
class OverrideRow(Adw.PreferencesRow):
    """Row for editing a host override."""
    __gtype_name__ = 'OverrideRow'

    pat_entry = Gtk.Template.Child()
    host_entry = Gtk.Template.Child()
    delete_btn = Gtk.Template.Child()

    def __init__(self, pattern='', host='', on_change=None, on_delete=None, **kwargs):
        super().__init__(**kwargs)
        self.on_change = on_change
        self.on_delete = on_delete

        self.pat_entry.set_text(pattern)
        self.host_entry.set_text(host)

        self.pat_entry.connect('changed', self.notify_change)
        self.host_entry.connect('changed', self.notify_change)
        self.delete_btn.connect('clicked', self.on_delete_clicked)

    def notify_change(self, *_args):
        """Notifies when data changes."""
        if self.on_change:
            self.on_change()

    def on_delete_clicked(self, _btn):
        """Callback for delete button."""
        if self.on_delete:
            self.on_delete(self)

    def get_texts(self):
        """Returns [pattern, host] list."""
        return [self.pat_entry.get_text(), self.host_entry.get_text()]


@Gtk.Template(filename='src/ui/path_match_row.ui')
class PathMatchRow(Adw.PreferencesRow):
    """Row for editing a path match pattern."""
    __gtype_name__ = 'PathMatchRow'

    pat_entry = Gtk.Template.Child()
    delete_btn = Gtk.Template.Child()

    def __init__(self, pattern='', on_change=None, on_delete=None, **kwargs):
        super().__init__(**kwargs)
        self.on_change = on_change
        self.on_delete = on_delete

        self.pat_entry.set_text(pattern)

        self.pat_entry.connect('changed', self.notify_change)
        self.delete_btn.connect('clicked', self.on_delete_clicked)

    def notify_change(self, *_args):
        """Notifies when data changes."""
        if self.on_change:
            self.on_change()

    def on_delete_clicked(self, _btn):
        """Callback for delete button."""
        if self.on_delete:
            self.on_delete(self)

    def get_texts(self):
        """Returns [pattern] list."""
        return [self.pat_entry.get_text()]


@Gtk.Template(filename='src/ui/routing_rule_row.ui')
class RoutingRuleRow(Adw.PreferencesRow):
    """Row for editing a routing rule."""
    __gtype_name__ = 'RoutingRuleRow'

    match_entry = Gtk.Template.Child()
    host_entry = Gtk.Template.Child()
    rewrite_entry = Gtk.Template.Child()
    delete_btn = Gtk.Template.Child()

    def __init__(self, match='', host='', rewrite='', on_change=None, on_delete=None, **kwargs):
        super().__init__(**kwargs)
        self.on_change = on_change
        self.on_delete = on_delete

        self.match_entry.set_text(match)
        self.host_entry.set_text(host)
        self.rewrite_entry.set_text(rewrite)

        self.match_entry.connect('changed', self.notify_change)
        self.host_entry.connect('changed', self.notify_change)
        self.rewrite_entry.connect('changed', self.notify_change)
        self.delete_btn.connect('clicked', self.on_delete_clicked)

    def notify_change(self, *_args):
        """Notifies when data changes."""
        if self.on_change:
            self.on_change()

    def on_delete_clicked(self, _btn):
        """Callback for delete button."""
        if self.on_delete:
            self.on_delete(self)

    def get_texts(self):
        """Returns [match, host, rewrite] list."""
        return [self.match_entry.get_text(), self.host_entry.get_text(), self.rewrite_entry.get_text()]


@Gtk.Template(filename='src/ui/layer_row.ui')
class LayerRow(Adw.ExpanderRow):
    """
    A widget representing a single configuration layer in the settings.
    Allows editing of layer properties like URL, headers, and colors.
    """
    __gtype_name__ = 'LayerRow'

    type_row = Gtk.Template.Child()
    provider_row = Gtk.Template.Child()
    name_row = Gtk.Template.Child()
    desc_row = Gtk.Template.Child()
    url_row = Gtk.Template.Child()

    header_color_button = Gtk.Template.Child()
    body_color_button = Gtk.Template.Child()

    text_color_button = Gtk.Template.Child()
    diff_text_color_button = Gtk.Template.Child()

    headers_group = Gtk.Template.Child()
    add_header_btn = Gtk.Template.Child()

    overrides_group = Gtk.Template.Child()
    add_override_btn = Gtk.Template.Child()

    path_match_group = Gtk.Template.Child()
    add_path_match_btn = Gtk.Template.Child()

    routing_rules_group = Gtk.Template.Child()
    add_routing_rule_btn = Gtk.Template.Child()

    delete_btn = Gtk.Template.Child()

    def __init__(self, layer_data=None, on_delete=None, on_change=None):
        super().__init__()
        self._loading = True

        self.on_delete_callback = on_delete
        self.on_change_callback = on_change

        self.header_rows = []
        self.override_rows = []
        self.path_match_rows = []
        self.routing_rule_rows = []

        # Setup Models for Type and Provider
        self.type_model = Gtk.StringList()
        self.provider_model = Gtk.StringList()

        # Populate Type Model
        self.types_list = list(ProviderType)
        for t in self.types_list:
            self.type_model.append(t.value)

        self.type_row.set_model(self.type_model)
        self.provider_row.set_model(self.provider_model)

        self.type_row.connect('notify::selected', self.on_type_changed)
        self.provider_row.connect('notify::selected', self.on_provider_changed)

        self.delete_btn.connect('clicked', self.on_delete_clicked)

        self.name_row.connect('notify::text', self.on_changed)
        self.desc_row.connect('notify::text', self.on_changed)
        self.url_row.connect('notify::text', self.on_changed)
        self.header_color_button.connect('color-set', self.on_changed)
        self.body_color_button.connect('color-set', self.on_changed)
        self.text_color_button.connect('color-set', self.on_changed)
        self.diff_text_color_button.connect('color-set', self.on_changed)

        self.add_header_btn.connect('clicked', self.on_add_header)
        self.add_override_btn.connect('clicked', self.on_add_override)
        self.add_path_match_btn.connect('clicked', self.on_add_path_match)
        self.add_routing_rule_btn.connect('clicked', self.on_add_routing_rule)

        if layer_data:
            self.load_data(layer_data)

        # Force update provider list if empty (e.g. new layer)
        if self.provider_model.get_n_items() == 0:
            self.on_type_changed(None, None)

        for button in [self.header_color_button, self.body_color_button,
                       self.text_color_button, self.diff_text_color_button]:
            if not button.get_rgba():
                button.set_rgba(Gdk.RGBA(0, 0, 0, 0))

        self._loading = False

    def on_type_changed(self, _row, _param):
        """Updates the provider list based on the selected type."""
        selected_idx = self.type_row.get_selected()
        if selected_idx < 0 or selected_idx >= len(self.types_list):
            return

        selected_type = self.types_list[selected_idx]

        # Show/Hide Routing Rules based on type
        if selected_type == ProviderType.CACHE_PROXY:
            self.routing_rules_group.set_visible(True)
        else:
            self.routing_rules_group.set_visible(False)

        # Clear provider model (Gtk.StringList doesn't have clear, so we create new or splice)
        # Splicing is cleaner
        n_items = self.provider_model.get_n_items()
        if n_items > 0:
            self.provider_model.splice(0, n_items, [])

        self.current_providers = get_providers_by_type(selected_type)

        # If no providers for this type (shouldn't happen with our setup), add a dummy
        # or handle gracefully. But we defined providers for all types.

        for prov in self.current_providers:
            self.provider_model.append(prov.name)

        # Select first by default if not loading
        if not self._loading and self.current_providers:
            self.provider_row.set_selected(0)
            # Trigger provider change to potentially update headers?
            # For now, we only update headers on user explicit action, but here we just update state.
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
            # We don't want to overwrite existing configuration blindly.
            if not self.header_rows and debug_headers:
                for key, value in debug_headers.items():
                    self.add_header_row(key, value)

        self.on_changed()

    def load_data(self, data):
        """Loads layer data into the UI widgets."""
        self.name_row.set_text(data.get('name', ''))
        self.desc_row.set_text(data.get('description', ''))
        self.url_row.set_text(data.get('host_url', ''))
        self.set_title(data.get('name', 'New Layer'))
        self.name_row.connect('notify::text',
                              lambda *args: self.set_title(self.name_row.get_text()))

        # Load Type
        layer_type_str = data.get('layer_type', ProviderType.CDN.value)
        # Find index
        type_idx = 0
        for i, t in enumerate(self.types_list):
            if t.value == layer_type_str:
                type_idx = i
                break
        self.type_row.set_selected(type_idx)

        # Force provider update immediately to populate the second dropdown
        self.on_type_changed(None, None)

        # Load Provider
        provider_str = data.get('provider', '')
        if provider_str:
            # Find index in current_providers
            prov_idx = 0
            for i, prov in enumerate(self.current_providers):
                if prov.name == provider_str:
                    prov_idx = i
                    break
            self.provider_row.set_selected(prov_idx)


        header_color = Gdk.RGBA()
        if not (data.get('header_color') and header_color.parse(data['header_color'])):
            header_color.parse('rgba(0,0,0,0)')
        self.header_color_button.set_rgba(header_color)

        body_color = Gdk.RGBA()
        if not (data.get('body_color') and body_color.parse(data['body_color'])):
            body_color.parse('rgba(0,0,0,0)')
        self.body_color_button.set_rgba(body_color)

        text_color = Gdk.RGBA()
        if not (data.get('text_color') and text_color.parse(data['text_color'])):
            text_color.parse('rgba(0,0,0,0)')
        self.text_color_button.set_rgba(text_color)

        diff_text_color = Gdk.RGBA()
        if not (data.get('diff_text_color') and
                diff_text_color.parse(data['diff_text_color'])):
            diff_text_color.parse('rgba(0,0,0,0)')
        self.diff_text_color_button.set_rgba(diff_text_color)

        custom_headers = data.get('custom_headers', {})
        if custom_headers:
            for key, value in custom_headers.items():
                self.add_header_row(key, value)

        overrides = data.get('host_overrides', [])
        if overrides:
            for override in overrides:
                self.add_override_row(override.get('path_pattern', ''),
                                      override.get('host_header', ''))

        path_matches = data.get('path_match_only', [])
        if path_matches:
            for pattern in path_matches:
                self.add_path_match_row(pattern)

        routing_rules = data.get('routing_rules', [])
        if routing_rules:
            for rule in routing_rules:
                self.add_routing_rule_row(
                    rule.get('path_match', ''),
                    rule.get('backend_host', ''),
                    rule.get('path_rewrite', '')
                )

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

    def add_header_row(self, key='', value=''):
        """Adds a header entry row."""
        row = HeaderRow(
            key=key, value=value,
            on_change=self.on_changed,
            on_delete=self.remove_header_row
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

    def add_override_row(self, pattern='', host=''):
        """Adds an override entry row."""
        row = OverrideRow(
            pattern=pattern, host=host,
            on_change=self.on_changed,
            on_delete=self.remove_override_row
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

    def add_path_match_row(self, pattern=''):
        """Adds a path match entry row."""
        row = PathMatchRow(
            pattern=pattern,
            on_change=self.on_changed,
            on_delete=self.remove_path_match_row
        )
        self.path_match_group.add_row(row)
        self.path_match_rows.append(row)

    def remove_path_match_row(self, row):
        """Removes a path match entry row."""
        self.path_match_group.remove(row)
        self.path_match_rows.remove(row)
        self.on_changed()

    def on_add_routing_rule(self, _btn):
        """Callback to add a new routing rule row."""
        self.add_routing_rule_row()
        self.on_changed()

    def add_routing_rule_row(self, match='', host='', rewrite=''):
        """Adds a routing rule entry row."""
        row = RoutingRuleRow(
            match=match, host=host, rewrite=rewrite,
            on_change=self.on_changed,
            on_delete=self.remove_routing_rule_row
        )
        self.routing_rules_group.add_row(row)
        self.routing_rule_rows.append(row)

    def remove_routing_rule_row(self, row):
        """Removes a routing rule entry row."""
        self.routing_rules_group.remove(row)
        self.routing_rule_rows.remove(row)
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
            'layer_type': selected_type,
            'provider': selected_provider,
            'name': self.name_row.get_text(),
            'description': self.desc_row.get_text(),
            'host_url': self.url_row.get_text(),
            'header_color': self.header_color_button.get_rgba().to_string(),
            'body_color': self.body_color_button.get_rgba().to_string(),
            'text_color': self.text_color_button.get_rgba().to_string(),
            'diff_text_color': self.diff_text_color_button.get_rgba().to_string(),
            'custom_headers': {},
            'host_overrides': [],
            'path_match_only': [],
            'routing_rules': []
        }

        for row in self.header_rows:
            k, v = row.get_texts()
            if k:
                data['custom_headers'][k] = v

        for row in self.override_rows:
            p, h = row.get_texts()
            if p and h:
                data['host_overrides'].append({'path_pattern': p, 'host_header': h})

        for row in self.path_match_rows:
            p, = row.get_texts()
            if p:
                data['path_match_only'].append(p)

        for row in self.routing_rule_rows:
            m, h, r = row.get_texts()
            if m and h:
                data['routing_rules'].append({
                    'path_match': m,
                    'backend_host': h,
                    'path_rewrite': r
                })

        return data
