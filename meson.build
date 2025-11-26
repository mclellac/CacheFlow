project('cacheflow',
          version: '0.1.0',
    meson_version: '>= 1.0.0',
  default_options: [ 'warning_level=2', 'werror=false', ],
)

i18n = import('i18n')
gnome = import('gnome')
python = import('python')

libadwaita_dep = dependency('libadwaita-1', version: '>= 1.2')

deps = [
  dependency('gio-2.0', version: '>= 2.62'),
  dependency('gtk4', version: '>= 4.8'),
  libadwaita_dep
]

py_installation = python.find_installation('python3')

subdir('data')
subdir('src')
subdir('po')

gnome.post_install(
     glib_compile_schemas: true,
    gtk_update_icon_cache: true,
  update_desktop_database: true,
)