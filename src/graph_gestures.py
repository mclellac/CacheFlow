"""
This module handles the gesture and event handling logic for the NodeGraph widget.
"""

import logging
from gi.repository import Gtk, Gdk

log = logging.getLogger(__name__)

RESIZE_HANDLE_SIZE = 15


class GraphGestures:
    """Handles all gesture and event handling for the NodeGraph."""

    def __init__(self, node_graph):
        self.node_graph = node_graph
        self.dragging_node = None
        self.resizing_node = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.pan_start_offset_x = 0
        self.pan_start_offset_y = 0
        self.is_panning = False
        self.mouse_x = 0
        self.mouse_y = 0

    def setup_gestures(self) -> None:
        """Sets up the gestures for the NodeGraph."""
        gesture_drag = Gtk.GestureDrag.new()
        gesture_drag.connect("drag-begin", self._on_drag_begin)
        gesture_drag.connect("drag-update", self._on_drag_update)
        gesture_drag.connect("drag-end", self._on_drag_end)
        self.node_graph.add_controller(gesture_drag)

        gesture_click = Gtk.GestureClick.new()
        gesture_click.set_button(1)
        gesture_click.connect("pressed", self._on_click)
        self.node_graph.add_controller(gesture_click)

        gesture_right_click = Gtk.GestureClick.new()
        gesture_right_click.set_button(3)
        gesture_right_click.connect("pressed", self._on_right_click)
        self.node_graph.add_controller(gesture_right_click)

        gesture_pan = Gtk.GestureDrag.new()
        gesture_pan.set_button(2)
        gesture_pan.connect("drag-begin", self._on_pan_begin)
        gesture_pan.connect("drag-update", self._on_pan_update)
        self.node_graph.add_controller(gesture_pan)

        scroll_controller = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL
        )
        scroll_controller.connect("scroll", self._on_scroll)
        self.node_graph.add_controller(scroll_controller)

        motion_controller = Gtk.EventControllerMotion.new()
        motion_controller.connect("motion", self._on_motion)
        self.node_graph.add_controller(motion_controller)

    def _on_right_click(
        self, _gesture: Gtk.GestureClick, _n_press: int, x: float, y: float
    ) -> None:
        """Shows context menu on right click."""
        if self.node_graph.popover_menu:
            self.node_graph.popover_menu.set_pointing_to(
                Gdk.Rectangle(int(x), int(y), 1, 1)
            )
            self.node_graph.popover_menu.popup()

    def _on_pan_begin(
        self, gesture: Gtk.GestureDrag, start_x: float, start_y: float
    ) -> None:
        """Starts panning operation."""
        self.pan_start_x = start_x
        self.pan_start_y = start_y
        self.pan_start_offset_x = self.node_graph.offset_x
        self.pan_start_offset_y = self.node_graph.offset_y
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    def _on_pan_update(
        self, _gesture: Gtk.GestureDrag, offset_x: float, offset_y: float
    ) -> None:
        """Updates panning offset."""
        self.node_graph.offset_x = self.pan_start_offset_x + offset_x
        self.node_graph.offset_y = self.pan_start_offset_y + offset_y
        self.node_graph.queue_draw()

    def _on_motion(
        self, _controller: Gtk.EventControllerMotion, x: float, y: float
    ) -> None:
        """Tracks mouse position."""
        self.mouse_x = x
        self.mouse_y = y

    def _on_scroll(
        self, _controller: Gtk.EventControllerScroll, _dx: float, dy: float
    ) -> bool:
        """Handles zooming via scroll."""
        x = self.mouse_x
        y = self.mouse_y

        wx = (x - self.node_graph.offset_x) / self.node_graph.scale
        wy = (y - self.node_graph.offset_y) / self.node_graph.scale

        zoom_factor = 1.1 if dy < 0 else 0.9
        new_scale = self.node_graph.scale * zoom_factor

        new_scale = max(0.1, min(new_scale, 5.0))

        self.node_graph.offset_x = x - wx * new_scale
        self.node_graph.offset_y = y - wy * new_scale
        self.node_graph.scale = new_scale

        self.node_graph.queue_draw()
        return True

    def _on_drag_begin(
        self, gesture: Gtk.GestureDrag, start_x: float, start_y: float
    ) -> None:
        """Handles the beginning of a drag operation."""
        log.debug("Drag begin at (%s, %s).", start_x, start_y)
        self.dragging_node = None
        self.resizing_node = None

        wx = (start_x - self.node_graph.offset_x) / self.node_graph.scale
        wy = (start_y - self.node_graph.offset_y) / self.node_graph.scale

        for node in reversed(self.node_graph.nodes):
            node_x, node_y, node_w, node_h = (
                node["x"],
                node["y"],
                node["width"],
                node["height"],
            )

            handle_x = node_x + node_w - RESIZE_HANDLE_SIZE
            handle_y = node_y + node_h - RESIZE_HANDLE_SIZE

            if (
                handle_x <= wx <= node_x + node_w
                and handle_y <= wy <= node_y + node_h
            ):
                self.resizing_node = node
                self.node_graph.selected_node_index = node["id"]
                self.node_graph.queue_draw()
                log.debug("Resizing node '%s'.", node["data"].name)
                gesture.set_state(Gtk.EventSequenceState.CLAIMED)
                return

            if (
                node_x <= wx <= node_x + node_w
                and node_y <= wy <= node_y + node_h
            ):
                self.dragging_node = node
                self.node_graph.selected_node_index = node["id"]
                self.node_graph.queue_draw()
                self.drag_offset_x = wx - node["x"]
                self.drag_offset_y = wy - node["y"]
                log.debug("Dragging node '%s'.", node["data"].name)
                gesture.set_state(Gtk.EventSequenceState.CLAIMED)
                return

        if self.node_graph.selected_node_index is not None:
            self.node_graph.selected_node_index = None
            self.node_graph.queue_draw()

        self.is_panning = True
        self.pan_start_x = start_x
        self.pan_start_y = start_y
        self.pan_start_offset_x = self.node_graph.offset_x
        self.pan_start_offset_y = self.node_graph.offset_y
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    def _on_drag_update(
        self, gesture: Gtk.GestureDrag, offset_x: float, offset_y: float
    ) -> None:
        """Handles the update during a drag operation."""
        ok, start_x, start_y = gesture.get_start_point()
        if not ok:
            return

        screen_x = start_x + offset_x
        screen_y = start_y + offset_y

        wx = (screen_x - self.node_graph.offset_x) / self.node_graph.scale
        wy = (screen_y - self.node_graph.offset_y) / self.node_graph.scale

        if self.dragging_node:
            target_x = wx - self.drag_offset_x
            target_y = wy - self.drag_offset_y
            self.dragging_node["x"] = round(target_x / 20) * 20
            self.dragging_node["y"] = round(target_y / 20) * 20

        elif self.resizing_node:
            min_w = self.resizing_node.get("min_width", 150)
            self.resizing_node["width"] = max(
                min_w, wx - self.resizing_node["x"]
            )
            self.resizing_node["height"] = max(
                100, wy - self.resizing_node["y"]
            )
        elif self.is_panning:
            self.node_graph.offset_x = self.pan_start_offset_x + offset_x
            self.node_graph.offset_y = self.pan_start_offset_y + offset_y

        self.node_graph.queue_draw()

    def _on_drag_end(
        self, gesture: Gtk.GestureDrag, offset_x: float, offset_y: float
    ) -> None:
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

    def _on_click(
        self, _gesture: Gtk.GestureClick, n_press: int, x: float, y: float
    ) -> None:
        """Handles click events."""
        wx = (x - self.node_graph.offset_x) / self.node_graph.scale
        wy = (y - self.node_graph.offset_y) / self.node_graph.scale

        if n_press == 1:
            hit_node = False
            for node in reversed(self.node_graph.nodes):
                if (
                    node["x"] <= wx <= node["x"] + node["width"]
                    and node["y"] <= wy <= node["y"] + node["height"]
                ):
                    self.node_graph.selected_node_index = node["id"]
                    self.node_graph.queue_draw()
                    hit_node = True
                    break

            if (
                not hit_node
                and self.node_graph.selected_node_index is not None
            ):
                self.node_graph.selected_node_index = None
                self.node_graph.queue_draw()

        if n_press == 2:
            for node in reversed(self.node_graph.nodes):
                if (
                    node["x"] <= wx <= node["x"] + node["width"]
                    and node["y"] <= wy <= node["y"] + node["height"]
                ):
                    log.debug(
                        "Double-click on node '%s', emitting signal.",
                        node["data"].name,
                    )
                    self.node_graph.emit("node-double-clicked", node["data"])
                    return
