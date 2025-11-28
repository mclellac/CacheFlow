# Animation Ideas for Node Graph Editor

## 1. Flowing Data Packets
- **Concept:** Visualize the flow of requests and responses as small "packets" or dots moving along the connection lines between nodes.
- **Direction:**
    - Packets flow from Client -> CDN -> Load Balancer -> Cache Proxy -> Backend during the request phase.
    - Packets flow back from Backend -> Client during the response phase.
- **Color:** Packet color could indicate the status of the request at that stage (e.g., Green for success, Red for error).
- **Speed:** Speed could correlate with latency (if measured), or be constant for a smooth effect.

## 2. Node "Pop-in" and Layout Transition
- **Concept:** When a new inspection result is loaded, instead of instantly snapping to the new layout, nodes animate into position.
- **Entrance:** Nodes could scale up from 0 to 100% size (pop-in).
- **Movement:** If the graph layout is reset or nodes are rearranged, they should slide smoothly to their new coordinates using an easing function (e.g., cubic-bezier).
- **Staggering:** Stagger the appearance of nodes layer by layer (Client first, then CDN, etc.) to mimic the traversal path.

## 3. Active Path Pulse
- **Concept:** The "Active Path" (the specific sequence of nodes that handled the request) should have a subtle, rhythmic pulsing glow.
- **Visuals:** The connection lines and the borders of the active nodes pulse in opacity or width.
- **Purpose:** Highlights the critical path taken by the request, separating it from inactive sibling nodes.

## 4. Selection Highlight Expansion
- **Concept:** When a user clicks a node, the selection ring/glow shouldn't just appear.
- **Animation:** It should expand outward from the node (like a ripple) or trace the border of the node.
- **Feedback:** Provides immediate, satisfying visual feedback for user interaction.

## 5. Connection Line Drawing
- **Concept:** When the graph first loads, connection lines "draw" themselves from source to destination.
- **Implementation:** Animate the stroke dash offset or progressively render the Bezier curve from t=0 to t=1.
- **Effect:** Reinforces the idea of a connected network being established.

## 6. Hover Effects
- **Concept:** When hovering over a node or connection line, scale it up slightly (e.g., 1.05x) or brighten its colors.
- **Connections:** Hovering a connection line could display a floating tooltip that follows the cursor with details (Latency, Protocol).

## 7. Status Code Reaction
- **Concept:** Nodes react visually to the HTTP status code they return.
- **200 OK:** A subtle green pulse or "check" icon animation.
- **4xx/5xx Error:** A shake animation (like a password reject) or a red flash.
- **Caching:** A "flash" effect if a Cache Hit is detected.
