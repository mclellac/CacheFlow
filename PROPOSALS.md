# CacheFlow Feature Proposals

The following features are proposed to assist in troubleshooting HTTP headers, Caching, and Network issues.

## 1. HTTP Headers Troubleshooting

### 1.1 Canonical Header Verification
- **Description:** Analyze response headers for non-standard casing (e.g., `content-type` vs `Content-Type`) or duplicate headers that might confuse downstream proxies.
- **Why:** While HTTP/2 enforces lowercase, legacy HTTP/1.1 intermediaries might rely on specific casing.
- **Implementation:** Extend `src/analysis/analyzer.py` to compare keys against a canonical dictionary.

### 1.2 Detailed Cookie Analysis
- **Description:** Visualize and validate `Set-Cookie` attributes (`Secure`, `HttpOnly`, `SameSite`, `Domain`, `Path`).
- **Why:** Misconfigured cookies are a common source of security and session issues.
- **Implementation:** Parse `Set-Cookie` headers in `analyzer.py` and warn if `Secure` is missing on HTTPS, or if `SameSite` is lax/none without `Secure`.

### 1.3 CORS Debugger
- **Description:** Analyze `Access-Control-Allow-*` headers.
- **Why:** CORS errors are frequent and often misunderstood.
- **Implementation:** Check if `Origin` matches `Access-Control-Allow-Origin`, validate `Access-Control-Allow-Methods`, and warn on wildcards with credentials.

### 1.4 Compression Verification
- **Description:** Verify that `Accept-Encoding: gzip, br` actually results in compressed content (`Content-Encoding`).
- **Why:** Uncompressed responses waste bandwidth and increase latency.
- **Implementation:** Modify `src/engine/engine.py` to optionally send compression headers and flag if the response is uncompressed text.

## 2. Caching Troubleshooting

### 2.1 "Why is this not cached?" Logic
- **Description:** A dedicated analysis mode that explicitly lists reasons why a response might be uncacheable (e.g., `Cache-Control: private`, `Vary: *`, `Set-Cookie` present).
- **Why:** Quickly identifying the "cache buster" is critical for performance tuning.
- **Implementation:** Enhance `HeaderAnalyzer` to return a `cacheability_score` and a list of `blockers`.

### 2.2 Stale-While-Revalidate Simulator
- **Description:** Visualize how `stale-while-revalidate` and `stale-if-error` directives would behave.
- **Why:** These complex directives are hard to reason about without simulation.
- **Implementation:** Add logic to `AnalysisReport` to explain the "freshness window" vs "staleness window".

### 2.3 ETag/Last-Modified Validation
- **Description:** Perform a follow-up request using `If-None-Match` or `If-Modified-Since` to verify the server returns `304 Not Modified`.
- **Why:** Ensures that conditional requests are working correctly for bandwidth savings.
- **Implementation:** Add a "Verify 304" button in the `HeaderDialog` that triggers a re-request in `CacheFlowEngine`.

## 3. HTTP Network Issues

### 3.1 Request Timing Waterfall
- **Description:** Break down the request latency into DNS lookup, TCP Connection, TLS Handshake, TTFB, and Content Download.
- **Why:** Helps pinpoint if the slowness is network (TCP/TLS) or application (TTFB).
- **Implementation:** Use `urllib3`'s `trace` or `requests` hooks (or migrate to `httpx` for better async/timing support) in `src/engine/engine.py`.

### 3.2 TLS/SSL Details
- **Description:** Display the negotiated Cipher Suite, TLS Protocol Version (1.2 vs 1.3), and Certificate Expiry.
- **Why:** Debugging legacy client connection issues or expiring certificates.
- **Implementation:** Extract socket info from the underlying `urllib3` connection in `CacheFlowEngine`.

### 3.3 HTTP Version Indicator
- **Description:** Show whether the response was served over HTTP/1.1, HTTP/2, or HTTP/3.
- **Why:** Verifying protocol upgrades.
- **Implementation:** `requests` is limited to HTTP/1.1. Consider adding support for HTTP/2 via `httpx` or similar libraries in the future.

### 3.4 IP Geolocation & ASN
- **Description:** Show the physical location and ISP (ASN) of the resolved IP address.
- **Why:** verify that traffic is being served from the expected geographic region (CDN PoP selection).
- **Implementation:** Integrate a lightweight GeoIP lookup (offline DB or API) in `src/engine/engine.py`.
