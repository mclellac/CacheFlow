# CacheFlow System Documentation

## Features

### Dynamic Routing Configuration
CacheFlow supports advanced configuration for Cache Proxy layers (e.g., Varnish) to simulate real-world routing scenarios. This allows users to define how a proxy handles incoming requests based on the request path.

*   **Path Matching**: Define rules to match specific request paths (e.g., `/api/v1`) using Regex or wildcards.
*   **Backend Selection**: Route requests to specific backend applications based on the matched path. Users can specify the backend host and the expected provider technology (e.g., OpenShift, Generic).
*   **Path Rewriting**: Automatically modify the request path (e.g., using regex substitution `s/find/replace/`) before forwarding it to the backend. This simulates `regsub` behavior common in Varnish and Nginx.
*   **Multiple Backends**: A single Cache Proxy layer can route to multiple different backends depending on the path, allowing for microservice-style architecture simulation.

### Layer Inspection
The core of CacheFlow is its inspection engine, which probes each configured layer in the infrastructure.

*   **Layer Types**: Supports CDN, Load Balancer, Cache Proxy, and Application Backend layers.
*   **Provider Integration**: Includes built-in knowledge for providers like Akamai, Varnish, Netscaler, and OpenShift.
*   **Header Analysis**: Analyzes HTTP headers at each hop to identify caching status, security headers, and potential issues.
*   **Diff View**: Visually compares headers between layers to highlight added, removed, or modified headers.

### Visualization
*   **Node Graph**: Displays the infrastructure as a directed graph, showing the flow of the request.
*   **Dynamic Graph Generation**: The graph is dynamically generated based on the actual routing path taken during inspection.

## Systems

### Inspection Engine
The `CacheFlowEngine` (`src/engine.py`) is responsible for executing HTTP requests. It has been enhanced to support dynamic routing. Instead of a static list of layers, the engine evaluates routing rules at the Cache Proxy layer to determine the next hop.

### Configuration Management
Configuration is managed via GSettings and the `ConfigManager` (`src/preferences.py`). Layer configurations are stored as structured data, including the new `routing_rules` for Cache Proxy layers.

### UI Components
*   **Preferences Window**: Allows users to configure layers and routing rules.
*   **Node Graph**: Custom widget (`src/node_graph.py`) using Cairo for rendering.
*   **Analysis Dialog**: Displays the results of the header analysis.
