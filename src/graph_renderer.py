"""
This module handles the rendering logic for the NodeGraph widget.
"""

from typing import Dict, Any

import cairo
from gi.repository import Adw, Pango, PangoCairo, GLib, Gdk
from .utils import get_accent_color
from .graph_utils import get_color, rounded_rectangle, ConnectionPoints

NODE_HEADER_HEIGHT = 55
LINE_HEIGHT = 22
PADDING = 15
RESIZE_HANDLE_SIZE = 15


class GraphRenderer:
    """Handles all drawing logic for the NodeGraph."""

    def __init__(self, node_graph):
        self.node_graph = node_graph

    def draw_graph_content(
        self,
        cr: cairo.Context,
        width: float,
        height: float,
        scale: float = 1.0,
        offset_x: float = 0,
        offset_y: float = 0,
    ) -> None:
        """Draws the entire graph content."""
        style_manager = Adw.StyleManager.get_default()
        is_dark = style_manager.get_dark()

        if is_dark:
            cr.set_source_rgba(0.1, 0.1, 0.1, 1)
        else:
            cr.set_source_rgba(0.95, 0.95, 0.95, 1)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        cr.save()
        cr.translate(offset_x, offset_y)
        cr.scale(scale, scale)

        self._draw_connections(cr)

        for node in self.node_graph.nodes:
            self._draw_node(cr, node)

        for node in self.node_graph.nodes:
            self._draw_resize_handle(cr, node)

        cr.restore()

    def _draw_connections(self, cr: cairo.Context) -> None:
        """Draws lines connecting the nodes."""
        r, g, b, _ = get_accent_color()
        cr.set_source_rgba(r, g, b, 0.8)
        cr.set_line_width(3)

        # We need to find the active node in each column/layer to connect them.
        # self.node_graph.nodes is a flat list of positioned nodes with 'data'.
        # We need to group them by 'layer' or simply find path from active to active.

        # Group nodes by X coordinate (or ID sequence, but X is safer if we reset layout)
        # Actually, since set_data creates them in order of layers, we can iterate carefully.
        # But flattening makes it hard to know which node connects to which if we don't know layers.
        # However, NodeData now has is_active flag.

        # Let's assume nodes are sorted by X (layers).
        # We want to connect active node of Layer N to active node of Layer N+1.

        # First, organize nodes by layers. We can infer layers from X coordinate or index if we tracked it.
        # Easier: Reconstruct layers from self.node_graph.nodes based on X position.

        layers = {}
        for node in self.node_graph.nodes:
            x = node["x"]
            if x not in layers:
                layers[x] = []
            layers[x].append(node)

        sorted_xs = sorted(layers.keys())

        for i in range(len(sorted_xs) - 1):
            curr_x = sorted_xs[i]
            next_x = sorted_xs[i + 1]

            curr_nodes = layers[curr_x]
            next_nodes = layers[next_x]

            # Find active node in current layer
            active_curr = next(
                (n for n in curr_nodes if n["data"].is_active), None
            )

            # Find active node in next layer
            active_next = next(
                (n for n in next_nodes if n["data"].is_active), None
            )

            if active_curr and active_next:
                self._draw_connection_line(cr, active_curr, active_next)

    def _draw_connection_line(self, cr, node_a, node_b):
        start_x = node_a["x"] + node_a["width"]
        start_y = node_a["y"] + node_a["height"] / 2

        end_x = node_b["x"]
        end_y = node_b["y"] + node_b["height"] / 2

        cr.move_to(start_x, start_y)
        c1_x = start_x + 100
        c1_y = start_y
        c2_x = end_x - 100
        c2_y = end_y
        cr.curve_to(c1_x, c1_y, c2_x, c2_y, end_x, end_y)
        cr.stroke()

        points = ConnectionPoints(
            start_x, start_y, c1_x, c1_y, c2_x, c2_y, end_x, end_y
        )
        self._draw_connection_label(cr, node_b, points)

    def _draw_connection_label(
        self,
        cr: cairo.Context,
        node_b: Dict[str, Any],
        points: ConnectionPoints,
    ) -> None:
        """Draws the label on the connection line."""
        request_url = node_b["data"].request_url
        request_host = node_b["data"].request_host

        if not request_url:
            return

        # Calculate midpoint on Bezier curve
        t = 0.5
        mid_x = (
            (1 - t) ** 3 * points.start_x
            + 3 * (1 - t) ** 2 * t * points.c1_x
            + 3 * (1 - t) * t**2 * points.c2_x
            + t**3 * points.end_x
        )
        mid_y = (
            (1 - t) ** 3 * points.start_y
            + 3 * (1 - t) ** 2 * t * points.c1_y
            + 3 * (1 - t) * t**2 * points.c2_y
            + t**3 * points.end_y
        )

        layout = PangoCairo.create_layout(cr)
        font_desc = Pango.FontDescription("Sans 12")
        layout.set_font_description(font_desc)

        method = node_b["data"].request_method
        text = f"{method} {request_url}"

        # Parse URLs to compare hosts
        from urllib.parse import urlparse

        try:
            parsed_req = urlparse(request_url)
            req_host = parsed_req.hostname
        except ValueError:
            req_host = None

        if request_host and request_host != req_host:
            text += f"\nHost: {request_host}"

        layout.set_text(text, -1)

        _, logical_rect = layout.get_extents()
        text_width = logical_rect.width / Pango.SCALE
        text_height = logical_rect.height / Pango.SCALE

        # Determine orientation of the line at midpoint to avoid collision
        # Simple derivative check
        dx = (
            3 * (1 - t) ** 2 * (points.c1_x - points.start_x)
            + 6 * (1 - t) * t * (points.c2_x - points.c1_x)
            + 3 * t**2 * (points.end_x - points.c2_x)
        )
        dy = (
            3 * (1 - t) ** 2 * (points.c1_y - points.start_y)
            + 6 * (1 - t) * t * (points.c2_y - points.c1_y)
            + 3 * t**2 * (points.end_y - points.c2_y)
        )

        is_vertical_dominant = abs(dy) > abs(dx)

        # Increase offsets to prevent overlapping
        offset_dist = 25

        if is_vertical_dominant:
            # Line is moving vertically, place text to side
            # Check if moving left or right
            # If end_x > start_x, it's moving right. mid point, tangent dx > 0
            # If dx > 0, moving right.
            # We want to place text on the "outside" of the curve if possible, or just consistently.
            # Let's try to place it to the right if there is space.
            text_x = mid_x + offset_dist
            text_y = mid_y - text_height / 2
        else:
            # Line is horizontal, place text above or below
            # Place above to avoid overlapping nodes below
            text_x = mid_x - text_width / 2
            text_y = mid_y - text_height - offset_dist

        # Background for readability
        if Adw.StyleManager.get_default().get_dark():
            cr.set_source_rgba(0.2, 0.2, 0.2, 0.8)
            text_color = (0.9, 0.9, 0.9, 1)
        else:
            cr.set_source_rgba(0.95, 0.95, 0.95, 0.8)
            text_color = (0.1, 0.1, 0.1, 1)

        # Draw background rect
        cr.rectangle(text_x - 2, text_y - 2, text_width + 4, text_height + 4)
        cr.fill()

        cr.set_source_rgba(*text_color)
        cr.move_to(text_x, text_y)
        PangoCairo.show_layout(cr, layout)

    def _draw_node(self, cr: cairo.Context, node: Dict[str, Any]) -> None:
        """Draws a single node."""
        x, y, w, h = node["x"], node["y"], node["width"], node["height"]
        style_manager = Adw.StyleManager.get_default()
        is_dark = style_manager.get_dark()

        is_active = node["data"].is_active

        # Dim inactive nodes
        alpha_mult = 1.0 if is_active else 0.5

        if self.node_graph.selected_node_index == node["id"]:
            r, g, b, _ = get_accent_color()
            cr.set_source_rgba(r, g, b, 0.4 * alpha_mult)
            rounded_rectangle(cr, x - 8, y - 8, w + 16, h + 16, 18)
            cr.fill()
            cr.set_source_rgba(r, g, b, 1.0 * alpha_mult)
            cr.set_line_width(3)
            rounded_rectangle(cr, x, y, w, h, 10)
            cr.stroke()

        cr.set_source_rgba(0.0, 0.0, 0.0, 0.4 * alpha_mult)
        rounded_rectangle(cr, x + 2, y + 3, w, h, 10)
        cr.fill()

        body_rgba = Gdk.RGBA()
        if node["data"].body_color:
            body_rgba.parse(node["data"].body_color)
        else:
            body_rgba.parse("rgba(0,0,0,0)")  # Fallback

        if body_rgba.alpha == 0:
            body_color = (
                (0.8, 0.8, 0.85, 1 * alpha_mult)
                if not is_dark
                else (0.2, 0.2, 0.25, 1 * alpha_mult)
            )
        else:
            body_color = (
                body_rgba.red,
                body_rgba.green,
                body_rgba.blue,
                body_rgba.alpha * alpha_mult,
            )
        cr.set_source_rgba(*body_color)

        rounded_rectangle(cr, x, y, w, h, 10)
        cr.fill_preserve()

        border_color = (
            (0.5, 0.5, 0.5, 0.8 * alpha_mult)
            if is_dark
            else (0.4, 0.4, 0.4, 0.8 * alpha_mult)
        )
        cr.set_source_rgba(*border_color)
        cr.set_line_width(1)
        cr.stroke()

        header_rgba = Gdk.RGBA()
        if node["data"].header_color:
            header_rgba.parse(node["data"].header_color)
        else:
            header_rgba.parse("rgba(0,0,0,0)")

        if header_rgba.alpha == 0:
            header_color = (
                (0.7, 0.7, 0.75, 1 * alpha_mult)
                if not is_dark
                else (0.3, 0.3, 0.35, 1 * alpha_mult)
            )
        else:
            header_color = (
                header_rgba.red,
                header_rgba.green,
                header_rgba.blue,
                header_rgba.alpha * alpha_mult,
            )
        cr.set_source_rgba(*header_color)

        rounded_rectangle(
            cr,
            x,
            y,
            w,
            NODE_HEADER_HEIGHT,
            10,
            corners={"bl": False, "br": False},
        )
        cr.fill_preserve()

        cr.set_source_rgba(*border_color)
        cr.set_line_width(0.5)
        cr.stroke()

        if is_dark:
            cr.set_source_rgba(1, 1, 1, 1 * alpha_mult)
        else:
            cr.set_source_rgba(0, 0, 0, 1 * alpha_mult)
        cr.select_font_face(
            "Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD
        )
        cr.set_font_size(16)
        cr.move_to(x + PADDING, y + 22)
        cr.show_text(node["data"].name)

        cr.set_font_size(12)
        cr.set_source_rgba(0.4, 0.4, 0.4, 1 * alpha_mult)
        if is_dark:
            cr.set_source_rgba(0.7, 0.7, 0.7, 1 * alpha_mult)

        cr.move_to(x + PADDING, y + 42)
        provider_name = (
            node["data"].provider if node["data"].provider else "Unknown"
        )
        cr.show_text(f"{provider_name}")

        if is_active:
            self._draw_node_text(cr, node, x, y, w, is_dark)
        else:
            self._draw_inactive_node(cr, node, x, y, w, h, is_dark)

    def _draw_inactive_node(self, cr, node, x, y, w, h, is_dark):
        """Draws a smaller, dimmed version for inactive nodes."""
        # Use a reduced height for inactive nodes if h is large, but h is passed from layout.
        # Ideally layout should have calculated a smaller height.
        # But we can just draw within the bounds.

        # Dimmed header color
        header_rgba = Gdk.RGBA()
        if node["data"].header_color:
            header_rgba.parse(node["data"].header_color)
        else:
            header_rgba.parse("rgba(0,0,0,0)")

        alpha = 0.4
        if header_rgba.alpha == 0:
            header_color = (
                (0.7, 0.7, 0.75, alpha)
                if not is_dark
                else (0.3, 0.3, 0.35, alpha)
            )
        else:
            header_color = (
                header_rgba.red,
                header_rgba.green,
                header_rgba.blue,
                alpha,
            )

        cr.set_source_rgba(*header_color)
        rounded_rectangle(cr, x, y, w, NODE_HEADER_HEIGHT, 10)
        cr.fill_preserve()

        border_color = (
            (0.5, 0.5, 0.5, 0.3) if is_dark else (0.4, 0.4, 0.4, 0.3)
        )
        cr.set_source_rgba(*border_color)
        cr.set_line_width(1)
        cr.stroke()

        # Text
        if is_dark:
            cr.set_source_rgba(1, 1, 1, 0.5)
        else:
            cr.set_source_rgba(0, 0, 0, 0.5)

        cr.select_font_face(
            "Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD
        )
        cr.set_font_size(14)
        cr.move_to(x + PADDING, y + 22)
        cr.show_text(node["data"].name)

        cr.set_font_size(10)
        cr.move_to(x + PADDING, y + 40)
        provider_name = (
            node["data"].provider if node["data"].provider else "Unknown"
        )
        cr.show_text(f"{provider_name}")

    def _draw_node_text(
        self,
        cr: cairo.Context,
        node: Dict[str, Any],
        x: float,
        y: float,
        w: float,
        is_dark: bool,
    ) -> None:
        """Draws the text content of the node."""
        font_desc_str = self.node_graph.settings.get_string("node-font")
        if not font_desc_str:
            font_desc_str = "Monospace 14"
        font_desc = Pango.FontDescription.from_string(font_desc_str)
        text_y = y + NODE_HEADER_HEIGHT + PADDING
        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(font_desc)
        layout.set_width((w - 2 * PADDING) * Pango.SCALE)
        layout.set_ellipsize(Pango.EllipsizeMode.END)

        for header, value, change_type, _ in node["data"].headers:
            if change_type == "ADDED":
                color = get_color(
                    node["data"].added_text_color,
                    is_dark,
                    (0, 0.5, 0, 1),
                    (0.5, 1.0, 0.5, 1),
                )
            elif change_type == "REMOVED":
                color = get_color(
                    node["data"].removed_text_color,
                    is_dark,
                    (0.8, 0, 0, 1),
                    (1.0, 0.5, 0.5, 1),
                )
            elif change_type == "MODIFIED":
                color = get_color(
                    node["data"].modified_text_color,
                    is_dark,
                    (0.8, 0.5, 0, 1),
                    (1.0, 0.8, 0.5, 1),
                )
            else:  # UNCHANGED or other
                color = get_color(
                    node["data"].text_color,
                    is_dark,
                    (0.1, 0.1, 0.1, 1),
                    (0.9, 0.9, 0.9, 1),
                )

            cr.set_source_rgba(*color)

            escaped_header = GLib.markup_escape_text(header)
            escaped_value = GLib.markup_escape_text(value)
            markup = f"<b>{escaped_header}:</b> {escaped_value}"
            layout.set_markup(markup, -1)

            cr.move_to(x + PADDING, text_y)
            PangoCairo.show_layout(cr, layout)
            text_y += LINE_HEIGHT

    def _draw_resize_handle(
        self, cr: cairo.Context, node: Dict[str, Any]
    ) -> None:
        """Draws a resize handle in the bottom-right corner of a node."""
        x = node["x"] + node["width"] - RESIZE_HANDLE_SIZE
        y = node["y"] + node["height"] - RESIZE_HANDLE_SIZE

        cr.set_source_rgba(0.5, 0.5, 0.5, 0.7)
        cr.move_to(x, y + RESIZE_HANDLE_SIZE)
        cr.line_to(x + RESIZE_HANDLE_SIZE, y)
        cr.line_to(x + RESIZE_HANDLE_SIZE, y + RESIZE_HANDLE_SIZE)
        cr.close_path()
        cr.fill()
