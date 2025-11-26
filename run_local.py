#!/usr/bin/env python3

import os
import sys
import runpy
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
    from gi.repository import Gio, GLib

    # Path to the compiled resources in the build directory
    resource_path = project_root / 'build' / 'src' / 'cacheflow.gresource'
    if not resource_path.exists():
        print(f"Error: Resource file not found at {resource_path}")
        print("Please build the project first using 'meson setup build && ninja -C build'")
        sys.exit(1)

    # Load and register the resources
    resource = Gio.Resource.load(str(resource_path))
    Gio.Resource._register(resource)

except (ImportError, ValueError, GLib.Error) as e:
    print(f"FATAL: Could not load GTK/Adwaita. {e}")
    sys.exit(1)

# Run the main application module
runpy.run_module('src.main', run_name='__main__')
