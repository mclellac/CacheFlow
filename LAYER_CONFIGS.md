# Layer Configuration Options

This document details the configuration options available for each layer type in CacheFlow.

The layer configurations will assist in guiding the request to other infrastructure by modifying the subsequent requests. The Application Backend layer doesn't need any configuration options as it is the last layer, and the layer above it will construct the final URL to HTTP Header inspect.

[] Layers are based on the target DOMAIN added. IE: User configures the domain that points to a CDN then the layers can be added such as CDN, etc.
[] Domain entry is the domain to be initially called and HTTP header inspected.

## 1. CDN (Content Delivery Network)

The CDN layer is the entry point for requests in most configurations.

**Configuration Options:**

* Default Origin: Accepts a domain that will be the default origin - for the next request to be made.
* We need to optionally be able to configure other Origins based on path matching that will be used if the path is matched, the domain for the request could be sent to a completely different origin. If there are no matches or no additional origins configured then the default origin will be used to construct the next HTTP request.
* all Origin configurations (default or additionally added) need to also include an option to specify a Host Header that will be used. This is optional, and only meant for configurations where host headers that are different from the request are needed to correctly route to the right application. If no Host Header is supplied for each possible origin config  (of which there can be many) then it will not be overriden on the next request.

## 2. Cache Proxy (e.g., Varnish, Nginx)

Intermediate caching layers that sit between the CDN and the Application Backend.

**Configuration Options:**

* **Host URL**: The internal hostname or IP of the cache server.
* **Host Overrides**: Rules to override the `Host` header based on path patterns for the next request.
* **Path Match Only**: (Optional) Filter to only process requests matching specific paths.
* **Routing Rules**: Logic to route requests to different backends based on path.

## 3. Load Balancer (e.g., NetScaler, HAProxy)

Distributes traffic to application backends.

**Configuration Options:**

* **Host URL**: The VIP or hostname of the load balancer.
* **Custom Headers**: Any required headers for persistence or routing.
* **Routing Rules**: Path-based routing configuration.

## 4. Application Backend (e.g., Origin, Kubernetes Pod)

* *Note: Application Backends generally do not require routing rules or host overrides as they are the final layer to be requested.*
