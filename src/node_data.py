"""
This module defines the NodeData class, which encapsulates the data structure
for individual nodes in the inspection graph.
"""

from typing import List, Tuple, Any, Optional, Dict

class NodeData:
    """Data class representing a node in the graph."""

    def __init__(self, name: str, headers: List[Tuple[str, str, bool, str]], **kwargs: Any):
        """
        Initialize the NodeData object.

        Args:
            name (str): The display name of the node.
            headers (list): A list of header tuples (key, value, is_diff, note).
            **kwargs: Additional attributes like colors and request details.
        """
        self.name = name
        self.headers = headers
        self.body_color = kwargs.get('body_color', '')
        self.header_color = kwargs.get('header_color', '')
        self.text_color = kwargs.get('text_color', '')
        self.diff_text_color = kwargs.get('diff_text_color', '')
        self.request_url = kwargs.get('request_url', '')
        self.request_host = kwargs.get('request_host', '')
        self.request_method = kwargs.get('request_method', 'GET')
        self.upstream_layer: Optional[Dict[str, Any]] = kwargs.get('upstream_layer', None)
        self.provider: str = kwargs.get('provider', '')
        self.layer_type: str = kwargs.get('layer_type', '')

    def get_property(self, name: str) -> Any:
        """
        Retrieve a property by name safely.

        Args:
            name (str): The name of the property to retrieve.

        Returns:
            Any: The value of the property or None if it doesn't exist.
        """
        return getattr(self, name, None)
