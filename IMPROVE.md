# CacheFlow Improvement Plan

## Code Duplication
[] Consolidate header comparison logic. Currently, `src/window.py` (`_compare_headers`) and `src/analyzer.py` (`analyze_layer`) both implement diffing logic (Added/Removed/Modified). The `HeaderAnalyzer` class should be the single source of truth for header comparison, returning a structure that `Window` can also use for graph node generation.
[] Extract repeated UI patterns. `src/analysis_dialog.py` and `src/header_dialog.py` both manually construct list rows using `Gtk.SignalListItemFactory`. Create a shared helper or widget (e.g., `HeaderRowWidget`) to handle common header display formatting (key, value, description styling).

## Code Organization
[] Refactor `src/window.py` to reduce complexity. The `Window` class currently manages UI, inspection orchestration, and result processing. Extract the inspection execution and result processing logic into a dedicated `InspectionController` or expand `CacheFlowEngine` to handle the business logic of interpreting results.
[] Decouple UI construction from logic in Dialogs. Move the inner class `AnalysisWrapper` and `HeaderItem` to a shared models module (e.g., `src/models.py`) to keep the Dialog files focused on View logic.
[] Standardize internal methods. Ensure all internal helper methods in `src/node_graph.py` and `src/window.py` strictly follow the `_` prefix convention and are grouped logically or moved to utility modules if generic.

## Analyzer Improvements
[] **Make Analyzer Resizable**: Convert `HeaderAnalysisDialog` from `Adw.Dialog` to `Adw.Window` (or `Gtk.Window`). This ensures the window is fully resizable, can be minimized/maximized independently of the main window, and solves the user's request for a resizable interface.
[] **Persist Analyzer Size**: Add GSettings keys (`analyzer-width`, `analyzer-height`) to save and restore the dimensions of the Analyzer window, ensuring a consistent user experience.
[] **Intelligent Explanations - Security**: Add checks for missing or misconfigured security headers:
    - `Strict-Transport-Security` (HSTS)
    - `Content-Security-Policy` (CSP)
    - `X-Content-Type-Options: nosniff`
    - `X-Frame-Options`
[] **Intelligent Explanations - Caching Conflicts**: Detect conflicting directives in `Cache-Control`, such as `no-store` combined with `max-age` or `public`.
[] **Intelligent Explanations - Cookie Caching**: specific warning if `Set-Cookie` is present on a response that is otherwise cacheable (missing `private` or `no-cache`), which is a common security risk.
[] **Intelligent Explanations - Stale Content**: Compare `Age` header against `Cache-Control: max-age`. If `Age` > `max-age`, flag it as "Stale/Expired".
[] **Intelligent Explanations - Routing**: Analyze the `Via` header to detect potential routing loops or excessive hops.
