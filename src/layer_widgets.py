"""
This module defines custom widgets used in the Layer configuration UI,
including the LayerRow for editing layer details.
"""

from gi.repository import Gtk, Adw, Gdk, GObject
from .providers.base import ProviderType
from .providers import get_providers_by_type


class ConfigRowMixin:
    """Mixin for configuration rows with change and delete handling."""

    def setup_mixin(self, on_change=None, on_delete=None):
        """Sets up the mixin with callback functions."""
        self.on_change = on_change
        self.on_delete = on_delete

        # Connect delete button if it exists (template child)
        if hasattr(self, 'delete_btn'):
            self.delete_btn.connect('clicked', self.on_delete_clicked)

    def notify_change(self, *_args):
        """Notifies when data changes."""
        if getattr(self, 'on_change', None):
            self.on_change()

    def on_delete_clicked(self, _btn):
        """Callback for delete button."""
        if getattr(self, 'on_delete', None):
            self.on_delete(self)


@Gtk.Template(filename='src/ui/header_row.ui')
class HeaderRow(ConfigRowMixin, Adw.PreferencesRow):
    """Row for editing a single header key-value pair."""
    __gtype_name__ = 'HeaderRow'

    key_entry = Gtk.Template.Child()
    val_entry = Gtk.Template.Child()
    delete_btn = Gtk.Template.Child()

    def __init__(self, key='', value='', on_change=None, on_delete=None, **kwargs):
        super().__init__(**kwargs)
        self.setup_mixin(on_change, on_delete)

        self.key_entry.set_text(key)
        self.val_entry.set_text(value)

        self.key_entry.connect('changed', self.notify_change)
        self.val_entry.connect('changed', self.notify_change)

    def get_texts(self):
        """Returns [key, value] list."""
        return [self.key_entry.get_text(), self.val_entry.get_text()]


@Gtk.Template(filename='src/ui/override_row.ui')
class OverrideRow(ConfigRowMixin, Adw.PreferencesRow):
    """Row for editing a host override."""
    __gtype_name__ = 'OverrideRow'

    pat_entry = Gtk.Template.Child()
    host_entry = Gtk.Template.Child()
    delete_btn = Gtk.Template.Child()

    def __init__(self, pattern='', host='', on_change=None, on_delete=None, **kwargs):
        super().__init__(**kwargs)
        self.setup_mixin(on_change, on_delete)

        self.pat_entry.set_text(pattern)
        self.host_entry.set_text(host)

        self.pat_entry.connect('changed', self.notify_change)
        self.host_entry.connect('changed', self.notify_change)

    def get_texts(self):
        """Returns [pattern, host] list."""
        return [self.pat_entry.get_text(), self.host_entry.get_text()]


@Gtk.Template(filename='src/ui/path_match_row.ui')
class PathMatchRow(ConfigRowMixin, Adw.PreferencesRow):
    """Row for editing a path match pattern."""
    __gtype_name__ = 'PathMatchRow'

    pat_entry = Gtk.Template.Child()
    delete_btn = Gtk.Template.Child()

    def __init__(self, pattern='', on_change=None, on_delete=None, **kwargs):
        super().__init__(**kwargs)
        self.setup_mixin(on_change, on_delete)

        self.pat_entry.set_text(pattern)
        self.pat_entry.connect('changed', self.notify_change)

    def get_texts(self):
        """Returns [pattern] list."""
        return [self.pat_entry.get_text()]


