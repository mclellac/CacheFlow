"""
This module contains the knowledge base for HTTP headers, including descriptions,
categories, and expected values.
"""

from typing import Dict, NamedTuple

class HeaderDefinition(NamedTuple):
    """
    Defines the properties of a known HTTP header.
    """
    description: str
    category: str
    expected_values: str

# Categories
CAT_CDN = "CDN"
CAT_CACHE = "Caching"
CAT_SECURITY = "Security"
CAT_PROXY = "Proxy"
CAT_DEBUG = "Debugging"
CAT_STANDARD = "Standard"
CAT_LOAD_BALANCER = "Load Balancer"

HEADER_KNOWLEDGE: Dict[str, HeaderDefinition] = {
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
    "via": HeaderDefinition(
        "Added by proxies, both forward and reverse, and can appear in the request "
        "headers and the response headers.",
        CAT_PROXY,
        "Protocol-Version Proxy-Name"
    ),

    # Akamai
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

    # Varnish
    "x-varnish": HeaderDefinition(
        "The ID of the current request and the ID of the request that populated the cache "
        "(if hit).",
        CAT_PROXY,
        "ID [ID]"
    ),

    # Security
    "strict-transport-security": HeaderDefinition(
        "Enforces the use of HTTPS.",
        CAT_SECURITY,
        "max-age=<seconds>; includeSubDomains"
    ),
    "content-security-policy": HeaderDefinition(
        "Controls resources the user agent is allowed to load for a given page.",
        CAT_SECURITY,
        "default-src 'self'; ..."
    ),
    "x-content-type-options": HeaderDefinition(
        "Prevents the browser from MIME-sniffing a response away from the declared content-type.",
        CAT_SECURITY,
        "nosniff"
    ),
    "x-frame-options": HeaderDefinition(
        "Indicates whether a browser should be allowed to render a page in a <frame>, "
        "<iframe>, <embed> or <object>.",
        CAT_SECURITY,
        "DENY, SAMEORIGIN"
    ),

    # Load Balancer / K8s
    "x-forwarded-for": HeaderDefinition(
        "Identifies the originating IP address of a client connecting to a web server "
        "through an HTTP proxy or load balancer.",
        CAT_LOAD_BALANCER,
        "IP address(es)"
    ),
    "x-forwarded-proto": HeaderDefinition(
        "Identifies the protocol (HTTP or HTTPS) that a client used to connect to "
        "your proxy or load balancer.",
        CAT_LOAD_BALANCER,
        "http, https"
    ),
    "x-original-host": HeaderDefinition(
        "The original Host header sent by the client, often preserved by Ingress controllers.",
        CAT_LOAD_BALANCER,
        "Hostname"
    ),
    "x-request-id": HeaderDefinition(
        "Unique ID for the request, often used for tracing across microservices.",
        CAT_DEBUG,
        "UUID"
    ),
}

def get_header_info(header_key: str) -> HeaderDefinition:
    """
    Retrieves the definition for a given header key.
    Returns a default definition if not found.
    """
    key = header_key.lower()
    return HEADER_KNOWLEDGE.get(key, HeaderDefinition(
        "Unknown or custom header.",
        "Unknown",
        "Any"
    ))
