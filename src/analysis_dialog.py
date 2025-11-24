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


@Gtk.Template(resource_path='/com/github/mclellac/CacheFlow/ui/analysis_dialog.ui')
class HeaderAnalysisDialog(Adw.Window):
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
        self.settings = Gio.Settings.new('com.github.mclellac.CacheFlow')

        self._restore_size()
        self.connect('close-request', self._on_close_request)

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

    def _restore_size(self):
        w = self.settings.get_int('analyzer-width')
        h = self.settings.get_int('analyzer-height')
        if w > 0 and h > 0:
            self.set_default_size(w, h)

    def _on_close_request(self, _win):
        w = self.get_width()
        h = self.get_height()
        self.settings.set_int('analyzer-width', w)
        self.settings.set_int('analyzer-height', h)
        return False
