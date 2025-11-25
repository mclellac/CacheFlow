# Application Audit Report

This document outlines the findings from the codebase audit, categorizing issues into Code Quality, UI/UX, Architecture, and Compliance.

## 1. Critical Bugs & Issues

- [x] Some GTK Buttons not using Adw.ButtonContent - LIBADWAITA IS TO BE USED ALWAYS OVER JUST GTK! <https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1.7/class.ButtonContent.html>
- [x] **Empty UI File**: `src/ui/window.ui` is a 0-byte file. It appears unused as `src/window.py` uses `src/ui/main.ui`, but it should be removed or populated to avoid confusion.
- [x] **Hardcoded Widget Creation**: `src/ui_utils.py` and `src/header_dialog.py` create widgets (e.g., `Gtk.Box`, `Gtk.Label`) directly in Python code within factory setup methods. This violates `AGENTS.md` Rule #1 ("ALL UI layout... must reside in src/ui/ as XML templates").
  * *Recommendation*: Create simple XML templates (e.g., `list_item_header.ui`, `column_item_label.ui`) and use `Gtk.Builder` or wrapper classes with `@Gtk.Template` to instantiate them in the factories.

## 2. Refactoring & Code Quality

- [x] **`src/layer_widgets.py` Duplication**: The classes `HeaderRow`, `OverrideRow`, `PathMatchRow`, and `RoutingRuleRow` share significant boilerplate code (initialization, signal connection, change notification).
  * *Recommendation*: Create a base class `BaseConfigRow` that handles the common signal connections and delete button logic.
- [x] **`src/window.py` Logic**:
  - [x] `on_inspect_clicked` modifies the configuration object in-memory (injecting `entry_point` into the first layer's `host_url`). This mutation is implicit and could lead to state issues.
  - [x] `_on_analyze_requested` relies on list index math (`idx + 1`) to find the upstream layer. This is brittle.
  - [x] *Recommendation*: Move the "Effective Configuration" logic (injecting entry points) into `InspectionController` or `CacheFlowEngine` to keep the UI layer clean.
- [x] **`src/engine.py` Complexity**: The `run_inspection_v2` method is growing large with dynamic routing logic, loop handling, and result processing.
  - [x] *Recommendation*: Extract the "Next Hop Calculation" into a dedicated helper class or method `RouteCalculator` that takes a layer + result and returns the next URL.

## 3. UI/UX Improvements (GNOME HIG / Libadwaita)

- [x] **Header Dialog**: The `HeaderDialog` (`src/header_dialog.py`) uses `Adw.Dialog` but manages its content with a `Gtk.ColumnView`.
  * *Suggestion*: Consolidate the "Analysis" and "Raw View" into a single cohesive interface, or ensure consistent styling. The "Analysis" view uses a rich list (good), while the "Header" view uses columns (functional, but maybe less "Adwaita-ish" for simple key-values).
- [x] **Node Graph**:
  - [x] *Suggestion*: Add Provider Icons (Akamai, Varnish, etc.) to the nodes in `NodeGraph` to verify the "Provider" selection visually.
  - [x] *Suggestion*: Context menus on nodes are mentioned in `REFACTOR.md` but not fully implemented/standardized.
- [x] **Preferences**:
  - [x] The "CNAME" field removal left the code cleaner, but `entry_point` in the GSettings schema is now effectively a duplicate of `domain_name`. Consider future schema migration to remove `entry_point` if it serves no distinct purpose.

## 4. `AGENTS.md` Compliance

- [x] **Rule #1 (UI Separation)**: Violated in `src/ui_utils.py` (`_setup_header_list_item`) and `src/header_dialog.py` (`_on_factory_setup_*`).
- [x] **Rule #3 (Comments)**: Code generally follows the "Docstrings only" rule, but some inline comments exist in `src/engine.py` (e.g., inside `_process_layer_dynamic`).

## 5. File Structure & Organization

- [x] **Unused Files**: `src/ui/window.ui` (empty).
- [x] **Test Location**: There are no tests in `src/tests/` or `tests/`.
  * *Recommendation*: Create a `tests/` directory and add unit tests for `engine.py` (routing logic) and `preferences.py` (persistence).

## 6. Architecture & Systems

* **Providers**: The `src/providers/` system is clean and extensible.
* **Analysis**: `src/analyzer.py` and `src/knowledge.py` are well separated.
- [x] **Dynamic Routing**: The new routing logic in `src/engine.py` is functional but essentially implements a small state machine. Documenting this state flow (Current URL -> Layer Rule -> Next URL) in `DESIGN.md` would be beneficial.

## Summary of Action Items

- [x] **Delete** `src/ui/window.ui`.
- [x] **Refactor** `src/ui_utils.py` and `src/header_dialog.py` to load list items from XML templates.
- [x] **Refactor** `src/layer_widgets.py` to reduce boilerplate.
- [x] **Clean up** inline comments in `src/engine.py`.
- [x] **Create** unit tests for the new routing engine logic.
- [x] ENSURE LIBADWAITA IS USED OVER ALL FOR UI WIDGETS!
