<<<<<<< HEAD
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
=======
project('cacheflow',
          version: '0.1.0',
    meson_version: '>= 1.0.0',
  default_options: [ 'warning_level=2', 'werror=false', ],
)

i18n = import('i18n')
gnome = import('gnome')




subdir('data')
subdir('src')
subdir('po')

gnome.post_install(
     glib_compile_schemas: true,
    gtk_update_icon_cache: true,
  update_desktop_database: true,
)
>>>>>>> main
