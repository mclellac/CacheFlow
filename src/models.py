"""
This module contains GObject models/wrappers for use in ListStores.
"""

from gi.repository import GObject
from .analyzer import AnalysisItem

class AnalysisWrapper(GObject.Object):
    """
    Wrapper for AnalysisItem to be used in GListStore.
    """
    __gtype_name__ = 'AnalysisWrapper'

    def __init__(self, item: AnalysisItem):
        super().__init__()
        self.item = item

class HeaderItem(GObject.Object):
    """
    A GObject wrapper for a single header item to be used in a GListStore.
    """
    __gtype_name__ = 'HeaderItem'

    def __init__(self, key, value, change_type, note=""):
        super().__init__()
        self.key = key
        self.value = value
        self.change_type = change_type
        self.note = note
