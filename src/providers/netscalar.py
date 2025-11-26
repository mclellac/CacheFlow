"""
Netscaler Load Balancer implementation.
"""

from typing import Dict
from .base import (
    HeaderDefinition,
    BaseProvider,
    ProviderType,
    CAT_LOAD_BALANCER,
)

NETSCALAR_HEADERS: Dict[str, HeaderDefinition] = {
    "ns-cache": HeaderDefinition(
        "NetScaler: Indicates if the response came from the NetScaler cache.",
        CAT_LOAD_BALANCER,
        "HIT, MISS",
    ),
    "x-citrix-am-lb-cookie": HeaderDefinition(
        "NetScaler: Citrix Load Balancer Cookie.",
        CAT_LOAD_BALANCER,
        "Cookie string",
    ),
}


class Netscalar(BaseProvider):
    """
    Netscalar Load Balancer Provider.
    """

    name = "Netscalar"
    provider_type = ProviderType.LOAD_BALANCER

    def get_debug_headers(self) -> Dict[str, str]:
        return {}

    def get_known_headers(self) -> Dict[str, HeaderDefinition]:
        return NETSCALAR_HEADERS
