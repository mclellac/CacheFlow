from gi.repository import Gtk, Adw, GObject, Gdk


@Gtk.Template(resource_path='/com/github/mclellac/CacheFlow/ui/layer_row.ui')
class LayerRow(Adw.ExpanderRow):
    __gtype_name__ = 'LayerRow'

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
        self.text_color_button.connect('color-set', self.on_changed)
        self.diff_text_color_button.connect('color-set', self.on_changed)

        self.add_header_btn.connect('clicked', self.on_add_header)
        self.add_override_btn.connect('clicked', self.on_add_override)
        self.add_path_match_btn.connect('clicked', self.on_add_path_match)

        if layer_data:
            self.load_data(layer_data)

        for button in [self.header_color_button, self.body_color_button, self.text_color_button, self.diff_text_color_button]:
            if not button.get_rgba():
                button.set_rgba(Gdk.RGBA(0, 0, 0, 0))

        self._loading = False

    def load_data(self, data):
        self.name_row.set_text(data.get('name', ''))
        self.desc_row.set_text(data.get('description', ''))
        self.url_row.set_text(data.get('host_url', ''))
        self.set_title(data.get('name', 'New Layer'))
        self.name_row.connect('notify::text', lambda *args: self.set_title(self.name_row.get_text()))

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
        if not (data.get('diff_text_color') and diff_text_color.parse(data['diff_text_color'])):
            diff_text_color.parse('rgba(0,0,0,0)')
        self.diff_text_color_button.set_rgba(diff_text_color)

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
        row = DeletableEntryRow(
            num_entries=2,
            texts=[key, value],
            placeholders=["Header Name", "Header Value"],
            on_change=self.on_changed,
            on_delete=self.remove_header_row
        )
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
        row = DeletableEntryRow(
            num_entries=2,
            texts=[pattern, host],
            placeholders=["Path Pattern (e.g. /news/*)", "Host Header"],
            on_change=self.on_changed,
            on_delete=self.remove_override_row
        )
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
        row = DeletableEntryRow(
            num_entries=1,
            texts=[pattern],
            placeholders=["Path Pattern (e.g. /api/*)"],
            on_change=self.on_changed,
            on_delete=self.remove_path_match_row
        )
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
            'text_color': self.text_color_button.get_rgba().to_string(),
            'diff_text_color': self.diff_text_color_button.get_rgba().to_string(),
            'custom_headers': {},
            'host_overrides': [],
            'path_match_only': []
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

        return data


class DeletableEntryRow(Adw.ActionRow):
    """A generic row with one or more entries and a delete button."""
    __gtype_name__ = 'DeletableEntryRow'

    def __init__(self, num_entries=1, texts=None, placeholders=None, on_change=None, on_delete=None, **kwargs):
        super().__init__(**kwargs)
        self.on_change = on_change
        self.on_delete = on_delete
        self.entries = []

        if texts is None:
            texts = [''] * num_entries
        if placeholders is None:
            placeholders = [''] * num_entries

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        for i in range(num_entries):
            entry = Gtk.Entry(hexpand=True)
            entry.set_text(texts[i])
            entry.set_placeholder_text(placeholders[i])
            entry.connect('changed', self.notify_change)
            box.append(entry)
            self.entries.append(entry)

        self.set_child(box)

        delete_btn = Gtk.Button(icon_name='user-trash-symbolic', valign=Gtk.Align.CENTER, has_frame=False)
        delete_btn.add_css_class('destructive-action')
        delete_btn.connect('clicked', lambda b: self.on_delete(self) if self.on_delete else None)
        self.add_suffix(delete_btn)

    def notify_change(self, *args):
        if self.on_change:
            self.on_change()

    def get_texts(self):
        return [entry.get_text() for entry in self.entries]
