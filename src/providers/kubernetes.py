"""
Kubernetes and Load Balancer headers.
"""

from typing import Dict
from .base import HeaderDefinition, CAT_LOAD_BALANCER, CAT_DEBUG

KUBERNETES_HEADERS: Dict[str, HeaderDefinition] = {
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
