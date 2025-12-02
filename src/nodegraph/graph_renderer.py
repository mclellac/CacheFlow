"""
This module handles the rendering logic for the NodeGraph widget.
"""

from typing import Dict, Any
from urllib.parse import urlparse

import math
import cairo
from gi.repository import Adw, Pango, PangoCairo, GLib, Gdk
from ..utils import get_accent_color
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
            if node.get("is_client"):
                self._draw_client_node(cr, node)
            else:
                self._draw_node(cr, node)

        for node in self.node_graph.nodes:
            if not node.get("is_client"):
                self._draw_resize_handle(cr, node)

        cr.restore()

    def _get_bezier_point(self, t, p0, p1, p2, p3):
        """Calculates a point on a cubic Bezier curve at time t."""
        u = 1 - t
        tt = t * t
        uu = u * u
        uuu = uu * u
        ttt = tt * t

        x = uuu * p0[0] + 3 * uu * t * p1[0] + 3 * u * tt * p2[0] + ttt * p3[0]
        y = uuu * p0[1] + 3 * uu * t * p1[1] + 3 * u * tt * p2[1] + ttt * p3[1]
        return x, y

    def _draw_connections(self, cr: cairo.Context) -> None:
        """Draws lines connecting the nodes."""
        r, g, b, _ = get_accent_color()
        cr.set_source_rgba(r, g, b, 0.8)
        cr.set_line_width(5)

        # Group nodes by layer_index
        layers = {}
        max_layer_index = -1
        min_layer_index = 0

        # Check for client node (index -1)
        client_node = next((n for n in self.node_graph.nodes if n.get("is_client")), None)
        if client_node:
            layers[-1] = [client_node]
            min_layer_index = -1

        for node in self.node_graph.nodes:
            # Skip client node as we already handled it
            if node.get("is_client"):
                continue
            idx = node.get("layer_index", 0)
            if idx not in layers:
                layers[idx] = []
            layers[idx].append(node)
            if idx > max_layer_index:
                max_layer_index = idx

        # Iterate through layer indices
        total_hops = max_layer_index - min_layer_index
        for i in range(min_layer_index, max_layer_index):
            curr_nodes = layers.get(i, [])
            next_nodes = layers.get(i + 1, [])

            if not curr_nodes or not next_nodes:
                continue

            # Find active node in current layer
            active_curr = None
            if i == -1:  # Client node is always active
                active_curr = curr_nodes[0]
            else:
                active_curr = next(
                    (n for n in curr_nodes if n["data"].is_active), None
                )

            # Find active node in next layer
            active_next = next(
                (n for n in next_nodes if n["data"].is_active), None
            )

            if active_curr and active_next:
                hop_index = i - min_layer_index
                self._draw_connection_line(
                    cr, active_curr, active_next, hop_index, total_hops
                )

    def _draw_connection_line(
        self, cr, node_a, node_b, hop_index: int, total_hops: int
    ):
        start_x = node_a["x"] + node_a["width"]
        start_y = node_a["y"] + node_a["height"] / 2

        end_x = node_b["x"]
        end_y = node_b["y"] + node_b["height"] / 2

        # Control points for a smooth curve
        c1_x = start_x + 100
        c1_y = start_y
        c2_x = end_x - 100
        c2_y = end_y

        intro_alpha = self.node_graph.intro_progress
        r, g, b, _ = get_accent_color()

        cr.save()

        # Common line width logic
        line_width = 5
        if node_b["data"].is_active:
            pulse = (math.sin(self.node_graph.animation_time * 5.0) + 1) / 2
            line_width = 5 + pulse * 2

        cr.set_line_width(line_width)

        # Latency-based color coding
        latency = node_b["data"].latency
        if latency:
            if latency < 100:
                # Green
                cr.set_source_rgba(0.2, 0.8, 0.2, 0.8 * intro_alpha)
            elif latency < 500:
                # Yellow/Orange
                cr.set_source_rgba(1.0, 0.8, 0.0, 0.8 * intro_alpha)
            else:
                # Red
                cr.set_source_rgba(1.0, 0.2, 0.2, 0.8 * intro_alpha)
        else:
            cr.set_source_rgba(r, g, b, 0.8 * intro_alpha)

        # Draw Single Line
        cr.move_to(start_x, start_y)
        cr.curve_to(c1_x, c1_y, c2_x, c2_y, end_x, end_y)
        cr.stroke()

        # Animations
        if intro_alpha > 0.8 and self.node_graph.show_animation:
            # Animation Speed and Cycle Logic
            SPEED = 4.0  # Faster speed
            # Cycle length includes a buffer to ensure the full packet train arrives
            # before the return journey begins.
            # Forward journey ends at t=total_hops (head arrives).
            # Tail arrives slightly later. We add 1.0 buffer.
            cycle_len = 2 * total_hops + 1.0
            t_global = (self.node_graph.animation_time * SPEED) % cycle_len

            # 1. Forward Journey (Green Packets)
            # Active in time window [hop_index, hop_index + 1.5) to allow tail to finish
            if hop_index <= t_global < hop_index + 1.5:
                local_t = t_global - hop_index
                cr.set_source_rgba(0.2, 0.9, 0.2, 1.0)  # Green
                self._draw_packet_group(
                    cr,
                    local_t,
                    start_x,
                    start_y,
                    c1_x,
                    c1_y,
                    c2_x,
                    c2_y,
                    end_x,
                    end_y,
                    reverse=False,
                )

            # 2. Backward Journey (Electric Blue Packets)
            # The backward journey starts after the forward journey completes + buffer.
            # Start of return phase:
            bw_phase_start = total_hops + 0.5

            # For hop_index `i`, the backward traversal is the (total_hops - 1 - i)-th step
            # of the return phase.
            bw_start_time = bw_phase_start + (total_hops - 1 - hop_index)

            if bw_start_time <= t_global < bw_start_time + 1.5:
                local_t = t_global - bw_start_time
                # Electric Blue (Cyan-ish)
                cr.set_source_rgba(0.0, 1.0, 1.0, 1.0)
                self._draw_packet_group(
                    cr,
                    1.0 - local_t,  # Reverse direction (1 -> 0)
                    start_x,
                    start_y,
                    c1_x,
                    c1_y,
                    c2_x,
                    c2_y,
                    end_x,
                    end_y,
                    reverse=True,  # Tells packet group to trail "forward" relative to movement
                )

        cr.restore()

        # Label attaches to the single line
        points = ConnectionPoints(
            start_x,
            start_y,
            c1_x,
            c1_y,
            c2_x,
            c2_y,
            end_x,
            end_y,
        )

        if self.node_graph.show_connection_labels:
            self._draw_connection_label(cr, node_b, points)

    def _draw_packet_group(
        self, cr, t_lead, start_x, start_y, c1_x, c1_y, c2_x, c2_y, end_x, end_y, reverse=False
    ):
        """Draws 3 close-together dots representing a packet group."""
        dots = 3
        spacing = 0.04

        for i in range(dots):
            # Calculate t for this dot
            if reverse:
                # Moving backwards (decreasing t), so trails are at t + spacing
                t = t_lead + (i * spacing)
            else:
                # Moving forwards (increasing t), so trails are at t - spacing
                t = t_lead - (i * spacing)

            if 0.0 <= t <= 1.0:
                px, py = self._get_bezier_point(
                    t, (start_x, start_y), (c1_x, c1_y), (c2_x, c2_y), (end_x, end_y)
                )
                cr.arc(px, py, 4, 0, 2 * math.pi)
                cr.fill()

    def _draw_connection_label(
        self,
        cr: cairo.Context,
        node_b: Dict[str, Any],
        points: ConnectionPoints,
    ) -> None:
        """Draws the label on the connection line."""

        # If node_b is the first real node (layer 0), it's connected from Client.
        # We need to display the request URL, but maybe formatted differently?
        # Actually node_b["data"] contains the request URL that reached this node.
        # So it should be fine.

        request_url = node_b["data"].request_url
        request_host = node_b["data"].request_host

        if not request_url:
            return

        cr.save()

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

        method = node_b["data"].request_method or ""
        # Sanitize URLs and avoid processing if too long
        if request_url and len(request_url) > 2000:
            display_url = request_url[:100] + "..."
        else:
            display_url = request_url

        text = f"{method} {display_url}"

        # Parse URLs to compare hosts
        try:
            parsed_req = urlparse(request_url)
            req_host = parsed_req.hostname
        except (ValueError, AttributeError):
            req_host = None

        if request_host and request_host != req_host:
            text += f"\nHost: {request_host}"

        latency = node_b["data"].latency
        if latency:
            text += f"\n{latency:.0f}ms"

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
        offset_dist = 35

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
        cr.restore()

    def _draw_node(self, cr: cairo.Context, node: Dict[str, Any]) -> None:
        """Draws a single node."""
        x, y, w, h = node["x"], node["y"], node["width"], node["height"]
        style_manager = Adw.StyleManager.get_default()
        is_dark = style_manager.get_dark()

        is_active = node["data"].is_active

        # Pop-in animation
        # Scale from center
        scale_factor = self.node_graph.intro_progress
        # Hover effect
        if self.node_graph.hovered_node_id == node["id"]:
            scale_factor *= 1.05

        if scale_factor != 1.0:
            cx = x + w / 2
            cy = y + h / 2
            cr.save()
            cr.translate(cx, cy)
            cr.scale(scale_factor, scale_factor)
            cr.translate(-cx, -cy)

        # Dim inactive nodes
        alpha_mult = 1.0 if is_active else 0.5

        # Check filter
        if self.node_graph.filter_text:
            if not self._node_matches_filter(node, self.node_graph.filter_text):
                alpha_mult *= 0.1

        # Selected state
        if self.node_graph.selected_node_index == node["id"]:
            r, g, b, _ = get_accent_color()
            # Multi-pass stroke for glow effect
            for i in range(3):
                alpha = (0.3 - (i * 0.1)) * alpha_mult
                width = 8 + (i * 4)
                cr.set_source_rgba(r, g, b, alpha)
                cr.set_line_width(width)
                rounded_rectangle(cr, x, y, w, h, 10)
                cr.stroke()

            # Hard border
            cr.set_source_rgba(r, g, b, 1.0 * alpha_mult)
            cr.set_line_width(5)
            rounded_rectangle(cr, x, y, w, h, 10)
            cr.stroke()
        elif is_active:
            # Active Path Pulse
            # Subtle pulse on the border
            pulse = (math.sin(self.node_graph.animation_time * 3.0) + 1) / 2 * 0.5 # 0.0 to 0.5
            r, g, b, _ = get_accent_color()
            cr.set_source_rgba(r, g, b, 0.3 + pulse * 0.3)
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

        # Draw status code if available
        status_code = node["data"].status_code
        if status_code:
            status_text = str(status_code)

            # Determine status color
            if 200 <= status_code < 300:
                status_color = (0.2, 0.8, 0.2, 1 * alpha_mult) # Green
            elif 300 <= status_code < 400:
                status_color = (1.0, 0.8, 0.2, 1 * alpha_mult) # Yellow/Orange
            elif 400 <= status_code < 500:
                status_color = (1.0, 0.4, 0.4, 1 * alpha_mult) # Red
            elif status_code >= 500:
                status_color = (0.8, 0.0, 0.0, 1 * alpha_mult) # Dark Red
            else:
                status_color = (0.6, 0.6, 0.6, 1 * alpha_mult) # Grey

            cr.set_source_rgba(*status_color)
            cr.select_font_face(
                "Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD
            )
            cr.set_font_size(14)

            # Align right in the header
            extents = cr.text_extents(status_text)
            status_x = x + w - PADDING - extents.width
            status_y = y + 32 # Vertically centered in header area roughly

            cr.move_to(status_x, status_y)
            cr.show_text(status_text)

        if is_active:
            self._draw_node_text(cr, node, x, y, w, is_dark)
        else:
            self._draw_inactive_node(cr, node, x, y, w, h, is_dark)

        if scale_factor != 1.0:
            cr.restore()

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

    def _node_matches_filter(self, node: Dict[str, Any], text: str) -> bool:
        """Checks if a node matches the filter text."""
        data = node["data"]
        # Check name
        if text in data.name.lower():
            return True
        # Check headers
        for k, v, _, _ in data.headers:
            if text in k.lower() or text in v.lower():
                return True
        return False

    def _draw_client_node(
        self, cr: cairo.Context, node: Dict[str, Any]
    ) -> None:
        """Draws the client/user node."""
        x, y, w, h = node["x"], node["y"], node["width"], node["height"]
        center_x = x + w / 2
        center_y = y + h / 2

        style_manager = Adw.StyleManager.get_default()
        is_dark = style_manager.get_dark()

        # Color based on theme
        if is_dark:
            cr.set_source_rgba(0.9, 0.9, 0.9, 1.0)
            text_color = (1.0, 1.0, 1.0, 1.0)
        else:
            cr.set_source_rgba(0.2, 0.2, 0.2, 1.0)
            text_color = (0.0, 0.0, 0.0, 1.0)

        # Draw a simple user icon (circle head, arc body)
        # Head
        cr.arc(center_x, center_y - 20, 15, 0, 2 * 3.14159)
        cr.fill()

        # Body
        cr.arc(center_x, center_y + 35, 30, 3.14159, 2 * 3.14159)
        cr.fill()

        # Text "Client" below
        cr.set_source_rgba(*text_color)
        cr.select_font_face(
            "Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD
        )
        cr.set_font_size(14)

        text = "Client"
        extents = cr.text_extents(text)
        cr.move_to(center_x - extents.width / 2, y + h + 20)
        cr.show_text(text)
