"""
This module serves as the entry point for the CacheFlow application.
It defines the CacheFlowApplication class and the main execution function.
"""

import sys
import os
import logging
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

# pylint: disable=wrong-import-position
from gi.repository import Gtk, Gio, Adw, GLib

from .window import Window
from .preferences import PreferencesWindow

logging.basicConfig(level=logging.DEBUG,
                    format="[%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger(__name__)


class CacheFlowApplication(Adw.Application):
    """The main application class inheriting from Adw.Application."""

    def __init__(self, version=None, **kwargs):
        super().__init__(**kwargs)
        self.version = version or "0.1.0"
        self.settings = None
        self.style_manager = None
        self.win = None
        log.debug("Application initialized (Version: %s).", self.version)
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        """Callback when the application is activated."""
        log.debug("Application activating.")
        self.settings = Gio.Settings.new("com.github.mclellac.CacheFlow")
        log.debug("GSettings schema 'com.github.mclellac.CacheFlow' loaded.")
        self.create_action("preferences", self.on_preferences_action)
        self.create_action("shortcuts", self.on_shortcuts_action)
        self.create_action("about", self.on_about_action)
        self.style_manager = Adw.StyleManager.get_default()
        self.style_manager.connect("notify::accent-color",
                                   self._on_accent_color_changed)
        self.style_manager.connect("notify::high-contrast",
                                   self._on_high_contrast_changed)
        self._update_color_scheme()
        self.set_accels_for_action("app.preferences", ["<Primary>comma"])
        self.set_accels_for_action("app.about", ["<Primary>question"])
        self.set_accels_for_action("app.quit", ["<Primary>q"])
        self.set_accels_for_action("win.inspect", ["<Primary>Return"])
        self.set_accels_for_action("win.export-graph", ["<Primary>e"])
        self.set_accels_for_action("win.reset-layout", ["<Primary>r"])
        log.debug("Accelerators configured.")
        if not self.get_active_window():
            log.debug("No active window found, creating new main window.")
            self.win = Window(application=app)
            self.win.present()
        else:
            log.debug("Main window already active, presenting it.")
            self.get_active_window().present()

    def _on_accent_color_changed(self, style_manager, _):
        log.debug("System accent color changed to: %s",
                  style_manager.get_accent_color())
        self._update_color_scheme()

    def _on_high_contrast_changed(self, style_manager, _):
        log.debug("System high contrast mode changed: %s",
                  style_manager.get_high_contrast())
        self._update_color_scheme()

    def _update_color_scheme(self):
        """Reads theme from settings and applies it."""
        theme = self.settings.get_string("theme")
        log.debug("Updating color scheme to '%s'.", theme)
        if theme == "light":
            self.style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        elif theme == "dark":
            self.style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            self.style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)

    def on_preferences_action(self, _action, _param):
        """Callback for the app.preferences action."""
        log.debug("Preferences action triggered.")
        prefs_window = PreferencesWindow(
            transient_for=self.get_active_window(), modal=True
        )
        log.debug("Presenting PreferencesWindow.")
        prefs_window.present()

    def on_about_action(self, _action, _param):
        """Callback for the app.about action."""
        log.debug("About action triggered.")
        if hasattr(Adw, "AboutDialog"):
            about = Adw.AboutDialog(
                application_name="CacheFlow",
                application_icon="com.github.mclellac.CacheFlow",
                developer_name="Carey McLelland",
                version=self.version,
                website="https://github.com/mclellac/CacheFlow",
                issue_url="https://github.com/mclellac/CacheFlow/issues",
                comments="An HTTP inspection tool for infrastructure layers.",
                copyright="© 2025 csm",
                license_type=Gtk.License.MIT_X11,
            )
            about.present(self.get_active_window())
        else:
            about = Adw.AboutWindow(
                application_name="CacheFlow",
                application_icon="com.github.mclellac.CacheFlow",
                developer_name="Carey McLelland",
                version=self.version,
                website="https://github.com/mclellac/CacheFlow",
                issue_url="https://github.com/mclellac/CacheFlow/issues",
                comments="An HTTP inspection tool for infrastructure layers.",
                copyright="© 2025 csm",
                license_type=Gtk.License.MIT_X11,
                transient_for=self.get_active_window(),
            )
            about.present()

    def on_shortcuts_action(self, _action, _param):
        """Callback for the app.shortcuts action."""
        log.debug("Shortcuts action triggered.")
        builder = Gtk.Builder()
        builder.add_from_resource(
            "/com/github/mclellac/CacheFlow/ui/shortcuts.ui"
        )
        win = builder.get_object("shortcuts_window")
        win.set_transient_for(self.get_active_window())
        win.present()

    def create_action(self, name, callback):
        """Helper to create a simple action and add it to the app."""
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        log.debug("Action '%s' created.", name)


def main(version):
    """Application entry point."""
    log.info("--- CacheFlow Application Start ---")
    log_file = os.path.join(GLib.get_user_cache_dir(), 'cacheflow.log')
    try:
        file_handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"
        )
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)
        log.info("Logging to %s", log_file)
    except OSError as e:
        log.warning("Failed to setup file logging: %s", e)

    app = CacheFlowApplication(
        version=version,
        application_id="com.github.mclellac.CacheFlow",
        flags=Gio.ApplicationFlags.FLAGS_NONE,
    )
    app.run(sys.argv)


if __name__ == '__main__':
    main(version="0.1.0-dev")
