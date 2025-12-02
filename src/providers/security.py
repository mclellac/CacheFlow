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
        meaning="Tells the browser to ONLY ever connect to this site using HTTPS (secure connection), never plain HTTP.",
        impact="Crucial for preventing Man-in-the-Middle attacks. If missing, a user typing 'http://example.com' could be intercepted before the redirect to HTTPS.",
        recommendation="Set to at least 1 year (max-age=31536000) and include 'includeSubDomains' and 'preload' for maximum security.",
    ),
    "content-security-policy": HeaderDefinition(
        "Controls resources the user agent is allowed to load for a given page.",
        CAT_SECURITY,
        "default-src 'self'; ...",
        meaning="A whitelist of where your site is allowed to load things from (scripts, images, styles).",
        impact="The most powerful tool against Cross-Site Scripting (XSS) and data injection attacks. If missing, malicious scripts can be loaded from anywhere.",
        recommendation="Start with strict defaults like \"default-src 'self'\" and add trusted domains as needed.",
    ),
    "x-content-type-options": HeaderDefinition(
        "Prevents the browser from MIME-sniffing a response away from the declared content-type.",
        CAT_SECURITY,
        "nosniff",
        meaning="Tells the browser: 'Trust what I say the file type is, don't guess'.",
        impact="Prevents attacks where a browser is tricked into running a non-script file (like an image) as a script.",
        recommendation="Always set this to 'nosniff'.",
    ),
    "x-frame-options": HeaderDefinition(
        "Indicates whether a browser should be allowed to render a page in a <frame>, "
        "<iframe>, <embed> or <object>.",
        CAT_SECURITY,
        "DENY, SAMEORIGIN",
        meaning="Controls if other sites can put your website inside a frame (like a picture-in-picture).",
        impact="Prevents 'Clickjacking' attacks where an attacker overlays an invisible frame of your site to trick users into clicking buttons.",
        recommendation="Use 'DENY' if you don't want to be framed, or 'SAMEORIGIN' if only you can frame yourself.",
    ),
    "referrer-policy": HeaderDefinition(
        "Controls how much referrer information should be included with requests.",
        CAT_SECURITY,
        "no-referrer, no-referrer-when-downgrade, origin, origin-when-cross-origin, "
        "same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url",
        meaning="Decides how much info about the 'current page' is sent to the 'next page' when you click a link.",
        impact="Protects user privacy by not leaking full URLs (which might contain sensitive IDs) to third-party sites.",
        recommendation="Use 'strict-origin-when-cross-origin' to balance privacy and functionality.",
    ),
    "x-xss-protection": HeaderDefinition(
        "Enables the Cross-site scripting (XSS) filter built into most recent web browsers.",
        CAT_SECURITY,
        "0, 1, 1; mode=block",
        meaning="A legacy feature to stop some XSS attacks.",
        impact="Largely replaced by Content-Security-Policy. Some modern browsers ignore it.",
        recommendation="Set to '0' (disable) if you use a strong Content-Security-Policy, otherwise '1; mode=block'.",
    ),
    "permissions-policy": HeaderDefinition(
        "Allows a site to enable or disable browser features and APIs.",
        CAT_SECURITY,
        "geolocation=(), camera=(), microphone=()",
        meaning="Controls what powerful browser features (like Camera, Location, Microphone) your site (and embedded frames) can use.",
        impact="Reduces the attack surface and improves privacy by disabling unused features.",
        recommendation="Disable all features you don't use (e.g., 'geolocation=()').",
    ),
    "cross-origin-opener-policy": HeaderDefinition(
        "Lets you ensure a top-level document does not share a browsing context group with cross-origin documents.",
        CAT_SECURITY,
        "same-origin, same-origin-allow-popups, unsafe-none",
        meaning="Isolates your site's process from other tabs.",
        impact="Prevents 'Spectre' attacks and cross-origin information leaks.",
        recommendation="Use 'same-origin' if possible.",
    ),
    "cross-origin-embedder-policy": HeaderDefinition(
        "Prevents a document from loading any cross-origin resources that don't explicitly grant the document permission.",
        CAT_SECURITY,
        "require-corp, unsafe-none, credentialless",
        meaning="Stops your site from loading external resources that haven't opted-in to being loaded by you.",
        impact="Required for using powerful features like SharedArrayBuffer.",
        recommendation="Use 'require-corp' if you need high-performance isolation.",
    ),
    "cross-origin-resource-policy": HeaderDefinition(
        "Allows you to control the set of origins that are empowered to include a resource.",
        CAT_SECURITY,
        "same-site, same-origin, cross-origin",
        meaning="Tells the browser who is allowed to read this specific resource (like an image or JSON file).",
        impact="Prevents other sites from reading your private images or data via scripts.",
        recommendation="Use 'same-origin' for private API responses.",
    ),
}
