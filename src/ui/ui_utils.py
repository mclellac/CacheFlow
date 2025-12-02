"""
Shared UI helpers and widgets to reduce duplication.
"""

from gi.repository import Gtk, Gdk, Pango, GLib
from ..analysis import knowledge


def show_header_popover(parent_widget, header_key):
    """
    Shows a popover with header information (ELI5).
    """
    info = knowledge.get_header_info(header_key)

    popover = Gtk.Popover()
    popover.set_parent(parent_widget)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    box.set_margin_top(12)
    box.set_margin_bottom(12)
    box.set_margin_start(12)
    box.set_margin_end(12)

    title = Gtk.Label(label=f"<b>{header_key}</b>", use_markup=True)
    title.add_css_class("title-4")
    title.set_xalign(0)
    box.append(title)

    desc = Gtk.Label(
        label=info.description, wrap=True, max_width_chars=40
    )
    desc.set_xalign(0)
    box.append(desc)

    if info.meaning:
        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        meaning_label = Gtk.Label(
            label=f"<b>Meaning:</b> {info.meaning}",
            use_markup=True,
            wrap=True,
            max_width_chars=40,
            xalign=0,
        )
        box.append(meaning_label)

    if info.impact:
        impact_label = Gtk.Label(
            label=f"<b>Impact:</b> {info.impact}",
            use_markup=True,
            wrap=True,
            max_width_chars=40,
            xalign=0,
        )
        box.append(impact_label)

    if info.recommendation:
        rec_label = Gtk.Label(
            label=f"<b>Recommendation:</b> {info.recommendation}",
            use_markup=True,
            wrap=True,
            max_width_chars=40,
            xalign=0,
        )
        box.append(rec_label)

    popover.set_child(box)
    popover.popup()


def create_header_list_factory(is_analysis: bool = False):
    """
    Creates a Gtk.SignalListItemFactory for displaying headers or analysis results.

    Args:
        is_analysis: If True, expects AnalysisWrapper items and displays icons/badges.
                     If False, expects HeaderItem and displays standard Key/Value.
    """
    factory = Gtk.SignalListItemFactory()

    def _on_header_clicked(gesture, _n_press, _x, _y):
        widget = gesture.get_widget()
        header_key = getattr(widget, "_header_key", None)
        if header_key:
            show_header_popover(widget, header_key)

    def _setup_structured(_factory, item):
        _setup_header_list_item(item)

        # Add click gesture to the title label
        box = item.get_child()
        icon = box.get_first_child()
        vbox = icon.get_next_sibling()
        title = vbox.get_first_child()

        gesture = Gtk.GestureClick()
        gesture.connect("released", _on_header_clicked)
        title.add_controller(gesture)

    def _bind_structured(
        _factory, item
    ):  # pylint: disable=too-many-statements
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

        # Store key for click handler
        if hasattr(obj, 'key'):
            title._header_key = obj.key
        elif hasattr(obj, 'item') and hasattr(obj.item, 'key'):
             title._header_key = obj.item.key
        else:
             title._header_key = None

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
    subtitle.set_text(
        analysis_item.value if analysis_item.value else "(No Value)"
    )
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
    builder = Gtk.Builder()
    builder.add_from_resource(
        "/com/github/mclellac/CacheFlow/ui/list_item_header.ui"
    )
    box = builder.get_object("box")
    item.set_child(box)
