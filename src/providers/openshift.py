"""
OpenShift Application Backend implementation.
"""

from typing import Dict
from .base import HeaderDefinition, BaseProvider, ProviderType, CAT_CONTENT

OPENSHIFT_HEADERS: Dict[str, HeaderDefinition] = {
    "x-ocp-pod": HeaderDefinition(
        "OpenShift: Identifies the pod serving the request (if exposed).",
        CAT_CONTENT,
        "Pod Name",
    )
}


class OpenShift(BaseProvider):
    """
    OpenShift Application Backend Provider.
    """

    name = "OpenShift"
    provider_type = ProviderType.APP_BACKEND

    def get_debug_headers(self) -> Dict[str, str]:
        return {}

    def get_known_headers(self) -> Dict[str, HeaderDefinition]:
        return OPENSHIFT_HEADERS
