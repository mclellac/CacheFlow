"""
This module defines the HeaderAnalysisDialog, a dialog for displaying
detailed analysis of HTTP headers.
"""

import logging
from gi.repository import Gtk, Adw, Gio

from .analyzer import HeaderAnalyzer
from .models import AnalysisWrapper
from .ui_utils import create_header_list_factory

log = logging.getLogger(__name__)


@Gtk.Template(
    resource_path="/com/github/mclellac/CacheFlow/ui/analysis_dialog.ui"
)
class HeaderAnalysisDialog(Adw.Dialog):
    """
    Dialog to display header analysis.
    """

    __gtype_name__ = "HeaderAnalysisDialog"

    window_title = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    list_view = Gtk.Template.Child()

    def __init__(self, current_layer, upstream_layer, **kwargs):
        super().__init__(**kwargs)

        self.analyzer = HeaderAnalyzer()
        self.model = Gio.ListStore(item_type=AnalysisWrapper)
        self.settings = Gio.Settings.new("com.github.mclellac.CacheFlow")

        width = self.settings.get_int("analyzer-width")
        height = self.settings.get_int("analyzer-height")
        if width > 0 and height > 0:
            self.set_content_width(width)
            self.set_content_height(height)

        self.connect("closed", self._on_closed)

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

        # Use shared factory
        factory = create_header_list_factory(is_analysis=True)
        self.list_view.set_factory(factory)

    def _on_closed(self, _dialog):
        width = self.get_content_width()
        height = self.get_content_height()
        self.settings.set_int("analyzer-width", width)
        self.settings.set_int("analyzer-height", height)
