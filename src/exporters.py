"""
This module handles data export and import functionality.
"""

import logging
from typing import Callable, List, Any, Optional

import yaml
from gi.repository import Gtk, GObject

log = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class BaseExporter(GObject.Object):
    """Base class for handling file chooser dialogs."""

    def __init__(self, parent_window: Gtk.Window):
        super().__init__()
        self.parent = parent_window

    def show_dialog(self, title: str, action: Gtk.FileChooserAction,
                    filters: List[Gtk.FileFilter],
                    callback: Callable[[str], None],
                    default_filename: Optional[str] = None) -> None:
        """Shows a file chooser dialog."""
        dialog = Gtk.FileChooserNative(
            title=title,
            action=action,
            transient_for=self.parent
        )

        if action == Gtk.FileChooserAction.SAVE and default_filename:
            dialog.set_current_name(default_filename)

        for file_filter in filters:
            dialog.add_filter(file_filter)

        def on_response(_dialog: Gtk.FileChooserNative, response_id: int) -> None:
            if response_id == Gtk.ResponseType.ACCEPT:
                file_obj = dialog.get_file()
                if file_obj:
                    filepath = file_obj.get_path()
                    if filepath:
                        callback(filepath)
            dialog.destroy()

        dialog.connect("response", on_response)
        dialog.show()


class ConfigExporter(BaseExporter):
    """Handles configuration export and import."""

    def export_config(self, data: List[Any], default_filename: str = "config.yaml",
                      on_success: Optional[Callable[[str], None]] = None) -> None:
        """Exports configuration data to a YAML file."""
        filter_yaml = Gtk.FileFilter()
        filter_yaml.set_name("YAML files")
        filter_yaml.add_pattern("*.yaml")
        filter_yaml.add_pattern("*.yml")

        def on_file_selected(filepath: str) -> None:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, sort_keys=False)
                log.info("Configuration exported to %s", filepath)
                if on_success:
                    on_success(filepath)
            except Exception as e:  # pylint: disable=broad-exception-caught
                log.error("Failed to export configuration: %s", e)

        self.show_dialog("Export Configuration", Gtk.FileChooserAction.SAVE,
                         [filter_yaml], on_file_selected, default_filename)

    def import_config(self, on_success: Callable[[List[Any]], None]) -> None:
        """Imports configuration data from a YAML file."""
        filter_yaml = Gtk.FileFilter()
        filter_yaml.set_name("YAML files")
        filter_yaml.add_pattern("*.yaml")
        filter_yaml.add_pattern("*.yml")

        def on_file_selected(filepath: str) -> None:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    layers_data = yaml.safe_load(f)

                if not isinstance(layers_data, list):
                    raise ValueError("Imported data must be a list of layers.")

                log.info("Configuration imported from %s", filepath)
                on_success(layers_data)
            except Exception as e:  # pylint: disable=broad-exception-caught
                log.error("Failed to import configuration: %s", e)

        self.show_dialog("Import Configuration", Gtk.FileChooserAction.OPEN,
                         [filter_yaml], on_file_selected)


class GraphExporter(BaseExporter):
    """Handles graph export."""

    def __init__(self, parent_window: Gtk.Window, export_callback: Callable[[str], None]):
        super().__init__(parent_window)
        self.export_callback = export_callback

    def export_graph(self) -> None:
        """Shows dialog to export graph."""
        filter_png = Gtk.FileFilter()
        filter_png.set_name("PNG Image")
        filter_png.add_pattern("*.png")

        filter_svg = Gtk.FileFilter()
        filter_svg.set_name("SVG Image")
        filter_svg.add_pattern("*.svg")

        filter_txt = Gtk.FileFilter()
        filter_txt.set_name("Text File")
        filter_txt.add_pattern("*.txt")

        self.show_dialog("Export Graph", Gtk.FileChooserAction.SAVE,
                         [filter_png, filter_svg, filter_txt], self.export_callback,
                         "graph.png")
