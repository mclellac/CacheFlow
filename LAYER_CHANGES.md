# Layer Configuration Changes

## Terminology Updates
- **Origins**: For CDN layers, configurations previously known as "Backends" are now referred to as "Origins".
- **Backends**: For Cache Proxy and Load Balancer layers, the term "Backends" is retained.

## Feature Additions
### CDN Origin Configuration
- **Multiple Origins**: CDN layers now support multiple origin configurations.
- **Domain Matching**: Origins can be routed based on the request domain name (host header) in addition to path matching.
- **Fallback**: A "Default Origin" is configured to handle requests that do not match any specific path or domain rules.

### Routing Logic
- The routing engine has been updated to evaluate domain matches (`domain_matches`) alongside path matches (`path_matches`).
- Rules are evaluated in the order they are defined. The first matching rule (path or domain) determines the next hop.

## UI Updates
- **Layer Row**: Labels dynamically update based on the layer type (e.g., "Default Origin" vs "Default Destination", "Origin Rules" vs "Backend Rules").
- **Origin/Backend Rules**:
    - The rule editor now includes a "Domain Matches" section.
    - Subtitles indicate the count of configured paths and domains.
    - Titles reflect the terminology ("Origin: ..." or "Backend: ...").
