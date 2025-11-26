# Layers Configuration

This document outlines the configuration options available for each Layer Type within the CacheFlow application preferences. Understanding these options is key to simulating and analyzing the flow of HTTP requests through your infrastructure.

## Common Layer Options

Every layer, regardless of its type, has the following basic options:

-   **Layer Type**: This dropdown menu determines the fundamental behavior of the layer.
    -   **Options**: `CDN`, `Cache Proxy`, `Load Balancer`.
    -   **Effect**: Selecting a type changes the set of available configuration options below it to those specific to that layer's function.
-   **Provider**: This dropdown selects the specific vendor or technology for the chosen Layer Type.
    -   **Options**: Varies by Layer Type (e.g., `Akamai` for CDN, `Varnish` for Cache Proxy).
    -   **Effect**: This selection allows the Header Analyzer to apply provider-specific knowledge, such as recognizing proprietary headers (e.g., `X-Cache` from Varnish).

## CDN (Content Delivery Network)

A CDN layer acts as the initial entry point for user traffic, routing requests to various origins based on defined rules.

-   **Host URL**: The public-facing domain name that the CDN is responsible for.
    -   **Input**: A fully qualified domain name (e.g., `www.example.com`).
    -   **Effect**: This is the domain that CacheFlow will perform a DNS lookup on to initiate the inspection. It simulates a user accessing this domain.
-   **Default Origin**: This group defines the fallback destination if no specific routing rules match a request.
    -   **Host**: The hostname or IP address of the default origin server.
    -   **Host Header**: The value of the `Host` HTTP header that will be sent to the origin server. This is often different from the origin's actual hostname.
-   **Origin Rules**: These rules allow for routing traffic to different origins based on request characteristics.
    -   **Path Match**: A URL path pattern (e.g., `/api/*`, `/images/`) used to match the request.
    -   **Host**: The hostname or IP address of the origin to use if the `Path Match` is successful.
    -   **Host Header**: The `Host` header to send to the origin specified in the rule.
-   **Custom Headers**: Allows for the addition of static HTTP headers to every request that passes through this layer.

### CDN Request Workflow

1.  CacheFlow initiates a request to the CDN layer's **Host URL**.
2.  The application evaluates the request against the list of **Origin Rules**.
3.  If the request path matches a rule's **Path Match** criteria, the request is forwarded to the **Host** defined in that specific rule. The `Host` header of this outgoing request is set to the rule's **Host Header** value.
4.  If no Origin Rule matches, the request is forwarded to the **Host** defined in the **Default Origin**. The `Host` header is set to the **Default Origin**'s **Host Header** value.
5.  Any **Custom Headers** are added to the request before it is sent to the determined origin.

## Cache Proxy

A Cache Proxy layer sits in front of backend applications to serve cached content and reduce load.

-   **Default Destination**: Defines the primary target for requests that are not served from the cache.
    -   **Host**: The hostname or IP address of the destination server (e.g., a load balancer or an application backend).
    -   **Host Header**: The `Host` header to be sent to the destination.
-   **Backends (Varnish Provider)**: Allows for defining known backend pools. This is primarily for visualization purposes.
    -   **Name**: A descriptive name for the backend (e.g., `api-servers`).
    -   **Application Type**: The type of application hosted on the backend (e.g., `OpenShift`, `AWS`). This adds a visual cue in the node graph.
    -   **Color**: A specific color to use for this backend in the generated graph.
-   **Custom Headers**: Static headers to be added to requests forwarded from this layer.

### Cache Proxy Workflow

1.  A request arrives at the Cache Proxy.
2.  The proxy logic (which is assumed, not simulated in detail) determines whether to serve from cache or forward the request.
3.  If forwarded, the request is sent to the **Host** defined in the **Default Destination**, with the corresponding **Host Header**. The defined Backends are used to enrich the graph visualization if the destination matches a backend definition.
4.  **Custom Headers** are added to the forwarded request.

## Load Balancer

A Load Balancer distributes incoming traffic across multiple backend servers.

-   **Default Destination**: The target for all traffic passing through this layer.
    -   **Host**: The hostname or IP address of the next-hop destination (e.g., a specific application server or another proxy).
    -   **Host Header**: The `Host` header value to send to that destination.
-   **Custom Headers**: Static headers to be added to all requests forwarded from the load balancer.

### Load Balancer Workflow

1.  A request arrives at the Load Balancer.
2.  The Load Balancer forwards the request to the **Host** specified in the **Default Destination**, setting the `Host` header to the configured **Host Header** value.
3.  **Custom Headers** are added before the request is sent.
