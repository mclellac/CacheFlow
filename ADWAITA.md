# Adwaita UI Audit & Enhancement Plan

This document outlines planned UI enhancements to align the CacheFlow application with the GNOME Human Interface Guidelines (HIG) and leverage modern features of Libadwaita (targeting version 1.5+).

## Structural Layout

- [x] **Migrate Main Window to `AdwToolbarView`**
  - **File**: `src/ui/main.ui`
  - **Current**: Uses a `GtkBox` containing an `AdwHeaderBar` and content.
  - **Change**: Replace the root child of `AdwApplicationWindow` with `AdwToolbarView`. Move `AdwHeaderBar` into the `<child type="top">` slot.
  - **Benefit**: Native handling of toolbar styling, collapsing, and window controls integration.

- [x] **Modernize Action Bar Styling**
  - **File**: `src/ui/main.ui` (Inner `GtkBox` with `path_entry`)
  - **Current**: A generic horizontal `GtkBox` with margins.
  - **Change**:
    - Option A: Move controls to the `AdwToolbarView` bottom bar.
    - Option B: Keep as content but wrap in a styled container (e.g., `.toolbar` style class) or use `AdwClamp` to ensure it doesn't stretch awkwardly on wide screens.

## Dialogs & Windows

- [x] **Refactor `HeaderDialog` to `AdwDialog`**
  - **File**: `src/ui/header_dialog.ui`, `src/header_dialog.py`
  - **Current**: Inherits `AdwMessageDialog` but acts as a content inspector.
  - **Change**: Inherit from `AdwDialog` (Libadwaita 1.5+).
    - Use `AdwToolbarView` inside the dialog.
    - Place the search entry in the top toolbar or a secondary bar.
    - Use `AdwDialog.presentation_mode` to adapt to mobile/desktop.
  - **Reason**: `AdwMessageDialog` is semantically for alerts (questions/errors), not for long-lived content views.

- [x] **Adopt `AdwAlertDialog` for Errors**
  - **File**: `src/window.py` (`show_error_dialog`)
  - **Current**: Uses `AdwMessageDialog`.
  - **Change**: Use `AdwAlertDialog` (Libadwaita 1.5+).
  - **Benefit**: Newer API, better adapting behavior.

- [x] **Update About Window**
  - **File**: `src/main.py` (assumed location of action handler)
  - **Change**: Ensure usage of `AdwAboutDialog` (Libadwaita 1.5+) instead of the older `AdwAboutWindow` or `GtkAboutDialog`.

## Feedback & State

- [x] **Implement `AdwToastOverlay`**
  - **File**: `src/ui/main.ui`
  - **Change**: Wrap the main content (inside `AdwToolbarView`) with `AdwToastOverlay`.
  - **Usage**:
    - Show toasts for "Configuration Exported/Imported" events instead of relying solely on logs or file dialog blocking.
    - Show non-critical inspection errors as toasts.

- [x] **Add Empty/Status States (`AdwStatusPage`)**
  - **File**: `src/ui/main.ui` (NodeGraph placeholder)
  - **Current**: The `NodeGraph` area is blank when no inspection has run.
  - **Change**: Overlay an `AdwStatusPage` when the graph data is empty.
    - **Icon**: `network-server-symbolic`
    - **Title**: "Ready to Inspect"
    - **Description**: "Enter a URL path and click Inspect to visualize the cache flow."
  - **File**: `src/ui/header_dialog.ui`
  - **Change**: Show an `AdwStatusPage` (icon: `system-search-symbolic`) when search results are empty.

## Visual Polish

- [x] **Standardize Icons**
  - **Check**: Ensure all actions use symbolic icons from the standard Adwaita set (e.g., `document-save-symbolic`, `edit-find-symbolic`).

- [x] **Typography & Colors**
  - **File**: `src/node_graph.py` (Cairo rendering)
  - **Change**: Ensure colors pulled from `AdwStyleManager` match the semantic colors (success, warning, error, accent) defined in the active theme rather than hardcoded RGB values where possible.

## Preferences

- [x] **File Chooser Modernization**
  - **File**: `src/exporters.py`
  - **Note**: Currently uses `GtkFileChooserNative`. This is correct as Libadwaita delegates file choosing to the underlying portal/GTK. No change needed, but ensure parentage is correct for modal behavior.
