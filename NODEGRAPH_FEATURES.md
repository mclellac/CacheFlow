# Node Graph Features: Multiple Cache Proxies & Backends

## Objective
Enable configuration and visualization of multiple nodes (Cache Proxies or Application Backends) operating at the same logical layer. The graph should display all configured nodes, but connection lines should only flow to the node that actually handled the request.

## Planned Changes

### 1. Data Model & Configuration
*   **File:** `src/config_manager.py`
    *   Update `_pack_layers` to handle a new optional key `nodes` in the layer dictionary.
    *   The `nodes` key will contain a list of dictionaries (`aa{sv}`), each representing a specific node configuration.
    *   Node attributes:
        *   `name`: Display name (e.g., "cache07").
        *   `host_url`: The base URL for this node.
        *   `match_header`: (Cache Proxy only) Header name to match against the *previous* layer's response.
        *   `match_value`: (Cache Proxy only) Value to match.
        *   `provider`: (App Backend only) Provider type (e.g., AWS, OpenShift).
        *   `header_color`, `body_color`: Node-specific colors.

### 2. UI Configuration (LayerRow)
*   **File:** `src/layer_widgets.py`
    *   Update `LayerRow` to include a new section for "Sibling Nodes" (visible for Cache Proxy and App Backend types).
    *   Implement a new `NodeRow` widget (similar to `OriginRuleRow`) to configure individual nodes.
    *   **Cache Proxy UI:**
        *   Allow adding multiple nodes.
        *   Each node has: Name, Host URL, Match Header, Match Value.
    *   **App Backend UI:**
        *   Allow adding multiple nodes.
        *   Each node has: Name, Host URL, Provider, Color Picker.

*   **File:** `src/ui/node_row.ui` (New)
    *   Template for the `NodeRow` widget.

### 3. Engine Logic (Dynamic Routing)
*   **File:** `src/engine.py`
    *   Modify `run_inspection` to pass the `result` (specifically response headers) of layer N to layer N+1 processing.
    *   Update `_process_layer_dynamic`:
        *   Check if `layer_config` has `nodes` defined.
        *   If `nodes` exist:
            *   **Routing Logic:** Iterate through nodes to find the target.
                *   *Cache Proxy:* Check if `previous_layer_headers` contains `match_header` with value `match_value`.
                *   *App Backend:* Check if `target_base` (resolved from previous layer's `routing_rules`) matches the node's `host_url`.
            *   **Selection:** The matched node becomes the active target.
            *   **Fallbacks:** If no match, maybe default to the first node or report an error.
        *   Return the result for the active node, but also include metadata about the `siblings` (other configured nodes) so the visualizer knows about them.
    *   The returned `result` dictionary should structure this:
        *   `active_node`: The processed node data.
        *   `siblings`: List of unvisited node configurations.

### 4. Visualization (Node Graph)
*   **File:** `src/inspection_controller.py`
    *   Update `_process_results` to handle the new result structure.
    *   Instead of creating a single `NodeData` per layer, create a list of `NodeData` objects for that layer index.
        *   The `active` node gets the full inspection data (headers, diffs).
        *   The `sibling` nodes get "placeholder" data (name, color, but no headers/diffs, or maybe just "Not Visited").
    *   Mark the active node so the renderer knows which one to connect.

*   **File:** `src/node_graph.py`
    *   Update `set_data` to accept a list of *lists* (or a structured object representing layers with multiple nodes).
    *   Layout logic:
        *   If a layer has multiple nodes, arrange them vertically at the same X coordinate.
        *   Adjust Y positions to center the group or stack them nicely.

*   **File:** `src/graph_renderer.py`
    *   Update `draw_graph_content` to iterate through the new data structure.
    *   Draw all nodes in the stack.
    *   **Connection Lines:**
        *   Draw line from Previous Active Node -> Current Active Node.
        *   Do *not* draw lines to/from inactive siblings.

### 5. Pre-commit
*   Standard verification steps.
