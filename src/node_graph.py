"""
This module defines the NodeGraph widget, which renders the inspection results
as a node-based graph using Cairo.
"""

import logging
from typing import List, Dict, Tuple, Any, Optional, NamedTuple

# pylint: disable=wrong-import-position
import cairo
import gi

gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, Adw, Pango, PangoCairo, Gio, GLib, GObject

from .utils import get_accent_color
from .exporters import GraphExporter

log = logging.getLogger(__name__)

NODE_WIDTH = 450
NODE_HEADER_HEIGHT = 45
LINE_HEIGHT = 22
PADDING = 15
RESIZE_HANDLE_SIZE = 15


class ConnectionPoints(NamedTuple):
    """Encapsulates the coordinates for a connection curve."""
    start_x: float
    start_y: float
    c1_x: float
    c1_y: float
    c2_x: float
    c2_y: float
    end_x: float
    end_y: float


# pylint: disable=too-many-instance-attributes
class NodeGraph(Gtk.DrawingArea):
    """A widget for drawing and interacting with a node-based graph."""

    __gtype_name__ = 'NodeGraph'
    __gsignals__ = {
        'node-double-clicked': (GObject.SignalFlags.RUN_FIRST, None,
                                (GObject.TYPE_PYOBJECT,)),
    }

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.nodes: List[Dict[str, Any]] = []
        self.dragging_node: Optional[Dict[str, Any]] = None
        self.resizing_node: Optional[Dict[str, Any]] = None
        self.selected_node_index: Optional[int] = None
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
        self.mouse_x = 0
        self.mouse_y = 0
        self.popover_menu: Optional[Gtk.PopoverMenu] = None
        self.exporter: Optional[GraphExporter] = None

        self.settings = Gio.Settings.new('com.github.mclellac.CacheFlow')
        log.debug("NodeGraph initialized.")
        self.set_draw_func(self._on_draw)

        style_manager = Adw.StyleManager.get_default()
        style_manager.connect('notify::dark', self._on_style_changed)

        self._setup_gestures()
        self._setup_context_menu()

    def _setup_gestures(self) -> None:
        gesture_drag = Gtk.GestureDrag.new()
        gesture_drag.connect("drag-begin", self._on_drag_begin)
        gesture_drag.connect("drag-update", self._on_drag_update)
        gesture_drag.connect("drag-end", self._on_drag_end)
        self.add_controller(gesture_drag)

        gesture_click = Gtk.GestureClick.new()
        gesture_click.set_button(1)
        gesture_click.connect("pressed", self._on_click)
        self.add_controller(gesture_click)

        gesture_right_click = Gtk.GestureClick.new()
        gesture_right_click.set_button(3)
        gesture_right_click.connect("pressed", self._on_right_click)
        self.add_controller(gesture_right_click)

        gesture_pan = Gtk.GestureDrag.new()
        gesture_pan.set_button(2)
        gesture_pan.connect("drag-begin", self._on_pan_begin)
        gesture_pan.connect("drag-update", self._on_pan_update)
        self.add_controller(gesture_pan)

        scroll_controller = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL
        )
        scroll_controller.connect("scroll", self._on_scroll)
        self.add_controller(scroll_controller)

        motion_controller = Gtk.EventControllerMotion.new()
        motion_controller.connect("motion", self._on_motion)
        self.add_controller(motion_controller)

    def _setup_context_menu(self) -> None:
        menu = Gio.Menu()
        menu.append("Reset Layout", "node-graph.reset-layout")
        menu.append("Export Graph...", "node-graph.export")

        self.popover_menu = Gtk.PopoverMenu.new_from_model(menu)
        self.popover_menu.set_parent(self)
        self.popover_menu.set_has_arrow(False)

        action_group = Gio.SimpleActionGroup()

        action_reset = Gio.SimpleAction.new("reset-layout", None)
        action_reset.connect("activate", self._on_reset_layout_action)
        action_group.add_action(action_reset)

        action_export = Gio.SimpleAction.new("export", None)
        action_export.connect("activate", self._on_export_action)
        action_group.add_action(action_export)

        self.insert_action_group("node-graph", action_group)

    def _on_right_click(self, _gesture: Gtk.GestureClick, _n_press: int, x: float,
                        y: float) -> None:
        """Shows context menu on right click."""
        if self.popover_menu:
            self.popover_menu.set_pointing_to(Gdk.Rectangle(int(x), int(y), 1, 1))
            self.popover_menu.popup()

    def _on_pan_begin(self, gesture: Gtk.GestureDrag, start_x: float,
                      start_y: float) -> None:
        """Starts panning operation."""
        self.pan_start_x = start_x
        self.pan_start_y = start_y
        self.pan_start_offset_x = self.offset_x
        self.pan_start_offset_y = self.offset_y
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    def _on_pan_update(self, _gesture: Gtk.GestureDrag, offset_x: float,
                       offset_y: float) -> None:
        """Updates panning offset."""
        self.offset_x = self.pan_start_offset_x + offset_x
        self.offset_y = self.pan_start_offset_y + offset_y
        self.queue_draw()

    def _on_motion(self, _controller: Gtk.EventControllerMotion, x: float,
                   y: float) -> None:
        """Tracks mouse position."""
        self.mouse_x = x
        self.mouse_y = y

    def _on_scroll(self, _controller: Gtk.EventControllerScroll, _dx: float,
                   dy: float) -> bool:
        """Handles zooming via scroll."""
        x = self.mouse_x
        y = self.mouse_y

        wx = (x - self.offset_x) / self.scale
        wy = (y - self.offset_y) / self.scale

        zoom_factor = 1.1 if dy < 0 else 0.9
        new_scale = self.scale * zoom_factor

        new_scale = max(0.1, min(new_scale, 5.0))

        self.offset_x = x - wx * new_scale
        self.offset_y = y - wy * new_scale
        self.scale = new_scale

        self.queue_draw()
        return True

    def reset_layout(self) -> None:
        """Resets the layout (scale and offset)."""
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.set_data([n['data'] for n in self.nodes])

    def _on_reset_layout_action(self, _action: Gio.SimpleAction, _param: GLib.Variant) -> None:
        self.reset_layout()

    def _on_export_action(self, _action: Gio.SimpleAction, _param: GLib.Variant) -> None:
        """Triggers the export dialog."""
        self.show_export_dialog()

    def show_export_dialog(self) -> None:
        """Shows the file chooser dialog for exporting."""
        if not self.exporter:
            self.exporter = GraphExporter(self.get_root(), self.export_graph)
        self.exporter.export_graph()

    def export_graph(self, filepath: str) -> None:
        """Exports the graph to the specified file."""
        if filepath.endswith('.png'):
            self._export_png(filepath)
        elif filepath.endswith('.svg'):
            self._export_svg(filepath)
        elif filepath.endswith('.txt'):
            self._export_text(filepath)
        else:
            self._export_png(filepath + ".png")

    def _get_total_bounds(self) -> Tuple[float, float]:
        if not self.nodes:
            return 100.0, 100.0

        max_x = max(n['x'] + n['width'] for n in self.nodes)
        max_y = max(n['y'] + n['height'] for n in self.nodes)
        return max_x + 50.0, max_y + 50.0

    def _export_png(self, filepath: str) -> None:
        width, height = self._get_total_bounds()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(width), int(height))
        cr = cairo.Context(surface)
        self._draw_graph_content(cr, width, height)
        surface.write_to_png(filepath)

    def _export_svg(self, filepath: str) -> None:
        width, height = self._get_total_bounds()
        surface = cairo.SVGSurface(filepath, width, height)
        cr = cairo.Context(surface)
        self._draw_graph_content(cr, width, height)
        surface.finish()

    def _export_text(self, filepath: str) -> None:
        # pylint: disable=unspecified-encoding
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
                f.write("\n" + "-" * 40 + "\n\n")

    def _on_style_changed(self, _style_manager: Adw.StyleManager, _param: Any) -> None:
        """Handles theme changes."""
        log.debug("System style (light/dark) changed, queueing redraw.")
        self.queue_draw()

    def set_data(self, nodes_data: List[Any]) -> None:
        """Sets the data for the nodes and arranges them."""
        log.info("Setting node data with %d nodes.", len(nodes_data))
        self.nodes = []
        x, y = 50.0, 50.0

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
                "height": NODE_HEADER_HEIGHT +
                          (len(node_data.headers) * LINE_HEIGHT) + PADDING,
                "data": node_data,
                "min_width": min_width,
            }
            self.nodes.append(node)
            x += node_width + 300
        self.queue_draw()

    def _on_draw(self, _area: Gtk.DrawingArea, cr: cairo.Context, width: int,
                 height: int) -> None:
        """The main drawing method."""
        self._draw_graph_content(cr, float(width), float(height),
                                 self.scale, self.offset_x, self.offset_y)

    def _draw_graph_content(self, cr: cairo.Context, width: float, height: float,
                            scale: float = 1.0, offset_x: float = 0,
                            offset_y: float = 0) -> None:
        """Draws the entire graph content."""
        # pylint: disable=too-many-arguments
        # pylint: disable=too-many-positional-arguments
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

        for node in self.nodes:
            self._draw_node(cr, node)

        for node in self.nodes:
            self._draw_resize_handle(cr, node)

        cr.restore()

    def _draw_connections(self, cr: cairo.Context) -> None:
        """Draws lines connecting the nodes."""
        # pylint: disable=too-many-locals
        r, g, b, _ = get_accent_color()
        cr.set_source_rgba(r, g, b, 0.8)
        cr.set_line_width(3)
        for i in range(len(self.nodes) - 1):
            node_a = self.nodes[i]
            node_b = self.nodes[i + 1]

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

            points = ConnectionPoints(start_x, start_y, c1_x, c1_y, c2_x, c2_y, end_x, end_y)
            self._draw_connection_label(cr, node_b, points)

    def _draw_connection_label(self, cr: cairo.Context, node_b: Dict[str, Any],
                               points: ConnectionPoints) -> None:
        """Draws the label on the connection line."""
        # pylint: disable=too-many-locals
        request_url = node_b["data"].request_url
        request_host = node_b["data"].request_host

        if not request_url:
            return

        mid_x = (0.125 * points.start_x + 0.375 * points.c1_x +
                 0.375 * points.c2_x + 0.125 * points.end_x)
        mid_y = (0.125 * points.start_y + 0.375 * points.c1_y +
                 0.375 * points.c2_y + 0.125 * points.end_y)

        layout = PangoCairo.create_layout(cr)
        font_desc = Pango.FontDescription("Sans 12")
        layout.set_font_description(font_desc)

        method = node_b["data"].request_method
        text = f"{method} {request_url}"
        if request_host:
            text += f"\nwith Host: {request_host}"

        layout.set_text(text, -1)

        _, logical_rect = layout.get_extents()
        text_width = logical_rect.width / Pango.SCALE
        text_height = logical_rect.height / Pango.SCALE

        dx = (0.75 * (points.c1_x - points.start_x) +
              1.5 * (points.c2_x - points.c1_x) +
              0.75 * (points.end_x - points.c2_x))
        dy = (0.75 * (points.c1_y - points.start_y) +
              1.5 * (points.c2_y - points.c1_y) +
              0.75 * (points.end_y - points.c2_y))

        is_horizontal = abs(dx) >= abs(dy)

        if is_horizontal:
            text_x = mid_x - text_width / 2
            text_y = mid_y - text_height - 5
        else:
            text_x = mid_x + 10
            text_y = mid_y - text_height / 2

        if Adw.StyleManager.get_default().get_dark():
            cr.set_source_rgba(0.8, 0.8, 0.8, 1)
        else:
            cr.set_source_rgba(0.2, 0.2, 0.2, 1)

        cr.move_to(text_x, text_y)
        PangoCairo.show_layout(cr, layout)

    def _get_color(self, color_str: str, is_dark: bool,
                   fallback_light: Tuple[float, float, float, float],
                   fallback_dark: Tuple[float, float, float, float]
                   ) -> Tuple[float, float, float, float]:
        rgba = Gdk.RGBA()
        if color_str and rgba.parse(color_str) and rgba.alpha > 0:
            return rgba.red, rgba.green, rgba.blue, rgba.alpha
        if is_dark:
            return fallback_dark
        return fallback_light

    def _draw_node(self, cr: cairo.Context, node: Dict[str, Any]) -> None:
        """Draws a single node."""
        # pylint: disable=too-many-locals
        x, y, w, h = node["x"], node["y"], node["width"], node["height"]
        style_manager = Adw.StyleManager.get_default()
        is_dark = style_manager.get_dark()

        if self.selected_node_index == node["id"]:
            r, g, b, _ = get_accent_color()
            cr.set_source_rgba(r, g, b, 0.4)
            self._rounded_rectangle(cr, x - 8, y - 8, w + 16, h + 16, 18)
            cr.fill()
            cr.set_source_rgba(r, g, b, 1.0)
            cr.set_line_width(3)
            self._rounded_rectangle(cr, x, y, w, h, 10)
            cr.stroke()

        cr.set_source_rgba(0.0, 0.0, 0.0, 0.4)
        self._rounded_rectangle(cr, x + 2, y + 3, w, h, 10)
        cr.fill()

        body_color = self._get_color(node['data'].body_color, is_dark,
                                     (0.8, 0.8, 0.85, 1), (0.2, 0.2, 0.25, 1))
        cr.set_source_rgba(*body_color)

        self._rounded_rectangle(cr, x, y, w, h, 10)
        cr.fill_preserve()

        border_color = (0.5, 0.5, 0.5, 0.8) if is_dark else (0.4, 0.4, 0.4, 0.8)
        cr.set_source_rgba(*border_color)
        cr.set_line_width(1)
        cr.stroke()

        header_color = self._get_color(node['data'].header_color, is_dark,
                                       (0.7, 0.7, 0.75, 1), (0.3, 0.3, 0.35, 1))
        cr.set_source_rgba(*header_color)

        self._rounded_rectangle(cr, x, y, w, NODE_HEADER_HEIGHT, 10,
                                corners={'bl': False, 'br': False})
        cr.fill_preserve()

        cr.set_source_rgba(*border_color)
        cr.set_line_width(0.5)
        cr.stroke()

        if is_dark:
            cr.set_source_rgba(1, 1, 1, 1)
        else:
            cr.set_source_rgba(0, 0, 0, 1)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(16)
        cr.move_to(x + PADDING, y + 25)
        cr.show_text(node["data"].name)

        self._draw_node_text(cr, node, x, y, w, is_dark)

    def _draw_node_text(self, cr: cairo.Context, node: Dict[str, Any],
                        x: float, y: float, w: float, is_dark: bool) -> None:
        """Draws the text content of the node."""
        # pylint: disable=too-many-arguments
        # pylint: disable=too-many-positional-arguments
        # pylint: disable=too-many-locals
        font_desc_str = self.settings.get_string('node-font')
        if not font_desc_str:
            font_desc_str = "Monospace 14"
        font_desc = Pango.FontDescription.from_string(font_desc_str)
        text_y = y + NODE_HEADER_HEIGHT + PADDING
        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(font_desc)
        layout.set_width((w - 2 * PADDING) * Pango.SCALE)
        layout.set_ellipsize(Pango.EllipsizeMode.END)

        for header, value, is_diff, _ in node["data"].headers:
            if is_diff:
                color = self._get_color(node['data'].diff_text_color, is_dark,
                                        (0, 0.5, 0, 1), (0.5, 1.0, 0.5, 1))
            else:
                color = self._get_color(node['data'].text_color, is_dark,
                                        (0.1, 0.1, 0.1, 1), (0.9, 0.9, 0.9, 1))

            cr.set_source_rgba(*color)

            escaped_header = GLib.markup_escape_text(header)
            escaped_value = GLib.markup_escape_text(value)
            markup = f"<b>{escaped_header}:</b> {escaped_value}"
            layout.set_markup(markup, -1)

            cr.move_to(x + PADDING, text_y)
            PangoCairo.show_layout(cr, layout)
            text_y += LINE_HEIGHT

    def _draw_resize_handle(self, cr: cairo.Context, node: Dict[str, Any]) -> None:
        """Draws a resize handle in the bottom-right corner of a node."""
        x = node["x"] + node["width"] - RESIZE_HANDLE_SIZE
        y = node["y"] + node["height"] - RESIZE_HANDLE_SIZE

        cr.set_source_rgba(0.5, 0.5, 0.5, 0.7)
        cr.move_to(x, y + RESIZE_HANDLE_SIZE)
        cr.line_to(x + RESIZE_HANDLE_SIZE, y)
        cr.line_to(x + RESIZE_HANDLE_SIZE, y + RESIZE_HANDLE_SIZE)
        cr.close_path()
        cr.fill()

    def _rounded_rectangle(self, cr: cairo.Context, x: float, y: float, w: float, h: float,
                           r: float, corners: Optional[Dict[str, bool]] = None) -> None:
        """Helper to draw a rectangle with rounded corners."""
        # pylint: disable=too-many-arguments
        # pylint: disable=too-many-positional-arguments
        if corners is None:
            corners = {'tl': True, 'tr': True, 'bl': True, 'br': True}
        cr.new_path()
        if corners.get('tl', True):
            cr.arc(x + r, y + r, r, 2 * (3.14 / 2), 3 * (3.14 / 2))
        else:
            cr.move_to(x, y)
        if corners.get('tr', True):
            cr.arc(x + w - r, y + r, r, 3 * (3.14 / 2), 4 * (3.14 / 2))
        else:
            cr.line_to(x + w, y)
        if corners.get('br', True):
            cr.arc(x + w - r, y + h - r, r, 0, 1 * (3.14 / 2))
        else:
            cr.line_to(x + w, y + h)
        if corners.get('bl', True):
            cr.arc(x + r, y + h - r, r, 1 * (3.14 / 2), 2 * (3.14 / 2))
        else:
            cr.line_to(x, y + h)
        cr.close_path()

    def _on_drag_begin(self, gesture: Gtk.GestureDrag, start_x: float,
                       start_y: float) -> None:
        """Handles the beginning of a drag operation."""
        log.debug("Drag begin at (%s, %s).", start_x, start_y)
        self.dragging_node = None
        self.resizing_node = None

        wx = (start_x - self.offset_x) / self.scale
        wy = (start_y - self.offset_y) / self.scale

        for node in reversed(self.nodes):
            node_x, node_y, node_w, node_h = (node["x"], node["y"],
                                              node["width"], node["height"])

            handle_x = node_x + node_w - RESIZE_HANDLE_SIZE
            handle_y = node_y + node_h - RESIZE_HANDLE_SIZE

            if (handle_x <= wx <= node_x + node_w and
                    handle_y <= wy <= node_y + node_h):
                self.resizing_node = node
                self.selected_node_index = node["id"]
                self.queue_draw()
                log.debug("Resizing node '%s'.", node['data'].name)
                gesture.set_state(Gtk.EventSequenceState.CLAIMED)
                return

            if node_x <= wx <= node_x + node_w and node_y <= wy <= node_y + node_h:
                self.dragging_node = node
                self.selected_node_index = node["id"]
                self.queue_draw()
                self.drag_offset_x = wx - node["x"]
                self.drag_offset_y = wy - node["y"]
                log.debug("Dragging node '%s'.", node['data'].name)
                gesture.set_state(Gtk.EventSequenceState.CLAIMED)
                return

        if self.selected_node_index is not None:
            self.selected_node_index = None
            self.queue_draw()

        self.is_panning = True
        self.pan_start_x = start_x
        self.pan_start_y = start_y
        self.pan_start_offset_x = self.offset_x
        self.pan_start_offset_y = self.offset_y
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    def _on_drag_update(self, gesture: Gtk.GestureDrag, offset_x: float,
                        offset_y: float) -> None:
        """Handles the update during a drag operation."""
        ok, start_x, start_y = gesture.get_start_point()
        if not ok:
            return

        screen_x = start_x + offset_x
        screen_y = start_y + offset_y

        wx = (screen_x - self.offset_x) / self.scale
        wy = (screen_y - self.offset_y) / self.scale

        if self.dragging_node:
            target_x = wx - self.drag_offset_x
            target_y = wy - self.drag_offset_y
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

    def _on_drag_end(self, gesture: Gtk.GestureDrag, offset_x: float,
                     offset_y: float) -> None:
        """Handles the end of a drag operation."""
        log.debug("Drag ended.")
        if self.dragging_node:
            self._on_drag_update(gesture, offset_x, offset_y)
            self.dragging_node = None
        elif self.resizing_node:
            self._on_drag_update(gesture, offset_x, offset_y)
            self.resizing_node = None
        elif self.is_panning:
            self._on_drag_update(gesture, offset_x, offset_y)
            self.is_panning = False

    def _on_click(self, _gesture: Gtk.GestureClick, n_press: int, x: float,
                  y: float) -> None:
        """Handles click events."""
        wx = (x - self.offset_x) / self.scale
        wy = (y - self.offset_y) / self.scale

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

        if n_press == 2:
            for node in reversed(self.nodes):
                if (node["x"] <= wx <= node["x"] + node["width"] and
                        node["y"] <= wy <= node["y"] + node["height"]):
                    log.debug("Double-click on node '%s', emitting signal.",
                              node['data'].name)
                    self.emit('node-double-clicked', node['data'])
                    return
