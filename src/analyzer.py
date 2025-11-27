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

    def _analyze_value(
        self, key: str, value: str, category: str, all_headers: Dict[str, str]
    ) -> str:
        """Checks for potential issues or provides deeper insight into a value.

        Args:
            key: The header key.
            value: The header value.
            category: The category of the header.
            all_headers: All headers for the current layer.

        Returns:
            A warning string if an issue is found, otherwise an empty string.
        """
        warnings = []
        key = key.lower()
        val_lower = value.lower()

        if key == "vary" and "*" in val_lower:
            warnings.append("Varying on '*' disables caching entirely.")

        if key == "cache-control":
            cc_warnings = self._analyze_cache_control(val_lower, category)
            if cc_warnings:
                warnings.extend(cc_warnings)

        if key == "set-cookie":
            cookie_warning = self._check_cookie_caching(all_headers)
            if cookie_warning:
                warnings.append(cookie_warning)

        if key == "age":
            age_warning = self._check_stale_content(value, all_headers)
            if age_warning:
                warnings.append(age_warning)

        if key == "via":
            via_warning = self._check_routing(value)
            if via_warning:
                warnings.append(via_warning)

        if key == "x-frame-options":
            if val_lower not in ["deny", "sameorigin"]:
                warnings.append(f"Uncommon X-Frame-Options value: {value}")

        if key == "x-content-type-options" and val_lower != "nosniff":
            warnings.append("Should usually be 'nosniff'.")

        return " ".join(warnings)

    def _analyze_cache_control(self, value: str, category: str) -> List[str]:
        """Analyzes the Cache-Control header for potential issues.

        Args:
            value: The value of the Cache-Control header.
            category: The category of the header.

        Returns:
            A list of warning strings.
        """
        warnings = []
        if "private" in value and category == "CDN":
            warnings.append("CDN layer has 'private' cache-control.")

        if "no-store" in value and ("max-age" in value or "s-maxage" in value):
            warnings.append("Conflict: 'no-store' is used with 'max-age'.")

        if "no-cache" in value and "max-age" in value:
            pass

        return warnings

    def _check_cookie_caching(self, headers: Dict[str, str]) -> str:
        """Checks for Set-Cookie headers on cacheable responses.

        Args:
            headers: All headers for the current layer.

        Returns:
            A warning string if a security risk is found, otherwise an empty
            string.
        """
        cc = headers.get("cache-control", "").lower()
        if "private" in cc or "no-cache" in cc or "no-store" in cc:
            return ""

        if "public" in cc or "max-age" in cc or "s-maxage" in cc:
            return "Security Risk: Set-Cookie present on cacheable response."

        return ""

    def _check_stale_content(
        self, age_val: str, headers: Dict[str, str]
    ) -> str:
        """Checks for stale content by comparing Age and max-age.

        Args:
            age_val: The value of the Age header.
            headers: All headers for the current layer.

        Returns:
            A warning string if stale content is detected, otherwise an empty
            string.
        """
        try:
            age = int(age_val)
        except ValueError:
            return "Invalid Age value."

        cc = headers.get("cache-control", "").lower()
        match = re.search(r"max-age=(\d+)", cc)
        if match:
            max_age = int(match.group(1))
            if age > max_age:
                return f"Stale: Age ({age}) > max-age ({max_age})."
        return ""

    def _check_routing(self, via_val: str) -> str:
        """Checks for potential routing loops by analyzing the Via header.

        Args:
            via_val: The value of the Via header.

        Returns:
            A warning string if a potential routing loop is detected, otherwise
            an empty string.
        """
        hops = via_val.count(",") + 1
        if hops > 4:
            return f"High hop count detected ({hops}). Potential routing loop?"
        return ""

    def _check_missing_security_headers(
        self, headers: Dict[str, str], ignore_keys: Optional[set] = None
    ) -> List[AnalysisItem]:
        """Checks for missing security headers.

        Args:
            headers: All headers for the current layer.
            ignore_keys: A set of keys to ignore (e.g. already marked removed).

        Returns:
            A list of AnalysisItem objects for each missing security header.
        """
        items = []
        security_headers = [
            "strict-transport-security",
            "content-security-policy",
            "x-content-type-options",
            "x-frame-options",
        ]
        ignore = ignore_keys or set()

        for key in security_headers:
            if key not in headers and key not in ignore:
                info = get_header_info(key)
                items.append(
                    AnalysisItem(
                        key=key,
                        value="(Missing)",
                        change_type="MISSING",
                        description=(
                            "Recommended security header missing. "
                            f"{info.description}"
                        ),
                        category=info.category,
                        warning="Security Risk",
                    )
                )
        return items

    def analyze_layer(
        self,
        current_layer: Dict[str, Any],
        upstream_layer: Optional[Dict[str, Any]],
        is_edge: bool = False,
    ) -> AnalysisReport:
        """Analyzes the headers of a layer against an upstream layer.

        Args:
            current_layer: The layer to analyze.
            upstream_layer: The upstream layer to compare against.
            is_edge: Whether this layer is the edge (client-facing) layer.

        Returns:
            An AnalysisReport object containing the analysis results.
        """
        current_headers = {
            k.lower(): v for k, v in current_layer.get("headers", {}).items()
        }

        original_keys = {
            k.lower(): k for k in current_layer.get("headers", {}).keys()
        }

        upstream_headers = {}
        if upstream_layer:
            upstream_headers = {
                k.lower(): v
                for k, v in upstream_layer.get("headers", {}).items()
            }
            for k in upstream_layer.get("headers", {}).keys():
                if k.lower() not in original_keys:
                    original_keys[k.lower()] = k

        items: List[AnalysisItem] = []

        for key, value in current_headers.items():
            display_key = original_keys.get(key, key)
            info: HeaderDefinition = get_header_info(key)
            warning = self._analyze_value(
                key, value, info.category, current_headers
            )

            if key not in upstream_headers:
                if upstream_layer is None:
                    items.append(
                        AnalysisItem(
                            key=display_key,
                            value=value,
                            change_type="UNCHANGED",
                            description=f"Original header. {info.description}",
                            category=info.category,
                            warning=warning,
                        )
                    )
                else:
                    items.append(
                        AnalysisItem(
                            key=display_key,
                            value=value,
                            change_type="ADDED",
                            description=f"New header. {info.description}",
                            category=info.category,
                            warning=warning,
                        )
                    )
            elif upstream_headers[key] != value:
                prev_val = upstream_headers[key]
                items.append(
                    AnalysisItem(
                        key=display_key,
                        value=value,
                        change_type="MODIFIED",
                        description=f"Changed from '{prev_val}'. "
                        f"{info.description}",
                        category=info.category,
                        warning=warning,
                    )
                )
            else:
                items.append(
                    AnalysisItem(
                        key=display_key,
                        value=value,
                        change_type="UNCHANGED",
                        description=info.description,
                        category=info.category,
                        warning=warning,
                    )
                )

        removed_keys = set()
        for key, value in upstream_headers.items():
            if key not in current_headers:
                removed_keys.add(key)
                display_key = original_keys.get(key, key)
                info = get_header_info(key)

                warning = ""
                # If a security header is removed, flag it as a risk
                if key in [
                    "strict-transport-security",
                    "content-security-policy",
                    "x-content-type-options",
                    "x-frame-options",
                ]:
                    warning = "Security Risk: Recommended header removed."

                items.append(
                    AnalysisItem(
                        key=display_key,
                        value=value,
                        change_type="REMOVED",
                        description=f"Header removed in this layer. "
                        f"{info.description}",
                        category=info.category,
                        warning=warning,
                    )
                )

        if current_headers and is_edge:
            missing_items = self._check_missing_security_headers(
                current_headers, ignore_keys=removed_keys
            )
            items.extend(missing_items)

        priority = {
            "MISSING": 0,
            "ADDED": 1,
            "MODIFIED": 2,
            "REMOVED": 3,
            "UNCHANGED": 4,
        }
        items.sort(key=lambda x: (priority.get(x.change_type, 5), x.key))

        return AnalysisReport(current_layer.get("name", "Unknown"), items)
