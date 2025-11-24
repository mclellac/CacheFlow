# CacheFlow Agent Guide

This document outlines the architectural rules and development guidelines for the CacheFlow project.

## Project Structure

- `src/`: Python source code.
- `src/ui/`: XML UI templates (`.ui` files) for GTK/Libadwaita widgets.
- `data/`: GSettings schema and other data files.

## Development Rules

### 1. UI Separation

**ALL** UI layout and widget definition code must reside in `src/ui/` as XML templates.

- **DO NOT** hardcode widget creation in Python (e.g., `Gtk.Box()`, `Gtk.Entry()`).
- Use `@Gtk.Template` in Python classes to bind to the XML resources.
- Subclass `Adw.Bin`, `Gtk.Box`, `Adw.PreferencesRow`, etc., in Python and link them to a template.

### 2. Configuration & Storage

- The application configuration is stored in **GSettings** using the schema `com.github.mclellac.CacheFlow`.
- Complex configuration structures (like layers) should be stored using the `aa{sv}` (array of dictionaries) variant type in GSettings.
- Use `GLib.Variant` to construct data for saving.

### 3. Code Style & Quality

- Use `src/` for all python source files.
- Ensure `__gtype_name__` matches the class name in Python and the template class in XML.
- Code must be **PEP8 compliant**.
- Code must pass **Pylint** tests without errors.
- **Comments must only be docstrings**. All other comments (e.g., `# inline comments`) are to be removed to ensure the code is self-documenting and clean.

## Architecture

- **`CacheFlowApplication`** (`main.py`): The main application entry point, inheriting from `Adw.Application`. It manages the application lifecycle, global actions (like Preferences and About), and the application-wide theme.

- **`Window`** (`window.py`): The main application window, inheriting from `Adw.ApplicationWindow`. It contains the primary UI elements like the header bar, path entry field, and the `NodeGraph`. It is responsible for initiating inspections and displaying their results.

- **`PreferencesWindow`** (`preferences.py`): A singleton window for managing all application settings, inheriting from `Adw.PreferencesWindow`. It handles loading and saving all configuration data to and from GSettings, including layer definitions and appearance settings like colors.

- **`NodeGraph`** (`node_graph.py`): A custom `Gtk.DrawingArea` widget responsible for all rendering of the node graph. It draws the nodes, text, and connections based on data from an inspection run and color preferences from GSettings. It also handles user interactions like dragging and resizing nodes.

- **`CacheFlowEngine`** (`engine.py`): The core non-UI logic for executing HTTP requests. It takes a configuration object, resolves DNS if necessary, constructs and sends requests for each layer, and returns the results.

- **`LayerRow`** (`layer_widgets.py`): A custom `Adw.ExpanderRow` widget used within the `PreferencesWindow`. It provides the UI for editing the details of a single configuration layer, including its name, URL, headers, and overrides.

## Known Pitfalls & Lessons Learned

This section documents critical bugs encountered during development and their required solutions. These patterns **must** be followed to avoid regressions.

### 1. Meson Build System: GSettings Installation

- **Problem**: Settings were not persistent after installation because the `glib-compile-schemas` command failed silently or with a "No such file or directory" error.
- **Root Cause**: The `meson.add_install_script` command was being passed a relative path. The script requires an absolute path to find the schema directory during installation.
- **Solution**: Always construct an absolute path for the post-install script argument.

  ```meson
  # In data/meson.build
  schema_dir = get_option('datadir') / 'glib-2.0' / 'schemas'
  absolute_schema_dir = get_option('prefix') / schema_dir
  
  install_data('com.github.mclellac.CacheFlow.gschema.xml', install_dir: schema_dir)
  meson.add_install_script('glib-compile-schemas', absolute_schema_dir)
  ```

### 2. GTK/Adwaita: Singleton Window Management

- **Problem**: The `PreferencesWindow` would sometimes become unresponsive and could not be closed after being opened once.
- **Root Cause**: `Adw.PreferencesWindow` (and many other GTK windows) only hides by default when closed, it is not destroyed. The application logic was attempting to re-show a hidden, inconsistent "zombie" window.
- **Solution**: For singleton windows that should be recreated on demand, explicitly set them to be destroyed when closed. This ensures the `destroy` signal is emitted and cleanup logic can run.

  ```python
  # In PreferencesWindow.__init__
  self.set_destroy_with_parent(True)
  ```

### 3. GSettings: `bind_with_mapping` Data Types

- **Problem**: Color preferences were not being loaded into the UI when the preferences window was opened.
- **Root Cause**: A misunderstanding of the data types passed to the mapping functions.
- **Solution**: The mapping functions must handle specific types for each direction:
  - The **`map_get`** function (setting -> widget) **receives a `GLib.Variant`** and must unpack it (e.g., with `.get_string()`).
  - The **`map_set`** function (widget -> setting) **receives a native Python type** (e.g., `Gdk.RGBA`) and **must return a `GLib.Variant`**.

  ```python
  # Correct mapping function signatures
  def setting_to_rgba(variant, _user_data=None):
      rgba_string = variant.get_string()
      # ...
  
  def rgba_to_setting(gdk_rgba, _user_data=None):
      return GLib.Variant('s', gdk_rgba.to_string())
  ```

## Dependencies

- `requests`
- `dnspython`
- `PyGObject` (gtk4, libadwaita)
