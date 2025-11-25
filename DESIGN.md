# CacheFlow Design & Architecture

## Objective

CacheFlow is a specialized development tool designed to inspect, analyze, and visualize HTTP headers as requests traverse through complex infrastructure layers (e.g., CDNs, Cache Proxies, Load Balancers, and Application Backends). Its primary goal is to help engineers debug caching issues, verify header behavior (manipulation, stripping, addition), and ensure security compliance across their stack.

## Core Systems

### 1. Configuration System (Domain-Centric)
The application moves away from static "Environments" to dynamic "Domain Configurations". A user starts by configuring a **Domain Name** (the entry point). From there, they define the infrastructure layers that sit behind that domain.

**Storage**: GSettings (`com.github.mclellac.CacheFlow`).
**Structure**:
- **Configurations**: A list of domain configs.
- **Layers**: Ordered list of infrastructure components for a domain.

### 2. Inspection Engine (`src/engine.py`)
The engine is responsible for executing the chain of HTTP requests.
- **Dynamic Routing**: Unlike a simple chain, the engine must determine the "Next Hop" URL dynamically based on the current layer's configuration and the request path.
- **Header Management**: Captures headers at each hop.
- **DNS Resolution**: Can resolve specific hostnames to target IPs (e.g., targeting a specific cache node while preserving the Host header).

### 3. Visualization (`src/node_graph.py`)
A custom-drawn Node Graph (using Cairo) visualizes the request path.
- **Nodes**: Represent layers.
- **Edges**: Represent the request flow, annotated with Method, URL, and Status.
- **Interaction**: Zoom, Pan, Drag-and-drop nodes.

### 4. Header Analyzer (`src/analyzer.py`)
Compares headers between the request and response, and between adjacent layers.
- **Diffing**: Identifies Added, Removed, Modified, and Unchanged headers.
- **Knowledge Base**: Provides context and warnings for specific headers (e.g., "Cache-Control is missing").

## Refactoring Plan: Dynamic Configuration & Routing

To support the requirements outlined in `LAYER_CONFIGS.md`, the following refactoring tasks are required.

### A. Data Model & GSettings Schema
The `layers` configuration needs to be more robust to support "Next Hop" determination.

1.  **Update Layer Schema**:
    *   **CDN Layer**:
        *   `default_origin`: (String) The default domain to route to if no rules match.
        *   `default_origin_host_header`: (String, Optional) Host header for the default origin.
        *   `routing_rules`: (List of Dicts)
            *   `path_match`: Glob pattern (e.g., `/images/*`).
            *   `destination_origin`: Domain to route to.
            *   `destination_host_header`: (Optional) Host header override.
    *   **Cache Proxy / Load Balancer**:
        *   `host_url`: The address of this specific layer (VIP/Node).
        *   `routing_rules`: Logic to route to different backends.
    *   **App Backend**:
        *   Terminal node. No routing configuration needed.

### B. UI Refactoring (`src/ui/`)
The `LayerRow` and associated dialogs must be updated to reflect these specific options per layer type.

1.  **CDN Configuration UI**:
    *   Remove generic "Host URL".
    *   Add "Default Origin" input.
    *   Add "Default Host Header" input.
    *   Add "Routing Rules" section (List view to add/remove rules).
2.  **Cache/LB Configuration UI**:
    *   Retain "Host URL" (this is the machine itself).
    *   Add "Routing Rules" for next-hop determination.

### C. Engine Logic (`src/engine.py`)
The `_process_layer` logic must be rewritten to calculate the `next_url` for the *subsequent* layer.

1.  **Input**: Current Request Path, Current Layer Config.
2.  **Logic**:
    *   Iterate through `routing_rules`.
    *   If `path_match` matches current path:
        *   Set `next_host` = `destination_origin` (or backend).
        *   Set `next_host_header` = `destination_host_header`.
    *   Else:
        *   Set `next_host` = `default_origin`.
        *   Set `next_host_header` = `default_origin_host_header`.
3.  **Output**: The computed URL and Headers for the *next* request in the chain.

### D. Migration Steps
1.  **Step 1**: Update `LayerRow` to conditionally show "Default Origin" vs "Host URL" based on Layer Type.
2.  **Step 2**: Implement the "Routing Rules" editor in the UI.
3.  **Step 3**: Update `CacheFlowEngine` to consume this new configuration structure.
4.  **Step 4**: Verify header passing and URL construction with tests/manual verification.
