"""
This module defines the NodeGraph widget, which renders the inspection results
as a node-based graph using Cairo.
"""

from .graph_gestures import GraphGestures
from .graph_renderer import GraphRenderer
from .exporters import GraphExporter
from gi.repository import Gtk, Gdk, Adw, Gio, GLib, GObject
import logging
from typing import List, Dict, Tuple, Any, Optional

# pylint: disable=wrong-import-position
import cairo
import gi

gi.require_version("PangoCairo", "1.0")


log = logging.getLogger(__name__)

NODE_WIDTH = 450
NODE_HEADER_HEIGHT = 55
LINE_HEIGHT = 22
PADDING = 15
GAP_X = 300
GAP_Y = 50


class NodeGraph(Gtk.DrawingArea):
    """A widget for drawing and interacting with a node-based graph."""

    __gtype_name__ = "NodeGraph"
    __gsignals__ = {
        "node-double-clicked": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (GObject.TYPE_PYOBJECT,),
        ),
    }

    def __init__(self, **kwargs: Any):
        """Initializes the NodeGraph.

        Args:
            **kwargs: Keyword arguments for the Gtk.DrawingArea.
        """
        super().__init__(**kwargs)
        self.nodes: List[Dict[str, Any]] = []
        self.layers_data: List[List[Any]] = (
            []
        )  # Store original layers data structure
        self.selected_node_index: Optional[int] = None
        self.hovered_node_id: Optional[int] = None
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.popover_menu: Optional[Gtk.PopoverMenu] = None
        self.exporter: Optional[GraphExporter] = None
        self.renderer = GraphRenderer(self)
        self.gestures = GraphGestures(self)

        self.settings = Gio.Settings.new("com.github.mclellac.CacheFlow")
        self.show_all_nodes = False
        self.show_connection_labels = True

        # Animation state
        self.animation_time = 0.0
        self.intro_progress = 0.0
        self.add_tick_callback(self._on_tick)

        log.debug("NodeGraph initialized.")
        self.set_draw_func(self._on_draw)

        style_manager = Adw.StyleManager.get_default()
        style_manager.connect("notify::dark", self._on_style_changed)

        self.gestures.setup_gestures()
        self._setup_context_menu()

    def _setup_context_menu(self) -> None:
        """Sets up the context menu for the graph."""
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

    def set_show_all_nodes(self, visible: bool) -> None:
        """Sets whether to show all nodes or just the active path."""
        self.show_all_nodes = visible
        self.set_data(self.layers_data)

    def set_show_connection_labels(self, visible: bool) -> None:
        """Sets whether to show connection labels."""
        self.show_connection_labels = visible
        self.queue_draw()

    def reset_layout(self) -> None:
        """Resets the layout (scale and offset)."""
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.set_data(self.layers_data)

    def _on_reset_layout_action(
        self, _action: Gio.SimpleAction, _param: GLib.Variant
    ) -> None:
        """Handles the reset-layout action.

        Args:
            _action: The action that emitted the signal.
            _param: The parameter for the action.
        """
        self.reset_layout()

    def _on_export_action(
        self, _action: Gio.SimpleAction, _param: GLib.Variant
    ) -> None:
        """Handles the export action.

        Args:
            _action: The action that emitted the signal.
            _param: The parameter for the action.
        """
        self.show_export_dialog()

    def show_export_dialog(self) -> None:
        """Shows the file chooser dialog for exporting."""
        if not self.exporter:
            self.exporter = GraphExporter(self.get_root(), self.export_graph)
        self.exporter.export_graph()

    def export_graph(self, filepath: str) -> None:
        """Exports the graph to the specified file.

        Args:
            filepath: The path to the file to export to.
        """
        if filepath.endswith(".png"):
            self._export_png(filepath)
        elif filepath.endswith(".svg"):
            self._export_svg(filepath)
        elif filepath.endswith(".txt"):
            self._export_text(filepath)
        else:
            self._export_png(filepath + ".png")

    def _get_total_bounds(self) -> Tuple[float, float]:
        """Calculates the total bounds of the graph.

        Returns:
            A tuple containing the width and height of the graph.
        """
        if not self.nodes:
            return 100.0, 100.0

        max_x = max(n["x"] + n["width"] for n in self.nodes)
        max_y = max(n["y"] + n["height"] for n in self.nodes)
        return max_x + 50.0, max_y + 50.0

    def _export_png(self, filepath: str) -> None:
        """Exports the graph to a PNG file.

        Args:
            filepath: The path to the file to export to.
        """
        width, height = self._get_total_bounds()
        surface = cairo.ImageSurface(
            cairo.FORMAT_ARGB32, int(width), int(height)
        )
        cr = cairo.Context(surface)
        self.renderer.draw_graph_content(cr, width, height)
        surface.write_to_png(filepath)

    def _export_svg(self, filepath: str) -> None:
        """Exports the graph to an SVG file.

        Args:
            filepath: The path to the file to export to.
        """
        width, height = self._get_total_bounds()
        surface = cairo.SVGSurface(filepath, width, height)
        cr = cairo.Context(surface)
        self.renderer.draw_graph_content(cr, width, height)
        surface.finish()

    def _export_text(self, filepath: str) -> None:
        """Exports the graph to a text file.

        Args:
            filepath: The path to the file to export to.
        """
        # pylint: disable=unspecified-encoding
        with open(filepath, "w") as f:
            for node in self.nodes:
                f.write(f"Node: {node['data'].name}\n")
                if hasattr(node["data"], "request_method"):
                    f.write(
                        f"URL: {node['data'].request_method} {node['data'].request_url}\n"
                    )
                f.write("Headers:\n")
                for h, v, diff, note in node["data"].headers:
                    marker = "*" if diff else " "
                    f.write(f" {marker} {h}: {v}")
                    if note:
                        f.write(f" ({note})")
                    f.write("\n")
                f.write("\n" + "-" * 40 + "\n\n")

    def _on_style_changed(
        self, _style_manager: Adw.StyleManager, _param: Any
    ) -> None:
        """Handles theme changes.

        Args:
            _style_manager: The style manager that emitted the signal.
            _param: The parameter for the signal.
        """
        log.debug("System style (light/dark) changed, queueing redraw.")
        self.queue_draw()

    def _on_tick(self, _widget: Gtk.Widget, frame_clock: Gdk.FrameClock) -> bool:
        """Handles the animation tick.

        Args:
            _widget: The widget that received the tick.
            frame_clock: The frame clock.

        Returns:
            True to continue calling this function.
        """
        self.animation_time += 0.01

        if self.intro_progress < 1.0:
            self.intro_progress += 0.05
            if self.intro_progress > 1.0:
                self.intro_progress = 1.0

        self.queue_draw()
        return True

    def set_data(self, layers_data: List[List[Any]]) -> None:
        """Sets the data for the nodes and arranges them.

        Args:
            layers_data: A list of lists of NodeData objects.
        """
        log.info("Setting graph data with %d layers.", len(layers_data))
        self.layers_data = layers_data
        self.nodes = []
        self.intro_progress = 0.0  # Reset intro animation
        x = 50.0

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 0, 0)
        cr = cairo.Context(surface)
        cr.select_font_face(
            "Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD
        )
        cr.set_font_size(16)

        node_id_counter = 0
        layer_index = 0

        # Calculate layout
        # Each layer gets an X position.
        # Nodes within a layer get Y positions.

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

        x += 100 + GAP_X

        # We want to align the active nodes along the Y=0 axis.
        target_center_y = 0.0

        for layer_nodes in layers_data:
            # First, check if input is List[List] or just List (backward compat for old linear list)
            if isinstance(layer_nodes, list):
                nodes_in_col = layer_nodes
            else:
                # Should not happen with new controller but safety check
                nodes_in_col = [layer_nodes]

            if not self.show_all_nodes:
                nodes_in_col = [n for n in nodes_in_col if n.is_active]

            # If no nodes are active in this layer (shouldn't happen for visited layers),
            # we might end up with empty column.
            if not nodes_in_col:
                continue

            # Find max width in this column
            max_col_width = NODE_WIDTH

            # First pass: measure all nodes in this layer/column
            nodes_dimensions = []
            active_node_index = 0

            for idx, node_data in enumerate(nodes_in_col):
                text_extents = cr.text_extents(node_data.name)
                min_width = text_extents.width + 2 * PADDING
                node_width = max(NODE_WIDTH, min_width)

                # Height depends on headers if expanded/active?
                # inactive nodes should be smaller?
                # "inactive nodes" are just blocks without headers.

                header_count = len(node_data.headers)
                node_height = NODE_HEADER_HEIGHT + PADDING
                if header_count > 0:
                    node_height += header_count * LINE_HEIGHT
                node_height += PADDING

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
                active_node_y_rel += nodes_dimensions[i]["height"] + GAP_Y

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
                    "width": dim[
                        "width"
                    ],  # Use individual width or column width? Usually uniform width looks better.
                    # Let's use individual width but maybe center align them if they differ?
                    # For simplicity, left align at X.
                    "height": dim["height"],
                    "data": dim["data"],
                    "min_width": dim["width"],  # Stored for reference
                    "is_client": False,
                }

                # If we want to force uniform width per column:
                # node["width"] = max_col_width

                self.nodes.append(node)
                node_id_counter += 1

                y += dim["height"] + GAP_Y

            x += max_col_width + GAP_X
            layer_index += 1

        # Final pass: Shift all nodes so that the topmost node is at a nice padding
        if self.nodes:
            min_y = min(n["y"] for n in self.nodes)
            desired_min_y = 50.0
            shift_y = desired_min_y - min_y

            for node in self.nodes:
                node["y"] += shift_y

        self.queue_draw()

    def _on_draw(
        self,
        _area: Gtk.DrawingArea,
        cr: cairo.Context,
        width: int,
        height: int,
    ) -> None:
        """The main drawing method.

        Args:
            _area: The drawing area.
            cr: The cairo context.
            width: The width of the drawing area.
            height: The height of the drawing area.
        """
        self.renderer.draw_graph_content(
            cr,
            float(width),
            float(height),
            self.scale,
            self.offset_x,
            self.offset_y,
        )
