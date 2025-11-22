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
- **NO YAML**. Do not use YAML for configuration storage or serialization.
- Complex configuration structures (like layers) should be stored using the `aa{sv}` (array of dictionaries) variant type in GSettings.
- Use `GLib.Variant` to construct data for saving.

### 3. Code Style
- Use `src/` for all python source files.
- Ensure `__gtype_name__` matches the class name in Python and the template class in XML.

## Architecture
- **LayerRow**: Located in `src/layer_widgets.py` and `src/ui/layer_row.ui`. Handles the editing of a single layer.
- **PreferencesWindow**: Manages the list of layers per environment and handles loading/saving to GSettings.
- **HeaderInspector**: Core logic for executing HTTP requests based on the configuration.

## Dependencies
- `requests`
- `dnspython`
- `PyGObject` (gtk4, libadwaita)
- **NO PyYAML**.
