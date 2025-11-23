# Audit Report & Updates

## Improvements & Changes

### UI/UX & Architecture
1.  **Refactor `LayerRow` Widgets**:
    - **Issue**: `src/layer_widgets.py` currently uses `DeletableEntryRow`, a generic Python class that constructs UI widgets (Box, Entry, Button) in code. This violates the `AGENTS.md` rule requiring all UI to be defined in XML templates.
    - **Fix**: Replaced `DeletableEntryRow` with dedicated classes (`HeaderRow`, `OverrideRow`, `PathMatchRow`) that use the existing XML templates (`header_row.ui`, `override_row.ui`, `path_match_row.ui`). This ensures strict separation of UI and logic.

2.  **Refactor `HeaderDialog`**:
    - **Issue**: `src/window.py` defines `HeaderDialog` entirely in Python code.
    - **Fix**: Created `src/ui/header_dialog.ui` and updated `HeaderDialog` to load from this template. This improves maintainability and consistency.

3.  **Application Window Management**:
    - **Issue**: Secondary windows like `PreferencesWindow` should be associated with the `Gtk.Application` instance.
    - **Fix**: Updated `src/main.py` to pass `application=self` when creating `PreferencesWindow`.

### Diff Functionality
- **Issue**: The previous diff logic compared every layer's headers against the *Origin* (the last layer). This made it difficult to see incremental changes (e.g., what a CDN layer added vs. what the Cache layer added).
- **Fix**: Updated the comparison logic in `src/window.py`. Now, each layer is compared against the *next* layer in the chain (its upstream source).
    - If Layer N has a header that differs from Layer N+1 (or Layer N+1 doesn't have it), it is marked as a diff.
    - This clearly highlights modifications introduced at each specific hop.

### Code Maintenance
- **Cleanup**: Removed unused code or simplified complex logic where appropriate.
- **Standards**: Enforced `AGENTS.md` guidelines regarding GSettings types and template usage.

### New Features
- **SSL/TLS Verification**: Added a user preference in `PreferencesWindow` to toggle SSL verification. Updated `src/engine.py` to respect this setting and added `verify-ssl` key to GSettings schema.

## Feature Suggestions
- **Async Inspection**: While the current inspection runs in a thread, `requests` is synchronous. Migrating to `aiohttp` or `httpx` could allow parallel layer inspection (though sequential is often required for flow verification) or better non-blocking behavior.
- **SNI Support**: When inspecting specific IPs (DNS override), `requests` does not send the correct SNI if the URL is modified to use the IP. This can be improved by using a custom transport adapter that forces the IP connection while keeping the hostname in the URL.

## Bugs Fixed
- `DeletableEntryRow` violated architecture rules.
- `PreferencesWindow` was not correctly associated with the application instance in `main.py`.
- **Header Dialog Values**: Fixed an issue where header values were not visible in the dialog. Explicitly bound the cell renderer text property.
- **Layer Text Colors**: Fixed an issue where text and diff text colors were not saved to GSettings, causing them to not persist or apply to the node graph. Added extensive logging to verify data flow.
