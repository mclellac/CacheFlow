gnome = import('gnome')

pkgdatadir = get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'src'

python_sources = [
  '__init__.py',
  'main.py',
  'node_data.py',
  'utils.py',
  'models.py',
]

ui_sources = [
  'ui/__init__.py',
  'ui/window.py',
  'ui/preferences.py',
  'ui/header_dialog.py',
  'ui/layer_widgets.py',
  'ui/layer_strategies.py',
  'ui/ui_utils.py',
  'ui/error_handler.py',
  'ui/cookie_dialog.py',
]

nodegraph_sources = [
  'nodegraph/__init__.py',
  'nodegraph/node_graph.py',
  'nodegraph/graph_renderer.py',
  'nodegraph/graph_gestures.py',
  'nodegraph/graph_utils.py',
  'nodegraph/layout.py',
]

engine_sources = [
  'engine/__init__.py',
  'engine/engine.py',
  'engine/routing.py',
  'engine/dns_adapter.py',
  'engine/inspection_controller.py',
]

analysis_sources = [
  'analysis/__init__.py',
  'analysis/analyzer.py',
  'analysis/knowledge.py',
  'analysis/analysis_dialog.py',
]

export_sources = [
  'export/__init__.py',
  'export/exporters.py',
]

config_sources = [
  'config/__init__.py',
  'config/config_manager.py',
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
py_installation.install_sources(ui_sources, subdir: 'cacheflow/ui')
py_installation.install_sources(nodegraph_sources, subdir: 'cacheflow/nodegraph')
py_installation.install_sources(engine_sources, subdir: 'cacheflow/engine')
py_installation.install_sources(analysis_sources, subdir: 'cacheflow/analysis')
py_installation.install_sources(export_sources, subdir: 'cacheflow/export')
py_installation.install_sources(config_sources, subdir: 'cacheflow/config')
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
  'ui/node_row.ui',
  'ui/add_config_dialog.ui',
  'ui/header_dialog.ui',
  'ui/analysis_dialog.ui',
  'ui/shortcuts.ui',
  'ui/list_item_header.ui',
  'ui/column_item_label.ui',
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
