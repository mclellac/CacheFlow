pkgdatadir = get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'src'

python_sources = [
  '__init__.py',
  'inspector.py',
  'main.py',
  'preferences.py',
  'test_inspector.py',
  'window.py',
]

py_installation.install_sources(python_sources, subdir: 'cacheflow')

gnome.compile_resources('cacheflow',
  'cacheflow.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

cacheflow_conf = configuration_data()
cacheflow_conf.set('PYTHON', py_installation.full_path())
cacheflow_conf.set('VERSION', meson.project_version())
cacheflow_conf.set('pkgdatadir', get_option('prefix') / pkgdatadir)
cacheflow_conf.set('localedir', get_option('prefix') / get_option('localedir'))

configure_file(
  input: 'cacheflow.in',
  output: 'cacheflow',
  configuration: cacheflow_conf,
  install: true,
  install_dir: get_option('bindir')
)
