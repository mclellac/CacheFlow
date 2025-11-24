"""
This module defines the HeaderDialog, a dialog window for displaying and
inspecting HTTP headers in detail.
"""

import logging
from gi.repository import Gtk, Adw, Gio, GObject, GLib, Pango, Gdk

from .utils import get_accent_color

log = logging.getLogger(__name__)


class HeaderItem(GObject.Object):
    """
    A GObject wrapper for a single header item to be used in a GListStore.
    """
    __gtype_name__ = 'HeaderItem'

    def __init__(self, key, value, is_diff, note=""):
        super().__init__()
        self.key = key
        self.value = value
        self.is_diff = is_diff
        self.note = note


@Gtk.Template(resource_path='/com/github/mclellac/CacheFlow/ui/header_dialog.ui')
class HeaderDialog(Adw.Dialog):
    """
    A dialog to display key-value headers from a node.
    Allows filtering and copying of header data.
    """
    __gtype_name__ = 'HeaderDialog'

    column_view = Gtk.Template.Child()
    column_key = Gtk.Template.Child()
    column_value = Gtk.Template.Child()
    column_note = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    window_title = Gtk.Template.Child()
    stack = Gtk.Template.Child()

    def __init__(self, headers, heading=None, **kwargs):
        super().__init__(**kwargs)
        self._clipboard_provider = None

        if heading and heading != "Headers":
            self.window_title.set_title(f"Headers for {heading}")

        self.model = Gio.ListStore(item_type=HeaderItem)
        headers_to_split = ['x-akamai-session-info', 'content-security-policy']

        for header, value, is_diff, note in headers:
            if header.lower() in headers_to_split and ';' in value:
                parts = [p.strip() for p in value.split(';') if p.strip()]
                if not parts:
                    self.model.append(HeaderItem(header, '', is_diff, note))
                    continue
                self.model.append(HeaderItem(header, parts[0] + ';', is_diff, note))
                for part in parts[1:]:
                    val_str = part + (';' if not part == parts[-1] else '')
                    self.model.append(HeaderItem('', val_str, is_diff, ""))
            else:
                self.model.append(HeaderItem(header, value, is_diff, note))

        self.filter = Gtk.CustomFilter.new(self._filter_func)
        self.filter_model = Gtk.FilterListModel(model=self.model, filter=self.filter)
        self.filter_model.connect("items-changed", self._on_items_changed)
        self.selection_model = Gtk.MultiSelection(model=self.filter_model)
        self.column_view.set_model(self.selection_model)

        self._setup_factories()
        self._setup_context_menu()

        self.search_entry.connect('search-changed', self._on_search_changed)

    def _on_items_changed(self, _model, _position, _removed, _added):
        if not self.filter_model.get_n_items():
            self.stack.set_visible_child_name("empty")
        else:
            self.stack.set_visible_child_name("list")

    def _filter_func(self, item, _user_data=None):
        query = self.search_entry.get_text().lower()
        if not query:
            return True
        return (query in item.key.lower() or
                query in item.value.lower() or
                query in item.note.lower())

    def _on_search_changed(self, _entry):
        self.filter.changed(Gtk.FilterChange.DIFFERENT)

    def _setup_factories(self):
        factory_key = Gtk.SignalListItemFactory()
        factory_key.connect("setup", self._on_factory_setup_key)
        factory_key.connect("bind", self._on_factory_bind_key)
        self.column_key.set_factory(factory_key)

        factory_value = Gtk.SignalListItemFactory()
        factory_value.connect("setup", self._on_factory_setup_value)
        factory_value.connect("bind", self._on_factory_bind_value)
        self.column_value.set_factory(factory_value)

        factory_note = Gtk.SignalListItemFactory()
        factory_note.connect("setup", self._on_factory_setup_note)
        factory_note.connect("bind", self._on_factory_bind_note)
        self.column_note.set_factory(factory_note)

    def _on_factory_setup_key(self, _factory, item):
        label = Gtk.Label(xalign=0)
        item.set_child(label)

    def _on_factory_bind_key(self, _factory, item):
        header_item = item.get_item()
        label = item.get_child()
        escaped_key = GLib.markup_escape_text(header_item.key)
        label.set_markup(f"<b>{escaped_key}</b>")

    def _on_factory_setup_value(self, _factory, item):
        label = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END)
        item.set_child(label)

    def _on_factory_bind_value(self, _factory, item):
        header_item = item.get_item()
        label = item.get_child()
        label.set_text(header_item.value)

        attrs = Pango.AttrList()
        if header_item.is_diff:
            attrs.insert(Pango.attr_weight_new(Pango.Weight.BOLD))

            r, g, b, _ = get_accent_color()
            r_val = int(r * 65535)
            g_val = int(g * 65535)
            b_val = int(b * 65535)
            attrs.insert(Pango.attr_foreground_new(r_val, g_val, b_val))
        else:
            attrs.insert(Pango.attr_weight_new(Pango.Weight.NORMAL))
        label.set_attributes(attrs)

    def _on_factory_setup_note(self, _factory, item):
        label = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END)
        label.add_css_class("dim-label")
        item.set_child(label)

    def _on_factory_bind_note(self, _factory, item):
        header_item = item.get_item()
        label = item.get_child()
        label.set_text(header_item.note)

    def _setup_context_menu(self):
        copy_action = Gio.SimpleAction.new("copy_selection", None)
        copy_action.connect("activate", self._on_copy_activated)

        action_group = Gio.SimpleActionGroup()
        action_group.add_action(copy_action)
        self.insert_action_group("dialog", action_group)

        menu_model = Gio.Menu()
        menu_model.append("Copy", "dialog.copy_selection")

        self.popover = Gtk.PopoverMenu.new_from_model(menu_model)
        self.popover.set_parent(self.column_view)

        click_controller = Gtk.GestureClick.new()
        click_controller.set_button(Gdk.BUTTON_SECONDARY)
        click_controller.connect("pressed", self._on_right_click)
        self.column_view.add_controller(click_controller)

        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.column_view.add_controller(key_controller)

    def _on_right_click(self, _gesture, _n_press, x, y):
        self.popover.set_pointing_to(Gdk.Rectangle(int(x), int(y), 1, 1))
        self.popover.popup()

    def _on_key_pressed(self, _controller, keyval, _keycode, state):
        if (state & Gdk.ModifierType.CONTROL_MASK) and keyval == Gdk.KEY_c:
            self.activate_action("dialog.copy_selection", None)
            return True
        return False

    def _on_copy_activated(self, _action, _param):
        log.debug("Copy action activated.")
        selection = self.selection_model.get_selection()
        if selection.is_empty():
            log.debug("No rows selected, nothing to copy.")
            return

        clipboard_text = []

        n_items = self.model.get_n_items()
        for i in range(n_items):
            if self.selection_model.is_selected(i):
                item = self.model.get_item(i)
                if item.key:
                    clipboard_text.append(f"{item.key}: {item.value}")

        if not clipboard_text:
            return

        text_to_copy = "\n".join(clipboard_text)
        log.debug("Attempting to copy text to clipboard: '%s'", text_to_copy)
        self._clipboard_provider = Gdk.ContentProvider.new_for_value(text_to_copy)
        clipboard = self.get_clipboard()
        clipboard.set_content(self._clipboard_provider)
        log.debug("Clipboard content set.")
