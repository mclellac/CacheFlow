"""
This module contains the CookieDialog class, which displays a list of cookies
collected during the inspection.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GObject, Gio


class CookieItem(GObject.Object):
    """GObject wrapper for a cookie."""

    __gtype_name__ = "CookieItem"

    name = GObject.Property(type=str)
    value = GObject.Property(type=str)
    domain = GObject.Property(type=str)
    path = GObject.Property(type=str)
    secure = GObject.Property(type=bool)
    http_only = GObject.Property(type=bool)
    same_site = GObject.Property(type=str)
    origin_layer = GObject.Property(type=str)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


@Gtk.Template(
    resource_path="/com/github/mclellac/CacheFlow/ui/cookie_dialog.ui"
)
class CookieDialog(Adw.Window):
    """A dialog to inspect cookies found during inspection."""

    __gtype_name__ = "CookieDialog"

    stack = Gtk.Template.Child()
    cookie_list = Gtk.Template.Child()

    def __init__(self, layers, parent_window=None, **kwargs):
        super().__init__(**kwargs)
        if parent_window:
            self.set_transient_for(parent_window)

        self.model = Gio.ListStore(item_type=CookieItem)
        self.selection_model = Gtk.SingleSelection(model=self.model)
        self.cookie_list.set_model(self.selection_model)

        self._setup_columns()
        self._populate_cookies(layers)

    def _setup_columns(self):
        self._add_text_column("Name", "name")
        self._add_text_column("Value", "value", truncate=True)
        self._add_text_column("Domain", "domain")
        self._add_text_column("Path", "path")
        self._add_text_column("Origin", "origin_layer")
        self._add_attributes_column()

    def _add_text_column(self, title, property_name, truncate=False):
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_text_factory_setup)
        factory.connect(
            "bind", self._on_text_factory_bind, (property_name, truncate)
        )
        col = Gtk.ColumnViewColumn(title=title, factory=factory)
        self.cookie_list.append_column(col)

    def _on_text_factory_setup(self, _factory, list_item):
        label = Gtk.Label(xalign=0)
        list_item.set_child(label)

    def _on_text_factory_bind(self, _factory, list_item, user_data):
        property_name, truncate = user_data
        item = list_item.get_item()
        label = list_item.get_child()
        value = getattr(item, property_name)
        if value is None:
            value = ""
        value = str(value)
        if truncate and len(value) > 40:
            value = value[:37] + "..."
        label.set_text(value)

    def _add_attributes_column(self):
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_attr_factory_setup)
        factory.connect("bind", self._on_attr_factory_bind)
        col = Gtk.ColumnViewColumn(title="Flags", factory=factory)
        self.cookie_list.append_column(col)

    def _on_attr_factory_setup(self, _factory, list_item):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        list_item.set_child(box)

    def _on_attr_factory_bind(self, _factory, list_item):
        item = list_item.get_item()
        box = list_item.get_child()
        # Clear existing children
        while child := box.get_first_child():
            box.remove(child)

        if item.secure:
            box.append(self._create_badge("Secure", "success"))
        else:
            box.append(self._create_badge("Insecure", "error"))

        if item.http_only:
            box.append(self._create_badge("HttpOnly", "accent"))

        if item.same_site:
            box.append(
                self._create_badge(f"SameSite={item.same_site}", "neutral")
            )

    def _create_badge(self, text, style_class):
        lbl = Gtk.Label(label=text)
        lbl.add_css_class("badge")
        lbl.add_css_class(style_class)
        return lbl

    def _populate_cookies(self, layers):
        found_cookies = False
        for layer in layers:
            for node in layer:
                if not node.is_active:
                    continue
                cookies = getattr(node, "cookies", [])
                for c in cookies:
                    found_cookies = True
                    item = CookieItem(
                        name=c.get("name"),
                        value=c.get("value"),
                        domain=c.get("domain"),
                        path=c.get("path"),
                        secure=c.get("secure"),
                        http_only=c.get("http_only"),
                        same_site=c.get("same_site"),
                        origin_layer=node.name,
                    )
                    self.model.append(item)

        if found_cookies:
            self.stack.set_visible_child_name("scrolled_window")
        else:
            self.stack.set_visible_child_name("empty_state")
