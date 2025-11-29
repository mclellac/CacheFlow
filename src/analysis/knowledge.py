"""
This module contains the knowledge base for HTTP headers, including descriptions,
categories, and expected values. It aggregates definitions from various providers.
"""

from typing import Dict

# Re-export HeaderDefinition for consumers (like analyzer.py)
# pylint: disable=unused-import
from ..providers.base import HeaderDefinition
from ..providers.standard import STANDARD_HEADERS
from ..providers.akamai import AKAMAI_HEADERS
from ..providers.varnish import VARNISH_HEADERS
from ..providers.netscalar import NETSCALAR_HEADERS
from ..providers.openshift import OPENSHIFT_HEADERS
from ..providers.security import SECURITY_HEADERS
from ..providers.kubernetes import KUBERNETES_HEADERS

HEADER_KNOWLEDGE: Dict[str, HeaderDefinition] = {}
HEADER_KNOWLEDGE.update(STANDARD_HEADERS)
HEADER_KNOWLEDGE.update(AKAMAI_HEADERS)
HEADER_KNOWLEDGE.update(VARNISH_HEADERS)
HEADER_KNOWLEDGE.update(NETSCALAR_HEADERS)
HEADER_KNOWLEDGE.update(OPENSHIFT_HEADERS)
HEADER_KNOWLEDGE.update(SECURITY_HEADERS)
HEADER_KNOWLEDGE.update(KUBERNETES_HEADERS)


def get_header_info(header_key: str) -> HeaderDefinition:
    """
    Retrieves the definition for a given header key.
    Returns a default definition if not found.
    """
    key = header_key.lower()
    return HEADER_KNOWLEDGE.get(
        key, HeaderDefinition("Unknown or custom header.", "Unknown", "Any")
    )
