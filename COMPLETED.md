# Completed Refactoring Tasks

- [x] **Set Default Colors**:
  - Implemented distinct default colors for CDN (Blue), Load Balancer (Purple), Cache Proxy (Teal), and Application Backend (Green).
  - Standardized text diff colors: Added (Green), Modified (Orange), Removed (Red).

- [x] **Clean Up Preferences UI**:
  - Refactored `LayerRow` to use `AdwPreferencesGroup` as the root, making top-level settings visible by default.
  - Converted "Nodes" and "Routing Rules" (Origins) to `AdwPreferencesGroup` to keep them open and accessible ("Use less expander rows").
  - Kept "Custom Headers", "Host Overrides", and "Path Match" as `AdwExpanderRow` to hide advanced settings.

- [x] **CDN Settings Overhaul**:
  - Simplified CDN configuration to "ONLY ORIGIN CONFIGS".
  - Hidden "Host URL", "Custom Headers", "Host Overrides", and "Path Match" for CDN layers.
  - Exposed "Default Origin" (Required) and "Origin Rules" (Additional Origins) as the primary configuration.
