import sys
import gi
import os

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gio, Gtk

# Ensure local schema is found if not installed
# Schema is in the project root (one level up from src)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
schema_dir = project_root

if 'GSETTINGS_SCHEMA_DIR' not in os.environ:
    os.environ['GSETTINGS_SCHEMA_DIR'] = schema_dir

try:
    from .window import Window
    from .preferences import PreferencesWindow
except ImportError:
    from window import Window
    from preferences import PreferencesWindow

class HeaderInspectorApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.github.mclellac.CacheFlow',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = Window(application=self)
        win.present()

    def do_startup(self):
        Adw.Application.do_startup(self)

        # Register Preferences Action
        action = Gio.SimpleAction.new('preferences', None)
        action.connect('activate', self.on_preferences_action)
        self.add_action(action)

        # Setup accelerators
        self.set_accels_for_action('app.quit', ['<Ctrl>q'])
        self.set_accels_for_action('app.preferences', ['<Ctrl>comma'])

    def on_preferences_action(self, action, param):
        # Check if existing preferences window is open
        for win in self.get_windows():
            if isinstance(win, PreferencesWindow):
                win.present()
                return

        # Create and show preferences
        # IMPORTANT: Pass application=self to prevent GC and register window
        prefs = PreferencesWindow(application=self, transient_for=self.props.active_window)
        prefs.present()

def main(version=None):
    app = HeaderInspectorApp()
    return app.run(sys.argv)

if __name__ == '__main__':
    sys.exit(main())
