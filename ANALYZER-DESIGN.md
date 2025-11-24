# HTTP Headers Analyzer Design

The HTTP Headers Analyzer is a proposed subsystem for CacheFlow designed to demystify the complex interactions between infrastructure layers by providing human-readable explanations of HTTP headers. It functions as an expert system that interprets raw header data from systems like Akamai CDN, Varnish, load balancers, and Kubernetes ingress controllers. Instead of simply displaying key-value pairs, the analyzer cross-references headers with a curated knowledge base to explain their purpose, decode their values, and highlight potential configuration issues (such as conflicting caching directives or missing security headers).

Crucially, the system implements a context-aware comparison engine that analyzes the evolution of headers as a request traverses the infrastructure stack. It identifies and explains specific changes between layers—classifying them as added, removed, or modified—and provides insights into *why* a change might have occurred (e.g., a CDN stripping a `Vary` header or a load balancer injecting a tracking ID). This feature aims to significantly reduce troubleshooting time for engineers debugging caching behavior, proxy chains, and backend configurations.

## Implementation Tasks

### ~~1. Header Knowledge Base (`src/knowledge.py`)~~
- ~~Create a new Python module `src/knowledge.py` to serve as the definitive source of header definitions.~~
- ~~Implement a dictionary-based structure mapping lowercase header names to `HeaderDefinition` objects (or named tuples) containing:~~
  - ~~`description`: A human-readable explanation of the header's purpose.~~
  - ~~`category`: Classification (e.g., CDN, Cache, Security, Proxy, Debugging).~~
  - ~~`expected_values`: A description or regex of typical values (e.g., "HIT", "MISS", timestamp).~~
- ~~Populate the knowledge base with common headers for:~~
  - ~~**Standards**: RFC 7234 (Caching), RFC 7231 (Semantics).~~
  - ~~**Akamai**: `Server-Timing`, `X-Cache`, `X-Akamai-Session-Info`, `X-True-Cache-Key`.~~
  - ~~**Varnish**: `X-Varnish`, `Age`, `Via`.~~
  - ~~**Kubernetes/OpenShift**: `X-Forwarded-*`, `X-Original-Host`, ingress annotations.~~
- ~~**Constraints**: Ensure strict PEP8 compliance and full docstring coverage.~~
- **Refactoring**: Split into `src/providers/` (Akamai, Varnish, etc.) to improve modularity and maintainability.

### ~~2. Analyzer Engine (`src/analyzer.py`)~~
- ~~Create a `HeaderAnalyzer` class responsible for generating analysis reports.~~
- ~~Implement a method `analyze_layer(current_layer, upstream_layer)` that returns an `AnalysisReport` object.~~
- ~~**Change Detection Logic**:~~
  - ~~Compare `current_layer` headers against `upstream_layer` headers.~~
  - ~~Categorize differences: `ADDED`, `REMOVED`, `MODIFIED`, `UNCHANGED`.~~
- ~~**Value Interpretation**:~~
  - ~~Implement logic to parse and explain complex header values (e.g., decoding Akamai debug headers or `Cache-Control` directives).~~
  - ~~Detect "Red Flags" (e.g., `Cache-Control: private` on a public CDN layer).~~
- ~~**Constraints**: 100% Pylint score required. Use type hinting (`typing` module) for all method signatures.~~

### ~~3. Analysis UI Template (`src/ui/analysis_dialog.ui`)~~
- ~~Create a new XML UI template for the analysis interface.~~
- ~~Use `Adw.Window` or `Adw.Dialog` as the root container to adhere to GNOME HIG.~~
- ~~**Layout Design**:~~
  - ~~Use `Adw.ToolbarView` for the window structure.~~
  - ~~Implement a `Gtk.ColumnView` or `Gtk.ListView` to display the analysis items.~~
  - ~~Use `Adw.StatusPage` for states where no analysis is available.~~
  - ~~Incorporate `Adw.PreferencesGroup` or grouped lists to separate "Changes", "Warnings", and "Informational" sections.~~
- ~~**Constraints**: Strictly separate UI definition from Python logic.~~

### ~~4. Analysis Dialog Controller (`src/analysis_dialog.py`)~~
- ~~Create a `HeaderAnalysisDialog` class inheriting from `Adw.Dialog` (or `Adw.Window`).~~
- ~~Use `@Gtk.Template` to bind to `src/ui/analysis_dialog.ui`.~~
- ~~Implement the logic to populate the view using data from `HeaderAnalyzer`.~~
- ~~Use `Gio.ListStore` and `Gtk.SignalListItemFactory` to efficiently render analysis items (with icons for Added/Removed/Warning).~~
- ~~Ensure specific visual indicators (colors/icons) align with the Adwaita icon set and system accent colors.~~

### ~~5. Integration (`src/window.py`)~~
- ~~Add an entry point to trigger the analysis.~~
  - ~~Option A: Add an "Analyze" button to the existing `HeaderDialog`.~~
  - ~~Option B: Add a context menu action "Analyze Layer" to the `NodeGraph` nodes.~~
- ~~Wire up the action to instantiate `HeaderAnalysisDialog` with the selected node and its upstream neighbor.~~
- ~~Ensure the analysis runs off the main thread if it involves complex parsing, or ensure it is fast enough to run synchronously.~~

### ~~6. Build System Update~~
- ~~Add `src/knowledge.py`, `src/analyzer.py`, and `src/analysis_dialog.py` to the `python_sources` list in `src/meson.build` to ensure they are installed.~~
- ~~Ensure the new UI template `src/ui/analysis_dialog.ui` is included in `src/cacheflow.gresource.xml`.~~
