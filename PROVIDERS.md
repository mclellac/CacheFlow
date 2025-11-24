# Provider Configuration Options

This document outlines the available preference options for each layer type and provider.

## Caching Proxy (Varnish)
- [x] **Host URL**: Define the entry point for the cache layer.
- [x] **Custom Headers**: Add specific headers (e.g., debug headers, auth tokens).
- [x] **Host Overrides**: Override the Host header based on path patterns.
- [x] **Path Match Only**: Restrict the layer to process only specific paths.
- [x] **Routing Rules**: Dynamic routing to backends.
    - [x] Path Match (Glob/Wildcard)
    - [x] Backend Host
    - [x] Path Rewrite
- [x] **Default Backend**: Define a default next-hop if no rules match.

## CDN (Akamai)
- [x] **Host URL**: Define the CDN Edge hostname.
- [x] **Custom Headers**: Pragma headers, etc.
- [x] **Host Overrides**: Specific host headers for paths.
- [x] **Routing Rules (Origins)**: Define origin selection logic.
    - [x] Path Match (Glob/Wildcard)
    - [x] Origin Host (Backend Host)
    - [x] Origin Host Header (Host Header for the origin connection)
    - [x] Path Rewrite
- [x] **Default Origin**: The default next layer if no rule matches.

## Load Balancer (Netscaler)
- [x] **Host URL**: VIP address/hostname.
- [x] **Custom Headers**: Debug headers.
- [ ] **Routing Rules**: Content Switching policies.
    - [ ] Path Match
    - [ ] Target Pool/Service
    - [ ] Header manipulation

## Application Backend (OpenShift / Kubernetes)
- [x] **Host URL**: Route/Ingress hostname.
- [x] **Custom Headers**: Application specific headers.
- [x] **Path Match Only**: Filter for specific app contexts.
- [ ] **Context Routing**: Internal routing within the mesh.
