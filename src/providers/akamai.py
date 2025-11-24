"""
Akamai CDN implementation.
"""

from typing import Dict
from .base import HeaderDefinition, BaseProvider, ProviderType, CAT_CDN

AKAMAI_HEADERS: Dict[str, HeaderDefinition] = {
    "server-timing": HeaderDefinition(
        "Communicates one or more metrics and descriptions for the given request-response cycle.",
        CAT_CDN,
        "app;dur=123, cdn-cache;desc=HIT"
    ),
    "x-cache": HeaderDefinition(
        "Akamai (and other CDNs): Indicates whether the response was served from cache.",
        CAT_CDN,
        "TCP_HIT, TCP_MISS, TCP_REFRESH_HIT"
    ),
    "x-akamai-session-info": HeaderDefinition(
        "Akamai debug header providing session details.",
        CAT_CDN,
        "Key-value pairs"
    ),
    "x-true-cache-key": HeaderDefinition(
        "The internal cache key used by the CDN to store the object.",
        CAT_CDN,
        "URL path + query params"
    ),
    "x-cache-key": HeaderDefinition(
        "The internal cache key used by the CDN to store the object.",
        CAT_CDN,
        "URL path + query params"
    ),
    "x-origin-server": HeaderDefinition(
        "Identifies the specific origin server that handled the request.",
        CAT_CDN,
        "Hostname"
    ),
    "x-cache-server": HeaderDefinition(
        "Identifies the specific cache server that handled the request.",
        CAT_CDN,
        "Hostname"
    ),
    "x-cache-key-extended-internal-use-only": HeaderDefinition(
        "Extended internal cache key details used by Akamai.",
        CAT_CDN,
        "Internal key format"
    ),
    "x-check-cacheable": HeaderDefinition(
        "Indicates whether the response was deemed cacheable by the CDN.",
        CAT_CDN,
        "YES, NO"
    ),
    "x-akamai-request-id": HeaderDefinition(
        "Unique identifier for the request assigned by Akamai.",
        CAT_CDN,
        "Hex string"
    ),
}

class Akamai(BaseProvider):
    """
    Akamai CDN Provider.
    """
    name = "Akamai"
    provider_type = ProviderType.CDN

    def get_debug_headers(self) -> Dict[str, str]:
        return {
            "Pragma": (
                "akamai-x-get-request-id, akamai-x-cache-on, akamai-x-cache-key, "
                "akamai-x-check-cacheable, akamai-x-get-cache-key, "
                "akamai-x-get-true-cache-key"
            )
        }

    def get_known_headers(self) -> Dict[str, HeaderDefinition]:
        return AKAMAI_HEADERS
