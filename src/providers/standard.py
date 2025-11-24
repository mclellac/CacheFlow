"""
Standard HTTP headers.
"""

from typing import Dict
from .base import HeaderDefinition, CAT_CACHE, CAT_STANDARD

STANDARD_HEADERS: Dict[str, HeaderDefinition] = {
    # Standard Caching
    "cache-control": HeaderDefinition(
        "Directives for caching mechanisms in both requests and responses.",
        CAT_CACHE,
        "public, private, no-cache, no-store, max-age=<seconds>"
    ),
    "vary": HeaderDefinition(
        "Tells downstream proxies how to match future request headers to decide whether "
        "the cached response can be used.",
        CAT_CACHE,
        "Accept-Encoding, User-Agent, Origin"
    ),
    "age": HeaderDefinition(
        "The time in seconds the object has been in a proxy cache.",
        CAT_CACHE,
        "Seconds (integer)"
    ),
    "expires": HeaderDefinition(
        "The date/time after which the response is considered stale.",
        CAT_CACHE,
        "HTTP-date"
    ),

    # Standard Semantics
    "server": HeaderDefinition(
        "Contains information about the software used by the origin server.",
        CAT_STANDARD,
        "Product/Version"
    ),
}
