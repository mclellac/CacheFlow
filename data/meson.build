pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())

# GSettings Schema
install_data('com.github.mclellac.CacheFlow.gschema.xml',
  install_dir: join_paths(get_option('datadir'), 'glib-2.0', 'schemas')
)

# Desktop File
i18n.merge_file(
  input: 'com.github.mclellac.CacheFlow.desktop.in',
  output: 'com.github.mclellac.CacheFlow.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)

# Icon
install_data('icons/hicolor/scalable/apps/com.github.mclellac.CacheFlow.svg',
  install_dir: join_paths(get_option('datadir'), 'icons/hicolor/scalable/apps')
)