import logging
from gi.repository import Gtk, Adw, Gio, GObject, GLib, Pango, Gdk

log = logging.getLogger(__name__)

class HeaderItem(GObject.Object):
    __gtype_name__ = 'HeaderItem'

    def __init__(self, key, value, is_diff, note=""):
        super().__init__()
        self.key = key
        self.value = value
        self.is_diff = is_diff
        self.note = note

@Gtk.Template(resource_path='/com/github/mclellac/CacheFlow/ui/header_dialog.ui')
class HeaderDialog(Adw.MessageDialog):
    """A dialog to display key-value headers from a node."""
    __gtype_name__ = 'HeaderDialog'

    column_view = Gtk.Template.Child()
    column_key = Gtk.Template.Child()
    column_value = Gtk.Template.Child()
    column_note = Gtk.Template.Child()

    def __init__(self, headers, **kwargs):
        super().__init__(**kwargs)
        self._clipboard_provider = None

        heading = self.get_heading()
        if heading and heading != "Headers":
            self.set_heading(f"Headers for {heading}")

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
                    self.model.append(HeaderItem('', part + (';' if not part == parts[-1] else ''), is_diff, ""))
            else:
                self.model.append(HeaderItem(header, value, is_diff, note))

        self.selection_model = Gtk.MultiSelection(model=self.model)
        self.column_view.set_model(self.selection_model)

        self._setup_factories()
        self._setup_context_menu()

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

    def _on_factory_setup_key(self, factory, item):
        label = Gtk.Label(xalign=0)
        item.set_child(label)

    def _on_factory_bind_key(self, factory, item):
        header_item = item.get_item()
        label = item.get_child()
        escaped_key = GLib.markup_escape_text(header_item.key)
        label.set_markup(f"<b>{escaped_key}</b>")

    def _on_factory_setup_value(self, factory, item):
        label = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END)
        item.set_child(label)

    def _on_factory_bind_value(self, factory, item):
        header_item = item.get_item()
        label = item.get_child()
        label.set_text(header_item.value)

        attrs = Pango.AttrList()
        if header_item.is_diff:
            attrs.insert(Pango.attr_weight_new(Pango.Weight.BOLD))
        else:
            attrs.insert(Pango.attr_weight_new(Pango.Weight.NORMAL))
        label.set_attributes(attrs)

    def _on_factory_setup_note(self, factory, item):
        label = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END)
        label.add_css_class("dim-label")
        item.set_child(label)

    def _on_factory_bind_note(self, factory, item):
        header_item = item.get_item()
        label = item.get_child()
        label.set_text(header_item.note)

    def _setup_context_menu(self):
        copy_action = Gio.SimpleAction.new("copy_selection", None)
        copy_action.connect("activate", self._on_copy_activated)

        action_group = Gio.SimpleActionGroup()
        action_group.add_action(copy_action)
        self.insert_action_group("dialog", action_group)

        # We need to trigger copy from keyboard or menu.
        # GtkColumnView doesn't have a simple 'popup-menu' signal like TreeView.
        # We attach a GestureClick to the ColumnView.

        menu_model = Gio.Menu()
        menu_model.append("Copy", "dialog.copy_selection")

        self.popover = Gtk.PopoverMenu.new_from_model(menu_model)
        self.popover.set_parent(self.column_view)

        click_controller = Gtk.GestureClick.new()
        click_controller.set_button(Gdk.BUTTON_SECONDARY)
        click_controller.connect("pressed", self._on_right_click)
        self.column_view.add_controller(click_controller)

        # Also support Ctrl+C?
        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.column_view.add_controller(key_controller)

    def _on_right_click(self, gesture, n_press, x, y):
        self.popover.set_pointing_to(Gdk.Rectangle(int(x), int(y), 1, 1))
        self.popover.popup()

    def _on_key_pressed(self, controller, keyval, keycode, state):
        if (state & Gdk.ModifierType.CONTROL_MASK) and keyval == Gdk.KEY_c:
            self.activate_action("dialog.copy_selection", None)
            return True
        return False

    def _on_copy_activated(self, action, param):
        log.debug("Copy action activated.")
        selection = self.selection_model.get_selection() # This returns a Bitset
        if selection.is_empty():
            log.debug("No rows selected, nothing to copy.")
            return

        clipboard_text = []
        # Bitset iteration
        # We need to map indices to items

        # Iterate manually or use get_item on model for each index
        count = selection.get_size()
        log.debug(f"Found {count} rows selected for copying.")

        # Get indices
        # Bitset doesn't support direct iteration easily in python gi yet?
        # We can loop through all items and check if selected (slow).
        # Or use get_nth or loop range.

        # Since it's a list, and we can't easily iterate bitset in PyGObject without helper (maybe?),
        # checking every item is safer for now if list is small.
        # Actually Gtk.SelectionModel has is_selected(i).

        n_items = self.model.get_n_items()
        for i in range(n_items):
            if self.selection_model.is_selected(i):
                item = self.model.get_item(i)
                if item.key:
                    clipboard_text.append(f"{item.key}: {item.value}")

        if not clipboard_text:
            return

        text_to_copy = "\n".join(clipboard_text)
        log.debug(f"Attempting to copy text to clipboard: '{text_to_copy}'")
        self._clipboard_provider = Gdk.ContentProvider.new_for_value(text_to_copy)
        clipboard = self.get_clipboard()
        clipboard.set_content(self._clipboard_provider)
        log.debug("Clipboard content set.")
