"""
This module implements the logic for analyzing HTTP headers across layers.
"""

from typing import Dict, List, Any, Optional, NamedTuple
from .knowledge import get_header_info, HeaderDefinition

class AnalysisItem(NamedTuple):
    """
    Represents a single analysis finding for a header.
    """
    key: str
    value: str
    change_type: str  # "ADDED", "REMOVED", "MODIFIED", "UNCHANGED"
    description: str
    category: str
    warning: str = ""

class AnalysisReport:
    """
    Container for the results of a layer analysis.
    """
    def __init__(self, layer_name: str, items: List[AnalysisItem]):
        self.layer_name = layer_name
        self.items = items

class HeaderAnalyzer:
    """
    Analyzes headers to detect changes and provide explanations.
    """

    def _analyze_value(self, key: str, value: str, category: str) -> str:
        """
        Checks for potential issues or provides deeper insight into the value.
        Returns a warning string if an issue is found, else empty string.
        """
        warning = ""
        key = key.lower()
        val_lower = value.lower()

        if key == "vary" and "*" in val_lower:
            warning = "Varying on '*' disables caching entirely."

        if key == "cache-control":
            if "private" in val_lower and category == "CDN":
                warning = "CDN layer has 'private' cache-control."

        return warning

    def analyze_layer(self, current_layer: Dict[str, Any],
                      upstream_layer: Optional[Dict[str, Any]]) -> AnalysisReport:
        """
        Analyzes the headers of the current layer against an upstream layer.
        """
        current_headers = {k.lower(): v for k, v in current_layer.get('headers', {}).items()}

        # Map lower-case keys back to original casing for display
        original_keys = {k.lower(): k for k in current_layer.get('headers', {}).keys()}

        upstream_headers = {}
        if upstream_layer:
            upstream_headers = {k.lower(): v for k, v in upstream_layer.get('headers', {}).items()}
            # Add upstream keys to original_keys map if not present
            for k in upstream_layer.get('headers', {}).keys():
                if k.lower() not in original_keys:
                    original_keys[k.lower()] = k

        items: List[AnalysisItem] = []

        # Check for Added, Modified, Unchanged
        for key, value in current_headers.items():
            display_key = original_keys.get(key, key)
            info: HeaderDefinition = get_header_info(key)
            warning = self._analyze_value(key, value, info.category)

            if key not in upstream_headers:
                items.append(AnalysisItem(
                    key=display_key,
                    value=value,
                    change_type="ADDED",
                    description=f"New header. {info.description}",
                    category=info.category,
                    warning=warning
                ))
            elif upstream_headers[key] != value:
                prev_val = upstream_headers[key]
                items.append(AnalysisItem(
                    key=display_key,
                    value=value,
                    change_type="MODIFIED",
                    description=f"Changed from '{prev_val}'. {info.description}",
                    category=info.category,
                    warning=warning
                ))
            else:
                items.append(AnalysisItem(
                    key=display_key,
                    value=value,
                    change_type="UNCHANGED",
                    description=info.description,
                    category=info.category,
                    warning=warning
                ))

        # Check for Removed
        for key, value in upstream_headers.items():
            if key not in current_headers:
                display_key = original_keys.get(key, key)
                info = get_header_info(key)
                items.append(AnalysisItem(
                    key=display_key,
                    value=value,  # Show the value that was removed
                    change_type="REMOVED",
                    description=f"Header removed in this layer. {info.description}",
                    category=info.category,
                    warning=""
                ))

        # Sort items: Added/Modified/Removed first, then Unchanged
        priority = {"ADDED": 0, "MODIFIED": 1, "REMOVED": 2, "UNCHANGED": 3}
        items.sort(key=lambda x: (priority.get(x.change_type, 4), x.key))

        return AnalysisReport(current_layer.get('name', 'Unknown'), items)
