"""App Store view — browse, view source, and download Picoware apps."""

import json
import os
import re
import threading
import tkinter.filedialog as fd
import tkinter.messagebox as mb
import urllib.request
from urllib.error import URLError
from urllib.parse import quote

import customtkinter as ctk

API_BASE = "https://www.jblanked.com/picoware/api"
MAX_APPS = 100
UA = "Picoware-Desktop"

PY_KEYWORDS = {
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return",
    "try", "while", "with", "yield",
}

PY_BUILTINS = {
    "abs", "all", "any", "bin", "bool", "bytes", "chr", "complex",
    "dict", "dir", "divmod", "enumerate", "eval", "exec", "filter",
    "float", "format", "frozenset", "getattr", "globals", "hasattr",
    "hash", "hex", "id", "input", "int", "isinstance", "issubclass",
    "iter", "len", "list", "locals", "map", "max", "min", "next",
    "object", "oct", "open", "ord", "pow", "print", "property",
    "range", "repr", "reversed", "round", "set", "setattr", "slice",
    "sorted", "str", "sum", "super", "tuple", "type", "vars", "zip",
    "self", "cls", "__init__", "__name__", "__main__",
}


def _quote_url(url: str) -> str:
    """Percent-encode unsafe characters in *url* while preserving structure."""
    return quote(url, safe=":/?&=#%")


def _http_get_json(url: str) -> dict | None:
    """Fetch *url* and parse the response as JSON. Returns ``None`` on failure."""
    req = urllib.request.Request(_quote_url(url), headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, OSError, json.JSONDecodeError):
        return None


