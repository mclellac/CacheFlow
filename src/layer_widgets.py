import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject

@Gtk.Template(resource_path='/com/github/mclellac/CacheFlow/ui/layer_row.ui')
class LayerRow(Adw.ExpanderRow):
    __gtype_name__ = 'LayerRow'

    name_row = Gtk.Template.Child()
    desc_row = Gtk.Template.Child()
    url_row = Gtk.Template.Child()

    headers_group = Gtk.Template.Child()
    add_header_btn = Gtk.Template.Child()

    overrides_group = Gtk.Template.Child()
    add_override_btn = Gtk.Template.Child()

    path_match_group = Gtk.Template.Child()
    add_path_match_btn = Gtk.Template.Child()

    delete_btn = Gtk.Template.Child()

    def __init__(self, layer_data=None, on_delete=None, on_change=None):
        super().__init__()
        self._loading = True

        self.on_delete_callback = on_delete
        self.on_change_callback = on_change

        self.header_rows = []
        self.override_rows = []
        self.path_match_rows = []

        self.delete_btn.connect('clicked', self.on_delete_clicked)

        # Connect signals for basic fields
        self.name_row.connect('notify::text', self.on_changed)
        self.desc_row.connect('notify::text', self.on_changed)
        self.url_row.connect('notify::text', self.on_changed)

        # Headers
        self.add_header_btn.connect('clicked', self.on_add_header)

        # Overrides
        self.add_override_btn.connect('clicked', self.on_add_override)

        # Path Matches
        self.add_path_match_btn.connect('clicked', self.on_add_path_match)

        if layer_data:
            self.load_data(layer_data)

        self._loading = False

    def load_data(self, data):
        self.name_row.set_text(data.get('name', ''))
        self.desc_row.set_text(data.get('description', ''))
        self.url_row.set_text(data.get('host_url', ''))
        self.set_title(data.get('name', 'New Layer'))
        self.name_row.connect('notify::text', lambda *args: self.set_title(self.name_row.get_text()))

        # Load Headers
        custom_headers = data.get('custom_headers', {})
        if custom_headers:
            for key, value in custom_headers.items():
                self.add_header_row(key, value)

        # Load Overrides
        overrides = data.get('host_overrides', [])
        if overrides:
            for override in overrides:
                self.add_override_row(override.get('path_pattern', ''), override.get('host_header', ''))

        # Load Path Matches
        path_matches = data.get('path_match_only', [])
        if path_matches:
            for pattern in path_matches:
                self.add_path_match_row(pattern)

    def on_changed(self, *args):
        if self._loading:
            return
        if self.on_change_callback:
            self.on_change_callback()

    def on_delete_clicked(self, btn):
        if self.on_delete_callback:
            self.on_delete_callback(self)

    # --- Headers ---
    def on_add_header(self, btn):
        self.add_header_row()
        self.on_changed()

    def add_header_row(self, key='', value=''):
        row = HeaderRow(key, value, on_change=self.on_changed, on_delete=self.remove_header_row)
        self.headers_group.add_row(row)
        self.header_rows.append(row)

    def remove_header_row(self, row):
        self.headers_group.remove(row)
        self.header_rows.remove(row)
        self.on_changed()

    # --- Overrides ---
    def on_add_override(self, btn):
        self.add_override_row()
        self.on_changed()

    def add_override_row(self, pattern='', host=''):
        row = OverrideRow(pattern, host, on_change=self.on_changed, on_delete=self.remove_override_row)
        self.overrides_group.add_row(row)
        self.override_rows.append(row)

    def remove_override_row(self, row):
        self.overrides_group.remove(row)
        self.override_rows.remove(row)
        self.on_changed()

    # --- Path Match ---
    def on_add_path_match(self, btn):
        self.add_path_match_row()
        self.on_changed()

    def add_path_match_row(self, pattern=''):
        row = PathMatchRow(pattern, on_change=self.on_changed, on_delete=self.remove_path_match_row)
        self.path_match_group.add_row(row)
        self.path_match_rows.append(row)

    def remove_path_match_row(self, row):
        self.path_match_group.remove(row)
        self.path_match_rows.remove(row)
        self.on_changed()

    def get_data(self):
        data = {
            'name': self.name_row.get_text(),
            'description': self.desc_row.get_text(),
            'host_url': self.url_row.get_text(),
            'custom_headers': {},
            'host_overrides': [],
            'path_match_only': []
        }

        # Headers
        for row in self.header_rows:
            k, v = row.get_data()
            if k: # Only add if key is present
                data['custom_headers'][k] = v

        # Overrides
        for row in self.override_rows:
            p, h = row.get_data()
            if p and h:
                data['host_overrides'].append({'path_pattern': p, 'host_header': h})

        # Path Matches
        for row in self.path_match_rows:
            p = row.get_data()
            if p:
                data['path_match_only'].append(p)

        return data

