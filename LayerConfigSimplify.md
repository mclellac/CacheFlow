# Layer Configuration Simplification Ideas

The current configuration structure allows defining multiple layers of the same type (e.g., "Application Backend") at the top level, which can lead to confusion about execution flow (sequential vs parallel).

Here are some ideas to simplify and clarify the configuration:

## 1. Explicit "Backend Group" Layer Type
Instead of defining multiple separate "Application Backend" layers at the root level, introduce a container layer type (e.g., "Backend Group" or "Application Cluster").

**Structure:**
```yaml
- name: Application Backends
  layer_type: Backend Group
  nodes:
    - name: Ocelot
      host_url: ...
    - name: Account Centre
      host_url: ...
    - name: S3 Static
      host_url: ...
```

**Benefits:**
- Visually groups related backends in the configuration UI.
- Explicitly models them as siblings/alternatives rather than a sequence.
- Reduces clutter in the main layer list.

## 2. Consolidate into "Application Backend" with Nodes
Similar to how "Cache Proxy" layers already support multiple `nodes` (siblings), the "Application Backend" layer could be restricted to a single entry in the main list, with all actual backend applications defined as nodes within it.

**Structure:**
```yaml
- name: Applications
  layer_type: Application Backend
  nodes:
    - name: Ocelot
      host_url: ...
    - name: Account Centre
      host_url: ...
```

**Benefits:**
- Uses existing `nodes` infrastructure.
- Aligns with how Cache Proxy siblings are handled.
- Prevents the user from accidentally creating chained backends when they intend parallel ones.

## 3. Strict Layer Architecture Enforcement
Enforce a strict 4-layer architecture in the UI: CDN -> Load Balancer -> Cache Proxy -> Application Backend.
The user would not be able to "add" new layers to the main list, but only configure the 4 existing slots. The "Application Backend" slot would allow adding multiple backend definitions (nodes).

**Benefits:**
- Eliminates ambiguity about layer order.
- Simplifies the mental model for the user.

## 4. Visual Indication of Routing Logic
In the UI, display routing arrows or conditions next to the layers to show *why* a transition happens.
For example, if the Cache Proxy has a rule "Path /news -> Ocelot", display this explicitly connecting the Cache Proxy layer to the Ocelot node in the configuration view.

## Recommendation
**Option 2** seems the most viable immediate step. We should encourage (or migrate) users to define multiple backend applications as `nodes` within a single "Application Backend" layer, rather than as separate top-level layers. The fix implemented in `src/engine.py` effectively treats consecutive backend layers as if they were Option 2, but making it explicit in the config would be better for clarity.
