"""
This module defines the NodeData class, which encapsulates the data structure
for individual nodes in the inspection graph.
"""

from typing import List, Tuple, Any, Optional, Dict


class NodeData:
    """Data class representing a node in the graph."""

    def __init__(
        self,
        name: str,
        headers: List[Tuple[str, str, str, str]],
        **kwargs: Any
    ):
        """
        Initializes the NodeData object.
        Args:
            name: The display name of the node.
            headers: A list of tuples, each containing (key, value, change_type, note).
            **kwargs: Additional attributes like colors and request details.
        """
        import logging

        log = logging.getLogger(__name__)
        log.debug(
            "Initializing NodeData for '%s' with %d headers.",
            name,
            len(headers),
        )

        self.name = name
        self.headers = headers
        self.body_color = kwargs.get("body_color", "")
        self.header_color = kwargs.get("header_color", "")
        self.text_color = kwargs.get("text_color", "")
        self.added_text_color = kwargs.get("added_text_color", "")
        self.removed_text_color = kwargs.get("removed_text_color", "")
        self.modified_text_color = kwargs.get("modified_text_color", "")
        self.request_url = kwargs.get("request_url", "")
        self.request_host = kwargs.get("request_host", "")
        self.request_method = kwargs.get("request_method", "GET")
        self.status_code = kwargs.get("status_code", None)
        self.upstream_layer: Optional[Dict[str, Any]] = kwargs.get(
            "upstream_layer", None
        )
        self.provider: str = kwargs.get("provider", "")
        self.layer_type: str = kwargs.get("layer_type", "")
        self.is_active: bool = kwargs.get("is_active", True)

    def get_property(self, name: str) -> Any:
        """
        Retrieve a property by name safely.

        Args:
            name (str): The name of the property to retrieve.

        Returns:
            Any: The value of the property or None if it doesn't exist.
        """
        return getattr(self, name, None)
