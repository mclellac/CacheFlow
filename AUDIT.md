# Codebase Audit Report

This document records the findings of a full code audit performed on the CacheFlow project.

## 1. Dead Code

### Unused UI Templates
- **File**: `src/ui/varnish_backend_row.ui`
- **Finding**: This UI template defines a class `VarnishBackendRow`, but there is no corresponding Python class in the codebase. The functionality appears to have been refactored into generic `NodeRow` or `OriginRuleRow` widgets.
- **Action**: Verify if strictly needed (unlikely) and delete to avoid confusion.

### Compatibility Artifacts
- **File**: `src/config_manager.py`
- **Finding**: The `_pack_layers` method still packs an empty `varnish_backends` list:
  ```python
  dict_builder.add_value(GLib.Variant("{sv}", ("varnish_backends", GLib.Variant("aa{sv}", []))))
  ```
- **Context**: Retained for backward compatibility with older configuration schemas.

## 2. Code Quality & Linting (Pylint)

The codebase achieved a high Pylint score (**9.74/10**), but several stylistic and minor issues remain.

### Style Violations
- **Line Length**: Multiple files exceed the 100 character limit (e.g., `src/graph_renderer.py`, `src/analyzer.py`, `src/engine.py`).
- **Indentation**: Inconsistent indentation (13 spaces instead of 12) found in `src/graph_renderer.py` and `src/node_graph.py`.
- **Import Order**: Imports in `src/main.py` and `src/node_graph.py` do not strictly follow the standard library -> third party -> local grouping.

### Complexity
- **Too Many Branches/Statements**:
  - `src/graph_renderer.py`: Drawing logic is complex with many conditionals.
  - `src/layer_widgets.py`: The `LayerRow` class is very large (>1000 lines) and handles too many responsibilities (UI setup, data loading, saving logic for multiple types). It has "Too many public methods" and "Too many branches".

### Specific Code Issues
- **Unused Arguments**: `src/graph_renderer.py:340` (Argument `h` is unused).
- **Mutable Default Arguments**: None explicitly flagged, but checked manually.
- **Exception Handling**: Broad exception handling (`Exception`) is used in `src/exporters.py` and `src/config_manager.py` but is correctly caught and logged.

## 3. Architecture & Design

### UI Separation
- **Status**: Excellent. The project strictly follows the separation of UI (XML templates) and Logic (Python classes). No hardcoded widget construction was found in Python files.

### Configuration Management
- **Status**: Robust. Configuration is centralized in `ConfigManager` and uses `GSettings` correctly with complex types (`aa{sv}`).
- **Note**: The persistence of `host_overrides` and `routing_rules` as lists of dictionaries (`aa{ss}`) within the layer variant is well-structured.

### Analysis Logic
- **Status**: The `HeaderAnalyzer` correctly identifies header changes.
- **Testing**: Tests confirm that the "Origin" layer (last layer) correctly reports headers as `UNCHANGED` (Original) rather than `ADDED`, respecting the logic that the origin is the baseline.

### Analyzer Window Usability
- **File**: `src/analysis_dialog.py` / `src/ui/analysis_dialog.ui`
- **Finding**: The Analyzer is implemented as an `Adw.Dialog`, which lacks resizing capabilities and standard window controls (close button) when not strictly controlled by a parent context.
- **Action**: Refactor to use `Adw.Window` to allow resizing and standard window management behavior.

### Node Graph Drawing
- **File**: `src/graph_utils.py`
- **Finding**: The `rounded_rectangle` function uses a rough approximation of PI (`3.14`), which may cause rendering artifacts in corner arcs.
- **Action**: Update to use `math.pi`.

- **File**: `src/graph_renderer.py`
- **Finding**: The connection drawing logic (`_draw_connections`) relies on floating-point `x` coordinates to group nodes into layers. This is fragile and can lead to missing connections if coordinate precision varies or if empty layers disrupt the layout.
- **Action**: Refactor to use explicit `layer_index` stored in the node data.

## 4. Security

- **Input Handling**: The application uses `yaml.safe_load` for importing configurations, preventing code execution vulnerabilities.
- **SSL/TLS**: SSL verification is enforced by default in `requests` but can be optionally disabled by the user via settings (`verify_ssl`). This is explicitly handled in `src/engine.py`.
- **Secrets**: No hardcoded secrets were found.

## 5. Recommendations

1.  **Delete Dead Code**: Remove `src/ui/varnish_backend_row.ui`.
2.  **Refactor `LayerRow`**: The `LayerRow` class in `src/layer_widgets.py` is becoming a "God Class" for layer configuration. Consider splitting it into smaller, type-specific sub-components (e.g., `CDNConfigStrategy`, `ProxyConfigStrategy`) to reduce complexity.
3.  **Standardize Formatting**: Run a formatter (like `black`) to fix indentation and line length issues automatically.
4.  **Fix Imports**: Reorder imports in `src/main.py` and `src/node_graph.py` to satisfy pylint.
5.  **Refactor Analyzer**: Convert `HeaderAnalysisDialog` to `Adw.Window` for better usability.
6.  **Fix Graph Drawing**: Improve `NodeGraph` robustness by using `layer_index` and `math.pi`.
