import gi
gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')
from gi.repository import Adw, Gtk, Gdk

Adw.init()
sm = Adw.StyleManager.get_default()
accent = sm.get_accent_color()
print(f"Type: {type(accent)}")
print(f"Dir: {dir(accent)}")
try:
    print(f"Red: {accent.red}")
except Exception as e:
    print(f"Error accessing .red: {e}")
