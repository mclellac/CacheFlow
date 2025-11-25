# Layer Configuration Options

This document details the configuration options available for each layer type in CacheFlow.

## 1. CDN (Content Delivery Network)

The CDN layer is the entry point for requests in most configurations.

**Configuration Options:**
*   **Host URL**: The domain name (e.g., `www.example.com`).
*   **Custom Headers**: Specific headers to enable debugging or control behavior (e.g., Pragma headers for Akamai).
*   **Routing Rules**: (Optional) If the CDN performs path-based routing to different origins.
*   **Default Backend**: (Optional) Fallback origin if no routing rules match.

## 2. Cache Proxy (e.g., Varnish, Nginx)

Intermediate caching layers that sit between the CDN and the Application Backend.

**Configuration Options:**
*   **Host URL**: The internal hostname or IP of the cache server.
*   **Custom Headers**: Debug headers (e.g., `X-Varnish-Debug`).
*   **Host Overrides**: Rules to override the `Host` header based on path patterns.
*   **Path Match Only**: (Optional) Filter to only process requests matching specific paths.
*   **Routing Rules**: Logic to route requests to different backends based on path.
*   **Default Backend**: Fallback origin.

## 3. Load Balancer (e.g., NetScaler, HAProxy)

Distributes traffic to application backends.

**Configuration Options:**
*   **Host URL**: The VIP or hostname of the load balancer.
*   **Custom Headers**: Any required headers for persistence or routing.
*   **Routing Rules**: Path-based routing configuration.
*   **Default Backend**: Fallback pool/origin.

## 4. Application Backend (e.g., Origin, Kubernetes Pod)

The final destination of the request.

**Configuration Options:**
*   **Host URL**: The internal hostname or IP of the application.
*   **Custom Headers**: (Optional) Headers required for the application to respond correctly.
*   *Note: Application Backends generally do not require routing rules or host overrides as they are the terminal point.*

## Implementation Plan

- [x] Audit `LayerRow` to restrict fields based on `ProviderType`.
- [x] CDN: Show URL, Headers, Routing (if applicable).
- [x] Cache Proxy: Show URL, Headers, Overrides, Path Match, Routing.
- [x] Load Balancer: Show URL, Headers, Routing.
- [x] App Backend: Show URL, Headers ONLY.
- [x] Refactor `AddConfigDialog` to strictly ask for Domain (CNAME is inferred or managed in the first layer options).
