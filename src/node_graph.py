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
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.pan_start_offset_x = 0
        self.pan_start_offset_y = 0
        self.is_panning = False

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

        gesture_right_click = Gtk.GestureClick.new()
        gesture_right_click.set_button(3)
        gesture_right_click.connect("pressed", self.on_right_click)
        self.add_controller(gesture_right_click)

        # Pan (Middle click) - Keeping this as alternative
        gesture_pan = Gtk.GestureDrag.new()
        gesture_pan.set_button(2)
        gesture_pan.connect("drag-begin", self.on_pan_begin)
        gesture_pan.connect("drag-update", self.on_pan_update)
        self.add_controller(gesture_pan)

        # Zoom (Scroll)
        scroll_controller = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.VERTICAL)
        scroll_controller.connect("scroll", self.on_scroll)
        self.add_controller(scroll_controller)

        self._setup_context_menu()

    def _setup_context_menu(self):
        menu = Gio.Menu()
        menu.append("Reset Layout", "node-graph.reset-layout")
        menu.append("Export Graph...", "node-graph.export")

        self.popover_menu = Gtk.PopoverMenu.new_from_model(menu)
        self.popover_menu.set_parent(self)
        self.popover_menu.set_has_arrow(False)

        # Actions
        action_group = Gio.SimpleActionGroup()

        action_reset = Gio.SimpleAction.new("reset-layout", None)
        action_reset.connect("activate", self.on_reset_layout)
        action_group.add_action(action_reset)

        action_export = Gio.SimpleAction.new("export", None)
        action_export.connect("activate", self.on_export_action)
        action_group.add_action(action_export)

        self.insert_action_group("node-graph", action_group)

    def on_right_click(self, gesture, n_press, x, y):
        self.popover_menu.set_pointing_to(Gdk.Rectangle(int(x), int(y), 1, 1))
        self.popover_menu.popup()

    def on_pan_begin(self, gesture, start_x, start_y):
        self.pan_start_x = start_x
        self.pan_start_y = start_y
        self.pan_start_offset_x = self.offset_x
        self.pan_start_offset_y = self.offset_y
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    def on_pan_update(self, gesture, offset_x, offset_y):
        self.offset_x = self.pan_start_offset_x + offset_x
        self.offset_y = self.pan_start_offset_y + offset_y
        self.queue_draw()

    def on_scroll(self, controller, dx, dy):
        # Zoom towards mouse pointer
        event = controller.get_current_event()
        if not event:
             return False

        x, y = event.get_position()

        # Calculate world coordinate under mouse before zoom
        wx = (x - self.offset_x) / self.scale
        wy = (y - self.offset_y) / self.scale

        zoom_factor = 1.1 if dy < 0 else 0.9
        new_scale = self.scale * zoom_factor

        # Clamp scale
        new_scale = max(0.1, min(new_scale, 5.0))

        # Calculate new offset to keep (wx, wy) at (x, y)
        self.offset_x = x - wx * new_scale
        self.offset_y = y - wy * new_scale
        self.scale = new_scale

        self.queue_draw()
        return True

    def on_reset_layout(self, action, param):
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.set_data([n['data'] for n in self.nodes])

    def on_export_action(self, action, param):
        self.show_export_dialog()

    def show_export_dialog(self):
        dialog = Gtk.FileChooserNative(title="Export Graph",
                                       action=Gtk.FileChooserAction.SAVE,
                                       transient_for=self.get_root())

        filter_png = Gtk.FileFilter()
        filter_png.set_name("PNG Image")
        filter_png.add_pattern("*.png")
        dialog.add_filter(filter_png)

        filter_svg = Gtk.FileFilter()
        filter_svg.set_name("SVG Image")
        filter_svg.add_pattern("*.svg")
        dialog.add_filter(filter_svg)

        filter_txt = Gtk.FileFilter()
        filter_txt.set_name("Text File")
        filter_txt.add_pattern("*.txt")
        dialog.add_filter(filter_txt)

        dialog.connect("response", self.on_export_response)
        dialog.show()

    def on_export_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.ACCEPT:
            file = dialog.get_file()
            filepath = file.get_path()
            if filepath:
                 self.export_graph(filepath)
        dialog.destroy()

    def export_graph(self, filepath):
        if filepath.endswith('.png'):
             self._export_png(filepath)
        elif filepath.endswith('.svg'):
             self._export_svg(filepath)
        elif filepath.endswith('.txt'):
             self._export_text(filepath)
        else:
             # Default to png
             self._export_png(filepath + ".png")

    def _get_total_bounds(self):
        if not self.nodes:
            return 100, 100

        max_x = max(n['x'] + n['width'] for n in self.nodes)
        max_y = max(n['y'] + n['height'] for n in self.nodes)
        return max_x + 50, max_y + 50

    def _export_png(self, filepath):
        width, height = self._get_total_bounds()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(width), int(height))
        cr = cairo.Context(surface)
        self.draw_graph_content(cr, width, height)
        surface.write_to_png(filepath)

    def _export_svg(self, filepath):
        width, height = self._get_total_bounds()
        surface = cairo.SVGSurface(filepath, width, height)
        cr = cairo.Context(surface)
        self.draw_graph_content(cr, width, height)
        surface.finish()

    def _export_text(self, filepath):
        with open(filepath, 'w') as f:
            for node in self.nodes:
                 f.write(f"Node: {node['data'].name}\n")
                 f.write(f"URL: {node['data'].request_method} {node['data'].request_url}\n")
                 f.write("Headers:\n")
                 for h, v, diff, note in node['data'].headers:
                     marker = "*" if diff else " "
                     f.write(f" {marker} {h}: {v}")
                     if note:
                         f.write(f" ({note})")
                     f.write("\n")
                 f.write("\n" + "-"*40 + "\n\n")

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
            text_extents = cr.text_extents(node_data.name)
            min_width = text_extents.width + 2 * PADDING
            node_width = max(NODE_WIDTH, min_width)
            node = {
                "id": i,
                "x": x,
                "y": y,
                "width": node_width,
                "height": NODE_HEADER_HEIGHT + (len(node_data.headers) * LINE_HEIGHT) + PADDING,
                "data": node_data,
                "min_width": min_width,
            }
            self.nodes.append(node)
            x += node_width + 300
        self.queue_draw()

    def on_draw(self, area, cr, width, height):
        """The main drawing method."""
        self.draw_graph_content(cr, width, height)

    def draw_graph_content(self, cr, width, height):
        style_manager = Adw.StyleManager.get_default()
        is_dark = style_manager.get_dark()

        if is_dark:
            cr.set_source_rgba(0.1, 0.1, 0.1, 1)
        else:
            cr.set_source_rgba(0.95, 0.95, 0.95, 1)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        cr.save()
        cr.translate(self.offset_x, self.offset_y)
        cr.scale(self.scale, self.scale)

        self.draw_connections(cr)

        for node in self.nodes:
            self.draw_node(cr, node)

        for node in self.nodes:
            self.draw_resize_handle(cr, node)

        cr.restore()

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
            request_url = node_b["data"].request_url
            request_host = node_b["data"].request_host

            if request_url:
                # Calculate midpoint of Bezier curve (t=0.5)
                # B(t) = (1-t)^3 P0 + 3(1-t)^2 t P1 + 3(1-t) t^2 P2 + t^3 P3
                # For t=0.5: 0.125*P0 + 0.375*P1 + 0.375*P2 + 0.125*P3

                mid_x = 0.125 * start_x + 0.375 * c1_x + 0.375 * c2_x + 0.125 * end_x
                mid_y = 0.125 * start_y + 0.375 * c1_y + 0.375 * c2_y + 0.125 * end_y

                layout = PangoCairo.create_layout(cr)
                font_desc = Pango.FontDescription("Sans 12")
                layout.set_font_description(font_desc)

                method = node_b["data"].request_method
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
        body_color_str = node['data'].body_color
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
        header_color_str = node['data'].header_color
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
        cr.show_text(node["data"].name)

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

        text_color_str = node['data'].text_color
        diff_color_str = node['data'].diff_text_color

        for header, value, is_diff, _ in node["data"].headers:
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

        # Convert to world coordinates
        wx = (start_x - self.offset_x) / self.scale
        wy = (start_y - self.offset_y) / self.scale

        for node in reversed(self.nodes):
            node_x, node_y, node_w, node_h = node["x"], node["y"], node["width"], node["height"]

            handle_x = node_x + node_w - RESIZE_HANDLE_SIZE
            handle_y = node_y + node_h - RESIZE_HANDLE_SIZE

            # Check resize handle collision (Strictly bounded)
            if (handle_x <= wx <= node_x + node_w and
                    handle_y <= wy <= node_y + node_h):
                self.resizing_node = node
                self.selected_node_index = node["id"]
                self.queue_draw()
                log.debug(f"Resizing node '{node['data'].name}'.")
                gesture.set_state(Gtk.EventSequenceState.CLAIMED)
                return

            # Check node body collision
            if node_x <= wx <= node_x + node_w and node_y <= wy <= node_y + node_h:
                self.dragging_node = node
                self.selected_node_index = node["id"]
                self.queue_draw()
                # Store offset from node origin in world coords
                self.drag_offset_x = wx - node["x"]
                self.drag_offset_y = wy - node["y"]
                log.debug(f"Dragging node '{node['data'].name}'.")
                gesture.set_state(Gtk.EventSequenceState.CLAIMED)
                return

        # If we didn't hit any node, deselect
        if self.selected_node_index is not None:
            self.selected_node_index = None
            self.queue_draw()

        # Start panning
        self.is_panning = True
        self.pan_start_x = start_x
        self.pan_start_y = start_y
        self.pan_start_offset_x = self.offset_x
        self.pan_start_offset_y = self.offset_y
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    def on_drag_update(self, gesture, offset_x, offset_y):
        """Handles the update during a drag operation."""
        ok, start_x, start_y = gesture.get_start_point()
        if not ok:
            return

        # Current screen pos
        screen_x = start_x + offset_x
        screen_y = start_y + offset_y

        # Current world pos
        wx = (screen_x - self.offset_x) / self.scale
        wy = (screen_y - self.offset_y) / self.scale

        if self.dragging_node:
            target_x = wx - self.drag_offset_x
            target_y = wy - self.drag_offset_y

            # Snap to grid (20px)
            self.dragging_node["x"] = round(target_x / 20) * 20
            self.dragging_node["y"] = round(target_y / 20) * 20

        elif self.resizing_node:
            min_w = self.resizing_node.get("min_width", 150)
            self.resizing_node["width"] = max(min_w, wx - self.resizing_node["x"])
            self.resizing_node["height"] = max(100, wy - self.resizing_node["y"])
        elif self.is_panning:
            self.offset_x = self.pan_start_offset_x + offset_x
            self.offset_y = self.pan_start_offset_y + offset_y

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
        elif self.is_panning:
            self.on_drag_update(gesture, offset_x, offset_y)
            self.is_panning = False

    def on_click(self, gesture, n_press, x, y):
        """Handles click events."""

        wx = (x - self.offset_x) / self.scale
        wy = (y - self.offset_y) / self.scale

        # Handle selection on single click (or first click of double)
        if n_press == 1:
            hit_node = False
            for node in reversed(self.nodes):
                if (node["x"] <= wx <= node["x"] + node["width"] and
                        node["y"] <= wy <= node["y"] + node["height"]):
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
            if wx >= node["x"] and wx <= node["x"] + node["width"] and \
               wy >= node["y"] and wy <= node["y"] + node["height"]:
                log.debug(f"Double-click on node '{node['data'].name}', emitting signal.")
                self.emit('node-double-clicked', node['data'])
                return
