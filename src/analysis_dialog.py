"""
This module defines the HeaderAnalysisDialog, a dialog for displaying
detailed analysis of HTTP headers.
"""

import logging
from gi.repository import Gtk, Adw, Gio, GObject, Pango

from .analyzer import HeaderAnalyzer, AnalysisItem

log = logging.getLogger(__name__)

class AnalysisWrapper(GObject.Object):
    """
    Wrapper for AnalysisItem to be used in GListStore.
    """
    __gtype_name__ = 'AnalysisWrapper'

    def __init__(self, item: AnalysisItem):
        super().__init__()
        self.item = item

@Gtk.Template(resource_path='/com/github/mclellac/CacheFlow/ui/analysis_dialog.ui')
class HeaderAnalysisDialog(Adw.Dialog):
    """
    Dialog to display header analysis.
    """
    __gtype_name__ = 'HeaderAnalysisDialog'

    window_title = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    list_view = Gtk.Template.Child()

    def __init__(self, current_layer, upstream_layer, **kwargs):
        super().__init__(**kwargs)

        self.analyzer = HeaderAnalyzer()
        self.model = Gio.ListStore(item_type=AnalysisWrapper)

        # Run analysis
        report = self.analyzer.analyze_layer(current_layer, upstream_layer)
        self.window_title.set_title(f"Analysis: {report.layer_name}")

        if not report.items:
            self.stack.set_visible_child_name("empty")
        else:
            self.stack.set_visible_child_name("list")
            for item in report.items:
                self.model.append(AnalysisWrapper(item))

        self.selection_model = Gtk.NoSelection(model=self.model)
        self.list_view.set_model(self.selection_model)

        self._setup_factory()

    def _setup_factory(self):
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind)
        self.list_view.set_factory(factory)

    def _on_factory_setup(self, _factory, item):
        # Create a row with:
        # VBox
        #   HBox: Icon, Key (Bold), Value (Mono)
        #   Label: Description (Wrap)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        root.set_margin_top(10)
        root.set_margin_bottom(10)
        root.set_margin_start(10)
        root.set_margin_end(10)

        # Top Row
        top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        icon = Gtk.Image()
        icon.set_pixel_size(24)
        top_box.append(icon)

        key_label = Gtk.Label(xalign=0)
        key_label.set_width_chars(20)
        key_label.set_ellipsize(Pango.EllipsizeMode.END)
        top_box.append(key_label)

        val_label = Gtk.Label(xalign=0)
        val_label.add_css_class("monospace")
        val_label.set_ellipsize(Pango.EllipsizeMode.END)
        top_box.append(val_label)

        root.append(top_box)

        # Description
        desc_label = Gtk.Label(xalign=0, wrap=True)
        desc_label.set_max_width_chars(60) # Prevent super wide
        desc_label.add_css_class("dim-label")
        root.append(desc_label)

        item.set_child(root)

    def _on_factory_bind(self, _factory, item):
        wrapper = item.get_item()
        analysis_item = wrapper.item
        root = item.get_child()

        top_box = root.get_first_child()
        icon = top_box.get_first_child()
        key_label = icon.get_next_sibling()
        val_label = key_label.get_next_sibling()

        desc_label = top_box.get_next_sibling()

        # Set content
        key_markup = f"<b>{analysis_item.key}</b>"
        key_label.set_markup(key_markup)

        val_str = analysis_item.value
        if len(val_str) > 50:
            val_str = val_str[:50] + "..."
        val_label.set_text(val_str)
        val_label.set_tooltip_text(analysis_item.value)

        desc_label.set_text(analysis_item.description)

        # Icon / Color
        icon_name = "text-x-generic-symbolic"
        css_class = ""

        if analysis_item.change_type == "ADDED":
            icon_name = "list-add-symbolic"
            css_class = "success"
        elif analysis_item.change_type == "REMOVED":
            icon_name = "list-remove-symbolic"
            css_class = "error"
        elif analysis_item.change_type == "MODIFIED":
            icon_name = "document-edit-symbolic"
            css_class = "warning"

        icon.set_from_icon_name(icon_name)

        # Reset classes
        icon.remove_css_class("success")
        icon.remove_css_class("error")
        icon.remove_css_class("warning")
        if css_class:
            icon.add_css_class(css_class)
