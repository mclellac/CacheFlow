pkgdatadir = get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'src'

python_sources = [
  'inspector.py',
  'main.py',
  'preferences.py',
  'test_inspector.py',
  'window.py',
]

py_installation.install_sources(python_sources, subdir: 'cacheflow/src')

install_data('ui/window.ui', install_dir: py_installation.get_install_dir() / 'cacheflow/src/ui')
install_data('ui/preferences.ui', install_dir: py_installation.get_install_dir() / 'cacheflow/src/ui')
