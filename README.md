 # CacheFlow

**A multi-layer HTTP header inspector for debugging complex web stacks.**

CacheFlow is a desktop utility designed to help developers, SREs, and DevOps engineers trace HTTP requests through various layers of their infrastructure, such as CDNs, caching proxies, and application backends. By showing the headers at each step, it simplifies debugging caching behavior, request routing, and header manipulation.

## Features

-   **Multi-Layer Inspection**: Define each step of your request pipeline (CDN, cache, backend) and inspect headers at each point.
-   **Environment Configurations**: Manage separate configurations for Production, Staging, QA, and Dev environments.
-   **Custom DNS Resolution**: Specify custom DNS servers to resolve hosts, bypassing system DNS—perfect for testing against specific data centers or internal services.
-   **Host Header Overrides**: Easily send requests to an IP address or internal hostname while setting the `Host` header to the public-facing domain.
-   **Path-Based Rules**: Apply certain layer inspections or `Host` header overrides only for specific URL path patterns (e.g., `/api/*`).
-   **Custom Headers**: Inject any headers you need for testing, such as debug flags or authentication tokens.
-   **GTK/Adwaita UI**: A clean, modern user interface for managing configurations and viewing results.

## How It Works

CacheFlow takes a YAML configuration that defines a series of "layers". For a given test path, it sends a request to each configured layer and displays the resulting status code and headers.

This allows you to verify, for example:
-   If your CDN is setting the correct `Cache-Control` headers.
-   If a custom `X-Varnish-Debug` header is being correctly processed by your caching layer.
-   If the `Host` header is being correctly rewritten before hitting your application backend.

## Configuration

Configuration is managed in the Preferences window. Each environment (Production, Staging, etc.) has its own YAML configuration.

Here is an example configuration that demonstrates key features:

```yaml
layers:
  - name: 'CDN_Edge'
    description: 'Akamai (External View)'
    host_url: 'https://www.example.com'
    custom_headers:
      Pragma: 'akamai-x-get-request-id, akamai-x-cache-on, akamai-x-cache-key'

  - name: 'Infra_Cache'
    description: 'Varnish (Internal Cache Layer)'
    host_url: 'http://cache.examplefarm.com'
    custom_headers:
      X-Varnish-Debug: 'true'
      X-Origin-Auth: 'secret-token-123'
    host_overrides:
      - path_pattern: '/api/*'
        host_header: 'api-internal.example.com'

  - name: 'Application_Backend_A'
    description: 'Openshift App Backend (mybackend.openshift.app.com)'
    host_url: 'https://mybackend.openshift.app.com'
    custom_headers: {}
    path_match_only:
      - '/products/*'
      - '/api/v1/*'
```

### Configuration Fields

Each item under `layers` is a request to be made.

-   `name`: (Required) A short, unique name for the layer.
-   `description`: (Optional) A brief description of what this layer represents.
-   `host_url`: (Required) The base URL to send the request to. The test path will be appended to this.
-   `custom_headers`: (Optional) A dictionary of headers to add to the request for this layer.
-   `host_overrides`: (Optional) A list of rules to dynamically change the `Host` header based on the test path.
    -   `path_pattern`: A glob-style pattern to match against the test path (e.g., `/api/*`).
    -   `host_header`: The `Host` header to use if the pattern matches.
-   `path_match_only`: (Optional) A list of glob-style patterns. This layer will only be tested if the test path matches one of these patterns.

## Usage

1.  **Configure**: Go to `Preferences` and select an environment tab (e.g., Production).
2.  **Define Layers**: Edit the YAML to define the layers of your web stack.
3.  **Set DNS (Optional)**: In `Preferences -> General`, add a comma-separated list of DNS server IPs if you need custom name resolution.
4.  **Inspect**: In the main window, choose the environment, enter a path to test (e.g., `/products/my-product`), and click "Inspect".
5.  **Analyze**: The results for each layer will be displayed, showing the status, headers, and the exact URL that was requested.

## Dependencies

This application is built with Python and GTK4.

-   **Python Libraries**:
    -   `PyGObject` (for GTK4 & Adwaita bindings)
    -   `requests`
    -   `dnspython`
-   **System Libraries**:
    -   GTK4
    -   libadwaita

It is primarily designed for Linux desktop environments, but should also be cross-platform and work on macOS.
