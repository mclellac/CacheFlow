"""
Security related headers.
"""

from typing import Dict
from .base import HeaderDefinition, CAT_SECURITY

SECURITY_HEADERS: Dict[str, HeaderDefinition] = {
    "strict-transport-security": HeaderDefinition(
        "Enforces the use of HTTPS.",
        CAT_SECURITY,
        "max-age=<seconds>; includeSubDomains",
    ),
    "content-security-policy": HeaderDefinition(
        "Controls resources the user agent is allowed to load for a given page.",
        CAT_SECURITY,
        "default-src 'self'; ...",
    ),
    "x-content-type-options": HeaderDefinition(
        "Prevents the browser from MIME-sniffing a response away from the declared content-type.",
        CAT_SECURITY,
        "nosniff",
    ),
    "x-frame-options": HeaderDefinition(
        "Indicates whether a browser should be allowed to render a page in a <frame>, "
        "<iframe>, <embed> or <object>.",
        CAT_SECURITY,
        "DENY, SAMEORIGIN",
    ),
    "referrer-policy": HeaderDefinition(
        "Controls how much referrer information should be included with requests.",
        CAT_SECURITY,
        "no-referrer, no-referrer-when-downgrade, origin, origin-when-cross-origin, "
        "same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url",
    ),
    "x-xss-protection": HeaderDefinition(
        "Enables the Cross-site scripting (XSS) filter built into most recent web browsers.",
        CAT_SECURITY,
        "0, 1, 1; mode=block",
    ),
}
