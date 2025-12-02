# UI Improvement Proposals

This document outlines planned improvements to the CacheFlow User Interface to align with GNOME HIG and leverage Libadwaita features, improving usability and aesthetics.

## 1. Header Bar De-cluttering

**Problem:** The main window header bar is currently overcrowded with individual toggle buttons for view options (Animation, Labels, Show All Nodes) and the Cookie Inspector.

**Proposals:**
*   **View Options Menu:** Consolidate the view toggles into a single `GtkMenuButton` (icon: `view-reveal-symbolic` or `display-symbolic`).
    *   **Menu Items:**
        *   Switch: Show Network Animation
        *   Switch: Show Connection Labels
        *   Switch: Show All Infrastructure
*   **Cookie Inspector:** Move the "Cookie Inspector" button to the primary Main Menu (hamburger menu) or keep it but ensure it has a distinct `suggested-action` or distinct style if it remains top-level. Alternatively, place it in the "View Options" menu if it's considered a tool.
*   **Search:** The search toggle is standard, but could be integrated into the View Options or kept as is.

## 2. Node Graph Enhancements

**Problem:** The node boxes are functional but could be more legible and "glanceable".

**Proposals:**
*   **Prominent Status Codes:**
    *   Increase the font size of the HTTP Status Code significantly (e.g., to 20pt or 24pt).
    *   Make the font weight **Bold**.
    *   Position it prominently in the top-right or top-left of the node header, with a colored indicator dot or text color corresponding to the status class (2xx Green, 3xx Yellow, 4xx/5xx Red).
*   **Typography:**
    *   Use the system interface font (`Inter` on standard GNOME) instead of generic Sans/Monospace where possible.
    *   Improve contrast for text against the node background color.
*   **Rounded Corners & Shadows:** Ensure node rectangles use modern rounded corners (already implemented) but perhaps add a subtle drop shadow (via Cairo) to lift active nodes off the canvas.

## 3. Connection Labels

**Problem:** Connection labels are static text and can be hard to read or interact with.

**Proposals:**
*   **Clickable URLs:**
    *   Implement hit-testing in `GraphGestures` to detect clicks on the connection label text.
    *   When clicked, open the URL in the system default browser (using `Gtk.FileLauncher` or `Gio.AppInfo`).
    *   Style the URL text as a link (blue/accent color, underlined on hover).
*   **Rich Styling:**
    *   Render the label as a "pill" or "badge" with a semi-transparent background (already done) but with more padding and a fully rounded shape.
    *   **Latency Indicator:** Add a small icon (e.g., a clock or speedometer) next to the latency text. Color-code the icon and text (Green/Yellow/Red).
    *   **Method Badge:** Display the HTTP Method (GET, POST) in a small, distinct badge style (e.g., uppercase, smaller font, bold, colored background).

## 4. Modern Dialogs & Navigation

**Problem:** The application uses standard windows for some dialogs and a simple dropdown for configuration switching.

**Proposals:**
*   **Adw.Dialog (Libadwaita 1.5+):**
    *   Migrate `HeaderDialog` and `CookieDialog` to use `Adw.Dialog` (or `Adw.BottomSheet` behavior on mobile) instead of separate `Adw.ApplicationWindow`s. This reinforces the modal nature and keeps context.
*   **Navigation:**
    *   Consider moving the "Configuration Switcher" from a dropdown in the header bar to a **Sidebar** (`Adw.NavigationSplitView` or `Adw.OverlaySplitView`).
    *   The sidebar would list all Domain Configurations. Clicking one loads the graph.
    *   This frees up significant space in the Header Bar and allows for managing many configurations more easily.
*   **Inspector Bar:**
    *   The "Path Entry" and "Inspect" button bar takes up vertical space.
    *   Consider making it a floating overlay bar (like in Maps or web browsers) or integrating it into the Header Bar only when needed (using `Adw.ViewSwitcher` logic?).
    *   Or keep it as a "Toolbar" but style it as a joined entry+button group (`Adw.Clamp`).

## 5. Visual Polish

*   **Dark Mode:** Ensure all custom Cairo drawing colors respect the system dark mode palette (Libadwaita named colors).
*   **Animations:**
    *   Smooth out the packet animation using a custom easing function.
    *   Add a "pulse" effect to the status code when a request completes.
