# Cache Proxy Configuration

This document explains the configuration fields for the **Cache Proxy** layer and details how the application determines which cache proxy node receives traffic (and thus, how the connection line is drawn in the Node Graph).

## Configuration Fields

When configuring a Cache Proxy layer, you are defining how the request is handled after leaving the Load Balancer (or previous layer) and before reaching the Application Backend.

### 1. Default Backend Host
*   **Description:** The hostname of the origin server or next-hop backend that this proxy should forward requests to by default.
*   **Usage:** If no specific "Routing Rules" match the request path, this host is used as the destination.
*   **Example:** `backend.example.internal`

### 2. Default Backend Host Header (Optional)
*   **Description:** The value to set for the `Host` header when forwarding requests to the Default Backend.
*   **Usage:** Useful if the backend server requires a specific Host header that differs from the request's hostname (e.g., for virtual hosting).
*   **Example:** `my-app.local`

### 3. Cache Rules / Routing Rules
*   **Description:** A list of rules that map specific request paths to specific backend destinations.
*   **Fields:**
    *   **Path Match:** A glob pattern (e.g., `/images/*`) to match against the request path.
    *   **Backend Host:** The destination host for requests matching this path.
    *   **Host Header:** (Optional) The Host header to send to this backend.
    *   **Path Rewrite:** (Optional) A string to replace the matching path with.
*   **Logic:** The engine checks these rules in order. The first rule that matches the request path determines the next hop. If none match, the "Default Backend Host" is used.

### 4. Custom Headers
*   **Description:** Key-Value pairs of HTTP headers to add or override in the request *before* it is sent to this layer.
*   **Usage:** Use this to simulate headers added by the previous layer (e.g., `X-Forwarded-For`, `CDN-Loop`) or to test specific cache behaviors (e.g., `Pragma: no-cache`).

### 5. Host Overrides
*   **Description:** Allows overriding the `Host` header sent to this layer based on specific path patterns.
*   **Usage:** Useful for testing scenarios where specific paths are routed to different virtual hosts on the same proxy.

### 6. Sibling Nodes (Cache Proxies)
*   **Description:** Defines the individual Cache Proxy instances (nodes) that exist at this layer. You can define multiple nodes (e.g., `Proxy A`, `Proxy B`) to simulate a sharded or load-balanced cache tier.
*   **Fields per Node:**
    *   **Name:** Display name for the node in the graph (e.g., "Varnish A").
    *   **Host URL:** The direct URL/IP to access this specific proxy instance.
    *   **Match Header / Match Value:** **Crucial for Visualization.** These fields determine *which* of the sibling nodes is considered "active" for a given request.

## Routing Logic & Visualization

The Node Graph draws a connection line from the previous layer to **one** specific Cache Proxy node. This visualization represents which proxy "handled" the request.

### How the Active Node is Selected

The code determines the active node by checking the **Node Selection Criteria** defined in each node's configuration:

1.  **Match Header:** The name of an HTTP header to inspect.
2.  **Match Value:** The expected value of that header.

The selection process proceeds as follows:

1.  **Check Previous Response Headers:**
    The engine first looks at the **HTTP Response Headers** received from the *previous* layer (e.g., the Load Balancer).
    *   *Example:* If your Load Balancer returns a header `X-Cache-Shard: shard-a`, and your Cache Proxy node is configured with Match Header `X-Cache-Shard` and Match Value `shard-a`, this node is selected.

2.  **Check Request Host Header (Fallback):**
    If the header is not found in the previous response, AND the configured Match Header is explicitly **`Host`**, the engine checks the **Request Host Header** of the current request.
    *   *Example:* If the Load Balancer routes traffic based on the Host header (e.g., `images.example.com` goes to Cache A, `api.example.com` goes to Cache B), configure Match Header `Host` and Match Value `images.example.com`.

3.  **Default Behavior:**
    If no nodes match the criteria (or if no Match Header is configured), the engine defaults to the **first** defined node in the list.

### Troubleshooting Graph Connections

If the line is not drawing to the right cache proxy:

1.  **Check the "Match Header" Configuration:** Ensure the header name matches exactly what the previous layer returns (or `Host` if routing by request host).
2.  **Check the "Match Value" Configuration:** Ensure the value matches exactly (case-sensitivity may apply).
3.  **Inspect the Previous Layer's Response:** Use the "Analyze" or "Headers" dialog on the *previous* layer node (e.g., Load Balancer) to verify it is actually returning the header you expect to match on. If the Load Balancer isn't returning `X-Cache-Shard`, the matching will fail.
