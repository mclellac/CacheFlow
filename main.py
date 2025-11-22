import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gio

from ui import MainWindow

class HeaderInspectorApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.example.HeaderInspector',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = MainWindow(application=self)
        win.present()

def main():
    app = HeaderInspectorApp()
    return app.run(sys.argv)

if __name__ == '__main__':
    sys.exit(main())
