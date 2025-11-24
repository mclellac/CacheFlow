# Refactor Documentation

## Preferences and Providers Refactor

**Goal:** Environments should be configured based on Technology stacks. Layers should be categorized by type then technology/provider.

- [x] Define `Provider` classes and `ProviderType` in `src/providers/`.
    - [x] Types: CDN, Load Balancer, Cache Proxies, Application Backends.
    - [x] Providers: Akamai (CDN), Netscalar (Load Balancer), Varnish (Cache Proxies), OpenShift (Application Backends).
- [ ] Update `src/preferences.py` to handle new configuration fields (`layer_type`, `provider`).
- [ ] Update `LayerRow` UI to include selectors for Type and Provider.
- [ ] Ensure `ConfigManager` saves and loads these new fields.
- [ ] Update `src/engine.py` (or where appropriate) to utilize Provider-specific logic (e.g., debug headers).

## Code Duplication

- [ ] Extract repeated UI patterns. `src/analysis_dialog.py` and `src/header_dialog.py` both manually construct list rows using `Gtk.SignalListItemFactory`. Create a shared helper or widget (e.g., `HeaderRowWidget`) to handle common header display formatting (key, value, description styling).

## Code Organization

- [ ] Refactor `src/window.py` to reduce complexity. Extract inspection execution and result processing logic.
- [ ] Standardize internal methods in `src/node_graph.py` and `src/window.py` (use `_` prefix).

## Improvements & Suggestions
(To be populated after refactor)