class HeaderRow(Adw.PreferencesRow):
    def __init__(self, key='', value='', on_change=None, on_delete=None):
        super().__init__()
        self.on_change = on_change
        self.on_delete = on_delete

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(12)
        box.set_margin_end(12)

        self.key_entry = Gtk.Entry(placeholder_text="Header")
        self.key_entry.set_text(key)
        self.key_entry.set_hexpand(True)
        self.key_entry.connect('changed', self.notify_change)

        self.val_entry = Gtk.Entry(placeholder_text="Value")
        self.val_entry.set_text(value)
        self.val_entry.set_hexpand(True)
        self.val_entry.connect('changed', self.notify_change)

        del_btn = Gtk.Button(icon_name="user-trash-symbolic")
        del_btn.add_css_class("flat")
        del_btn.connect('clicked', lambda b: self.on_delete(self) if self.on_delete else None)

        box.append(self.key_entry)
        box.append(Gtk.Label(label=":"))
        box.append(self.val_entry)
        box.append(del_btn)

        self.set_child(box)

    def notify_change(self, *args):
        if self.on_change:
            self.on_change()

    def get_data(self):
        return self.key_entry.get_text(), self.val_entry.get_text()

class OverrideRow(Adw.PreferencesRow):
    def __init__(self, pattern='', host='', on_change=None, on_delete=None):
        super().__init__()
        self.on_change = on_change
        self.on_delete = on_delete

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(12)
        box.set_margin_end(12)

        self.pat_entry = Gtk.Entry(placeholder_text="/path/*")
        self.pat_entry.set_text(pattern)
        self.pat_entry.set_hexpand(True)
        self.pat_entry.connect('changed', self.notify_change)

        self.host_entry = Gtk.Entry(placeholder_text="host.example.com")
        self.host_entry.set_text(host)
        self.host_entry.set_hexpand(True)
        self.host_entry.connect('changed', self.notify_change)

        del_btn = Gtk.Button(icon_name="user-trash-symbolic")
        del_btn.add_css_class("flat")
        del_btn.connect('clicked', lambda b: self.on_delete(self) if self.on_delete else None)

        box.append(self.pat_entry)
        box.append(Gtk.Label(label="→"))
        box.append(self.host_entry)
        box.append(del_btn)

        self.set_child(box)

    def notify_change(self, *args):
        if self.on_change:
            self.on_change()

    def get_data(self):
        return self.pat_entry.get_text(), self.host_entry.get_text()

class PathMatchRow(Adw.PreferencesRow):
    def __init__(self, pattern='', on_change=None, on_delete=None):
        super().__init__()
        self.on_change = on_change
        self.on_delete = on_delete

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(12)
        box.set_margin_end(12)

        self.pat_entry = Gtk.Entry(placeholder_text="/path/*")
        self.pat_entry.set_text(pattern)
        self.pat_entry.set_hexpand(True)
        self.pat_entry.connect('changed', self.notify_change)

        del_btn = Gtk.Button(icon_name="user-trash-symbolic")
        del_btn.add_css_class("flat")
        del_btn.connect('clicked', lambda b: self.on_delete(self) if self.on_delete else None)

        box.append(self.pat_entry)
        box.append(del_btn)

        self.set_child(box)

    def notify_change(self, *args):
        if self.on_change:
            self.on_change()

    def get_data(self):
        return self.pat_entry.get_text()
