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
  'inspection_controller.py',
  'routing.py',
  'models.py',
  'config_manager.py',
  'graph_utils.py',
  'graph_renderer.py',
  'graph_gestures.py',
]

providers_sources = [
  'providers/__init__.py',
  'providers/base.py',
  'providers/standard.py',
  'providers/akamai.py',
  'providers/varnish.py',
  'providers/netscalar.py',
  'providers/openshift.py',
  'providers/security.py',
  'providers/kubernetes.py',
]

py_installation.install_sources(python_sources, subdir: 'cacheflow')
py_installation.install_sources(providers_sources, subdir: 'cacheflow/providers')

ui_files = files([
  'ui/main.ui',
  'ui/preferences.ui',
  'ui/layer_row.ui',
  'ui/header_row.ui',
  'ui/override_row.ui',
  'ui/path_match_row.ui',
  'ui/origin_rule_row.ui',
  'ui/domain_match_row.ui',
  'ui/add_config_dialog.ui',
  'ui/header_dialog.ui',
  'ui/analysis_dialog.ui',
  'ui/shortcuts.ui',
  'ui/list_item_header.ui',
  'ui/column_item_label.ui',
  'ui/varnish_backend_row.ui',
])

gnome.compile_resources('cacheflow',
  'cacheflow.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
  source_dir: '.',
  c_name: 'cacheflow',
  dependencies: ui_files
)

cacheflow_conf = configuration_data()
cacheflow_conf.set('PYTHON', py_installation.full_path())
cacheflow_conf.set('VERSION', meson.project_version())
cacheflow_conf.set('pkgdatadir', get_option('prefix') / pkgdatadir)
cacheflow_conf.set('pythondir', py_installation.get_install_dir())
cacheflow_conf.set('localedir', get_option('prefix') / get_option('localedir'))

configure_file(
  input: 'cacheflow.in',
  output: 'cacheflow',
  configuration: cacheflow_conf,
  install: true,
  install_dir: get_option('bindir')
)