@Gtk.Template(filename='src/ui/domain_match_row.ui')
class DomainMatchRow(ConfigRowMixin, Adw.PreferencesRow):
    """Row for editing a domain match pattern."""
    __gtype_name__ = 'DomainMatchRow'

    pat_entry = Gtk.Template.Child()
    delete_btn = Gtk.Template.Child()

    def __init__(self, pattern='', on_change=None, on_delete=None, **kwargs):
        super().__init__(**kwargs)
        self.setup_mixin(on_change, on_delete)

        self.pat_entry.set_text(pattern)
        self.pat_entry.connect('changed', self.notify_change)

    def get_texts(self):
        """Returns [pattern] list."""
        return [self.pat_entry.get_text()]


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

    origin_rules_group = Gtk.Template.Child()
    add_origin_rule_btn = Gtk.Template.Child()

    varnish_backend_group = Gtk.Template.Child()
    add_varnish_backend_btn = Gtk.Template.Child()

    default_backend_group = Gtk.Template.Child()
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
        self.varnish_backend_rows = []

        # Setup Models for Type and Provider
        self.type_model = Gtk.StringList()
        self.provider_model = Gtk.StringList()

        # Populate Type Model, excluding APP_BACKEND
        self.types_list = [t for t in list(ProviderType) if t != ProviderType.APP_BACKEND]
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
        self.default_backend_host_row.connect('notify::text', self.on_changed)
        self.default_backend_header_row.connect('notify::text', self.on_changed)
        self.header_color_button.connect('color-set', self.on_changed)
        self.body_color_button.connect('color-set', self.on_changed)
        self.text_color_button.connect('color-set', self.on_changed)
        self.diff_text_color_button.connect('color-set', self.on_changed)

        self.add_header_btn.connect('clicked', self.on_add_header)
        self.add_override_btn.connect('clicked', self.on_add_override)
        self.add_path_match_btn.connect('clicked', self.on_add_path_match)
        self.add_origin_rule_btn.connect('clicked', self.on_add_origin_rule)
        self.add_varnish_backend_btn.connect('clicked', self.on_add_varnish_backend)

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

        # Configure Visibility and Labels based on Type
        if selected_type == ProviderType.CDN:
            self.url_row.set_visible(False)
            self.default_backend_group.set_visible(True)
            self.default_backend_group.set_title("Default Origin")
            self.origin_rules_group.set_visible(True)
            self.origin_rules_group.set_title("Origin Rules")
            self.overrides_group.set_visible(False)
            self.path_match_group.set_visible(False)

        elif selected_type in (ProviderType.CACHE_PROXY, ProviderType.LOAD_BALANCER):
            self.url_row.set_visible(True)
            self.default_backend_group.set_visible(False) # No default backend, falls through or routed
            self.origin_rules_group.set_visible(True)
            self.origin_rules_group.set_title("Routing Rules")
            self.overrides_group.set_visible(True)
            self.path_match_group.set_visible(True)
            self.varnish_backend_group.set_visible(False)

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

            if selected_provider_cls.name == "Varnish":
                self.varnish_backend_group.set_visible(True)
            else:
                self.varnish_backend_group.set_visible(False)

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
        self.name_row.set_text(data.get('name', ''))
        self.desc_row.set_text(data.get('description', ''))
        self.url_row.set_text(data.get('host_url', ''))
        self.default_backend_host_row.set_text(data.get('default_backend_host', ''))
        self.default_backend_header_row.set_text(data.get('default_backend_host_header', ''))
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
        # and set visibility before loading other fields
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

        origin_rules = data.get('origin_rules', [])
        if origin_rules:
            for origin_data in origin_rules:
                self.add_origin_rule_row(origin_data)

        varnish_backends = data.get('varnish_backends', [])
        if varnish_backends:
            for backend_data in varnish_backends:
                self.add_varnish_backend_row(backend_data)

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
        self.headers_group.add(row)
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
        self.overrides_group.add(row)
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
        self.path_match_group.add(row)
        self.path_match_rows.append(row)

    def remove_path_match_row(self, row):
        """Removes a path match entry row."""
        self.path_match_group.remove(row)
        self.path_match_rows.remove(row)
        self.on_changed()

    def on_add_origin_rule(self, _btn):
        """Callback to add a new backend rule row."""
        self.add_origin_rule_row()
        self.on_changed()

    def add_origin_rule_row(self, origin_data=None):
        """Adds an origin rule entry row."""
        row = OriginRuleRow(
            origin_data=origin_data,
            on_change=self.on_changed,
            on_delete=self.remove_origin_rule_row
        )
        self.origin_rules_group.add(row)
        self.origin_rule_rows.append(row)

    def remove_origin_rule_row(self, row):
        """Removes an origin rule entry row."""
        self.origin_rules_group.remove(row)
        self.origin_rule_rows.remove(row)
        self.on_changed()

    def on_add_varnish_backend(self, _btn):
        """Callback to add a new Varnish backend row."""
        self.add_varnish_backend_row()
        self.on_changed()

    def add_varnish_backend_row(self, backend_data=None):
        """Adds a Varnish backend entry row."""
        row = VarnishBackendRow(
            backend_data=backend_data,
            on_change=self.on_changed,
            on_delete=self.remove_varnish_backend_row
        )
        self.varnish_backend_group.add(row)
        self.varnish_backend_rows.append(row)

    def remove_varnish_backend_row(self, row):
        """Removes a Varnish backend entry row."""
        self.varnish_backend_group.remove(row)
        self.varnish_backend_rows.remove(row)
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
            'default_backend_host': self.default_backend_host_row.get_text(),
            'default_backend_host_header': self.default_backend_header_row.get_text(),
            'header_color': self.header_color_button.get_rgba().to_string(),
            'body_color': self.body_color_button.get_rgba().to_string(),
            'text_color': self.text_color_button.get_rgba().to_string(),
            'diff_text_color': self.diff_text_color_button.get_rgba().to_string(),
            'custom_headers': {},
            'host_overrides': [],
            'path_match_only': [],
            'origin_rules': []
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

        # Flatten origin rules from origin rows
        for origin_row in self.origin_rule_rows:
            origin_data = origin_row.get_data()
            if origin_data['origin_host']:
                data['origin_rules'].append(origin_data)

        for backend_row in self.varnish_backend_rows:
            backend_data = backend_row.get_data()
            if backend_data['name']:
                data['varnish_backends'].append(backend_data)

        return data


