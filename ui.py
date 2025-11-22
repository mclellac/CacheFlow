import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GObject
import threading

from inspector import HeaderInspector

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_title("HTTP Header Inspector")
        self.set_default_size(800, 600)

        # Main content
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        # Header Bar
        header_bar = Adw.HeaderBar()
        main_box.append(header_bar)

        # Content Area
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content_box.set_margin_top(10)
        content_box.set_margin_bottom(10)
        content_box.set_margin_start(10)
        content_box.set_margin_end(10)
        main_box.append(content_box)

        # Config File Selection
        config_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        content_box.append(config_box)

        self.config_entry = Gtk.Entry()
        self.config_entry.set_placeholder_text("Path to config.yaml")
        self.config_entry.set_hexpand(True)
        config_box.append(self.config_entry)

        browse_btn = Gtk.Button(label="Browse")
        browse_btn.connect("clicked", self.on_browse_clicked)
        config_box.append(browse_btn)

        # Test Path Input
        path_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        content_box.append(path_box)

        path_label = Gtk.Label(label="Test Path:")
        path_box.append(path_label)

        self.path_entry = Gtk.Entry()
        self.path_entry.set_placeholder_text("/path/to/test")
        self.path_entry.set_hexpand(True)
        path_box.append(self.path_entry)

        # Run Button
        self.run_btn = Gtk.Button(label="Run Inspection")
        self.run_btn.add_css_class("suggested-action")
        self.run_btn.connect("clicked", self.on_run_clicked)
        content_box.append(self.run_btn)

        # Spinner
        self.spinner = Gtk.Spinner()
        content_box.append(self.spinner)

        # Results Area (Scrolled Window with Text View)
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_vexpand(True)
        content_box.append(scrolled_window)

        self.result_view = Gtk.TextView()
        self.result_view.set_editable(False)
        self.result_view.set_monospace(True)
        self.result_view.set_wrap_mode(Gtk.WrapMode.WORD)
        scrolled_window.set_child(self.result_view)

        # Set default config if exists
        import os
        if os.path.exists("config.yaml"):
            self.config_entry.set_text(os.path.abspath("config.yaml"))

    def on_browse_clicked(self, button):
        file_dialog = Gtk.FileDialog()
        file_dialog.open(self, None, self.on_file_selected)

    def on_file_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                self.config_entry.set_text(file.get_path())
        except Exception as e:
            print(f"Error selecting file: {e}")

    def on_run_clicked(self, button):
        config_path = self.config_entry.get_text()
        test_path = self.path_entry.get_text()

        if not config_path:
            self.append_text("Error: Please select a config file.\n")
            return

        self.result_view.get_buffer().set_text("")
        self.run_btn.set_sensitive(False)
        self.spinner.start()

        # Run in separate thread
        thread = threading.Thread(target=self.run_inspection_thread, args=(config_path, test_path))
        thread.start()

    def run_inspection_thread(self, config_path, test_path):
        try:
            inspector = HeaderInspector(config_path)
            # If test path is empty, use default from config (inspector handles None)
            path_to_use = test_path if test_path else None

            results = inspector.run_inspection(path_to_use)

            # Format results
            output = ""
            for res in results:
                output += f"=== Layer: {res['name']} ===\n"
                if 'description' in res and res['description']:
                    output += f"Description: {res['description']}\n"
                output += f"URL: {res['url']}\n"
                if res.get('sent_host_header'):
                    output += f"Host Override: {res['sent_host_header']}\n"

                if 'error' in res:
                    output += f"ERROR: {res['error']}\n"
                else:
                    output += f"Status: {res['status_code']}\n"
                    output += "Headers:\n"
                    for k, v in res['headers'].items():
                        output += f"  {k}: {v}\n"
                output += "\n" + "-"*40 + "\n\n"

            GObject.idle_add(self.update_ui_success, output)

        except Exception as e:
            GObject.idle_add(self.update_ui_error, str(e))

    def update_ui_success(self, output):
        self.result_view.get_buffer().set_text(output)
        self.run_btn.set_sensitive(True)
        self.spinner.stop()

    def update_ui_error(self, error_msg):
        self.result_view.get_buffer().set_text(f"An error occurred:\n{error_msg}")
        self.run_btn.set_sensitive(True)
        self.spinner.stop()

    def append_text(self, text):
        buffer = self.result_view.get_buffer()
        end_iter = buffer.get_end_iter()
        buffer.insert(end_iter, text)
