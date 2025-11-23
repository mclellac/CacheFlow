# SPDX-License-Identifier: MIT

import gi
import cairo

from gi.repository import Gtk, Gdk, Adw, Pango, Gio

NODE_WIDTH = 300
NODE_HEADER_HEIGHT = 40
LINE_HEIGHT = 18
PADDING = 10

class NodeGraph(Gtk.DrawingArea):
    """A widget for drawing and interacting with a node-based graph."""

    __gtype_name__ = 'NodeGraph'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.nodes = []
        self.dragging_node = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        self.settings = Gio.Settings.new('com.github.mclellac.CacheFlow')
        self.set_draw_func(self.on_draw)

        style_manager = Adw.StyleManager.get_default()
        style_manager.connect('notify::dark', self.on_style_changed)

        # Event controllers for mouse interaction
        gesture_drag = Gtk.GestureDrag.new()
        gesture_drag.connect("drag-begin", self.on_drag_begin)
        gesture_drag.connect("drag-update", self.on_drag_update)
        gesture_drag.connect("drag-end", self.on_drag_end)
        self.add_controller(gesture_drag)

        gesture_click = Gtk.GestureClick.new()
        gesture_click.set_button(1) # Primary button
        gesture_click.connect("pressed", self.on_click)
        self.add_controller(gesture_click)

    def on_style_changed(self, style_manager, _):
        self.queue_draw()

    def set_data(self, nodes_data):
        """Sets the data for the nodes and arranges them."""
        print(f"[DEBUG] NodeGraph.set_data: Received data for {len(nodes_data)} nodes.")
        self.nodes = []
        x, y = 50, 50
        for i, node_data in enumerate(nodes_data):
            node = {
                "id": i,
                "x": x,
                "y": y,
                "width": NODE_WIDTH,
                "height": NODE_HEADER_HEIGHT + (len(node_data["headers"]) * LINE_HEIGHT) + PADDING,
                "data": node_data,
            }
            self.nodes.append(node)
            x += NODE_WIDTH + 100  # Arrange horizontally
        print(f"[DEBUG] NodeGraph.set_data: Created internal node structure: {self.nodes}")
        self.queue_draw()

    def on_draw(self, area, cr, width, height):
        """The main drawing method."""
        style_manager = Adw.StyleManager.get_default()
        is_dark = style_manager.get_dark()

        # Draw background
        if is_dark:
            cr.set_source_rgba(0.1, 0.1, 0.1, 1) # Dark background
        else:
            cr.set_source_rgba(0.95, 0.95, 0.95, 1) # Light background

        cr.paint()

        # Draw connections
        self.draw_connections(cr)

        # Draw nodes
        for node in self.nodes:
            self.draw_node(cr, node)

    def draw_connections(self, cr):
        """Draws lines connecting the nodes."""
        style_manager = Adw.StyleManager.get_default()
        if style_manager.get_dark():
            cr.set_source_rgba(0.7, 0.7, 0.7, 0.8)
        else:
            cr.set_source_rgba(0.3, 0.3, 0.3, 0.8)
        cr.set_line_width(3)
        for i in range(len(self.nodes) - 1):
            node_a = self.nodes[i]
            node_b = self.nodes[i+1]

            start_x = node_a["x"] + node_a["width"]
            start_y = node_a["y"] + node_a["height"] / 2

            end_x = node_b["x"]
            end_y = node_b["y"] + node_b["height"] / 2

            # Use a bezier curve for a smoother connection
            cr.move_to(start_x, start_y)
            c1_x = start_x + 100
            c1_y = start_y
            c2_x = end_x - 100
            c2_y = end_y
            cr.curve_to(c1_x, c1_y, c2_x, c2_y, end_x, end_y)
            cr.stroke()

    def draw_node(self, cr, node):
        """Draws a single node."""
        x, y, w, h = node["x"], node["y"], node["width"], node["height"]
        is_dark = Adw.StyleManager.get_default().get_dark()

        # Custom colors take precedence
        body_color_str = node['data'].get('body_color')
        header_color_str = node['data'].get('header_color')

        body_rgba = Gdk.RGBA()
        header_rgba = Gdk.RGBA()

        # Node body
        if body_color_str and body_rgba.parse(body_color_str) and body_rgba.alpha > 0:
             cr.set_source_rgba(body_rgba.red, body_rgba.green, body_rgba.blue, body_rgba.alpha)
        elif is_dark:
            cr.set_source_rgba(0.2, 0.2, 0.25, 1) # Default dark
        else:
            cr.set_source_rgba(0.8, 0.8, 0.85, 1) # Default light
        self.rounded_rectangle(cr, x, y, w, h, 10)
        cr.fill()

        # Header
        if header_color_str and header_rgba.parse(header_color_str) and header_rgba.alpha > 0:
            cr.set_source_rgba(header_rgba.red, header_rgba.green, header_rgba.blue, header_rgba.alpha)
        elif is_dark:
            cr.set_source_rgba(0.3, 0.3, 0.35, 1) # Default dark
        else:
            cr.set_source_rgba(0.7, 0.7, 0.75, 1) # Default light
        self.rounded_rectangle(cr, x, y, w, NODE_HEADER_HEIGHT, 10, corners={'bl': False, 'br': False})
        cr.fill()

        # Header text
        if is_dark:
            cr.set_source_rgba(1, 1, 1, 1)
        else:
            cr.set_source_rgba(0, 0, 0, 1)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(16)
        cr.move_to(x + PADDING, y + 25)
        cr.show_text(node["data"]["name"])

        # Content text (headers)
        font_desc_str = self.settings.get_string('node-font')
        if not font_desc_str:
            font_desc_str = "Monospace 14"
        font_desc = Pango.FontDescription.from_string(font_desc_str)
        cr.select_font_face(font_desc.get_family(), cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(font_desc.get_size() / Pango.SCALE)
        text_y = y + NODE_HEADER_HEIGHT + PADDING
        for header, value, is_diff in node["data"]["headers"]:
            if is_diff:
                cr.set_source_rgba(0.5, 1.0, 0.5, 1)  # Highlight diffs in green
            elif is_dark:
                cr.set_source_rgba(0.9, 0.9, 0.9, 1)
            else:
                cr.set_source_rgba(0.1, 0.1, 0.1, 1)

            # Truncate long headers for display
            header_text = f"{header}: {value}"
            if len(header_text) > 45:
                header_text = header_text[:42] + "..."

            cr.move_to(x + PADDING, text_y)
            cr.show_text(header_text)
            text_y += LINE_HEIGHT

    def rounded_rectangle(self, cr, x, y, w, h, r, corners=None):
        """Helper to draw a rectangle with rounded corners."""
        if corners is None:
            corners = {'tl': True, 'tr': True, 'bl': True, 'br': True}
        cr.new_path()
        if corners.get('tl', True): cr.arc(x + r, y + r, r, 2 * (3.14 / 2), 3 * (3.14 / 2))
        else: cr.move_to(x, y)
        if corners.get('tr', True): cr.arc(x + w - r, y + r, r, 3 * (3.14 / 2), 4 * (3.14 / 2))
        else: cr.line_to(x + w, y)
        if corners.get('br', True): cr.arc(x + w - r, y + h - r, r, 0, 1 * (3.14 / 2))
        else: cr.line_to(x + w, y + h)
        if corners.get('bl', True): cr.arc(x + r, y + h - r, r, 1 * (3.14 / 2), 2 * (3.14 / 2))
        else: cr.line_to(x, y + h)
        cr.close_path()

    def on_drag_begin(self, gesture, start_x, start_y):
        """Handles the beginning of a drag operation."""
        for node in reversed(self.nodes): # Check from top-most node
            if start_x >= node["x"] and start_x <= node["x"] + node["width"] and \
               start_y >= node["y"] and start_y <= node["y"] + node["height"]:
                self.dragging_node = node
                self.drag_offset_x = start_x - node["x"]
                self.drag_offset_y = start_y - node["y"]
                gesture.set_state(Gtk.EventSequenceState.CLAIMED)
                return
        gesture.set_state(Gtk.EventSequenceState.DENIED)

    def on_drag_update(self, gesture, offset_x, offset_y):
        """Handles the update during a drag operation."""
        if self.dragging_node:
            ok, start_x, start_y = gesture.get_start_point()
            if not ok:
                return
            self.dragging_node["x"] = start_x + offset_x - self.drag_offset_x
            self.dragging_node["y"] = start_y + offset_y - self.drag_offset_y
            self.queue_draw()

    def on_drag_end(self, gesture, offset_x, offset_y):
        """Handles the end of a drag operation."""
        if self.dragging_node:
            self.on_drag_update(gesture, offset_x, offset_y) # Final update
            self.dragging_node = None

    def on_click(self, gesture, n_press, x, y):
        """Handles click events, specifically double-clicks."""
        if n_press != 2: # We only care about double-clicks
            return

        for node in reversed(self.nodes):
            if x >= node["x"] and x <= node["x"] + node["width"] and \
               y >= node["y"] and y <= node["y"] + node["height"]:
                self.show_details_window(node)
                return

    def show_details_window(self, node):
        """Creates and shows a window with the full header details for a node."""
        parent_window = self.get_root()

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_min_content_height(400)
        scrolled_window.set_vexpand(True)

        # Use a TextView for selectable text
        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text_view.set_left_margin(10)
        text_view.set_right_margin(10)
        text_view.set_top_margin(10)
        text_view.set_bottom_margin(10)
        buffer = text_view.get_buffer()
        scrolled_window.set_child(text_view)

        full_text = ""
        for header, value, is_diff in node["data"]["headers"]:
            full_text += f"{header}: {value}\n"

        buffer.set_text(full_text)

        dialog = Adw.MessageDialog(
            transient_for=parent_window,
            heading=f"Headers for {node['data']['name']}",
            extra_child=scrolled_window
        )

        dialog.add_response("close", "Close")
        dialog.connect("response", lambda d, r: d.close())
        dialog.present()