@Gtk.Template(filename='src/ui/varnish_backend_row.ui')
class VarnishBackendRow(ConfigRowMixin, Adw.ExpanderRow):
    """Row for editing a Varnish backend."""
    __gtype_name__ = 'VarnishBackendRow'

    name_row = Gtk.Template.Child()
    type_row = Gtk.Template.Child()
    color_button = Gtk.Template.Child()
    delete_btn = Gtk.Template.Child()

    def __init__(self, backend_data=None, on_change=None, on_delete=None, **kwargs):
        super().__init__(**kwargs)
        self.setup_mixin(on_change, on_delete)
        self._loading = True

        self.type_model = Gtk.StringList()
        self.app_backend_providers = get_providers_by_type(ProviderType.APP_BACKEND)
        for provider in self.app_backend_providers:
            self.type_model.append(provider.name)
        self.type_model.append("Other")
        self.type_row.set_model(self.type_model)

        self.name_row.connect('notify::text', self.on_name_changed)
        self.type_row.connect('notify::selected', self.notify_change)
        self.color_button.connect('color-set', self.notify_change)

        if backend_data:
            self.load_data(backend_data)
        else:
            self.on_name_changed(self.name_row)

        self._loading = False

    def on_name_changed(self, entry):
        """Updates the row title and notifies of change."""
        name = entry.get_text()
        self.set_title(f"Backend: {name}" if name else "Backend: (Not Set)")
        self.notify_change()

    def load_data(self, data):
        """Loads backend data into the UI."""
        self.name_row.set_text(data.get('name', ''))
        self.on_name_changed(self.name_row)

        type_str = data.get('type', 'OpenShift')
        items = self.type_model.get_n_items()
        for i in range(items):
            if self.type_model.get_string(i) == type_str:
                self.type_row.set_selected(i)
                break

        color = Gdk.RGBA()
        if not (data.get('color') and color.parse(data['color'])):
            color.parse('rgba(0,0,0,0)')
        self.color_button.set_rgba(color)

    def get_data(self):
        """Returns the backend data."""
        selected_idx = self.type_row.get_selected()
        type_str = "OpenShift"
        if selected_idx >= 0:
            type_str = self.type_model.get_string(selected_idx)

        return {
            'name': self.name_row.get_text(),
            'type': type_str,
            'color': self.color_button.get_rgba().to_string()
        }


