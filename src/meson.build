gnome = import('gnome')

pkgdatadir = get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'src'

python_sources = [
  '__init__.py',
  'window.py',
  'engine.py',
  'layer_widgets.py',
  'main.py',
  'node_graph.py',
  'preferences.py',
  'header_dialog.py',
  'dns_adapter.py',
  'node_data.py',
  'utils.py',
  'exporters.py',
  'knowledge.py',
  'analyzer.py',
  'analysis_dialog.py',
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
cacheflow_conf.set('pythondir', py_installation.get_install_dir())
cacheflow_conf.set('localedir', get_option('prefix') / get_option('localedir'))
cacheflow_conf.set('gi_typelib_path', libadwaita_typelib_dir)

configure_file(
  input: 'cacheflow.in',
  output: 'cacheflow',
  configuration: cacheflow_conf,
  install: true,
  install_dir: get_option('bindir')
)