"""
Shared UI helpers and widgets to reduce duplication.
"""

from gi.repository import Gtk, Pango

def create_header_list_factory(is_analysis: bool = False):
    """
    Creates a Gtk.SignalListItemFactory for displaying headers or analysis results.

    Args:
        is_analysis: If True, expects AnalysisWrapper items and displays icons/badges.
                     If False, expects HeaderItem and displays standard Key/Value.
    """
    factory = Gtk.SignalListItemFactory()

    # Re-writing to use a custom widget structure in setup that is easier to update in bind
    def _setup_structured(_factory, item):
        _setup_header_list_item(item)

    def _bind_structured(_factory, item): # pylint: disable=too-many-statements
        box = item.get_child()
        icon = box.get_first_child()
        vbox = icon.get_next_sibling()
        title = vbox.get_first_child()
        subtitle = title.get_next_sibling()
        badge = vbox.get_next_sibling()

        obj = item.get_item()

        # Reset styles
        box.remove_css_class("header-diff")
        box.remove_css_class("error")
        title.remove_css_class("warning")
        title.remove_css_class("error")
        title.remove_css_class("success")
        icon.set_visible(False)
        badge.set_text("")

        if is_analysis:
            _bind_analysis_item(obj.item, title, subtitle, box, icon, badge)

        else:
            # HeaderItem
            title.set_text(obj.key)
            subtitle.set_text(obj.value)
            if obj.note:
                box.set_tooltip_text(obj.note)
            else:
                box.set_tooltip_text("")

            if obj.is_diff:
                box.add_css_class("header-diff")
                badge.set_text("DIFF")
            else:
                badge.set_text("")

    factory.connect("setup", _setup_structured)
    factory.connect("bind", _bind_structured)

    return factory

def _bind_analysis_item(analysis_item, title, subtitle, box, icon, badge):
    """Helper to bind analysis item data."""
    title.set_text(analysis_item.key)
    subtitle.set_text(analysis_item.value if analysis_item.value else "(No Value)")
    box.set_tooltip_text(
        f"{analysis_item.description}\nCategory: {analysis_item.category}"
    )

    icon_name = None
    style = None

    if analysis_item.warning:
        icon_name = "dialog-warning-symbolic"
        style = "warning"
    elif analysis_item.change_type == "ADDED":
        icon_name = "list-add-symbolic"
        style = "success"
    elif analysis_item.change_type == "REMOVED":
        icon_name = "list-remove-symbolic"
        style = "error"
    elif analysis_item.change_type == "MODIFIED":
        icon_name = "document-edit-symbolic"
        style = "warning"
    elif analysis_item.change_type == "MISSING":
        icon_name = "security-high-symbolic"
        style = "error"

    if icon_name:
        icon.set_from_icon_name(icon_name)
        icon.set_visible(True)
        if style:
            title.add_css_class(style)

    if analysis_item.change_type != "UNCHANGED":
        badge.set_text(analysis_item.change_type)
    else:
        badge.set_text("")

    if analysis_item.change_type == "MISSING":
        box.add_css_class("error")

def _setup_header_list_item(item):
    """Helper to setup the widget structure for header list items."""
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    box.set_margin_start(12)
    box.set_margin_end(12)
    box.set_margin_top(8)
    box.set_margin_bottom(8)

    # Icon (Analysis only)
    icon = Gtk.Image()
    icon.set_pixel_size(16)
    box.append(icon)

    # Text Stack
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    vbox.set_hexpand(True)

    title = Gtk.Label(xalign=0)
    title.add_css_class("heading")
    title.set_ellipsize(Pango.EllipsizeMode.END)

    subtitle = Gtk.Label(xalign=0)
    subtitle.add_css_class("caption")
    subtitle.set_ellipsize(Pango.EllipsizeMode.END)

    vbox.append(title)
    vbox.append(subtitle)
    box.append(vbox)

    # Suffix/Badge
    badge = Gtk.Label()
    badge.add_css_class("caption")
    box.append(badge)

    item.set_child(box)
