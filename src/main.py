# SPDX-License-Identifier: MIT

import sys
import gi
# This MUST be done before any other gi imports.
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Gio, Adw
# Now that the versions are set, we can import the rest of the application.
from .window import Window
from .preferences import PreferencesWindow

class CacheFlowApplication(Adw.Application):
    """The main application."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.create_action('preferences', self.on_preferences_action)
        self.create_action('about', self.on_about_action)
        self.connect('activate', self.on_activate)

        # Load and apply the theme at startup
        self.settings = Gio.Settings.new('com.github.mclellac.CacheFlow')
        self.load_theme()

    def on_activate(self, app):
        self.win = Window(application=app)
        self.win.present()

    def load_theme(self):
        """Reads theme from settings and applies it."""
        theme = self.settings.get_string('theme')
        style_manager = Adw.StyleManager.get_default()
        if theme == 'light':
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        elif theme == 'dark':
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else: # 'system' or default
            style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)

    def on_preferences_action(self, action, param):
        """Callback for the app.preferences action."""
        # There is only one preferences window, so we can create it once and show it
        if not hasattr(self, 'prefs_window'):
            self.prefs_window = PreferencesWindow(transient_for=self.get_active_window(), modal=True)

        self.prefs_window.present()

    def on_about_action(self, action, param):
        """Callback for the app.about action."""
        about = Adw.AboutWindow(
            application_name="CacheFlow",
            application_icon="com.github.mclellac.CacheFlow",
            developer_name="M.V.V. McClellan",
            version="0.1.0",
            website="https://github.com/mclellac/CacheFlow",
            transient_for=self.get_active_window()
        )
        about.present()

    def create_action(self, name, callback):
        """Helper to create a simple action and add it to the app."""
        action = Gio.SimpleAction.new(name, None)
        action.connect('activate', callback)
        self.add_action(action)

def main(version):
    """Application entry point."""
    app = CacheFlowApplication(application_id='com.github.mclellac.CacheFlow',
                               flags=Gio.ApplicationFlags.FLAGS_NONE)
    app.run(sys.argv)