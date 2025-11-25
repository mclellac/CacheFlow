# Code Audit

This document tracks the audit and refactoring process for the CacheFlow project.

## High-Level Goals

- [ ] Separate concerns and organize code better.
- [ ] Reduce the size of large files.
- [ ] Ensure code is consistent and simple.
- [ ] Reduce code complexity and duplication.
- [ ] Increase debugging, error handling, and stability.
- [ ] Ensure all code adheres to `AGENTS.md` and Adwaita/GNOME HIG.
- [ ] Ensure all `Gtk.Button` widgets use `Adw.ButtonContent`.
- [ ] Identify and remove dead code.

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
- [ ] **Complexity:** The drawing and event handling logic is complex and hard to follow.

### `src/layer_widgets.py`
- [ ] **Duplication:** There may be duplicated code between the different `*Row` widgets.

## UI and Adwaita Compliance
- [ ] Review all `.ui` files to ensure they follow Adwaita and GNOME HIG.
- [ ] Replace any remaining `Gtk.Button` instances that don't use `Adw.ButtonContent`.
