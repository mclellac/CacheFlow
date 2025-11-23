import logging
import cairo
import gi

gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, Adw, Pango, PangoCairo, Gio, GLib, GObject

log = logging.getLogger(__name__)

NODE_WIDTH = 400
NODE_HEADER_HEIGHT = 40
LINE_HEIGHT = 18
PADDING = 10
RESIZE_HANDLE_SIZE = 15


class NodeGraph(Gtk.DrawingArea):
    """A widget for drawing and interacting with a node-based graph."""

    __gtype_name__ = 'NodeGraph'
    __gsignals__ = {
        'node-double-clicked': (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT,)),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.nodes = []
        self.dragging_node = None
        self.resizing_node = None
        self.selected_node_index = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        self.settings = Gio.Settings.new('com.github.mclellac.CacheFlow')
        log.debug("NodeGraph initialized.")
        self.set_draw_func(self.on_draw)

        style_manager = Adw.StyleManager.get_default()
        style_manager.connect('notify::dark', self.on_style_changed)

        gesture_drag = Gtk.GestureDrag.new()
        gesture_drag.connect("drag-begin", self.on_drag_begin)
        gesture_drag.connect("drag-update", self.on_drag_update)
        gesture_drag.connect("drag-end", self.on_drag_end)
        self.add_controller(gesture_drag)

        gesture_click = Gtk.GestureClick.new()
        gesture_click.set_button(1)
        gesture_click.connect("pressed", self.on_click)
        self.add_controller(gesture_click)

    def on_style_changed(self, style_manager, _):
        log.debug("System style (light/dark) changed, queueing redraw.")
        self.queue_draw()

    def set_data(self, nodes_data):
        """Sets the data for the nodes and arranges them."""
        log.info(f"Setting node data with {len(nodes_data)} nodes.")
        self.nodes = []
        x, y = 50, 50

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 0, 0)
        cr = cairo.Context(surface)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(16)

        for i, node_data in enumerate(nodes_data):
            text_extents = cr.text_extents(node_data["name"])
            min_width = text_extents.width + 2 * PADDING
            node_width = max(NODE_WIDTH, min_width)
            node = {
                "id": i,
                "x": x,
                "y": y,
                "width": node_width,
                "height": NODE_HEADER_HEIGHT + (len(node_data["headers"]) * LINE_HEIGHT) + PADDING,
                "data": node_data,
                "min_width": min_width,
            }
            self.nodes.append(node)
            x += node_width + 300
        self.queue_draw()

    def on_draw(self, area, cr, width, height):
        """The main drawing method."""
        style_manager = Adw.StyleManager.get_default()
        is_dark = style_manager.get_dark()

        if is_dark:
            cr.set_source_rgba(0.1, 0.1, 0.1, 1)
        else:
            cr.set_source_rgba(0.95, 0.95, 0.95, 1)
        cr.paint()

        self.draw_connections(cr)

        for node in self.nodes:
            self.draw_node(cr, node)

        for node in self.nodes:
            self.draw_resize_handle(cr, node)

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

            cr.move_to(start_x, start_y)
            c1_x = start_x + 100
            c1_y = start_y
            c2_x = end_x - 100
            c2_y = end_y
            cr.curve_to(c1_x, c1_y, c2_x, c2_y, end_x, end_y)
            cr.stroke()

            # Draw request info text on the line
            request_url = node_b["data"].get("request_url")
            request_host = node_b["data"].get("request_host")

            if request_url:
                # Calculate midpoint of Bezier curve (t=0.5)
                # B(t) = (1-t)^3 P0 + 3(1-t)^2 t P1 + 3(1-t) t^2 P2 + t^3 P3
                # For t=0.5: 0.125*P0 + 0.375*P1 + 0.375*P2 + 0.125*P3

                mid_x = 0.125 * start_x + 0.375 * c1_x + 0.375 * c2_x + 0.125 * end_x
                mid_y = 0.125 * start_y + 0.375 * c1_y + 0.375 * c2_y + 0.125 * end_y

                layout = PangoCairo.create_layout(cr)
                font_desc = Pango.FontDescription("Sans 12")
                layout.set_font_description(font_desc)

                method = node_b["data"].get("request_method", "GET")
                text = f"{method} {request_url}"
                if request_host:
                    text += f"\nwith Host: {request_host}"

                layout.set_text(text, -1)

                ink_rect, logical_rect = layout.get_extents()
                text_width = logical_rect.width / Pango.SCALE
                text_height = logical_rect.height / Pango.SCALE

                # Calculate derivative at t=0.5 to determine orientation
                # B'(t) = 3(1-t)^2(P1-P0) + 6(1-t)t(P2-P1) + 3t^2(P3-P2)
                # At t=0.5: 0.75(P1-P0) + 1.5(P2-P1) + 0.75(P3-P2)
                # P0=(start_x, start_y), P1=(c1_x, c1_y), P2=(c2_x, c2_y), P3=(end_x, end_y)

                dx = 0.75 * (c1_x - start_x) + 1.5 * (c2_x - c1_x) + 0.75 * (end_x - c2_x)
                dy = 0.75 * (c1_y - start_y) + 1.5 * (c2_y - c1_y) + 0.75 * (end_y - c2_y)

                # Determine orientation
                is_horizontal = abs(dx) >= abs(dy)

                if is_horizontal:
                    # Place above the line
                    text_x = mid_x - text_width / 2
                    text_y = mid_y - text_height - 5
                else:
                    # Place to the right of the line
                    text_x = mid_x + 10
                    text_y = mid_y - text_height / 2

                if Adw.StyleManager.get_default().get_dark():
                    cr.set_source_rgba(0.8, 0.8, 0.8, 1)
                else:
                    cr.set_source_rgba(0.2, 0.2, 0.2, 1)

                cr.move_to(text_x, text_y)
                PangoCairo.show_layout(cr, layout)

    def draw_node(self, cr, node):
        """Draws a single node."""
        x, y, w, h = node["x"], node["y"], node["width"], node["height"]
        style_manager = Adw.StyleManager.get_default()
        is_dark = style_manager.get_dark()

        # --- 0. Draw Selection Indicator (Glow/Border) ---
        if self.selected_node_index == node["id"]:
            accent = None
            # Try to get the actual RGBA color (Libadwaita 1.6+)
            if hasattr(style_manager, "get_accent_color_rgba"):
                accent = style_manager.get_accent_color_rgba()

            if accent:
                r, g, b = accent.red, accent.green, accent.blue
            else:
                # Fallback to a default blue
                r, g, b = 0.2, 0.5, 0.9

            # Draw glow
            cr.set_source_rgba(r, g, b, 0.3)
            self.rounded_rectangle(cr, x - 5, y - 5, w + 10, h + 10, 15)
            cr.fill()
            # Draw wider border
            cr.set_source_rgba(r, g, b, 1.0)
            cr.set_line_width(3)
            self.rounded_rectangle(cr, x, y, w, h, 10)
            cr.stroke()

        # --- 1. Draw Shadow ---
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.4)
        self.rounded_rectangle(cr, x + 2, y + 3, w, h, 10)
        cr.fill()

        # --- 2. Draw Node Body and Border ---
        body_rgba = Gdk.RGBA()
        body_color_str = node['data'].get('body_color')
        if body_color_str and body_rgba.parse(body_color_str) and body_rgba.alpha > 0:
            cr.set_source_rgba(body_rgba.red, body_rgba.green, body_rgba.blue, body_rgba.alpha)
        elif is_dark:
            cr.set_source_rgba(0.2, 0.2, 0.25, 1)  # Fallback dark body
        else:
            cr.set_source_rgba(0.8, 0.8, 0.85, 1)  # Fallback light body

        self.rounded_rectangle(cr, x, y, w, h, 10)
        cr.fill_preserve()

        border_color = (0.5, 0.5, 0.5, 0.8) if is_dark else (0.4, 0.4, 0.4, 0.8)
        cr.set_source_rgba(*border_color)
        cr.set_line_width(1)
        cr.stroke()

        # --- 3. Draw Header and Border ---
        header_rgba = Gdk.RGBA()
        header_color_str = node['data'].get('header_color')
        if header_color_str and header_rgba.parse(header_color_str) and header_rgba.alpha > 0:
            cr.set_source_rgba(header_rgba.red, header_rgba.green, header_rgba.blue, header_rgba.alpha)
        elif is_dark:
            cr.set_source_rgba(0.3, 0.3, 0.35, 1)  # Fallback dark header
        else:
            cr.set_source_rgba(0.7, 0.7, 0.75, 1)  # Fallback light header

        self.rounded_rectangle(cr, x, y, w, NODE_HEADER_HEIGHT, 10, corners={'bl': False, 'br': False})
        cr.fill_preserve()

        cr.set_source_rgba(*border_color)
        cr.set_line_width(0.5)
        cr.stroke()

        # --- 4. Draw Text ---
        if is_dark:
            cr.set_source_rgba(1, 1, 1, 1)
        else:
            cr.set_source_rgba(0, 0, 0, 1)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(16)
        cr.move_to(x + PADDING, y + 25)
        cr.show_text(node["data"]["name"])

        font_desc_str = self.settings.get_string('node-font')
        if not font_desc_str:
            font_desc_str = "Monospace 14"
        font_desc = Pango.FontDescription.from_string(font_desc_str)
        text_y = y + NODE_HEADER_HEIGHT + PADDING
        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(font_desc)
        layout.set_width((w - 2 * PADDING) * Pango.SCALE)
        layout.set_ellipsize(Pango.EllipsizeMode.END)

        text_rgba = Gdk.RGBA()
        diff_rgba = Gdk.RGBA()

        text_color_str = node['data'].get('text_color')
        diff_color_str = node['data'].get('diff_text_color')

        for header, value, is_diff, _ in node["data"]["headers"]:
            if is_diff:
                if diff_color_str and diff_rgba.parse(diff_color_str) and diff_rgba.alpha > 0:
                    cr.set_source_rgba(diff_rgba.red, diff_rgba.green, diff_rgba.blue, diff_rgba.alpha)
                elif is_dark:
                    cr.set_source_rgba(0.5, 1.0, 0.5, 1)  # Fallback dark diff
                else:
                    cr.set_source_rgba(0, 0.5, 0, 1)  # Fallback light diff
            elif text_color_str and text_rgba.parse(text_color_str) and text_rgba.alpha > 0:
                cr.set_source_rgba(text_rgba.red, text_rgba.green, text_rgba.blue, text_rgba.alpha)
            else:
                if is_dark:
                    cr.set_source_rgba(0.9, 0.9, 0.9, 1)  # Fallback dark text
                else:
                    cr.set_source_rgba(0.1, 0.1, 0.1, 1)  # Fallback light text

            escaped_header = GLib.markup_escape_text(header)
            escaped_value = GLib.markup_escape_text(value)
            markup = f"<b>{escaped_header}:</b> {escaped_value}"
            layout.set_markup(markup, -1)

            cr.move_to(x + PADDING, text_y)
            PangoCairo.show_layout(cr, layout)
            text_y += LINE_HEIGHT

    def draw_resize_handle(self, cr, node):
        """Draws a resize handle in the bottom-right corner of a node."""
        x = node["x"] + node["width"] - RESIZE_HANDLE_SIZE
        y = node["y"] + node["height"] - RESIZE_HANDLE_SIZE

        cr.set_source_rgba(0.5, 0.5, 0.5, 0.7)
        cr.move_to(x, y + RESIZE_HANDLE_SIZE)
        cr.line_to(x + RESIZE_HANDLE_SIZE, y)
        cr.line_to(x + RESIZE_HANDLE_SIZE, y + RESIZE_HANDLE_SIZE)
        cr.close_path()
        cr.fill()

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
        log.debug(f"Drag begin at ({start_x}, {start_y}).")
        self.dragging_node = None
        self.resizing_node = None

        for node in reversed(self.nodes):
            node_x, node_y, node_w, node_h = node["x"], node["y"], node["width"], node["height"]

            handle_x = node_x + node_w - RESIZE_HANDLE_SIZE
            handle_y = node_y + node_h - RESIZE_HANDLE_SIZE

            # Check resize handle collision (Strictly bounded)
            if (handle_x <= start_x <= node_x + node_w and
                    handle_y <= start_y <= node_y + node_h):
                self.resizing_node = node
                self.selected_node_index = node["id"]
                self.queue_draw()
                log.debug(f"Resizing node '{node['data']['name']}'.")
                gesture.set_state(Gtk.EventSequenceState.CLAIMED)
                return

            # Check node body collision
            if node_x <= start_x <= node_x + node_w and node_y <= start_y <= node_y + node_h:
                self.dragging_node = node
                self.selected_node_index = node["id"]
                self.queue_draw()
                self.drag_offset_x = start_x - node["x"]
                self.drag_offset_y = start_y - node["y"]
                log.debug(f"Dragging node '{node['data']['name']}'.")
                gesture.set_state(Gtk.EventSequenceState.CLAIMED)
                return

        # If we didn't hit any node, deselect
        if self.selected_node_index is not None:
            self.selected_node_index = None
            self.queue_draw()

        gesture.set_state(Gtk.EventSequenceState.DENIED)

    def on_drag_update(self, gesture, offset_x, offset_y):
        """Handles the update during a drag operation."""
        ok, start_x, start_y = gesture.get_start_point()
        if not ok:
            return

        if self.dragging_node:
            self.dragging_node["x"] = start_x + offset_x - self.drag_offset_x
            self.dragging_node["y"] = start_y + offset_y - self.drag_offset_y
        elif self.resizing_node:
            min_w = self.resizing_node.get("min_width", 150)
            self.resizing_node["width"] = max(min_w, start_x + offset_x - self.resizing_node["x"])
            self.resizing_node["height"] = max(100, start_y + offset_y - self.resizing_node["y"])

        self.queue_draw()

    def on_drag_end(self, gesture, offset_x, offset_y):
        """Handles the end of a drag operation."""
        log.debug("Drag ended.")
        if self.dragging_node:
            self.on_drag_update(gesture, offset_x, offset_y)
            self.dragging_node = None
        elif self.resizing_node:
            self.on_drag_update(gesture, offset_x, offset_y)
            self.resizing_node = None

    def on_click(self, gesture, n_press, x, y):
        """Handles click events."""

        # Handle selection on single click (or first click of double)
        if n_press == 1:
            hit_node = False
            for node in reversed(self.nodes):
                if (node["x"] <= x <= node["x"] + node["width"] and
                        node["y"] <= y <= node["y"] + node["height"]):
                    self.selected_node_index = node["id"]
                    self.queue_draw()
                    hit_node = True
                    break

            if not hit_node and self.selected_node_index is not None:
                self.selected_node_index = None
                self.queue_draw()

        if n_press != 2:
            return

        for node in reversed(self.nodes):
            if x >= node["x"] and x <= node["x"] + node["width"] and \
               y >= node["y"] and y <= node["y"] + node["height"]:
                log.debug(f"Double-click on node '{node['data']['name']}', emitting signal.")
                # The node object passed to the signal should have a get_property method
                # The handler in window.py expects an object with a 'headers' property.
                # The 'data' dictionary in our node structure contains this.
                class NodeData:
                    def get_property(self, name):
                        return node['data'].get(name)
                self.emit('node-double-clicked', NodeData())
                return