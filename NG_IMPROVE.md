# Node Graph & Dialog Improvements

This document outlines the audit findings and suggested improvements for the Node Graph editor and associated dialogs in CacheFlow.

## Audit Findings

### Node Graph (`src/node_graph.py`)
- **Rendering**: Uses `Gtk.DrawingArea` with Cairo for manual rendering. This provides flexibility but requires manual handling of all interactions and accessibility.
- **Performance**: The entire graph is redrawn on every frame during drag/resize operations. For the expected small number of nodes (CDN layers), this is acceptable, but could be optimized (e.g., using `Gtk.Snapshot` or caching surfaces) if the graph grows.
- **Layout**: Nodes are automatically positioned linearly. There is no support for branching or alternative layouts.
- **Interactions**: Dragging and resizing are manually implemented using gesture controllers. The logic is sound but tightly coupled to the drawing code.
- **Data Passing**: The `node-double-clicked` signal passes an ad-hoc python object (`NodeData` class defined inline). This should be formalized.
- **Accessibility**: The graph is opaque to screen readers.

### Header Dialog (`src/header_dialog.py`)
- **Diff Logic**: Currently indicates differences solely by bolding the text. It compares the current layer against the *next* layer in the list (upstream).
- **UI**: Uses `Gtk.ColumnView` which is modern and efficient.
- **Copying**: Supports context menu copying.

## Suggested Improvements

### 1. Detailed Diff Information (High Priority)
**Request**: Add a column to the header dialogs to note changed or set headers.
**Implementation**:
- Modify `Window._compare_headers` to generate descriptive notes (e.g., "Changed from 'X' at Origin").
- Update `HeaderDialog` to include a "Notes" column.
- Update `HeaderItem` to store this note.

### 2. Search and Filtering
Add a search entry to the `HeaderDialog` to allow users to quickly find specific headers (e.g., "cache-control", "x-amz").

### 3. Graph Export
Add functionality to export the rendered graph as an image file (PNG) or vector (SVG). This would be useful for documentation or sharing inspection results.

### 4. Layout Management
- **Reset Layout**: Add a button to reset node positions to the default linear arrangement.
- **Auto-Snap**: Implement grid snapping for cleaner manual layout.

### 5. Zoom and Pan
Implement a viewport system to allow zooming in/out and panning the graph canvas, enabling support for larger/more complex graphs.

### 6. Refactoring
- **Node Data Model**: Define a proper `GObject` or Python dataclass for `NodeData` to improve type safety and clarity when passing data between the graph and the window.
- **Theme Handling**: Ensure all colors (including diff/node colors) strictly follow the system theme (Light/Dark) or user preferences, avoiding hardcoded fallbacks where possible.

### 7. Accessibility
Explore implementing `Gtk.Accessible` for the Node Graph to expose nodes as navigable elements to assistive technologies.
