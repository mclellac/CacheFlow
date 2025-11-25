
import os
import sys
import runpy
import subprocess

try:
    import gi
except ModuleNotFoundError:
    print("FATAL: 'gi' module not found.")
    sys.exit(1)

# Set the GI_TYPELIB_PATH
typelib_path = '/usr/lib/x86_64-linux-gnu/girepository-1.0'
if os.path.exists(typelib_path):
    os.environ['GI_TYPELIB_PATH'] = typelib_path
    print(f"Set GI_TYPELIB_PATH to: {typelib_path}")
else:
    print("Warning: Could not determine GI_TYPELIB_PATH.")

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gio, GLib

# Add the project root to the Python path, so 'src' is a package
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Set the GSettings schema directory
schema_dir = os.path.join(project_root, 'build', 'data')
os.environ['GSETTINGS_SCHEMA_DIR'] = schema_dir

# Load the GResource bundle
resource_path = os.path.join(project_root, 'build', 'src', 'cacheflow.gresource')
try:
    resource = Gio.Resource.load(resource_path)
    Gio.Resource._register(resource)
    print(f"Successfully loaded GResource from: {resource_path}")
except GLib.Error as e:
    print(f"FATAL: Failed to load application resources from {resource_path}. {e}")
    sys.exit(1)

# Now that resources are loaded, run the 'src.main' module
print("Starting CacheFlow application...")
runpy.run_module('src.main', run_name='__main__')
print("CacheFlow application finished.")
