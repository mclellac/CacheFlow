# Code Audit

This document tracks the audit and refactoring process for the CacheFlow project.

## High-Level Goals

- [x] Separate concerns and organize code better.
- [x] Reduce the size of large files.
- [x] Ensure code is consistent and simple.
- [x] Reduce code complexity and duplication.
- [x] Increase debugging, error handling, and stability.
- [x] Ensure all code adheres to `AGENTS.md` and Adwaita/GNOME HIG.
- [x] Ensure all `Gtk.Button` widgets use `Adw.ButtonContent`.
- [x] Identify and remove dead code.

## File-Specific Audit Items

### `src/window.py`
- [x] **Complexity:** The `Window` class is large and handles too many responsibilities (UI, inspection orchestration, data processing).
- [x] **Separation of Concerns:** Logic for handling inspection results is tightly coupled with the UI.
- **Note:** Moved inspection logic to `src/inspection_controller.py`.

### `src/preferences.py`
- [x] **Complexity:** The `PreferencesWindow` class is very large and manages all application settings.
- [x] **Separation of Concerns:** Data handling for GSettings is mixed with UI logic.
- **Note:** Moved `ConfigManager` to `src/config_manager.py` to separate data from UI.

### `src/engine.py`
- [x] **Error Handling:** Improved error handling for network requests.
- [x] **Complexity:** The main request-handling loop is simplified.

### `src/node_graph.py`
- [x] **Complexity:** The drawing and event handling logic is complex and hard to follow.
- **Note:** Refactored into `graph_utils.py`, `graph_renderer.py`, and `graph_gestures.py`.

### `src/layer_widgets.py`
- [x] **Duplication:** There may be duplicated code between the different `*Row` widgets.
- **Note:** Created a `BaseEntryRow` class to reduce duplication.

## UI and Adwaita Compliance
- [x] Review all `.ui` files to ensure they follow Adwaita and GNOME HIG.
- [x] Replace any remaining `Gtk.Button` instances that don't use `Adw.ButtonContent`.
