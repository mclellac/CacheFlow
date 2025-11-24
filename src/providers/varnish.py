"""
Varnish Proxy implementation.
"""

from typing import Dict
from .base import HeaderDefinition, BaseProvider, ProviderType, CAT_PROXY

VARNISH_HEADERS: Dict[str, HeaderDefinition] = {
    "via": HeaderDefinition(
        "Added by proxies, both forward and reverse, and can appear in the request "
        "headers and the response headers.",
        CAT_PROXY,
        "Protocol-Version Proxy-Name"
    ),
    "x-varnish": HeaderDefinition(
        "The ID of the current request and the ID of the request that populated the cache "
        "(if hit).",
        CAT_PROXY,
        "ID [ID]"
    ),
}

class Varnish(BaseProvider):
    """
    Varnish Cache Proxy Provider.
    """
    name = "Varnish"
    provider_type = ProviderType.CACHE_PROXY

    def get_debug_headers(self) -> Dict[str, str]:
        # Varnish debug headers often depend on VCL configuration, but these are common conventions
        return {
            "X-Varnish-Debug": "true"
        }

    def get_known_headers(self) -> Dict[str, HeaderDefinition]:
        return VARNISH_HEADERS
