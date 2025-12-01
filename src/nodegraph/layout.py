"""
This module encapsulates the layout logic for the NodeGraph.
It is responsible for calculating the positions of nodes in the graph.
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import cairo

@dataclass
class LayoutConfig:
    """Configuration constants for graph layout."""
    node_width: int = 450
    node_header_height: int = 55
    line_height: int = 22
    padding: int = 15
    gap_x: int = 300
    gap_y: int = 50

# Default instance for backward compatibility or default usage
DEFAULT_LAYOUT = LayoutConfig()

class GraphLayout:
    """Calculates node positions for the graph."""

    def __init__(self, show_all_nodes: bool = False, config: LayoutConfig = DEFAULT_LAYOUT):
        """
        Args:
            show_all_nodes: Whether to include all sibling nodes in the layout.
            config: Layout configuration.
        """
        self.show_all_nodes = show_all_nodes
        self.config = config
        self.nodes: List[Dict[str, Any]] = []

    def calculate_layout(self, layers_data: List[List[Any]]) -> List[Dict[str, Any]]:
        """Calculates the layout for the given data.

        Args:
            layers_data: A list of lists of NodeData objects.

        Returns:
            A list of node dictionaries with 'x', 'y', 'width', 'height' etc.
        """
        self.nodes = []
        x = 50.0

        # Create a dummy cairo surface/context for text measurement
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 0, 0)
        cr = cairo.Context(surface)
        cr.select_font_face(
            "Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD
        )
        cr.set_font_size(16)

        node_id_counter = 0
        layer_index = 0

        # Prepend a client node
        # Center at Y=0 initially for alignment
        client_node = {
            "id": node_id_counter,
            "layer_index": -1,
            "x": 50.0,
            "y": -50.0,
            "width": 100,
            "height": 100,
            "data": None,  # Special marker for client node
            "min_width": 100,
            "is_client": True,
        }
        self.nodes.append(client_node)
        node_id_counter += 1

        x += 100 + self.config.gap_x

        # We want to align the active nodes along the Y=0 axis.
        target_center_y = 0.0

        for layer_nodes in layers_data:
            # First, check if input is List[List] or just List (backward compat)
            if isinstance(layer_nodes, list):
                nodes_in_col = layer_nodes
            else:
                nodes_in_col = [layer_nodes]

            if not self.show_all_nodes:
                nodes_in_col = [n for n in nodes_in_col if n.is_active]

            if not nodes_in_col:
                continue

            # Find max width in this column
            max_col_width = self.config.node_width

            # First pass: measure all nodes in this layer/column
            nodes_dimensions = []
            active_node_index = 0

            for idx, node_data in enumerate(nodes_in_col):
                text_extents = cr.text_extents(node_data.name)
                min_width = text_extents.width + 2 * self.config.padding
                node_width = max(self.config.node_width, min_width)

                header_count = len(node_data.headers)
                node_height = self.config.node_header_height + self.config.padding
                if header_count > 0:
                    node_height += header_count * self.config.line_height
                node_height += self.config.padding

                nodes_dimensions.append(
                    {
                        "width": node_width,
                        "height": node_height,
                        "data": node_data,
                    }
                )

                if node_data.is_active:
                    active_node_index = idx

                if node_width > max_col_width:
                    max_col_width = node_width

            # Second pass: assign positions
            # Calculate start Y for the column such that the active node is centered at target_center_y

            # Calculate the relative Y center of the active node from the top of the column
            active_node_y_rel = 0.0
            for i in range(active_node_index):
                active_node_y_rel += nodes_dimensions[i]["height"] + self.config.gap_y

            active_node_y_rel += (
                nodes_dimensions[active_node_index]["height"] / 2.0
            )

            # Start Y for the column
            y = target_center_y - active_node_y_rel

            for dim in nodes_dimensions:
                node = {
                    "id": node_id_counter,
                    "layer_index": layer_index,
                    "x": x,
                    "y": y,
                    "width": dim["width"],
                    "height": dim["height"],
                    "data": dim["data"],
                    "min_width": dim["width"],  # Stored for reference
                    "is_client": False,
                }

                self.nodes.append(node)
                node_id_counter += 1

                y += dim["height"] + self.config.gap_y

            x += max_col_width + self.config.gap_x
            layer_index += 1

        # Final pass: Shift all nodes so that the topmost node is at a nice padding
        if self.nodes:
            min_y = min(n["y"] for n in self.nodes)
            desired_min_y = 50.0
            shift_y = desired_min_y - min_y

            for node in self.nodes:
                node["y"] += shift_y

        return self.nodes
