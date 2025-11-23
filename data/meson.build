schema_dir = get_option('datadir') / 'glib-2.0' / 'schemas'
absolute_schema_dir = get_option('prefix') / schema_dir

install_data(
  'com.github.mclellac.CacheFlow.gschema.xml',
  install_dir: schema_dir
)

meson.add_install_script('glib-compile-schemas', absolute_schema_dir)