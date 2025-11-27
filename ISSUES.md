# Issues and Plan

## Node Graph Visualization
- [x] **Show all configured sibling nodes**: Implemented in `src/inspection_controller.py` by mapping `result.get("siblings")`.
- [x] **Inactive Node Styling**: Implemented in `src/graph_renderer.py` via `_draw_inactive_node` which draws smaller, dimmed nodes.
- [x] **Connector Lines**: Logic in `_draw_connections` calculates lines between active nodes.
- [x] **Connection Labels**:
    - [x] Display HTTP Method and Path.
    - [x] Display Host header only if different from the URL host.
    - [x] **Text Positioning**: Offset increased in `src/graph_renderer.py` to avoid overlap.

## Routing Logic
- [x] **Fix Backend Selection**: Path-based routing fixed in `src/engine.py` by normalizing URLs (stripping scheme) before comparison.

## Header Diff / Analysis
- [x] **Missing Cache-Control**: Fixed in `src/engine.py` by suppressing `Accept-Encoding` header to match `curl` behavior, preventing servers from serving varying content (e.g. compressed) that lacks cache headers.
- [x] **Diff Accuracy**: Verified via existing tests and manual analysis logic.

## Plan - Completed

1.  **Fix Routing Logic (`src/engine.py`, `src/routing.py`)**:
    -   Normalized URLs in `_select_node_from_siblings`.
2.  **Update Data Structure (`src/engine.py`, `src/inspection_controller.py`)**:
    -   Mapped `url` and `sent_host_header` to `request_url` and `request_host`.
3.  **Update Graph Rendering (`src/graph_renderer.py`, `src/node_graph.py`)**:
    -   Implemented inactive node drawing.
    -   Improved text positioning.
4.  **Fix Header Analyzer (`src/analyzer.py`)**:
    -   Confirmed behavior with tests.
5.  **Fix Missing Headers (`src/engine.py`)**:
    -   Implemented `Accept-Encoding` suppression to resolve missing headers in compressed responses.
