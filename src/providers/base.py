"""
Base definitions for header providers.
"""

from typing import NamedTuple

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
