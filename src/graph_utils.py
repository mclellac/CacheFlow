"""
This module provides utility classes and functions for the NodeGraph widget.
"""

from typing import NamedTuple, Dict, Tuple, Optional
from gi.repository import Gdk

class ConnectionPoints(NamedTuple):
    """Encapsulates the coordinates for a connection curve."""
    start_x: float
    start_y: float
    c1_x: float
    c1_y: float
    c2_x: float
    c2_y: float
    end_x: float
    end_y: float

def get_color(color_str: str, is_dark: bool,
              fallback_light: Tuple[float, float, float, float],
              fallback_dark: Tuple[float, float, float, float]
              ) -> Tuple[float, float, float, float]:
    """
    Parses a color string and returns a tuple of RGBA values.
    If the color string is invalid, it returns a fallback color.
    """
    rgba = Gdk.RGBA()
    if color_str and rgba.parse(color_str) and rgba.alpha > 0:
        return rgba.red, rgba.green, rgba.blue, rgba.alpha
    if is_dark:
        return fallback_dark
    return fallback_light

def rounded_rectangle(cr, x: float, y: float, w: float, h: float,
                      r: float, corners: Optional[Dict[str, bool]] = None) -> None:
    """Helper to draw a rectangle with rounded corners."""
    if corners is None:
        corners = {'tl': True, 'tr': True, 'bl': True, 'br': True}
    cr.new_path()
    if corners.get('tl', True):
        cr.arc(x + r, y + r, r, 2 * (3.14 / 2), 3 * (3.14 / 2))
    else:
        cr.move_to(x, y)
    if corners.get('tr', True):
        cr.arc(x + w - r, y + r, r, 3 * (3.14 / 2), 4 * (3.14 / 2))
    else:
        cr.line_to(x + w, y)
    if corners.get('br', True):
        cr.arc(x + w - r, y + h - r, r, 0, 1 * (3.14 / 2))
    else:
        cr.line_to(x + w, y + h)
    if corners.get('bl', True):
        cr.arc(x + r, y + h - r, r, 1 * (3.14 / 2), 2 * (3.14 / 2))
    else:
        cr.line_to(x, y + h)
    cr.close_path()
