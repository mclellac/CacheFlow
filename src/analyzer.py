"""
This module implements the logic for analyzing HTTP headers across layers.
"""

import re
from typing import Dict, List, Any, Optional, NamedTuple
from .knowledge import get_header_info, HeaderDefinition

class AnalysisItem(NamedTuple):
    """
    Represents a single analysis finding for a header.
    """
    key: str
    value: str
    change_type: str  # "ADDED", "REMOVED", "MODIFIED", "UNCHANGED", "MISSING"
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

    def _analyze_value(self, key: str, value: str, category: str,
                       all_headers: Dict[str, str]) -> str:
        """
        Checks for potential issues or provides deeper insight into the value.
        Returns a warning string if an issue is found, else empty string.
        """
        warnings = []
        key = key.lower()
        val_lower = value.lower()

        # Check for Vary: *
        if key == "vary" and "*" in val_lower:
            warnings.append("Varying on '*' disables caching entirely.")

        # Check Cache-Control
        if key == "cache-control":
            cc_warnings = self._analyze_cache_control(val_lower, category)
            if cc_warnings:
                warnings.extend(cc_warnings)

        # Check Set-Cookie on cacheable response
        if key == "set-cookie":
            cookie_warning = self._check_cookie_caching(all_headers)
            if cookie_warning:
                warnings.append(cookie_warning)

        # Check Age vs Max-Age
        if key == "age":
            age_warning = self._check_stale_content(value, all_headers)
            if age_warning:
                warnings.append(age_warning)

        # Check Via header for routing issues
        if key == "via":
            via_warning = self._check_routing(value)
            if via_warning:
                warnings.append(via_warning)

        # Check Security Header Values
        if key == "x-frame-options":
            if val_lower not in ["deny", "sameorigin"]:
                warnings.append(f"Uncommon X-Frame-Options value: {value}")

        if key == "x-content-type-options" and val_lower != "nosniff":
            warnings.append("Should usually be 'nosniff'.")

        return " ".join(warnings)

    def _analyze_cache_control(self, value: str, category: str) -> List[str]:
        warnings = []
        if "private" in value and category == "CDN":
            warnings.append("CDN layer has 'private' cache-control.")

        # Check for conflicts
        if "no-store" in value and ("max-age" in value or "s-maxage" in value):
            warnings.append("Conflict: 'no-store' is used with 'max-age'.")

        if "no-cache" in value and "max-age" in value:
             # This is technically valid (revalidate), but often confused.
             # I'll leave it unless strict mode.
            pass

        return warnings

    def _check_cookie_caching(self, headers: Dict[str, str]) -> str:
        cc = headers.get("cache-control", "").lower()
        if "private" in cc or "no-cache" in cc or "no-store" in cc:
            return ""

        # If public or max-age is set, and Set-Cookie is present
        if "public" in cc or "max-age" in cc or "s-maxage" in cc:
            return "Security Risk: Set-Cookie present on cacheable response."

        return ""

    def _check_stale_content(self, age_val: str, headers: Dict[str, str]) -> str:
        try:
            age = int(age_val)
        except ValueError:
            return "Invalid Age value."

        cc = headers.get("cache-control", "").lower()
        match = re.search(r'max-age=(\d+)', cc)
        if match:
            max_age = int(match.group(1))
            if age > max_age:
                return f"Stale: Age ({age}) > max-age ({max_age})."
        return ""

    def _check_routing(self, via_val: str) -> str:
        # Simple heuristic: count commas
        hops = via_val.count(',') + 1
        if hops > 4:
            return f"High hop count detected ({hops}). Potential routing loop?"
        return ""

    def _check_missing_security_headers(self, headers: Dict[str, str]) -> List[AnalysisItem]:
        items = []
        # List of critical security headers to check
        security_headers = [
            "strict-transport-security",
            "content-security-policy",
            "x-content-type-options",
            "x-frame-options"
        ]

        for key in security_headers:
            if key not in headers:
                info = get_header_info(key)
                items.append(AnalysisItem(
                    key=key, # Keep lowercase or capitalize? Display key is usually capitalized.
                    value="(Missing)",
                    change_type="MISSING",
                    description=f"Recommended security header missing. {info.description}",
                    category=info.category,
                    warning="Security Risk"
                ))
        return items

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
            warning = self._analyze_value(key, value, info.category, current_headers)

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

        # Check for Missing Security Headers
        # (only if this layer has headers, to avoid noise on error layers)
        if current_headers:
            missing_items = self._check_missing_security_headers(current_headers)
            items.extend(missing_items)

        # Sort items: Missing/Added/Modified/Removed first, then Unchanged
        # Priority: MISSING=0, ADDED=1, MODIFIED=2, REMOVED=3, UNCHANGED=4
        priority = {"MISSING": 0, "ADDED": 1, "MODIFIED": 2, "REMOVED": 3, "UNCHANGED": 4}
        items.sort(key=lambda x: (
            priority.get(x.change_type, 5),
            x.key
        ))

        return AnalysisReport(current_layer.get('name', 'Unknown'), items)
