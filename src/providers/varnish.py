"""
Varnish Proxy headers.
"""

from typing import Dict
from .base import HeaderDefinition, CAT_PROXY

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