def _http_get_text(url: str) -> str | None:
    """Fetch *url* and return the response body as a string. Returns ``None`` on failure."""
    req = urllib.request.Request(_quote_url(url), headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (URLError, OSError):
        return None


def _http_download(url: str, dest_path: str) -> bool:
    """Download *url* to *dest_path*. Returns ``True`` on success."""
    try:
        req = urllib.request.Request(_quote_url(url), headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as resp:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(resp.read())
        return True
    except (URLError, OSError):
        return False


class SourceViewer(ctk.CTkToplevel):
    """Toplevel window that displays Python source code with syntax highlighting."""

    def __init__(self, master, title: str = "Source Code", source: str = "", **kwargs):
        super().__init__(master, **kwargs)
        self.title(f"Source: {title}")
        self.geometry("860x640")
        self.minsize(400, 300)
        self.after(50, self.lift)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._text = ctk.CTkTextbox(
            self,
            font=("Courier New", 13),
            wrap="none",
            activate_scrollbars=True,
        )
        self._text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self._text.tag_config("keyword", foreground="#569CD6")
        self._text.tag_config("string", foreground="#CE9178")
        self._text.tag_config("comment", foreground="#6A9955")
        self._text.tag_config("number", foreground="#B5CEA8")
        self._text.tag_config("builtin", foreground="#DCDCAA")
        self._text.tag_config("decorator", foreground="#C586C0")
        self._text.tag_config("self", foreground="#569CD6")

        if source:
            self.set_source(source)

    def set_source(self, source: str) -> None:
        """Load *source* into the viewer and apply highlighting."""
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.insert("1.0", source)
        self._apply_highlighting()
        self._text.configure(state="disabled")

    def _apply_highlighting(self) -> None:
        """Apply Python syntax highlighting tags to the text widget."""
        content = self._text.get("1.0", "end-1c")
        length = len(content)

        protected = [False] * (length + 1)

        for match in re.finditer(
            r'("""[\s\S]*?""")|(\'\'\'[\s\S]*?\'\'\')', content
        ):
            s, e = match.start(), match.end()
            for i in range(s, e):
                protected[i] = True
            self._text.tag_add("string", f"1.0+{s}c", f"1.0+{e}c")

        for match in re.finditer(r"#.*$", content, re.MULTILINE):
            s, e = match.start(), match.end()
            if not any(protected[s:e]):
                for i in range(s, e):
                    protected[i] = True
                self._text.tag_add("comment", f"1.0+{s}c", f"1.0+{e}c")

        for match in re.finditer(
            r'(?<!\\)"(?:[^"\\\n]|\\.)*"|(?<!\\)\'(?:[^\'\\\n]|\\.)*\'',
            content,
        ):
            s, e = match.start(), match.end()
            if not any(protected[s:e]):
                for i in range(s, e):
                    protected[i] = True
                self._text.tag_add("string", f"1.0+{s}c", f"1.0+{e}c")

        for match in re.finditer(r"@\w+", content):
            s, e = match.start(), match.end()
            if not any(protected[s:e]):
                self._text.tag_add("decorator", f"1.0+{s}c", f"1.0+{e}c")

        for match in re.finditer(r"\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b", content):
            s, e = match.start(), match.end()
            if not any(protected[s:e]):
                self._text.tag_add("number", f"1.0+{s}c", f"1.0+{e}c")

        for match in re.finditer(r"\b[a-zA-Z_]\w*\b", content):
            s, e = match.start(), match.end()
            if protected[s]:
                continue
            word = content[s:e]
            if word in PY_KEYWORDS:
                self._text.tag_add("keyword", f"1.0+{s}c", f"1.0+{e}c")
            elif word in PY_BUILTINS:
                self._text.tag_add("builtin", f"1.0+{s}c", f"1.0+{e}c")


class StoreView(ctk.CTkFrame):
    """App Store view with app listing, source viewing, and download support."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._apps: list[dict] = []
        self._selected_app_id: int | None = None
        self._selected_details: dict | None = None
        self._fetch_lock = threading.Lock()

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the store layout: header, sidebar list, and detail panel."""
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        self._build_header()
        self._build_sidebar()
        self._build_detail_panel()

    def _build_header(self) -> None:
        """Create the top bar with title and refresh button."""
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 5))

        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(
            header,
            text="App Store",
            font=ctk.CTkFont(size=20, weight="bold"),
            fg_color="transparent",
        ).grid(row=0, column=0, sticky="w")

        self._refresh_btn = ctk.CTkButton(
            header, text="Refresh", command=self._refresh, width=90
        )
        self._refresh_btn.grid(row=0, column=1, sticky="e")

        self._status_label = ctk.CTkLabel(
            header,
            text="",
            fg_color="transparent",
            text_color="gray",
        )
        self._status_label.grid(row=0, column=1, sticky="e", padx=(0, 100))

    def _build_sidebar(self) -> None:
        """Create the scrollable app list on the left."""
        sidebar = ctk.CTkFrame(self, width=280, fg_color="transparent")
        sidebar.grid(row=1, column=0, sticky="ns", padx=(10, 5), pady=(0, 10))
        sidebar.grid_propagate(False)

        sidebar.grid_rowconfigure(0, weight=1)
        sidebar.grid_columnconfigure(0, weight=1)

        self._list_frame = ctk.CTkScrollableFrame(sidebar, label_text="Apps")
        self._list_frame.grid(row=0, column=0, sticky="nsew")

        self._show_placeholder("Click Refresh to load apps")

    def _build_detail_panel(self) -> None:
        """Create the detail panel on the right."""
        self._detail_panel = ctk.CTkFrame(self, fg_color="transparent")
        self._detail_panel.grid(
            row=1, column=1, sticky="nsew", padx=(5, 10), pady=(0, 10)
        )
        self._detail_panel.grid_rowconfigure(0, weight=1)
        self._detail_panel.grid_columnconfigure(0, weight=1)

        self._detail_placeholder = ctk.CTkLabel(
            self._detail_panel,
            text="Select an app to view details",
            fg_color="transparent",
            text_color="gray",
        )
        self._detail_placeholder.grid(row=0, column=0, sticky="n")

    def _clear_list(self) -> None:
        """Remove all widgets from the app list frame."""
        for w in self._list_frame.winfo_children():
            w.destroy()

    def _show_placeholder(self, text: str) -> None:
        """Display a placeholder message in the sidebar."""
        self._clear_list()
        ctk.CTkLabel(
            self._list_frame, text=text, fg_color="transparent", text_color="gray"
        ).pack(pady=20)

    def _populate_list(self) -> None:
        """Fill the sidebar with app entries."""
        self._clear_list()

        if not self._apps:
            self._show_placeholder("No apps found")
            return

        for app in self._apps:
            entry = ctk.CTkFrame(self._list_frame, fg_color="transparent")
            entry.pack(fill="x", pady=2)

            btn = ctk.CTkButton(
                entry,
                text=app.get("title", "Unknown"),
                anchor="w",
                fg_color="transparent",
                hover_color=("gray75", "gray30"),
                text_color=("gray10", "gray90"),
                command=lambda a=app: self._on_app_selected(a["id"]),
            )
            btn.pack(fill="x")

    def _clear_detail_panel(self, keep_placeholder: bool = False) -> None:
        """Remove widgets from the detail panel, optionally preserving the placeholder."""
        for w in self._detail_panel.winfo_children():
            if keep_placeholder and w is self._detail_placeholder:
                continue
            w.destroy()

    def _show_detail(self, details: dict) -> None:
        """Render app details in the right panel."""
        self._clear_detail_panel()

        title = details.get("title", "Unknown")
        version = details.get("version", "?")
        description = details.get("description", "No description available.")
        authors = details.get("authors", [])
        file_structure = details.get("file_structure", [])
        file_downloads = details.get("file_downloads", [])

        scroll = ctk.CTkScrollableFrame(self._detail_panel, label_text="")
        scroll.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(
            scroll,
            text=f"{title}  v{version}",
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color="transparent",
        ).pack(anchor="w", pady=(5, 2))

        if authors:
            ctk.CTkLabel(
                scroll,
                text=f"by {', '.join(authors)}",
                fg_color="transparent",
                text_color="gray",
            ).pack(anchor="w", pady=(0, 10))

        desc_label = ctk.CTkLabel(
            scroll,
            text=description,
            fg_color="transparent",
            wraplength=380,
            justify="left",
        )
        desc_label.pack(anchor="w", pady=(0, 10))

        ctk.CTkFrame(scroll, height=1, fg_color="gray40").pack(fill="x", pady=5)

        ctk.CTkLabel(
            scroll,
            text="Files",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="transparent",
        ).pack(anchor="w", pady=(5, 2))

        if file_downloads:
            self._build_file_list(scroll, file_downloads)
        elif file_structure:
            self._build_structure_list(scroll, file_structure)
        else:
            ctk.CTkLabel(
                scroll,
                text="No downloadable files listed.",
                fg_color="transparent",
                text_color="gray",
            ).pack(anchor="w")

        ctk.CTkFrame(scroll, height=1, fg_color="gray40").pack(fill="x", pady=10)

        self._build_action_buttons(scroll, details)

    def _build_file_list(
        self, parent: ctk.CTkScrollableFrame, file_downloads: list[dict]
    ) -> None:
        """Build the interactive file list with View/Download per file."""
        for fd_entry in file_downloads:
            path = fd_entry.get("path", "unknown")
            view_url = fd_entry.get("github_url", "")
            size = fd_entry.get("file_size", 0)
            size_str = f" ({size:,} B)" if size else ""

            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=1)

            ctk.CTkLabel(
                row,
                text=f"{path}{size_str}",
                fg_color="transparent",
                anchor="w",
            ).pack(side="left", fill="x", expand=True)

            view_btn = ctk.CTkButton(
                row,
                text="View",
                width=50,
                command=lambda u=view_url, p=path: self._view_source(u, p),
            )
            view_btn.pack(side="right", padx=2)

    def _build_structure_list(
        self, parent: ctk.CTkScrollableFrame, file_structure: list[str]
    ) -> None:
        """Show a plain file list when no download URLs are available."""
        for path in file_structure:
            ctk.CTkLabel(
                parent,
                text=f"  {path}",
                fg_color="transparent",
                anchor="w",
            ).pack(anchor="w")

    def _build_action_buttons(
        self, parent: ctk.CTkScrollableFrame, details: dict
    ) -> None:
        """Create View Source and Download All buttons."""
        file_downloads = details.get("file_downloads", [])

        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(fill="x", pady=(5, 10))

        if file_downloads:
            first = file_downloads[0]
            main_url = first.get("github_url", "")
            main_path = first.get("path", "source.py")

            ctk.CTkButton(
                btn_row,
                text="View Source",
                command=lambda: self._view_source(main_url, main_path),
                width=130,
            ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_row,
            text="Download All",
            command=lambda: self._download_app(details),
            width=130,
        ).pack(side="left")

    def _refresh(self) -> None:
        """Fetch the app list from the API in a background thread."""
        self._refresh_btn.configure(state="disabled")
        self._status_label.configure(text="Loading...")
        self._show_placeholder("Loading apps...")
        self._clear_detail_panel(keep_placeholder=True)
        if not self._detail_placeholder.winfo_exists():
            self._detail_placeholder = ctk.CTkLabel(
                self._detail_panel,
                text="Select an app to view details",
                fg_color="transparent",
                text_color="gray",
            )
            self._detail_placeholder.grid(row=0, column=0, sticky="n")
        self._selected_app_id = None
        self._selected_details = None

        threading.Thread(target=self._fetch_apps_thread, daemon=True).start()

    def _fetch_apps_thread(self) -> None:
        """Background: fetch the list of apps from the API."""
        with self._fetch_lock:
            url = f"{API_BASE}/apps/{MAX_APPS}/0/"
            data = _http_get_json(url)

        if data and data.get("success") and data.get("apps"):
            self._apps = data["apps"]
            self.after(0, self._on_apps_loaded)
        else:
            self.after(0, self._on_apps_failed)

    def _on_apps_loaded(self) -> None:
        """Update UI after successful app list fetch."""
        self._refresh_btn.configure(state="normal")
        self._status_label.configure(text=f"{len(self._apps)} apps loaded")
        self._populate_list()

    def _on_apps_failed(self) -> None:
        """Update UI after failed app list fetch."""
        self._refresh_btn.configure(state="normal")
        self._status_label.configure(text="Failed to load")
        self._show_placeholder("Failed to load apps.\nCheck your connection and try again.")

    def _on_app_selected(self, app_id: int) -> None:
        """Handle app selection — fetch details in the background."""
        self._selected_app_id = app_id
        self._clear_detail_panel()
        ctk.CTkLabel(
            self._detail_panel,
            text="Loading details...",
            fg_color="transparent",
            text_color="gray",
        ).grid(row=0, column=0, sticky="n")

        threading.Thread(
            target=self._fetch_details_thread, args=(app_id,), daemon=True
        ).start()

    def _fetch_details_thread(self, app_id: int) -> None:
        """Background: fetch app details from the API."""
        url = f"{API_BASE}/app/{app_id}/"
        data = _http_get_json(url)

        if data and data.get("success") and data.get("app"):
            self._selected_details = data["app"]
            self.after(0, lambda: self._show_detail(data["app"]))
        else:
            self.after(0, self._on_details_failed)

    def _on_details_failed(self) -> None:
        """Update UI after failed detail fetch."""
        self._clear_detail_panel()
        ctk.CTkLabel(
            self._detail_panel,
            text="Failed to load app details.",
            fg_color="transparent",
            text_color="gray",
        ).grid(row=0, column=0, sticky="n")

    def _view_source(self, url: str, path: str) -> None:
        """Fetch source from *url* and open in a SourceViewer window."""
        if not url:
            mb.showwarning("View Source", "No source URL available for this file.")
            return

        self._status_label.configure(text="Fetching source...")

        def _fetch_and_show() -> None:
            source = _http_get_text(url)
            if source is not None:
                filename = os.path.basename(path) or "source.py"
                self.after(0, lambda: SourceViewer(self, title=filename, source=source))
                self.after(0, lambda: self._status_label.configure(text=""))
            else:
                self.after(
                    0,
                    lambda: mb.showerror(
                        "View Source", "Failed to fetch source code."
                    ),
                )
                self.after(0, lambda: self._status_label.configure(text=""))

        threading.Thread(target=_fetch_and_show, daemon=True).start()

    def _download_app(self, details: dict) -> None:
        """Download all app files to a user-chosen directory."""
        file_downloads = details.get("file_downloads", [])
        if not file_downloads:
            mb.showinfo("Download", "No files available to download.")
            return

        dest_dir = fd.askdirectory(title="Select download folder")
        if not dest_dir:
            return

        app_title = details.get("title", "app").replace(" ", "_")
        app_dir = os.path.join(dest_dir, app_title)

        self._refresh_btn.configure(state="disabled")
        self._status_label.configure(text="Downloading...")

        def _pick_url(entry: dict) -> str:
            """Return the best available download URL for an entry."""
            for key in ("github_url", "download_url"):
                url = entry.get(key, "")
                if url and url.startswith("http"):
                    return url
            return ""

        def _download_all() -> None:
            failed: list[str] = []
            for entry in file_downloads:
                url = _pick_url(entry)
                path = entry.get("path", "")
                if not url or not path:
                    if path:
                        failed.append(path)
                    continue
                dest = os.path.join(app_dir, path)
                if not _http_download(url, dest):
                    failed.append(path)

            self.after(0, lambda: self._on_download_complete(app_dir, failed))

        threading.Thread(target=_download_all, daemon=True).start()

    def _on_download_complete(self, app_dir: str, failed: list[str]) -> None:
        """Update UI after download completes."""
        self._refresh_btn.configure(state="normal")
        self._status_label.configure(text="Download complete")
        if failed:
            mb.showwarning(
                "Download",
                f"Downloaded to:\n{app_dir}\n\nFailed files ({len(failed)}):\n"
                + "\n".join(failed),
            )
        else:
            mb.showinfo("Download", f"All files downloaded to:\n{app_dir}")


