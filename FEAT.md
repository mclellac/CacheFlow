 Feature Wishlist & UI Improvements

This document outlines suggested features and improvements to make CacheFlow more accessible to non-technical users ("Management", "Directors") while adhering to GNOME HIG and Libadwaita standards.

## 1. "ELI5" Header Insights (Explain Like I'm 5)

**Goal:** Transform the Analysis tool from a "diff checker" into an "infrastructure consultant".

* **Contextual Explanations:**
  * **Current:** "Header removed." or "Value: private".
  * **Proposed:** Add structured metadata to the Knowledge Base:
    * `Meaning`: "This header tells the browser how long to save this file."
    * `Impact`: "Because this is set to 'private', CDNs cannot cache it. This increases load on your servers."
    * `Recommendation`: "If this image is public, change this to 'public, max-age=3600'."
* **Business Impact Scoring:**
  * Flag issues with specific "Business Impact" badges: `Performance Risk`, `Security Risk`, `Reliability Risk`.
  * Example: A missing `Vary` header on a multilingual site -> "Performance Risk: Users might see the wrong language version."

## 2. Simplified "Director Mode" Configuration

**Goal:** Reduce configuration anxiety by hiding complexity and using plain English.

* **Progressive Disclosure:**
  * Hide "Custom Headers", "Host Overrides", and "Path Match Only" behind an **"Advanced Settings"** expander in each layer.
  * Hide color pickers for "Diff Text" (Added/Removed/Modified) completely. Use theme-aware semantic colors (Green/Red/Orange) automatically.
* **Renamed Concepts:**
  * `Nodes` -> **"Servers"** or **"Instances"**.
  * `Routing Rules` -> **"Traffic Rules"**.
  * `Host Overrides` -> **"Host Header Override"**.
* **Smart Presets (The "I use Akamai" Button):**
  * When adding a layer, offer a **"Load Preset"** button.
  * Presets: "Akamai (CDN)", "Netscalar (Load Balancer)", "Varnish (Reverse Proxy)", "Application (OpenShift)".
  * Loading a preset pre-fills standard headers (like `x-cache-key` or `X-Cache`) and behaviors.

## 3. Visual Rule Builder

**Goal:** Make routing logic understandable without needing to know Regex.

* **Natural Language Rules:**
  * Replace the complex `OriginRuleRow` (Backend Host, Rewrite, Matchers) with a sentence builder:
    * "If path **starts with** `[ /images/ ]` then send to **[ Image Server ]**".
  * Use `Adw.ComboRow` for conditions ("starts with", "equals", "contains").
* **Visual Feedback:**
  * Show a small "preview" chip of a matching URL when a rule is created.

## 4. Interactive Knowledge Base

**Goal:** Educate the user on-demand.

* **Built-in Dictionary:**
  * Add a **"Header Encyclopedia"** accessible from the main menu or via a generic "Help" button.
  * Searchable list of all known headers with their "ELI5" descriptions.
* **Click-to-Explain:**
  * In the Node Graph or Analysis view, clicking any header name should pop up a small `Adw.Popover` with the simplified definition.

## 5. GNOME HIG & UI Polish

**Goal:** Ensure the app feels like a first-class GNOME citizen.

* **Toolbar View Migration:**
  * Migrate the main window to `AdwToolbarView` (libadwaita 1.4+). This allows for better placement of the top bar and potential bottom bars for status.
* **Status Pages:**
  * Use `Adw.StatusPage` for empty states (e.g., "No Configuration Loaded", "No Headers Found").
  * Make these states actionable (e.g., a big "Create Configuration" button in the center).
* **Toast Notifications:**
  * Replace log messages or print statements with `Adw.Toast` for user feedback (e.g., "Configuration Saved", "Export Complete").
* **Refined Layer List:**
  * The `LayerRow` is currently very tall. Consider collapsing the "Nodes" list by default or using a summary row (e.g., "3 Active Nodes") that expands on click.
