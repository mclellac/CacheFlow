"""
Encyclopedia window for browsing HTTP headers.
"""

import logging
from gi.repository import Gtk, Adw, Gio, GObject
from ..models import HeaderItem
from ..analysis import knowledge
from .ui_utils import create_header_list_factory

log = logging.getLogger(__name__)

@Gtk.Template(resource_path="/com/github/mclellac/CacheFlow/ui/encyclopedia.ui")
class Encyclopedia(Adw.Window):
    """
    A window to display definitions for all known HTTP headers.
    """
    __gtype_name__ = "Encyclopedia"

    search_entry = Gtk.Template.Child()
    list_view = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.model = Gio.ListStore(item_type=HeaderItem)
        self._populate_model()

        self.filter = Gtk.CustomFilter.new(self._filter_func)
        self.filter_model = Gtk.FilterListModel(model=self.model, filter=self.filter)
        self.selection_model = Gtk.NoSelection(model=self.filter_model)
        self.list_view.set_model(self.selection_model)

        # Reuse factory from ui_utils, non-analysis mode
        factory = create_header_list_factory(is_analysis=False)
        self.list_view.set_factory(factory)

        self.search_entry.connect("search-changed", self._on_search_changed)

    def _populate_model(self):
        """Populates the model with all known headers."""
        for key, info in sorted(knowledge.HEADER_KNOWLEDGE.items()):
            # We map:
            # key -> Header Name
            # value -> Category
            # note -> Description
            item = HeaderItem(key, info.category, "UNCHANGED", info.description)
            self.model.append(item)

    def _filter_func(self, item, _user_data=None):
        """Filters headers based on search query."""
        query = self.search_entry.get_text().lower()
        if not query:
            return True
        return (query in item.key.lower() or
                query in item.value.lower() or
                query in item.note.lower())

    def _on_search_changed(self, _entry):
        """Handles changes in the search entry."""
        self.filter.changed(Gtk.FilterChange.DIFFERENT)
