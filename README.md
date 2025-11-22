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

CacheFlow works by simulating requests to each layer of your web stack based on a fconfiguration. Instead of tracing a single request as it passes through the infrastructure, the application makes a series of independent, targeted requests to endpoints you define for each layer (e.g., CDN, cache, backend).

When you provide a path to inspect, CacheFlow consults the active environment's configuration. For each defined `layer`, it constructs and sends a new HTTP request using that layer's specific `host_url`, `custom_headers`, and `host_overrides`. The responses are then displayed side-by-side, allowing you to compare the headers from each component. The results for each layer are visualized in a node-graph interface, making it easy to see the request flow and compare headers at each step.

This allows you to verify, for example:
-   If your CDN is setting the correct `Cache-Control` headers.
-   If a custom `X-Varnish-Debug` header is being correctly processed by your caching layer.
-   If the `Host` header is being correctly rewritten before hitting your application backend.

## Configuration

Configuration is managed entirely within the Preferences window. The application uses GSettings to store its configuration, which is standard for GNOME applications. You can define layers, custom headers, and other settings for each environment directly within the application's graphical interface.

In the Preferences window, you can configure one or more layers for each environment. Each layer represents a request to be made.

### Configuration Fields

For each layer, you can specify the following:

-   **Name**: (Required) A short, unique name for the layer.
-   **Description**: (Optional) A brief description of what this layer represents.
-   **Host URL**: (Required) The base URL to send the request to. The test path will be appended to this.
-   **Custom Headers**: (Optional) Headers to add to the request for this layer.
-   **Host Overrides**: (Optional) Rules to dynamically change the `Host` header based on the test path.
    -   **Path Pattern**: A glob-style pattern to match against the test path (e.g., `/api/*`).
    -   **Host Header**: The `Host` header to use if the pattern matches.
-   **Path Match Only**: (Optional) A list of glob-style patterns. This layer will only be tested if the test path matches one of these patterns.

### GSettings Configuration Example

While the recommended way to manage configuration is through the application's Preferences window, you can also inspect or modify the settings directly using the `gsettings` command-line tool. The application stores its settings in the `com.github.mclellac.cacheflow` schema.

The configuration for each environment is stored in a separate key. Here's how you might view the configuration for the production environment:

```bash
gsettings get com.github.mclellac.cacheflow config-prod
```

This will return the configuration string for that environment. You can also set it directly. Below is an example of a complete configuration for all environments using `gsettings`.

```bash
# Production Environment
gsettings set com.github.mclellac.cacheflow config-prod '[
  {"name": "CDN", "host_url": "https://www.example.com"},
  {"name": "Backend", "host_url": "http://10.0.1.10", "host_overrides": [{"path_pattern": "*", "host_header": "www.example.com"}]}
]'

# Staging Environment
gsettings set com.github.mclellac.cacheflow config-staging '[
  {"name": "Staging CDN", "host_url": "https://staging.example.com"},
  {"name": "Staging Backend", "host_url": "http://10.0.2.20", "host_overrides": [{"path_pattern": "*", "host_header": "staging.example.com"}]}
]'

# QA and Dev are initially empty
gsettings set com.github.mclellac.cacheflow config-qa '[]'
gsettings set com.github.mclellac.cacheflow config-dev '[]'
```

## Usage

1.  **Open Preferences**: Navigate to the `Preferences` window.
2.  **Select Environment**: Choose an environment tab (e.g., Production, Staging).
3.  **Define Layers**: Configure the layers of your web stack using the UI.
4.  **Set Global Options (Optional)**: In the `Application` page, you can set custom DNS servers.
5.  **Inspect a Path**: In the main window, select your configured environment, enter a path (e.g., `/products/my-product`), and click "Inspect".
6.  **Analyze Results**: The response headers for each configured layer will be displayed in a node graph, showing the status and headers for each request.

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
