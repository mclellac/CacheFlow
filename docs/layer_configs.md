# Layer Configuration Guide

This document details all available configuration options for the infrastructure layers in CacheFlow. It explains what each option does, how the inspection engine uses it, and provides examples for common scenarios.

## Table of Contents
1. [Common Settings](#common-settings)
2. [Layer Types & Specifics](#layer-types--specifics)
   - [CDN (Content Delivery Network)](#cdn-content-delivery-network)
   - [Load Balancer](#load-balancer)
   - [Cache Proxy](#cache-proxy)
   - [Application Backend](#application-backend)
3. [Routing & Matching](#routing--matching)
4. [Sibling Nodes](#sibling-nodes)
5. [Configuration Examples](#configuration-examples)

---

## Common Settings

Every layer shares a set of base configuration options.

### General
- **Name**: A friendly name for the layer (e.g., "Akamai Edge", "Varnish Internal"). Used in the graph and reports.
- **Description**: A short description of the layer's purpose.
- **Provider**: The specific technology or vendor (e.g., "Akamai", "Nginx", "AWS", "Varnish").
  - *Usage*: Selecting a provider may pre-populate "Debug Headers" known to expose internal cache states (e.g., `X-Cache`, `X-Varnish`).

### Appearance (Colors)
Each layer allows full color customization for the visualization graph:
- **Header Color**: Background color for the node's title bar.
- **Body Color**: Background color for the node's content area.
- **Text Colors**:
  - **Regular**: Standard text color.
  - **Added**: Color for headers that appear for the first time in this layer (Green).
  - **Removed**: Color for headers present upstream but missing in this layer (Red).
  - **Modified**: Color for headers whose values changed in this layer (Orange).

### HTTP Configuration
- **Custom Headers**: A list of Key-Value pairs to inject into the request sent *to* this layer.
  - *Usage*: Useful for adding authentication tokens (`Authorization`), debug flags (`Pragma: akamai-x-cache-on`), or forcing specific behaviors.
- **Host Overrides**: A mapping of "Path Pattern" -> "Host Header".
  - *Usage*: If a request matches the path pattern (e.g., `/api/*`), the `Host` header sent to this layer is forced to the specified value (e.g., `api.internal.svc`).

---

## Layer Types & Specifics

### CDN (Content Delivery Network)
Represents the public entry point of your infrastructure.
- **Origins**: A list of backend rules defining where the CDN forwards traffic.
- **Default Origin Host**: The fallback hostname if no specific routing rules match.
- *Hidden Fields*: `Host URL` is hidden because the CDN typically uses the global `Entry Point` (Domain Name) of the configuration.

### Load Balancer
Represents a traffic distributor (e.g., Nginx, HAProxy, AWS ALB).
- **Hostname**: The DNS name or IP of the load balancer itself (e.g., `lb-public.example.com`).
- **Target Pools**: Groups of downstream nodes (usually Cache Proxies or Backends) that traffic is routed to.
- **Default Target Host**: The fallback destination.

### Cache Proxy
Represents an internal caching layer (e.g., Varnish, Squid).
- **Nodes**: One or more sibling proxy instances.
- **Cache Rules**: Logic to determine which sibling handles the request (e.g., based on consistent hashing of a header).
- **Default Origin Server**: The upstream application server this proxy talks to.

### Application Backend
Represents the final origin server (e.g., Web Server, App Server, S3 Bucket).
- **Application Server Address**: The final destination URL (e.g., `https://app-node-01.internal`).
- *Note*: This layer typically does not have "Routing Rules" as it is the terminus of the request chain.

---

## Routing & Matching

CacheFlow uses a flexible routing engine to simulate how traffic moves through your stack.

### Path Matching
- **Path Pattern**: Glob-style patterns (e.g., `/static/*`, `*.jpg`).
- **Path Match Only (Layer Level)**: If configured, the entire layer is **skipped** unless the request path matches one of these patterns.

### Routing Rules (Next Hop)
Defined within "Origins" (CDN) or "Target Pools" (LB/Proxy).
- **Backend Host**: The hostname/URL of the next layer to contact.
- **Backend Host Header**: The `Host` header to send to that next layer.
- **Path Match**: Only apply this rule if the path matches (e.g., `/images/*`).
- **Domain Match**: Only apply this rule if the current request's Host header matches (e.g., `static.example.com`).
- **Path Rewrite**: Regex-based rewriting of the URL path before sending to the next layer.
  - *Format*: `s/pattern/replacement/` (e.g., `s|^/api/v1/|/v1/|`).

---

## Sibling Nodes

For layers like **Cache Proxy** or **Load Balancer**, you can define multiple "Sibling Nodes" to represent a cluster.

### Configuration
- **Name**: Node identifier (e.g., "Cache-East", "Cache-West").
- **Host URL**: The specific address of this node.
- **Matching Logic**:
  - **Match Header**: The header name to inspect from the *previous layer's response* (e.g., `X-Served-By`).
  - **Match Value**: The value to look for.
- **Usage**:
  1. The engine sends a request to the previous layer.
  2. It inspects the response headers.
  3. If `X-Served-By: cache-east-01` is present, and a sibling node is configured to match that value, the visualization highlights that specific node as the active path.

---

## Configuration Examples

### Example 1: Standard CDN to Origin
**Scenario**: Simple website served by Akamai, forwarding to a single Nginx origin.

**Layer 1: CDN (Akamai)**
- **Type**: CDN
- **Default Origin Host**: `origin.example.com`
- **Custom Headers**: `Pragma: akamai-x-cache-on` (To enable debug headers)

**Layer 2: Backend (Nginx)**
- **Type**: Application Backend
- **Host URL**: `https://origin.example.com`

---

### Example 2: Microservices Routing (Load Balancer)
**Scenario**: An ALB routes `/api/*` to an API Service and everything else to a Web Service.

**Layer 1: Load Balancer (AWS ALB)**
- **Type**: Load Balancer
- **Hostname**: `alb.example.com`
- **Target Pools**:
  - **Rule A**:
    - **Path Match**: `/api/*`
    - **Backend Host**: `api-internal.example.com`
  - **Rule B**:
    - **Path Match**: `*` (Catch-all implied if no other match, or set as Default Target)
    - **Backend Host**: `web-internal.example.com`

**Layer 2a: API Service**
- **Type**: Application Backend
- **Host URL**: `https://api-internal.example.com`
- **Path Match Only**: `/api/*` (Ensures this layer is only shown/checked for API requests)

**Layer 2b: Web Service**
- **Type**: Application Backend
- **Host URL**: `https://web-internal.example.com`

---

### Example 3: Clustered Varnish with Sharding
**Scenario**: Traffic is distributed across two Varnish nodes based on hashing. We want to see which one served the request.

**Layer 1: Load Balancer**
- **Type**: Load Balancer
- **Default Target Host**: `varnish-cluster.local`

**Layer 2: Varnish Cache**
- **Type**: Cache Proxy
- **Nodes**:
  - **Node 1**:
    - Name: "Varnish-A"
    - Host URL: `http://10.0.0.1`
    - Match Header: `X-Varnish-Server`
    - Match Value: `server-a`
  - **Node 2**:
    - Name: "Varnish-B"
    - Host URL: `http://10.0.0.2`
    - Match Header: `X-Varnish-Server`
    - Match Value: `server-b`

**Note**: When the inspection runs, if the response from the Load Balancer (or previous hop) indicates which Varnish handled it via the `X-Varnish-Server` header, the graph will visually route to that specific node.
