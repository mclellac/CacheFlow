from gi.repository import Gtk, Adw, GObject, Gdk


@Gtk.Template(resource_path='/com/github/mclellac/CacheFlow/ui/layer_row.ui')
class LayerRow(Adw.ExpanderRow):
    __gtype_name__ = 'LayerRow'

    name_row = Gtk.Template.Child()
    desc_row = Gtk.Template.Child()
    url_row = Gtk.Template.Child()

    header_color_button = Gtk.Template.Child()
    body_color_button = Gtk.Template.Child()

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

        self.name_row.connect('notify::text', self.on_changed)
        self.desc_row.connect('notify::text', self.on_changed)
        self.url_row.connect('notify::text', self.on_changed)
        self.header_color_button.connect('color-set', self.on_changed)
        self.body_color_button.connect('color-set', self.on_changed)

        self.add_header_btn.connect('clicked', self.on_add_header)
        self.add_override_btn.connect('clicked', self.on_add_override)
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

        header_color = Gdk.RGBA()
        if data.get('header_color') and header_color.parse(data['header_color']):
            self.header_color_button.set_rgba(header_color)

        body_color = Gdk.RGBA()
        if data.get('body_color') and body_color.parse(data['body_color']):
            self.body_color_button.set_rgba(body_color)

        custom_headers = data.get('custom_headers', {})
        if custom_headers:
            for key, value in custom_headers.items():
                self.add_header_row(key, value)

        overrides = data.get('host_overrides', [])
        if overrides:
            for override in overrides:
                self.add_override_row(override.get('path_pattern', ''), override.get('host_header', ''))

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

    def on_add_header(self, btn):
        self.add_header_row()
        self.on_changed()

    def add_header_row(self, key='', value=''):
        row = HeaderRow(key=key, value=value, on_change=self.on_changed, on_delete=self.remove_header_row)
        self.headers_group.add_row(row)
        self.header_rows.append(row)

    def remove_header_row(self, row):
        self.headers_group.remove(row)
        self.header_rows.remove(row)
        self.on_changed()

    def on_add_override(self, btn):
        self.add_override_row()
        self.on_changed()

    def add_override_row(self, pattern='', host=''):
        row = OverrideRow(pattern=pattern, host=host, on_change=self.on_changed, on_delete=self.remove_override_row)
        self.overrides_group.add_row(row)
        self.override_rows.append(row)

    def remove_override_row(self, row):
        self.overrides_group.remove(row)
        self.override_rows.remove(row)
        self.on_changed()

    def on_add_path_match(self, btn):
        self.add_path_match_row()
        self.on_changed()

    def add_path_match_row(self, pattern=''):
        row = PathMatchRow(pattern=pattern, on_change=self.on_changed, on_delete=self.remove_path_match_row)
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
            'header_color': self.header_color_button.get_rgba().to_string(),
            'body_color': self.body_color_button.get_rgba().to_string(),
            'custom_headers': {},
            'host_overrides': [],
            'path_match_only': []
        }

        for row in self.header_rows:
            k, v = row.get_data()
            if k:
                data['custom_headers'][k] = v

        for row in self.override_rows:
            p, h = row.get_data()
            if p and h:
                data['host_overrides'].append({'path_pattern': p, 'host_header': h})

        for row in self.path_match_rows:
            p = row.get_data()
            if p:
                data['path_match_only'].append(p)

        return data


@Gtk.Template(resource_path='/com/github/mclellac/CacheFlow/ui/header_row.ui')
class HeaderRow(Adw.PreferencesRow):
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
        self.delete_btn.connect('clicked', lambda b: self.on_delete(self) if self.on_delete else None)

    def notify_change(self, *args):
        if self.on_change:
            self.on_change()

    def get_data(self):
        return self.key_entry.get_text(), self.val_entry.get_text()


@Gtk.Template(resource_path='/com/github/mclellac/CacheFlow/ui/override_row.ui')
class OverrideRow(Adw.PreferencesRow):
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
        self.delete_btn.connect('clicked', lambda b: self.on_delete(self) if self.on_delete else None)

    def notify_change(self, *args):
        if self.on_change:
            self.on_change()

    def get_data(self):
        return self.pat_entry.get_text(), self.host_entry.get_text()


@Gtk.Template(resource_path='/com/github/mclellac/CacheFlow/ui/path_match_row.ui')
class PathMatchRow(Adw.PreferencesRow):
    __gtype_name__ = 'PathMatchRow'

    pat_entry = Gtk.Template.Child()
    delete_btn = Gtk.Template.Child()

    def __init__(self, pattern='', on_change=None, on_delete=None, **kwargs):
        super().__init__(**kwargs)
        self.on_change = on_change
        self.on_delete = on_delete

        self.pat_entry.set_text(pattern)

        self.pat_entry.connect('changed', self.notify_change)
        self.delete_btn.connect('clicked', lambda b: self.on_delete(self) if self.on_delete else None)

    def notify_change(self, *args):
        if self.on_change:
            self.on_change()

    def get_data(self):
        return self.pat_entry.get_text()
