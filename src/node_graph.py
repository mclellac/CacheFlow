"""
This module defines the NodeGraph widget, which renders the inspection results
as a node-based graph using Cairo.
"""

from .graph_gestures import GraphGestures
from .graph_renderer import GraphRenderer
from .exporters import GraphExporter
from gi.repository import Gtk, Adw, Gio, GLib, GObject
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
        self.layers_data: List[List[Any]] = [] # Store original layers data structure
        self.selected_node_index: Optional[int] = None
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.popover_menu: Optional[Gtk.PopoverMenu] = None
        self.exporter: Optional[GraphExporter] = None
        self.renderer = GraphRenderer(self)
        self.gestures = GraphGestures(self)

        self.settings = Gio.Settings.new("com.github.mclellac.CacheFlow")
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
                if hasattr(node['data'], 'request_method'):
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

    def set_data(self, layers_data: List[List[Any]]) -> None:
        """Sets the data for the nodes and arranges them.

        Args:
            layers_data: A list of lists of NodeData objects.
        """
        log.info("Setting graph data with %d layers.", len(layers_data))
        self.layers_data = layers_data
        self.nodes = []
        x = 50.0

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 0, 0)
        cr = cairo.Context(surface)
        cr.select_font_face(
            "Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD
        )
        cr.set_font_size(16)

        node_id_counter = 0

        # Calculate layout
        # Each layer gets an X position.
        # Nodes within a layer get Y positions.

        for layer_nodes in layers_data:
            # First, check if input is List[List] or just List (backward compat for old linear list)
            if isinstance(layer_nodes, list):
                nodes_in_col = layer_nodes
            else:
                 # Should not happen with new controller but safety check
                 nodes_in_col = [layer_nodes]

            # Find max width in this column
            max_col_width = NODE_WIDTH

            # First pass: measure all nodes in this layer/column
            nodes_dimensions = []
            for node_data in nodes_in_col:
                text_extents = cr.text_extents(node_data.name)
                min_width = text_extents.width + 2 * PADDING
                node_width = max(NODE_WIDTH, min_width)

                # Height depends on headers if expanded/active?
                # inactive nodes should be smaller?
                # "inactive nodes" are just blocks without headers.

                header_count = len(node_data.headers)
                node_height = NODE_HEADER_HEIGHT + PADDING
                if header_count > 0:
                     node_height += (header_count * LINE_HEIGHT)

                nodes_dimensions.append({
                    "width": node_width,
                    "height": node_height,
                    "data": node_data
                })

                if node_width > max_col_width:
                    max_col_width = node_width

            # Second pass: assign positions
            # Center the column vertically? Or top align?
            # Let's stack them starting from y=50 with gaps.
            y = 50.0

            for dim in nodes_dimensions:
                node = {
                    "id": node_id_counter,
                    "x": x,
                    "y": y,
                    "width": dim["width"], # Use individual width or column width? Usually uniform width looks better.
                    # Let's use individual width but maybe center align them if they differ?
                    # For simplicity, left align at X.
                    "height": dim["height"],
                    "data": dim["data"],
                    "min_width": dim["width"], # Stored for reference
                }

                # If we want to force uniform width per column:
                # node["width"] = max_col_width

                self.nodes.append(node)
                node_id_counter += 1

                y += dim["height"] + GAP_Y

            x += max_col_width + GAP_X

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
