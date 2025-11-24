# CacheFlow Improvement Plan

## Code Duplication

[] Extract repeated UI patterns. `src/analysis_dialog.py` and `src/header_dialog.py` both manually construct list rows using `Gtk.SignalListItemFactory`. Create a shared helper or widget (e.g., `HeaderRowWidget`) to handle common header display formatting (key, value, description styling).

## Code Organization

[] Refactor `src/window.py` to reduce complexity. The `Window` class currently manages UI, inspection orchestration, and result processing. Extract the inspection execution and result processing logic into a dedicated `InspectionController` or expand `CacheFlowEngine` to handle the business logic of interpreting results.
[] Standardize internal methods. Ensure all internal helper methods in `src/node_graph.py` and `src/window.py` strictly follow the `_` prefix convention and are grouped logically or moved to utility modules if generic.

## Refactor Preferences and how nodes will work

[x] Envioronments should be configured based on Technology stacks and application backends as this tool is intended to be used by enterprises which can have complex infrastructure configurations. Layers should be configured based first on selecting the Layer technology (IE: If the user has a CDN they could add an Akamai Layer and configure any overrides or settings from there. If they then have a Load Balancer at Origin, they could select a Load Balancer and the type of load balancer ie: Netscalar, and configure what they need to there.) Layers should be categorized by type then technology/provider. So CDN is the type, Akamai is the provider. Load Balancer is the type, Netscalar is the provider. Cache Proxies is the type, Varnish is the provider, then Application Backends is the Type, OpenShift is the provider. The code for this should reside in src/providers, and for now lets stick with implementing Akamai, Netscalar, Varnish, and OpenShift for the applicaiton backends.
[] Preferences will need to be updated to use this new Providers configurations
