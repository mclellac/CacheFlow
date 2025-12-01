"""
This module defines strategies for handling layer-specific configuration logic.
"""

from typing import Dict, Any, List, Optional
from ..providers.base import ProviderType


class LayerConfigStrategy:
    """Base strategy for layer configuration."""

    def __init__(self, layer_type: ProviderType):
        self.layer_type = layer_type

    def get_visibility(self) -> Dict[str, bool]:
        """Returns a dictionary of visibility flags for UI elements."""
        return {
            "url": True,
            "default_backend": True,
            "routing": True,
            "overrides": True,
            "path_match": True,
            "nodes": True,
            "headers": True,
        }

    def get_labels(self) -> Dict[str, str]:
        """Returns a dictionary of labels for UI elements."""
        return {
            "url_title": "Host URL",
            "default_backend_host_title": "Default Backend Host",
            "default_backend_header_title": "Default Backend Host Header (Optional)",
            "routing_rules_title": "Backend Rules",
            "routing_rules_subtitle": "Define backend destinations based on request paths.",
            "add_routing_rule_tooltip": "Add New Backend",
            "rule_label_prefix": "Backend",
        }

    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Processes data before saving (e.g., flattening rules)."""
        return data


class CDNConfigStrategy(LayerConfigStrategy):
    """Configuration strategy for CDN layers."""

    def __init__(self):
        super().__init__(ProviderType.CDN)

    def get_visibility(self) -> Dict[str, bool]:
        return {
            "url": False,
            "default_backend": True,
            "routing": True,
            "overrides": False,
            "path_match": False,
            "nodes": False,
            "headers": False,  # Explicitly hide for CDN
        }

    def get_labels(self) -> Dict[str, str]:
        return {
            "url_title": "Host URL",  # Hidden but key required
            "default_backend_host_title": "Default Origin Host (Fallback)",
            "default_backend_header_title": "Default Origin Host Header",
            "routing_rules_title": "Origins",
            "routing_rules_subtitle": "Configure origin servers and matching rules.",
            "add_routing_rule_tooltip": "Add New Origin",
            "rule_label_prefix": "Origin",
        }


class LBConfigStrategy(LayerConfigStrategy):
    """Configuration strategy for Load Balancer layers."""

    def __init__(self):
        super().__init__(ProviderType.LOAD_BALANCER)

    def get_visibility(self) -> Dict[str, bool]:
        return {
            "url": True,
            "default_backend": True,
            "routing": True,
            "overrides": True,
            "path_match": True,
            "nodes": False,
            "headers": True,
        }

    def get_labels(self) -> Dict[str, str]:
        return {
            "url_title": "Load Balancer Hostname (e.g. lb.example.com)",
            "default_backend_host_title": "Default Target Host (Fallback)",
            "default_backend_header_title": "Default Target Host Header (Optional)",
            "routing_rules_title": "Target Pools",
            "routing_rules_subtitle": "Configure target pools (e.g. Cache Proxies) and matching rules.",
            "add_routing_rule_tooltip": "Add New Target Pool",
            "rule_label_prefix": "Target",
        }


class ProxyConfigStrategy(LayerConfigStrategy):
    """Configuration strategy for Cache Proxy layers."""

    def __init__(self):
        super().__init__(ProviderType.CACHE_PROXY)

    # Uses default visibility and labels mostly, can override if needed
    def get_visibility(self) -> Dict[str, bool]:
        return {
            "url": False,
            "default_backend": True,
            "routing": True,
            "overrides": True,
            "path_match": True,
            "nodes": True,
            "headers": True,
        }


class BackendConfigStrategy(LayerConfigStrategy):
    """Configuration strategy for Application Backend layers."""

    def __init__(self):
        super().__init__(ProviderType.APP_BACKEND)

    def get_visibility(self) -> Dict[str, bool]:
        return {
            "url": False,
            "default_backend": False,
            "routing": False,
            "overrides": False,
            "path_match": False,
            "nodes": True,
            "headers": True,
        }


def get_strategy(layer_type: ProviderType) -> LayerConfigStrategy:
    """Factory function to get the appropriate strategy."""
    strategies = {
        ProviderType.CDN: CDNConfigStrategy,
        ProviderType.LOAD_BALANCER: LBConfigStrategy,
        ProviderType.CACHE_PROXY: ProxyConfigStrategy,
        ProviderType.APP_BACKEND: BackendConfigStrategy,
    }
    strategy_cls = strategies.get(layer_type, CDNConfigStrategy)
    return strategy_cls()