@Gtk.Template(filename='src/ui/origin_rule_row.ui')
class OriginRuleRow(ConfigRowMixin, Adw.ExpanderRow):
    """Row for editing an origin and its associated path/domain matches."""
    __gtype_name__ = 'OriginRuleRow'

    host_entry = Gtk.Template.Child()
    host_header_entry = Gtk.Template.Child()
    path_match_group = Gtk.Template.Child()
    add_path_btn = Gtk.Template.Child()
    domain_match_group = Gtk.Template.Child()
    add_domain_btn = Gtk.Template.Child()
    delete_btn = Gtk.Template.Child()

    def __init__(self, origin_data=None, on_change=None, on_delete=None, **kwargs):
        super().__init__(**kwargs)
        self.setup_mixin(on_change, on_delete)
        self._loading = True

        self.path_match_rows = []
        self.domain_match_rows = []

        self.host_entry.connect('changed', self.on_origin_host_changed)
        self.host_header_entry.connect('changed', self.notify_change)
        self.add_path_btn.connect('clicked', self.on_add_path_clicked)
        self.add_domain_btn.connect('clicked', self.on_add_domain_clicked)

        if origin_data:
            self.load_data(origin_data)
        else:
            self.on_origin_host_changed(self.host_entry)

        self._loading = False

    def on_origin_host_changed(self, entry):
        """Updates the row title and notifies of change."""
        host = entry.get_text()
        self.set_title(f"Origin: {host}" if host else "Origin: (Not Set)")
        self.notify_change()

    def load_data(self, data):
        """Loads origin data into the UI."""
        self.host_entry.set_text(data.get('origin_host', ''))
        self.host_header_entry.set_text(data.get('origin_host_header', ''))
        self.on_origin_host_changed(self.host_entry)

        for path in data.get('path_matches', []):
            self.add_path_match_row(pattern=path)

        for domain in data.get('domain_matches', []):
            self.add_domain_match_row(pattern=domain)

        self.update_subtitle()

    def on_add_path_clicked(self, _btn):
        """Callback to add a new path match row."""
        self.add_path_match_row()
        self.notify_change()

    def add_path_match_row(self, pattern=''):
        """Adds a path match entry row."""
        row = PathMatchRow(
            pattern=pattern,
            on_change=self.notify_change,
            on_delete=self.remove_path_match_row
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

    def add_domain_match_row(self, pattern=''):
        """Adds a domain match entry row."""
        row = DomainMatchRow(
            pattern=pattern,
            on_change=self.notify_change,
            on_delete=self.remove_domain_match_row
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
        path_count = len(self.path_match_rows)
        domain_count = len(self.domain_match_rows)
        self.set_subtitle(f"{path_count} Path{'s' if path_count != 1 else ''}, {domain_count} Domain{'s' if domain_count != 1 else ''}")

    def get_data(self):
        """Returns the origin and match data."""
        return {
            'origin_host': self.host_entry.get_text(),
            'origin_host_header': self.host_header_entry.get_text(),
            'path_matches': [row.get_texts()[0] for row in self.path_match_rows if row.get_texts()[0]],
            'domain_matches': [row.get_texts()[0] for row in self.domain_match_rows if row.get_texts()[0]]
        }
