project('header-inspector',
  version: '0.1.0',
  meson_version: '>= 0.50.0',
)

gnome = import('gnome')
python = import('python')

py_installation = python.find_installation('python3')

# Compile the GSettings schema
gnome.compile_schemas(depend_files: 'org.example.headerinspector.gschema.xml')

# Install the schema
install_data('org.example.headerinspector.gschema.xml',
  install_dir: get_option('datadir') / 'glib-2.0' / 'schemas'
)

subdir('src')
