"""
Base definitions for header providers.
"""

from typing import NamedTuple, Dict
from enum import Enum

class HeaderDefinition(NamedTuple):
    """
    Defines the properties of a known HTTP header.
    """
    description: str
    category: str
    expected_values: str

class ProviderType(Enum):
    """
    Enum for the types of layers in the infrastructure.
    """
    CDN = "CDN"
    LOAD_BALANCER = "Load Balancer"
    CACHE_PROXY = "Cache Proxy"

class BaseProvider:
    """
    Base class for all providers.
    """
    name: str = "Unknown"
    provider_type: ProviderType = ProviderType.CDN

    def get_debug_headers(self) -> Dict[str, str]:
        """
        Returns a dictionary of headers to enable debugging features for this provider.
        """
        return {}

    def get_known_headers(self) -> Dict[str, HeaderDefinition]:
        """
        Returns a dictionary of known headers for this provider.
        """
        return {}

# Categories
CAT_CDN = "CDN"
CAT_CACHE = "Caching"
CAT_SECURITY = "Security"
CAT_PROXY = "Proxy"
CAT_DEBUG = "Debugging"
CAT_STANDARD = "Standard"
CAT_LOAD_BALANCER = "Load Balancer"
CAT_AUTH = "Authentication"
CAT_CORS = "CORS"
CAT_COOKIES = "Cookies"
CAT_CONTENT = "Content"
CAT_CONNECTION = "Connection"
CAT_DEPRECATED = "Deprecated"
