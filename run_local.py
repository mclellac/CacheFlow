#!/usr/bin/env python3

import os
import sys
import runpy
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Try to import gi, and fall back to system site-packages if missing
# This helps when running in a venv that doesn't have PyGObject installed
try:
    import gi
except ImportError:
    for path in ['/usr/lib/python3/dist-packages', '/usr/lib64/python3/site-packages']:
        if os.path.exists(path) and path not in sys.path:
            sys.path.append(path)

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
    try:
        resource = Gio.Resource.load(str(resource_path))
        Gio.Resource._register(resource)
    except GLib.Error as e:
        print(f"FATAL: Failed to load application resources. {e}")
        sys.exit(1)

except (ImportError, ValueError) as e:
    print(f"FATAL: Could not load GTK/Adwaita. {e}")
    print("Please ensure libadwaita and python3-gi are installed.")
    sys.exit(1)

# Run the main application module
runpy.run_module('src.main', run_name='__main__')
