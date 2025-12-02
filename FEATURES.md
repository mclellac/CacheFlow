# Application Audit & Feature Suggestions

## Overview

CacheFlow is a powerful tool for visualizing and debugging HTTP header flows through complex infrastructure. To enhance its capabilities for Network Engineers and SREs troubleshooting HTTP headers, caching, and network issues, the following features are suggested.

## Feature Suggestions

### 1. Request/Response Diffing

**Problem:** Currently, diffs are shown between adjacent layers. Troubleshooting often requires comparing a specific layer (e.g., Origin) directly with the Client layer to see exactly what was lost or changed end-to-end.
**Feature:** Allow users to select any two nodes in the graph and open a "Diff View" side-by-side, independent of their position in the flow.

### 3. Latency Visualization [x]

**Problem:** Network issues are often latency-related, not just header-related.
**Feature:**

* Measure TTFB (Time To First Byte) for each hop during inspection.
* Color-code the connection lines (Green/Yellow/Red) based on latency thresholds.
* Display the latency in milliseconds on the connection label.

### 4. Cookie Jar Analysis [x]

**Problem:** Session issues are frequently caused by `Set-Cookie` attributes (Domain, Path, Secure, SameSite) being stripped or modified.
**Feature:** A dedicated "Cookie Inspector" panel that aggregates all cookies set across all layers, highlighting inconsistencies or security flags (e.g., missing `Secure` on HTTPS).

### 5. HAR (HTTP Archive) Import/Export

**Problem:** Issues often happen intermittently or reported by users. Engineers need to analyze past traffic.
**Feature:**

* **Import:** Allow loading a `.har` file to visualize a past request flow (requires HAR files to contain internal hop data, or multiple HARs).
* **Export:** Export the current inspection result as a standardized HAR file for use in other tools (Chrome DevTools, Charles Proxy).

### 6. CORS Debugger

**Problem:** CORS errors are a common source of frontend breakage.
**Feature:** An automatic analysis of `Access-Control-*` headers.

* Visual warning if `Origin` header in request does not match `Access-Control-Allow-Origin`.
* Check for missing `Access-Control-Allow-Methods` or `Access-Control-Allow-Headers`.

### 7. Header Search & Filter [x]

**Problem:** In complex configurations with dozens of headers, finding a specific custom header (e.g., `X-Custom-Trace-Id`) is tedious.
**Feature:** A search bar in the main view that highlights nodes containing the matching header key or value.

### 9. TLS/SSL Inspection Details

**Problem:** HTTPS termination points and protocol version downgrades can cause issues.
**Feature:** Display TLS version (e.g., TLS 1.2, 1.3) and Cipher Suite on the connection lines or node details. Identify where SSL termination occurs.

### 10. Trace ID Correlation [x]

**Problem:** correlating logs across systems is hard.
**Feature:** Automatically detect common trace headers (`X-Request-ID`, `X-Amzn-Trace-Id`, `b3`) and highlight if the ID changes or is dropped between layers.
