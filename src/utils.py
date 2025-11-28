"""
Utility functions for CacheFlow.
"""

from typing import Tuple

from gi.repository import Adw


def get_accent_color() -> Tuple[float, float, float, float]:
    """
    Returns the system accent color as (r, g, b, a) floats.
    Falls back to a default blue if not available.
    """
    style_manager = Adw.StyleManager.get_default()
    if hasattr(style_manager, "get_accent_color_rgba"):
        accent = style_manager.get_accent_color_rgba()
        if accent:
            return accent.red, accent.green, accent.blue, accent.alpha

    # Fallback default (Red)
    return 1.0, 0.2, 0.2, 1.0
