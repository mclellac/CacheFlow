# Improvement Plan

## Todo List

- [x] **Refactor Theme Handling**: Centralize theme logic in `CacheFlowApplication` (src/main.py). `PreferencesWindow` should only update the GSettings key, and `CacheFlowApplication` should listen for changes to the 'theme' setting to update `Adw.StyleManager`.
- [x] **Singleton Window Management**: Ensure `PreferencesWindow` is properly managed. Current implementation creates a new instance on every open. It should either be destroyed on close (to free resources) or reused (singleton pattern).
- [x] **Thread Safety in Inspection**: `Window.do_inspection_thread` accesses `self.settings` (a GObject) from a background thread. GObjects are not thread-safe. Settings should be read in the main thread and passed to the worker thread.
- [x] **Code Cleanup**: Utilize the `version` argument in `main()` to set the application version.
- [x] **Fix SSL Verification with Custom DNS**: The current engine replaces the hostname with the IP address in the URL when using custom DNS. This causes SSL verification to fail (hostname mismatch). Implement a solution that connects to the target IP while preserving the original hostname for SNI and certificate verification.
- [x] **Replace Deprecated Widgets**: `HeaderDialog` uses `Gtk.ListStore` and `Gtk.TreeView`, which are deprecated in GTK4. Replace with `Gtk.ListView` and `Gtk.ColumnView`.
- [x] **Separate UI from Logic**: `Window.process_and_display_results` mixes UI color logic (reading from config) with data processing. Refactor to separate these concerns.
- [x] **Improve Error Handling**: Replace hardcoded error strings with constants or localized strings. Ensure all network exceptions are caught and reported user-friendly.
- [x] **Logging Improvements**: Configure more robust logging, potentially logging to a file or UI console, not just stderr.
- [x] **Refactor `CacheFlowEngine`**: The engine class handles DNS, HTTP requests, and result formatting. Consider splitting DNS resolution into a helper or separate class.
