# Layer Configurations

This document outlines the available configuration options for each layer in a domain configuration.

## General Options

These options are available for all layer types.

- `name`: (String) The display name of the layer.
- `description`: (String) A description of the layer.
- `layer_type`: (String) The type of the layer. Can be `CDN`, `Cache Proxy`, or `Load Balancer`.
- `provider`: (String) The provider of the layer (e.g., `Akamai`, `Varnish`, `Netscalar`).
- `host_url`: (String) The base URL for the layer.
- `default_backend_host`: (String) The default backend host for the layer.
- `default_backend_host_header`: (String) The default backend host header for the layer.
- `header_color`: (String) The color of the header in the node graph (e.g., `rgba(0,0,0,0)`).
- `body_color`: (String) The color of the body in the node graph.
- `text_color`: (String) The color of the text in the node graph.
- `diff_text_color`: (String) The color of the diff text in the node graph.
- `custom_headers`: (Dict) A dictionary of custom headers to add to the request.
- `host_overrides`: (List of Dicts) A list of host header overrides. Each dictionary should have a `path_pattern` and `host_header`.
- `path_match_only`: (List of Strings) A list of path patterns to match. If this list is not empty, the layer will only be processed if the request path matches one of the patterns.
- `routing_rules`: (List of Dicts) A list of routing rules. Each dictionary can have a `path_match`, `backend_host`, `path_rewrite`, and `backend_host_header`.
