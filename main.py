import sys
import gi
import os

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gio, Gtk

# Ensure local schema is found if not installed
current_dir = os.path.dirname(os.path.abspath(__file__))
schema_dir = current_dir
if 'GSETTINGS_SCHEMA_DIR' not in os.environ:
    os.environ['GSETTINGS_SCHEMA_DIR'] = schema_dir

from window import Window
from preferences import PreferencesWindow

class HeaderInspectorApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='org.example.headerinspector',
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
        # Create and show preferences
        prefs = PreferencesWindow(transient_for=self.props.active_window)
        prefs.present()

def main():
    app = HeaderInspectorApp()
    return app.run(sys.argv)

if __name__ == '__main__':
    sys.exit(main())
