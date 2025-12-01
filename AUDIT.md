# Codebase Audit Report

This document records the findings of a full code audit performed on the CacheFlow project, with a focus on stability, code simplification, reducing duplication, and separation of concerns.

## 1. Directory Structure & Organization

The current codebase is largely flat within the `src/` directory. Grouping related modules into subdirectories will improve navigability and separation of concerns.

### Proposed Structure
*   `src/ui/`: Contains all UI-related Python classes (`window.py`, `preferences.py`, `header_dialog.py`, `layer_widgets.py`, etc.) and the existing XML templates.
*   `src/nodegraph/`: Contains all graph visualization logic (`node_graph.py`, `graph_renderer.py`, `graph_gestures.py`, `graph_utils.py`).
*   `src/engine/`: Contains the core inspection engine logic (`engine.py`, `routing.py`, `dns_adapter.py`, `inspection_controller.py`).
*   `src/analysis/`: Contains analysis logic (`analyzer.py`, `knowledge.py`, `analysis_dialog.py`).
*   `src/export/`: Contains export/import logic (`exporters.py`).
*   `src/config/`: Contains configuration management (`config_manager.py`).
*   `src/providers/`: Existing provider implementations.

## 2. Stability & Complexity

### `src/engine.py`
*   **Run Inspection Complexity**: The `run_inspection` method is over 150 lines and handles both linear processing and dynamic sibling selection/creation. The sibling selection logic (`_select_node_from_siblings`) is used in two different contexts (Cache Proxy vs App Backend) with slightly different requirements, leading to intertwined logic.
*   **Error Handling**: Catches broad `requests.exceptions.RequestException`. While safe, it should ensure that specific errors (like DNS vs Connection) are bubbled up with distinct types for better UI feedback (currently partially implemented via `error_type`).

### `src/node_graph.py`
*   **Layout Logic**: The `set_data` method contains significant layout calculation logic (calculating X/Y coordinates, column widths, vertical centering). This should be extracted to a separate `LayoutManager` or `GraphLayout` class within the `nodegraph` module to separate "calculating positions" from "managing the widget".
*   **Data Coupling**: The widget directly manipulates dictionaries representing nodes. Using a `Node` data class (or enhancing `NodeData`) for internal graph representation would be more robust than loose dictionaries.

### `src/preferences.py`
*   **Logic Mixing**: `PreferencesWindow` handles UI setup, GSettings binding, AND logic for importing/exporting configurations (parsing legacy lists vs new config objects). The import/export business logic should be moved to `src/export/importers.py` or integrated into `ConfigManager`.
*   **Manual Data Gathering**: `save_current_config` manually aggregates data from `LayerRow` widgets. This coupling means `PreferencesWindow` must know about the structure of every layer type.

### `src/layer_widgets.py`
*   **God Class**: `LayerRow` is a massive class handling the configuration UI for ALL layer types (CDN, Proxy, Backend, etc.). It switches behavior based on `layer_type`.
*   **Refactoring**: This should be refactored into a base `LayerRow` and specific subclasses (e.g., `CDNLayerRow`, `BackendLayerRow`) or use a Strategy pattern more effectively (it currently uses `layer_strategies.py` but the UI code is still monolithic).

## 3. Code Duplication

*   **Sibling Selection**: Logic for selecting a node from siblings exists in `engine.py`'s `run_inspection` (for Backend candidates) and `_process_layer_dynamic` (for Cache Proxy nodes). This logic is similar but duplicated/split.
*   **Import Logic**: Import logic appears to be split between `exporters.py` (file reading) and `preferences.py` (data parsing/validation). This should be centralized.

## 4. Separation of Concerns

*   **UI vs Logic**: Generally good, but `PreferencesWindow` contains too much business logic regarding configuration structure and migration.
*   **Graph Rendering**: `GraphRenderer` correctly separates drawing from the widget, but the `NodeGraph` widget still retains layout responsibility.
*   **Engine vs Controller**: `InspectionController` correctly orchestrates the background thread, keeping `Window` responsive.

## 5. Dead Code & Cleanups

*   [x] **Unused Template**: `src/ui/varnish_backend_row.ui` does not have a corresponding Python class and should be removed if confirmed unused.
*   **Legacy Code**: `src/config_manager.py` retains empty `varnish_backends` packing for backward compatibility. This is acceptable but should be noted for future cleanup.

## 6. Recommendations

1. [x] **Reorganize Directories**: Move files into the proposed `src/nodegraph`, `src/engine`, `src/export`, `src/ui` structure.
2. [x] **Extract Layout Logic**: Move layout calculation from `NodeGraph.set_data` to a new `src/nodegraph/layout.py`.
3. [x] **Refactor Engine**: Split `run_inspection` into smaller, composable methods. Unify sibling selection logic.
4. [x] **Refactor Preferences**: Move import/export parsing logic out of `PreferencesWindow` into `ConfigManager` or a dedicated `Importer`.
5.  **Refactor LayerRow**: Split `LayerRow` into subclasses or further decouple using the existing Strategy pattern.

## 7. Code Quality & Standards

*   [x] **Type Hinting**: While present in `engine.py` and `node_graph.py`, it is inconsistent in `main.py` and `preferences.py`. The project should enforce type checking (mypy) across all modules to ensure robustness.
*   [x] **Import Management**: `gi.require_version` calls are scattered (e.g., in `main.py` and `node_graph.py`). These should be centralized at the application entry point (e.g., `__init__.py` or the top of `main.py`) to prevent runtime errors or inconsistent version requirements.
*   [x] **Logging Configuration**: Logging setup is split between the global scope and the `main()` function in `src/main.py`. This should be centralized to ensure consistent formatting and handlers across the application lifecycle.

## 8. UI/UX & GNOME HIG

*   [x] **Error Feedback**: `Window.on_inspection_failed` displays raw exception strings to the user via `Adw.AlertDialog`. These should be mapped to user-friendly, localized error messages to improve the user experience.
*   [x] **Widget Compatibility**: `src/main.py` contains fallback logic for `Adw.AboutDialog` vs `Adw.AboutWindow`. The project should standardize on the targeted Libadwaita version to remove unnecessary compatibility checks.
*   **Accessibility**: `src/node_graph.py` draws text and elements using Cairo but does not appear to provide accessibility descriptors (via `Gtk.Accessible` or `Atk`) for the graph nodes. This makes the core visualization inaccessible to screen readers.

## 9. Implementation Details

*   [x] **Hardcoded Layout Constants**: `src/node_graph.py` relies on global constants (`NODE_WIDTH`, `GAP_X`) for layout calculations. These should be encapsulated in a `LayoutConfig` class or resource to allow for potential dynamic scaling, theming, or user configuration.
*   [x] **DNS Resolution**: `src/engine.py` performs manual DNS resolution using `dns.resolver`. While wrapped in the controller, care must be taken to ensure the `DNSAdapter` and resolution logic handle timeouts and failures gracefully without leaking implementation details (like `dnspython` exceptions) to the UI.
