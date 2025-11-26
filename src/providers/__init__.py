"""
Central registry for providers.
"""

from typing import Dict, Type, List
from .base import BaseProvider, ProviderType
from .akamai import Akamai
from .varnish import Varnish
from .netscalar import Netscalar
from .openshift import OpenShift

PROVIDERS: Dict[str, Type[BaseProvider]] = {
    "Akamai": Akamai,
    "Varnish": Varnish,
    "Netscalar": Netscalar,
    "OpenShift": OpenShift,
}


def get_providers_by_type(
    provider_type: ProviderType,
) -> List[Type[BaseProvider]]:
    """
    Returns a list of providers matching the given type.
    """
    return [p for p in PROVIDERS.values() if p.provider_type == provider_type]


def get_provider_class(name: str) -> Type[BaseProvider]:
    """
    Returns the provider class for the given name.
    """
    return PROVIDERS.get(name, BaseProvider)
