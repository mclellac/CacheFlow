# Node Graph Animation Ideas

This document outlines potential animation enhancements for the Node Graph Editor in CacheFlow to improve user experience and visual appeal.

## 1. Node Entry Animation
When the inspection results are loaded and nodes are displayed:
- **Effect:** Nodes should "pop" or "fade" in sequentially from left to right (Client -> CDN -> Origin).
- **Duration:** 200-300ms per layer, with a slight stagger.
- **Benefit:** visually reinforces the flow of traffic and makes the graph update feel less abrupt.

## 2. Connection Line Drawing
When nodes are connected:
- **Effect:** The bezier curves connecting nodes should "draw" themselves from the source node to the destination node.
- **Implementation:** Animate the stroke dash offset or progressively render the path.
- **Benefit:** Clearly shows the direction of traffic flow, which is crucial for understanding the request path.

## 3. Active Path Pulse
To highlight the active request path among sibling nodes:
- **Effect:** The connection lines and node borders of the active path should have a subtle, periodic "pulse" or "glow" effect.
- **Benefit:** Helps the user focus on the relevant nodes when many sibling nodes are visible (e.g., multiple cache proxies).

## 4. Selection Highlight Transition
When a user clicks a node:
- **Effect:** The selection highlight (accent color border/glow) should smoothy transition (fade/scale) from the previously selected node to the new one, or fade in if no node was selected.
- **Benefit:** Provides a smoother, more modern interactive feel.

## 5. Layout Reorganization
When "Reset Layout" is clicked or nodes are automatically repositioned:
- **Effect:** Nodes should slide to their new positions using an ease-in-out interpolation rather than jumping instantly.
- **Benefit:** Helps the user maintain mental context of where nodes are moving.
