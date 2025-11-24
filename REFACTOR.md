# Refactor Documentation

## Preferences and Providers Refactor

**Goal:** Environments should be configured based on Technology stacks. Layers should be categorized by type then technology/provider.

- [x] Define `Provider` classes and `ProviderType` in `src/providers/`.
    - [x] Types: CDN, Load Balancer, Cache Proxies, Application Backends.
    - [x] Providers: Akamai (CDN), Netscalar (Load Balancer), Varnish (Cache Proxies), OpenShift (Application Backends).
- [x] Update `src/preferences.py` to handle new configuration fields (`layer_type`, `provider`).
- [x] Update `LayerRow` UI to include selectors for Type and Provider.
- [x] Ensure `ConfigManager` saves and loads these new fields.
- [x] Update `src/engine.py` (or where appropriate) to utilize Provider-specific logic (e.g., debug headers).
    - *Note:* Debug headers are currently handled in `LayerRow` by populating `custom_headers`.
    - *Update:* Added known headers from new providers to `src/knowledge.py`.

## Code Duplication

- [x] Extract repeated UI patterns. `src/analysis_dialog.py` and `src/header_dialog.py` both manually construct list rows using `Gtk.SignalListItemFactory`. Create a shared helper or widget (e.g., `HeaderRowWidget`) to handle common header display formatting (key, value, description styling).
    - *Implemented `create_header_list_factory` in `src/ui_utils.py` and applied to `src/analysis_dialog.py`. Note: `header_dialog.py` uses a multi-column view which is quite different from the list view in analysis, but we can likely refactor it later or accept the difference. The analysis dialog was the main target for the "list row" duplication.*

## Code Organization

- [x] Refactor `src/window.py` to reduce complexity. Extract inspection execution and result processing logic.
    - *Created `src/controller.py` with `InspectionController`. Moved inspection logic and `NodeData` creation there.*
- [ ] Standardize internal methods in `src/node_graph.py` and `src/window.py` (use `_` prefix).

## Improvements & Suggestions

### UI/UX
- [ ] **Unified Header View:** Refactor `HeaderDialog` to use `src/ui_utils.py` or similar factory logic if possible, or create a unified "Header List" widget that supports both multi-column and rich-list presentations.
- [ ] **Provider Icons:** Display provider icons (Akamai, Varnish, etc.) in the Node Graph or Analysis view.
- [ ] **Validation:** Add validation for `host_url` in Preferences to ensure it's a valid URL before saving.
- [ ] **Context Menus:** Improve context menus on nodes to allow "Re-inspect Node" or "Copy Headers" directly from the graph.

### Architecture
- [ ] **Async Engine:** Move `CacheFlowEngine` to use `aiohttp` or run entirely in a worker thread/process with proper async communication, rather than `threading.Thread` with synchronous `requests`.
- [ ] **Plugin System:** The Provider system is a good start. Expanding it to load providers dynamically from a user folder would allow extensibility.
- [ ] **Dependency Injection:** The `Window` class constructs many dependencies (`HeaderAnalyzer`, `InspectionController`). Using a DI pattern or a central `AppContext` could improve testability.

### Code Quality
- [ ] **Type Safety:** Expand type hints in `src/engine.py` and `src/controller.py` to be more specific (e.g., defining TypedDicts for layer config).
- [ ] **Testing:** Add unit tests for `InspectionController` and `HeaderAnalyzer` mocking the engine/data sources.
