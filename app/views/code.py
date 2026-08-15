"""Code Editor view — write, edit, and run code on a connected Picoware device."""

import os
import threading
import tkinter.filedialog as fd
import tkinter.messagebox as mb
import tkinter.simpledialog as sd

import customtkinter as ctk

from views import device

EDITOR_FONT = ("Courier New", 13)


class CodeView(ctk.CTkFrame):
    """Editor with Run/Save controls that target a device via mpremote."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._file_path: str | None = None
        self._busy = False
        self._stop_event = threading.Event()

        self._build_ui()
        self._refresh_ports()

    def _build_ui(self) -> None:
        """Build the header, toolbar, editor, and output console."""
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=3)
        self.grid_rowconfigure(3, weight=2)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_toolbar()
        self._build_editor()
        self._build_console()

    def _build_header(self) -> None:
        """Create the title bar with port selector and status."""
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(
            header,
            text="Code Editor",
            font=ctk.CTkFont(size=20, weight="bold"),
            fg_color="transparent",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(header, text="Port:", fg_color="transparent").grid(
            row=0, column=1, padx=(10, 5)
        )
        self.port_var = ctk.StringVar(value="Auto-detect")
        self.port_combo = ctk.CTkComboBox(
            header, values=["Auto-detect"], variable=self.port_var, width=220
        )
        self.port_combo.grid(row=0, column=2)

        ctk.CTkButton(
            header, text="Refresh", command=self._refresh_ports, width=70
        ).grid(row=0, column=3, padx=(5, 0))

        self.status_label = ctk.CTkLabel(
            header, text="Not Connected", fg_color="transparent", text_color="gray"
        )
        self.status_label.grid(row=0, column=4, padx=(10, 0))

    def _build_toolbar(self) -> None:
        """Create file and device action buttons."""
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        bar.grid_columnconfigure(4, weight=1)

        self._new_btn = ctk.CTkButton(bar, text="New", width=60, command=self._new_file)
        self._new_btn.grid(row=0, column=0, padx=(0, 4))

        self._open_btn = ctk.CTkButton(bar, text="Open", width=60, command=self._open_file)
        self._open_btn.grid(row=0, column=1, padx=4)

        self._save_btn = ctk.CTkButton(bar, text="Save", width=60, command=self._save_file)
        self._save_btn.grid(row=0, column=2, padx=4)

        self._save_as_btn = ctk.CTkButton(
            bar, text="Save As", width=70, command=self._save_file_as
        )
        self._save_as_btn.grid(row=0, column=3, padx=4)

        self._run_btn = ctk.CTkButton(bar, text="Run on Device", width=110, command=self._run)
        self._run_btn.grid(row=0, column=5, padx=(10, 4))

        self._stop_btn = ctk.CTkButton(
            bar, text="Stop", width=60, command=self._stop, state="disabled"
        )
        self._stop_btn.grid(row=0, column=6, padx=4)

        self._to_dev_btn = ctk.CTkButton(
            bar, text="Save to Device", width=110, command=self._save_to_device
        )
        self._to_dev_btn.grid(row=0, column=7, padx=4)

        self._list_btn = ctk.CTkButton(
            bar, text="List Files", width=80, command=self._list_files
        )
        self._list_btn.grid(row=0, column=8, padx=4)

    def _build_editor(self) -> None:
        """Create the code editor textbox."""
        frame = ctk.CTkFrame(self)
        frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 5))
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        self.editor = ctk.CTkTextbox(
            frame,
            font=EDITOR_FONT,
            wrap="none",
            activate_scrollbars=True,
        )
        self.editor.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.editor.insert("1.0", "print('Hello Picoware!')\n")

    def _build_console(self) -> None:
        """Create the read-only output console."""
        frame = ctk.CTkFrame(self)
        frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 10))
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        self.console = ctk.CTkTextbox(
            frame,
            font=EDITOR_FONT,
            wrap="word",
            activate_scrollbars=True,
            state="disabled",
        )
        self.console.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

    def _refresh_ports(self) -> None:
        """Scan for serial ports and populate the dropdown."""
        ports = ["Auto-detect"] + device.list_ports()
        self.port_combo.configure(values=ports)

    def _selected_port(self) -> str:
        """Return the selected port, or 'auto' for auto-detect."""
        selected = self.port_var.get()
        return "auto" if selected in ("", "Auto-detect") else selected

    def _console_write(self, text: str) -> None:
        """Append *text* to the output console."""
        self.console.configure(state="normal")
        self.console.insert("end", text)
        self.console.see("end")
        self.console.configure(state="disabled")

    def _on_output(self, text: str) -> None:
        """Queue output from a worker thread onto the UI thread."""
        self.after(0, lambda: self._console_write(text))

    def _set_busy(self, busy: bool) -> None:
        """Enable or disable action buttons while an operation runs."""
        self._busy = busy
        state = "disabled" if busy else "normal"
        self._run_btn.configure(state=state)
        self._save_btn.configure(state=state)
        self._save_as_btn.configure(state=state)
        self._to_dev_btn.configure(state=state)
        self._list_btn.configure(state=state)
        self._stop_btn.configure(state="normal" if busy else "disabled")
        self.status_label.configure(
            text="Running…" if busy else "Not Connected", text_color="gray"
        )

    def _new_file(self) -> None:
        """Clear the editor for a new file."""
        self.editor.delete("1.0", "end")
        self._file_path = None

    def _open_file(self) -> None:
        """Load a local Python file into the editor."""
        path = fd.askopenfilename(
            title="Open Python File",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as exc:
            mb.showerror("Open", f"Could not open file:\n{exc}")
            return
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", content)
        self._file_path = path
        self.status_label.configure(text=os.path.basename(path), text_color="gray")

    def _save_file(self) -> None:
        """Save the editor contents to the current file, or prompt for one."""
        if self._file_path is None:
            self._save_file_as()
            return
        self._write_file(self._file_path)

    def _save_file_as(self) -> None:
        """Prompt for a local path and save the editor contents there."""
        path = fd.asksaveasfilename(
            title="Save Python File",
            defaultextension=".py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")],
        )
        if not path:
            return
        if self._write_file(path):
            self._file_path = path
            self.status_label.configure(text=os.path.basename(path), text_color="gray")

    def _write_file(self, path: str) -> bool:
        """Write the editor contents to *path*. Returns True on success."""
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.editor.get("1.0", "end-1c"))
            return True
        except OSError as exc:
            mb.showerror("Save", f"Could not save file:\n{exc}")
            return False

    def _run(self) -> None:
        """Run the editor contents on the device in a background thread."""
        if self._busy:
            return
        code = self.editor.get("1.0", "end-1c")
        if not code.strip():
            return
        self._set_busy(True)
        self._stop_event = threading.Event()
        self._console_write("--- Run ---\n")
        threading.Thread(
            target=self._run_thread, args=(code, self._selected_port()), daemon=True
        ).start()

    def _run_thread(self, code: str, port: str) -> None:
        """Background: execute *code* on the device."""
        code_ = device.run_script(code, device=port, on_output=self._on_output,
                                  stop_event=self._stop_event)
        self.after(0, self._set_busy, False)
        if code_ == 0:
            self.after(0, lambda: self._console_write("--- Done ---\n"))
        elif self._stop_event.is_set():
            self.after(0, lambda: self._console_write("--- Stopped ---\n"))
        else:
            self.after(0, lambda: self._console_write("--- Failed ---\n"))

    def _stop(self) -> None:
        """Interrupt the running script on the device."""
        self._stop_event.set()
        device.stop_current()

    def _save_to_device(self) -> None:
        """Copy the editor contents to a file on the device."""
        if self._busy:
            return
        code = self.editor.get("1.0", "end-1c")
        if not code.strip():
            return
        default = os.path.basename(self._file_path) if self._file_path else "main.py"
        remote = sd.askstring("Save to Device", "Remote filename:", initialvalue=default)
        if not remote:
            return
        self._set_busy(True)
        self._console_write(f"--- Save to device: {remote} ---\n")
        threading.Thread(
            target=self._save_to_device_thread, args=(code, remote, self._selected_port()),
            daemon=True,
        ).start()

    def _save_to_device_thread(self, code: str, remote: str, port: str) -> None:
        """Background: write *code* to a temp file and copy it to the device."""
        import tempfile

        try:
            with tempfile.NamedTemporaryFile(
                "w", suffix=".py", delete=False, encoding="utf-8"
            ) as f:
                f.write(code)
                tmp = f.name
        except OSError as exc:
            self.after(0, lambda: self._console_write(f"Save failed: {exc}\n"))
            self.after(0, self._set_busy, False)
            return
        try:
            _, out = device.save_to_device(tmp, remote, device=port)
        finally:
            os.unlink(tmp)
        self.after(0, lambda: self._console_write(out))
        self.after(0, self._set_busy, False)

    def _list_files(self) -> None:
        """List the device filesystem in the console."""
        if self._busy:
            return
        self._set_busy(True)
        self._console_write("--- Device files ---\n")
        threading.Thread(
            target=self._list_files_thread, args=(self._selected_port(),), daemon=True
        ).start()

    def _list_files_thread(self, port: str) -> None:
        """Background: fetch the device file listing."""
        _, out = device.list_files(device=port)
        self.after(0, lambda: self._console_write(out))
        self.after(0, self._set_busy, False)
