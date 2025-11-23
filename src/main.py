import sys
import gi
import os
import logging

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Gio, Adw, GLib

from .window import Window
from .preferences import PreferencesWindow

logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger(__name__)


class CacheFlowApplication(Adw.Application):
    """The main application."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        log.debug("Application initialized.")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        self.settings = Gio.Settings.new("com.github.mclellac.CacheFlow")
        self.create_action("preferences", self.on_preferences_action)
        self.create_action("about", self.on_about_action)
        self.style_manager = Adw.StyleManager.get_default()
        self.style_manager.connect("notify::accent-color", self._on_accent_color_changed)
        self.style_manager.connect("notify::high-contrast", self._on_high_contrast_changed)
        self._update_color_scheme()
        self.set_accels_for_action("app.preferences", ["<Primary>comma"])
        self.set_accels_for_action("app.about", ["<Primary>question"])
        if not self.get_active_window():
            self.win = Window(application=app)
            self.win.present()

    def _on_accent_color_changed(self, style_manager, _):
        log.debug(f"System accent color changed to: {style_manager.get_accent_color()}")
        self._update_color_scheme()

    def _on_high_contrast_changed(self, style_manager, _):
        log.debug(
            f"System high contrast mode changed: {style_manager.get_high_contrast()}"
        )
        self._update_color_scheme()

    def _update_color_scheme(self):
        """Reads theme from settings and applies it."""
        theme = self.settings.get_string("theme")
        if theme == "light":
            self.style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        elif theme == "dark":
            self.style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            self.style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)

    def on_preferences_action(self, action, param):
        """Callback for the app.preferences action."""
        log.debug("Preferences action triggered. Creating new PreferencesWindow.")
        prefs_window = PreferencesWindow(
            transient_for=self.get_active_window(), modal=True
        )
        prefs_window.present()

    def on_about_action(self, action, param):
        """Callback for the app.about action."""
        about = Adw.AboutWindow(
            application_name="CacheFlow",
            application_icon="com.github.mclellac.CacheFlow",
            developer_name="Carey McLelland",
            version="0.1.0",
            website="https://github.com/mclellac/CacheFlow",
            transient_for=self.get_active_window(),
        )
        about.present()

    def create_action(self, name, callback):
        """Helper to create a simple action and add it to the app."""
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)


def main(version):
    """Application entry point."""
    app = CacheFlowApplication(
        application_id="com.github.mclellac.CacheFlow",
        flags=Gio.ApplicationFlags.FLAGS_NONE,
    )
    app.run(sys.argv)
