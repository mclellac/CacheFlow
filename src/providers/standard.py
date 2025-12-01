"""
Standard HTTP headers.
"""

from typing import Dict
from .base import (
    HeaderDefinition,
    CAT_CACHE,
    CAT_STANDARD,
    CAT_AUTH,
    CAT_CORS,
    CAT_COOKIES,
    CAT_CONTENT,
    CAT_CONNECTION,
    CAT_DEPRECATED,
    CAT_PROXY,
)

STANDARD_HEADERS: Dict[str, HeaderDefinition] = {
    # Authentication
    "authorization": HeaderDefinition(
        "Contains the credentials to authenticate a user-agent with a server.",
        CAT_AUTH,
        "Basic <credentials>, Bearer <token>",
    ),
    "www-authenticate": HeaderDefinition(
        "Defines the authentication method that should be used to access a resource.",
        CAT_AUTH,
        "Basic, Bearer, Digest, Negotiate",
    ),
    "proxy-authenticate": HeaderDefinition(
        "Defines the authentication method that should be used to access a resource "
        "behind a proxy server.",
        CAT_AUTH,
        "Basic, Digest, Negotiate",
    ),
    "proxy-authorization": HeaderDefinition(
        "Contains the credentials to authenticate a user agent with a proxy server.",
        CAT_AUTH,
        "Basic <credentials>",
    ),
    # Caching
    "cache-control": HeaderDefinition(
        "Directives for caching mechanisms in both requests and responses.",
        CAT_CACHE,
        "public, private, no-cache, no-store, max-age=<seconds>",
        meaning="This header tells the browser and CDNs how long to save this file.",
        impact="If set incorrectly, users might see old content (cached too long) or your servers might be overloaded (cached too short).",
        recommendation="For static assets (images, css), use 'public, max-age=31536000'. For dynamic content, use 'no-cache'.",
    ),
    "vary": HeaderDefinition(
        "Tells downstream proxies how to match future request headers to decide whether "
        "the cached response can be used.",
        CAT_CACHE,
        "Accept-Encoding, User-Agent, Origin",
        meaning="This helps caches serve different versions of the same URL based on user headers (like language or compression).",
        impact="Missing this header can cause users to receive the wrong version (e.g. wrong language). Too many values can reduce cache efficiency.",
        recommendation="Only include headers that actually change the response body (e.g., 'Accept-Encoding' or 'Accept-Language').",
    ),
    "age": HeaderDefinition(
        "The time in seconds the object has been in a proxy cache.",
        CAT_CACHE,
        "Seconds (integer)",
    ),
    "expires": HeaderDefinition(
        "The date/time after which the response is considered stale.",
        CAT_CACHE,
        "HTTP-date",
    ),
    "clear-site-data": HeaderDefinition(
        "Clears browsing data (cookies, storage, cache) associated with the requesting "
        "website.",
        CAT_CACHE,
        '"cache", "cookies", "storage", "executionContexts"',
    ),
    # Connection Management
    "connection": HeaderDefinition(
        "Controls whether the network connection stays open after the current "
        "transaction finishes.",
        CAT_CONNECTION,
        "keep-alive, close",
    ),
    "keep-alive": HeaderDefinition(
        "Controls how long a persistent connection should stay open.",
        CAT_CONNECTION,
        "timeout=<seconds>, max=<number>",
    ),
    "transfer-encoding": HeaderDefinition(
        "Specifies the form of encoding used to safely transfer the resource to the user.",
        CAT_CONNECTION,
        "chunked, compress, deflate, gzip",
    ),
    # Content Negotiation
    "accept": HeaderDefinition(
        "Informs the server about the types of data that can be sent back.",
        CAT_STANDARD,
        "text/html, application/json, */*",
    ),
    "accept-encoding": HeaderDefinition(
        "The encoding algorithm (usually compression) that can be used on the resource sent back.",
        CAT_STANDARD,
        "gzip, deflate, br",
    ),
    "accept-language": HeaderDefinition(
        "Informs the server about the human language the server is expected to send back.",
        CAT_STANDARD,
        "en-US, fr, de",
    ),
    # Cookies
    "cookie": HeaderDefinition(
        "Contains stored HTTP cookies previously sent by the server with the Set-Cookie header.",
        CAT_COOKIES,
        "name=value; name2=value2",
    ),
    "set-cookie": HeaderDefinition(
        "Send cookies from the server to the user-agent.",
        CAT_COOKIES,
        "name=value; Path=/; Secure; HttpOnly; SameSite=Strict",
    ),
    # CORS
    "access-control-allow-origin": HeaderDefinition(
        "Indicates whether the response can be shared.",
        CAT_CORS,
        "*, <origin>, null",
    ),
    "access-control-allow-credentials": HeaderDefinition(
        "Indicates whether the response to the request can be exposed when the credentials "
        "flag is true.",
        CAT_CORS,
        "true",
    ),
    "access-control-allow-headers": HeaderDefinition(
        "Used in response to a preflight request to indicate which HTTP headers can be used "
        "when making the actual request.",
        CAT_CORS,
        "<header-name>[, <header-name>]*",
    ),
    "access-control-allow-methods": HeaderDefinition(
        "Specifies the methods allowed when accessing the resource in response to a "
        "preflight request.",
        CAT_CORS,
        "GET, POST, OPTIONS, PUT, DELETE",
    ),
    "access-control-expose-headers": HeaderDefinition(
        "Indicates which headers can be exposed as part of the response by listing their names.",
        CAT_CORS,
        "<header-name>[, <header-name>]*",
    ),
    "access-control-max-age": HeaderDefinition(
        "Indicates how long the results of a preflight request can be cached.",
        CAT_CORS,
        "Seconds",
    ),
    "origin": HeaderDefinition(
        "Indicates where a fetch originates from.",
        CAT_CORS,
        "<scheme>://<host>[:<port>]",
    ),
    # Content / Message Body
    "content-length": HeaderDefinition(
        "The size of the resource, in decimal number of bytes.",
        CAT_CONTENT,
        "Integer",
    ),
    "content-type": HeaderDefinition(
        "Indicates the media type of the resource.",
        CAT_CONTENT,
        "MIME type (e.g., text/html; charset=utf-8)",
    ),
    "content-encoding": HeaderDefinition(
        "Used to specify the compression algorithm.",
        CAT_CONTENT,
        "gzip, br, deflate",
    ),
    "content-language": HeaderDefinition(
        "Describes the human language(s) intended for the audience.",
        CAT_CONTENT,
        "en, fr",
    ),
    "content-location": HeaderDefinition(
        "Indicates an alternate location for the returned data.",
        CAT_CONTENT,
        "URL",
    ),
    "content-disposition": HeaderDefinition(
        "Indicates if the resource should be displayed inline or handled like a download.",
        CAT_CONTENT,
        'inline, attachment; filename="filename.jpg"',
    ),
    "content-range": HeaderDefinition(
        "Indicates where in a full body message a partial message belongs.",
        CAT_CONTENT,
        "bytes <unit>-<unit>/<total>",
    ),
    # Request Context
    "host": HeaderDefinition(
        "Specifies the domain name of the server and optionally the TCP port number.",
        CAT_STANDARD,
        "domain.com, domain.com:port",
    ),
    "referer": HeaderDefinition(
        "The address of the previous web page from which a link to the currently requested "
        "page was followed.",
        CAT_STANDARD,
        "URL",
    ),
    "user-agent": HeaderDefinition(
        "Contains a characteristic string that allows the network protocol peers to identify "
        "the application type.",
        CAT_STANDARD,
        "Mozilla/5.0 ...",
    ),
    # Response Context
    "allow": HeaderDefinition(
        "Lists the set of HTTP request methods supported by a resource.",
        CAT_STANDARD,
        "GET, POST, HEAD",
    ),
    "server": HeaderDefinition(
        "Contains information about the software used by the origin server.",
        CAT_STANDARD,
        "Apache/2.4.1 (Unix)",
    ),
    "date": HeaderDefinition(
        "The date and time at which the message was originated.",
        CAT_STANDARD,
        "HTTP-date",
    ),
    "location": HeaderDefinition(
        "Indicates the URL to redirect a page to.", CAT_STANDARD, "URL"
    ),
    "refresh": HeaderDefinition(
        "Directs the browser to reload the page or redirect to another.",
        CAT_STANDARD,
        "5; url=http://example.com/",
    ),
    "retry-after": HeaderDefinition(
        "Indicates how long the user agent should wait before making a follow-up request.",
        CAT_STANDARD,
        "Seconds or HTTP-date",
    ),
    # Proxies
    "forwarded": HeaderDefinition(
        "Contains information from the client-facing side of proxy servers.",
        CAT_PROXY,
        "by=<identifier>; for=<identifier>; host=<host>; proto=<http|https>",
    ),
    "via": HeaderDefinition(
        "Added by proxies, both forward and reverse proxies, and can appear in request "
        "and response headers.",
        CAT_PROXY,
        "1.1 varnish",
    ),
    "x-forwarded-for": HeaderDefinition(
        "Identifies the originating IP addresses of a client connecting through an HTTP "
        "proxy or load balancer.",
        CAT_PROXY,
        "client, proxy1, proxy2",
    ),
    "x-forwarded-host": HeaderDefinition(
        "Identifies the original host requested that a client used to connect to your "
        "proxy or load balancer.",
        CAT_PROXY,
        "host:port",
    ),
    "x-forwarded-proto": HeaderDefinition(
        "Identifies the protocol (HTTP or HTTPS) that a client used to connect to your "
        "proxy or load balancer.",
        CAT_PROXY,
        "http, https",
    ),
    # Deprecated
    "pragma": HeaderDefinition(
        "Implementation-specific header that may have various effects anywhere along the "
        "request-response chain.",
        CAT_DEPRECATED,
        "no-cache",
    ),
    "warning": HeaderDefinition(
        "General warning information about possible problems.",
        CAT_DEPRECATED,
        "199 Miscellaneous warning",
    ),
}
