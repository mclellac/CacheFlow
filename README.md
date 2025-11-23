# CacheFlow

A GTK application to inspect and visualize HTTP cache headers across a multi-layered infrastructure.

## Overview

CacheFlow helps you understand how HTTP headers, particularly those related to caching (`Cache-Control`, `Expires`, `Pragma`), are processed and transformed as a request passes through different layers of your infrastructure, such as a CDN, a caching proxy, and the origin application.

It provides a node-based graphical interface where each layer is represented as a movable node. This allows you to clearly see the flow of the request and compare the response headers at each step.

## Workflow

1.  **Configure Environments**:
    *   Go to `Preferences`. The application supports multiple environments (e.g., Production, Staging, Dev).
    *   For each environment, you can define the layers of your infrastructure. A layer consists of a name and a base URL.
    *   The layers should be ordered from the outermost (e.g., CDN) to the innermost (e.g., Application Origin).

2.  **Select an Environment**:
    *   Use the environment switcher on the main window's header bar to select the environment you want to inspect (e.g., Production).

3.  **Inspect a Path**:
    *   Enter the path you want to test (e.g., `/products/widget-x`) in the entry field.
    *   Click the "Inspect" button.

4.  **Analyze the Results**:
    *   CacheFlow will send a request to each configured layer for the specified path.
    *   A graph will be displayed, with each node representing a layer in your stack.
    *   Each node shows the HTTP response headers received from that layer.
    *   Headers that are *different* from the subsequent layer are highlighted in green, making it easy to spot where headers are being added, removed, or modified.
    *   You can drag and rearrange the nodes on the canvas to organize the view to your liking.

## Features

*   Visual node-based graph of your infrastructure layers.
*   Side-by-side comparison of HTTP response headers.
*   Highlighting of header differences between layers.
*   Support for multiple, configurable environments.
*   Custom DNS resolver settings.