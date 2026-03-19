from micropython import const

FILE_BROWSER_VIEWER = const(0)
FILE_BROWSER_MANAGER = const(1)
FILE_BROWSER_SELECTOR = const(2)


class FileBrowser:
    """
    Class to handle file browsing, text editing, and image viewing within Picoware.
    """

    PANE_LEFT = const(0)
    PANE_RIGHT = const(1)

    MODE_NONE = const(0)
    MODE_MKDIR = const(1)
    MODE_RENAME = const(2)
    MODE_COPY_SAME = const(3)

    ACT_NONE = const(0)
    ACT_DELETE = const(1)
    ACT_COPY = const(2)
    ACT_MOVE = const(3)
    ACT_RENAME = const(4)

    OPTIONS_LABELS = ("Hidden Files", "Dir Enter")

    MODE_EDITING = 0
    MODE_MENU = 1

    def __init__(
        self,
        view_manager,
        mode=FILE_BROWSER_SELECTOR,
        start_directory="",
        allowed_extensions=[],
    ):
        """Initialize the file browser."""
        import json
        from picoware.system.vector import Vector

        # Link to system managers
        self._vm = view_manager
        self._mode = mode

        # State tracking and caching
        self._stat_cache = {}
        self._allowed_extensions = allowed_extensions

        # UI overlays
        self._loading = None
        self._is_help_screen = False
        self._show_options = False
        self._show_info = False
        self._needs_redraw = True
        self._opt_idx = 0
        self._info_data = []

        self._context_menu = None
        self._confirm_menu = None

        # Input handling for renaming/creating folders
        self._input_active = False
        self._input_text = ""
        self._input_cursor = 0
        self._cursor_frame = 0
        self._input_mode = self.MODE_NONE
        self._context_target_path = ""
        self._pending_action = self.ACT_NONE
        self._pending_dest_path = ""

        self._is_shift = False
        self._is_caps = False

        # Text Editor and Image Viewer state
        self._is_editing = False
        self._edit_file = ""
        self._edit_unsaved = False
        self._text_editor = None
        self._editor_state = self.MODE_EDITING

        self._is_viewing_image = False
        self._is_viewing_text = False
        self._text_viewer_box = None
        self._image_load_state = 0
        self._image_path = ""
        self._jpeg_vec = Vector(0, 0)
        self._info_box = None

        _start = start_directory if start_directory else "/"

        # Core application state to be saved/loaded
        self._app_state = {
            "left_path": _start,
            "right_path": _start,
            "left_files": [],
            "right_files": [],
            "left_index": 0,
            "right_index": 0,
            "left_top": 0,
            "right_top": 0,
            "active_pane": self.PANE_LEFT,
            "show_hidden": False,
            "dir_menu": False,
            "marked": [],
        }

        # Load user settings if they exist
        try:
            data = self._vm.storage.read(
                "picoware/settings/file_browser_state.json", "r"
            )
            if data:
                loaded = json.loads(data)
                self._app_state.update(
                    {k: loaded.get(k, self._app_state[k]) for k in self._app_state}
                )
                del loaded
            del data
        except Exception as e:
            self._vm.log(f"Failed to load settings: {e}", 2)

        self._app_state["left_path"] = _start
        self._app_state["right_path"] = _start

        if mode in (FILE_BROWSER_VIEWER, FILE_BROWSER_SELECTOR):
            self._app_state["dir_menu"] = False

        self.__refresh_panes()
        self._needs_redraw = True

        draw = self._vm.draw
        self._scale_og = Vector(draw.scale_x, draw.scale_y)
        draw.set_scaling(draw.size.x // 320, draw.size.y // 320, True)

    def __del__(self):
        """Cleanup resources to prevent RAM build-up."""
        if self._loading:
            self._loading.stop()
            del self._loading
            self._loading = None
        if self._context_menu:
            del self._context_menu
            self._context_menu = None
        if self._confirm_menu:
            del self._confirm_menu
            self._confirm_menu = None
        if self._info_box:
            del self._info_box
            self._info_box = None
        if self._text_viewer_box:
            del self._text_viewer_box
            self._text_viewer_box = None
        if self._text_editor:
            del self._text_editor
            self._text_editor = None

        self._app_state = None
        self._stat_cache = None
        self._edit_file = None
        self._info_data = None

        del self._jpeg_vec
        del self._scale_og

    @property
    def directory(self) -> str:
        """Get the current directory path."""
        _dir = (
            self._app_state["left_path"]
            if self._app_state["active_pane"] == self.PANE_LEFT
            else self._app_state["right_path"]
        )
        if _dir.startswith("/sd/"):
            _dir = _dir[3:]
        return _dir

    @property
    def path(self) -> str:
        """Get the current path."""
        act = self._app_state["active_pane"]
        p_dir = (
            self._app_state["left_path"]
            if act == self.PANE_LEFT
            else self._app_state["right_path"]
        )
        f_lst = (
            self._app_state["left_files"]
            if act == self.PANE_LEFT
            else self._app_state["right_files"]
        )
        idx = (
            self._app_state["left_index"]
            if act == self.PANE_LEFT
            else self._app_state["right_index"]
        )

        if len(f_lst) == 0:
            return p_dir

        fname = f_lst[idx]
        _path = f"/{fname}" if p_dir == "/" else f"{p_dir}/{fname}"

        if _path.startswith("/sd/"):
            _path = _path[3:]
        return _path

    @property
    def stats(self) -> dict:
        """Get statistics about the current file."""
        _p = self.path
        _storage = self._vm.storage
        return {
            "directory": self.directory,
            "path": _p,
            "size": _storage.size(_p),
            "type": _p.split(".")[-1] if "." in _p else "unknown",
        }

    def __file_edit(self, path) -> bool:
        """Start editing a text file."""
        ext = path.split(".")[-1].lower() if "." in path else ""
        if ext not in (
            "txt",
            "py",
            "json",
            "csv",
            "md",
            "ini",
            "log",
            "xml",
            "html",
            "conf",
            "sh",
            "bat",
            "yml",
            "yaml",
            "toml",
            "cfg",
            "css",
            "js",
            "h",
            "c",
            "cpp",
            "php",
            "env",
            "gitignore",
            "lua",
            "bas",
            "",
        ):
            self._vm.alert("Unsupported file format.")
            self._needs_redraw = True
            return False

        self._edit_file = path
        self._edit_unsaved = False
        self._editor_state = self.MODE_EDITING
        self._is_shift = False
        self._is_caps = False
        self._is_editing = True
        self._needs_redraw = True

        from picoware.gui.text_editor import TextEditor

        self._text_editor = TextEditor(self._vm)
        data = self._vm.storage.read(path, "r")
        self._text_editor.set_text(data)
        del data

        return True

    def __file_view(self, path) -> None:
        """View a file (image or text) based on its extension."""
        ext = path.split(".")[-1].lower() if "." in path else ""
        if ext in ("jpg", "jpeg", "bmp"):
            self._is_viewing_image = True
            self._image_load_state = 0
            self._image_path = path
            self._needs_redraw = True
        elif ext in (
            "txt",
            "py",
            "json",
            "csv",
            "md",
            "ini",
            "log",
            "xml",
            "html",
            "conf",
            "sh",
            "bat",
            "yml",
            "yaml",
            "toml",
            "cfg",
            "css",
            "js",
            "h",
            "c",
            "cpp",
            "php",
            "env",
            "gitignore",
            "lua",
            "bas",
            "",
        ):
            self._is_viewing_text = True
            self._edit_file = path

            data = self._vm.storage.read(path, "r")

            from picoware.gui.textbox import TextBox

            draw = self._vm.draw
            self._text_viewer_box = TextBox(
                draw,
                0,
                320,
                self._vm.foreground_color,
                self._vm.background_color,
            )
            self._text_viewer_box.set_text(data)
            self._text_viewer_box.refresh()
            del data

            self._needs_redraw = True
        else:
            self._vm.alert("Unsupported file format.")
            self._needs_redraw = True

    def __load_directory_contents(self, path):
        """Load the contents of a directory."""
        items = []
        show_hid = self._app_state.get("show_hidden", False)

        try:
            d_list = self._vm.storage.read_directory(path)
            temp_list = []

            for entry in d_list:
                itm = entry["filename"]
                if itm in (".", "..") or (not show_hid and itm.startswith(".")):
                    continue

                if self._allowed_extensions and not entry["is_directory"]:
                    ext = itm.split(".")[-1].lower() if "." in itm else ""
                    if ext not in self._allowed_extensions:
                        continue

                fp = f"/{itm}" if path == "/" else f"{path}/{itm}"
                is_d = entry["is_directory"]
                self._stat_cache[fp] = (is_d, -1)
                temp_list.append((itm, is_d))

            del d_list

            # Sort by: Folders first, then name
            temp_list.sort(key=lambda x: (not x[1], x[0].lower()))

            items = [x[0] for x in temp_list]
            del temp_list
        except Exception as e:
            self._vm.log(f"Error loading directory contents: {e}", 2)
            items = ["<ERROR>"]

        return [".."] + items if path != "/" else items

    def __loading_run(self, title: str, percentage: float) -> None:
        """Run a loading animation with a title and percentage completion."""
        if percentage >= 1.0:
            if self._loading:
                self._loading.stop()
                del self._loading
                self._loading = None
            return

        if not self._loading:
            from picoware.gui.loading import Loading

            self._loading = Loading(
                self._vm.draw, self._vm.foreground_color, self._vm.background_color
            )

        self._loading.set_text(title)
        self._loading.animate(swap=True)

    def __menu_spawn(self, title: str, items: list):
        """Helper to construct a pop-up context menu overlaid on the main interface."""
        from picoware.gui.menu import Menu

        fg = self._vm.foreground_color
        bg = self._vm.background_color
        sel = self._vm.selected_color
        draw = self._vm.draw
        m = Menu(draw, title, 0, 320, fg, bg, sel, bg)
        for i in items:
            m.add_item(i)
        m.set_selected(0)
        return m

    def __refresh_panes(self) -> None:
        """Refresh the file lists for both panes."""
        self._stat_cache.clear()
        self._app_state["left_files"].clear()
        self._app_state["left_files"] = self.__load_directory_contents(
            self._app_state["left_path"]
        )
        self._app_state["left_index"] = max(
            0,
            min(self._app_state["left_index"], len(self._app_state["left_files"]) - 1),
        )
        self._app_state["right_files"].clear()
        self._app_state["right_files"] = self.__load_directory_contents(
            self._app_state["right_path"]
        )
        self._app_state["right_index"] = max(
            0,
            min(
                self._app_state["right_index"], len(self._app_state["right_files"]) - 1
            ),
        )

    def __render(self) -> None:
        """Draw the UI based on the current state."""
        draw = self._vm.draw
        sw, sh, mx = 320, 320, 160
        color_fg = self._vm.foreground_color
        color_bg = self._vm.background_color
        color_sel = self._vm.selected_color

        # 1. Image Viewer Overlay (State Machine for Loading Animation)
        if self._is_viewing_image:
            if self._image_load_state < 5:
                if not self._loading:
                    from picoware.gui.loading import Loading

                    self._loading = Loading(draw, color_fg, color_bg)
                    self._loading.set_text("Loading Image...")

                self._loading.animate(swap=True)
                self._image_load_state += 1
                self._needs_redraw = True
                return

            if self._image_load_state == 5:
                if self._loading:
                    self._loading.stop()
                    del self._loading
                    self._loading = None

                draw.erase()

                if self._image_path.lower().endswith("bmp"):
                    draw.image_bmp(self._jpeg_vec, self._image_path, self._vm.storage)
                else:
                    if not draw.image_jpeg(
                        self._jpeg_vec, self._image_path, self._vm.storage
                    ):
                        draw._text(10, 30, "Format not supported", color_fg)
                        draw._text(10, 45, "or resolution too large.", color_fg)
                        draw._text(10, 60, "(Must be Baseline JPEG)", color_fg)
                        draw._fill_rectangle(0, sh - 12, sw, 12, color_sel)
                        draw._text(2, sh - 10, "BACK : Close Image", color_bg)

                draw.swap()
                self._image_load_state = 6
                self._needs_redraw = False
                return

            self._needs_redraw = False
            return

        # 1.5 Text Viewer Overlay (Read-Only with Word Wrap)
        if self._is_viewing_text:
            draw._fill_rectangle(0, 0, sw, 20, color_sel)
            draw._text(5, 4, f"View: {self._edit_file.split('/')[-1]}", color_fg)
            draw._fill_rectangle(0, sh - 20, sw, 20, color_sel)
            draw._text(5, sh - 16, "UP/DWN:Scroll   BACK:Close", color_fg)

            if self._text_viewer_box:
                self._text_viewer_box.refresh()
            else:
                draw.swap()
            self._needs_redraw = False
            return

        # 2. Text Editor Overlay
        if self._is_editing:
            if self._text_editor is not None:
                if self._editor_state == self.MODE_MENU:
                    self._context_menu.refresh()
                else:
                    self._text_editor.refresh()
                self._needs_redraw = False
                return

        draw.erase()

        # 3. Help Screen Overlay
        if self._is_help_screen:
            draw._text(10, 5, "--- FILE BROWSER SHORTCUTS ---", color_sel)
            draw._text(10, 20, "[MAIN BROWSER]", color_sel)
            draw._text(10, 32, "UP/DWN:Scroll   L/R:Switch Pane", color_fg)
            draw._text(10, 44, "CENTER:Menu     BACK:Exit App", color_fg)
            draw._text(10, 56, "SPACE:Mark/Sel  D:Delete Marked", color_fg)
            draw._text(10, 68, "N:New Folder    I:File Info", color_fg)
            draw._text(10, 80, "M:Dir Enter Mode", color_fg)
            draw._text(10, 92, "O:Options       H:Toggle Help", color_fg)
            draw._text(10, 108, "[TEXT EDITOR]", color_sel)
            draw._text(10, 120, "Arrows:Cursor   CENTER:Newline", color_fg)
            draw._text(10, 132, "SHF/CAPS:Upper  BSPC:Delete Char", color_fg)
            draw._text(10, 144, "BACK:Menu (Save/Exit/Whitespace)", color_fg)
            draw._text(10, 160, "[TEXT ENTRY & MENUS]", color_sel)
            draw._text(10, 172, "SHF/CAPS:Case   L/R:Move Cursor", color_fg)
            draw._text(10, 184, "CENTER:Confirm  BACK:Cancel", color_fg)
            draw._text(10, 200, "[IMAGE & TEXT VIEWER]", color_sel)
            draw._text(10, 212, "UP/DWN:Scroll   BACK: Close", color_fg)

            draw.swap()
            self._needs_redraw = False
            return

        # 4. File Info Window
        if self._show_info:
            if self._info_box is None:
                from picoware.gui.textbox import TextBox

                self._info_box = TextBox(draw, 0, 320, color_fg, color_bg)

            self._info_box.set_text(self._info_data)
            self._info_box.refresh()
            self._needs_redraw = False
            return

        # 5. Options Menu
        if self._show_options:
            draw._fill_rectangle(10, 10, sw - 20, sh - 20, color_bg)
            draw._rectangle(10, 10, sw - 20, sh - 20, color_sel)
            draw._fill_rectangle(10, 10, sw - 20, 20, color_sel)
            draw._text(15, 14, "OPTIONS MENU", color_sel)
            for i, l in enumerate(self.OPTIONS_LABELS):
                yp = 35 + (i * 15)
                tc = color_sel if i == self._opt_idx else color_fg
                if i == self._opt_idx:
                    draw._fill_rectangle(12, yp - 2, sw - 24, 13, color_bg)
                draw._text(20, yp, l + ":", tc)
                v = ""
                if i == 0:
                    v = "Show" if self._app_state.get("show_hidden", False) else "Hide"
                elif i == 1:
                    v = "Menu" if self._app_state.get("dir_menu", True) else "Open"
                draw._text(130, yp, f"< {v} >", tc)
            draw._fill_rectangle(10, sh - 30, sw - 20, 20, color_sel)
            draw._text(15, sh - 26, "[L/R] Edit   [BACK/ENT] Save", color_bg)
            draw.swap()
            self._needs_redraw = False
            return

        # 6. Text Input Overlay (for renaming/creating)
        if self._input_active:
            by = (sh - 70) // 2
            draw._fill_rectangle(10, by, sw - 20, 70, color_bg)
            draw._rectangle(10, by, sw - 20, 70, color_sel)
            draw._fill_rectangle(10, by, sw - 20, 16, color_sel)

            ts = (
                "RENAME"
                if self._input_mode == self.MODE_RENAME
                else "COPY AS" if self._input_mode == self.MODE_COPY_SAME else "NEW DIR"
            )
            ind = "A" if self._is_caps else ("^" if self._is_shift else "a")

            draw._text(15, by + 2, f"{ts} [{ind}]:", color_bg)
            draw._text(15, by + 24, self._input_text, color_fg)

            self._cursor_frame = (self._cursor_frame + 1) % 16
            if self._cursor_frame < 8:
                draw._fill_rectangle(
                    15 + (self._input_cursor * 6), by + 35, 6, 2, color_fg
                )

            self._needs_redraw = True
            draw._text(15, by + 48, "ENT:Save BACK:Cancel", color_sel)
            draw.swap()
            return

        # 7. Action Menus (Context and Confirmations)
        if self._confirm_menu:
            self._confirm_menu.refresh()
            draw.swap()
            self._needs_redraw = False
            return

        if self._context_menu:
            self._context_menu.refresh()
            draw.swap()
            self._needs_redraw = False
            return

        # 8. Main Dual-Pane Browser View
        draw._fill_rectangle(0, 0, sw, 12, color_sel)
        dm = "Menu" if self._app_state.get("dir_menu", True) else "Open"

        mk_len = len(self._app_state["marked"])
        mk_str = f" [Sel:{mk_len}]" if mk_len > 0 else ""

        draw._text(2, 2, f"File Browser [Dir:{dm}]{mk_str}", color_fg)
        draw._fill_rectangle(mx, 12, 1, sh - 24, color_sel)

        c_lim, n_lim, m_itm = (mx - 8) // 6, ((mx - 8) // 6) - 6, (sh - 38) // 12
        ap = self._app_state["active_pane"]

        storage = self._vm.storage
        for pn in (self.PANE_LEFT, self.PANE_RIGHT):
            il = pn == self.PANE_LEFT
            xb = 0 if il else mx + 1
            ps = self._app_state["left_path"] if il else self._app_state["right_path"]
            fl = self._app_state["left_files"] if il else self._app_state["right_files"]
            ix = self._app_state["left_index"] if il else self._app_state["right_index"]

            top_key = "left_top" if il else "right_top"
            si = self._app_state.get(top_key, 0)

            if ix < si:
                si = ix
            elif ix >= si + m_itm:
                si = ix - m_itm + 1

            self._app_state[top_key] = si

            if ap == pn:
                draw._fill_rectangle(xb, 12, mx - (0 if il else 1), 12, color_sel)
            draw._text(xb + 2, 14, ps[:c_lim], color_fg)

            yo = 26
            for i, fn in enumerate(fl[si : si + m_itm]):
                ai = i + si
                fp = f"/{fn}" if ps == "/" else f"{ps}/{fn}"

                if fn == "..":
                    isd, fz = True, 0
                else:
                    if fp in self._stat_cache:
                        isd, fz = self._stat_cache[fp]
                        if not isd and fz == -1:
                            fz = storage.size(fp)
                            self._stat_cache[fp] = (isd, fz)
                    else:
                        isd = storage.is_directory(fp)
                        fz = storage.size(fp)
                        self._stat_cache[fp] = (isd, fz)

                if ap == pn:
                    if ai == ix:
                        draw._fill_rectangle(
                            xb + (0 if il else 1),
                            yo - 1,
                            mx - (2 if il else 3),
                            10,
                            color_sel,
                        )

                if isd:
                    szs = "<DIR>"
                elif fz < 1024:
                    szs = f"{fz}B"
                elif fz < 1048576:
                    szs = f"{fz//1024}K"
                else:
                    szs = f"{fz//1048576}M"

                mk_char = "*" if fp in self._app_state["marked"] else ""
                dn = f"{mk_char}/{fn}" if isd else f"{mk_char}{fn}"

                pl = max(0, c_lim - len(dn[:n_lim]) - len(szs))
                draw._text(xb + 2, yo, dn[:n_lim] + (" " * pl) + szs, color_fg)
                yo += 12

        draw._fill_rectangle(0, sh - 12, sw, 12, color_sel)
        if self._mode == FILE_BROWSER_SELECTOR:
            draw._text(2, sh - 10, "ENT:Sel M:DirMode O:Opt", color_fg)
        else:
            draw._text(
                2,
                sh - 10,
                "ENT:Menu SPC:Mark N:New M:DirMode O:Opt H:Help",
                color_fg,
            )
        draw.swap()
        self._needs_redraw = False

    def __save_settings(self) -> bool:
        """Save user settings."""
        import json

        try:
            save_dict = {
                k: self._app_state[k]
                for k in [
                    "left_path",
                    "right_path",
                    "active_pane",
                    "show_hidden",
                    "dir_menu",
                    "left_top",
                    "right_top",
                ]
            }
            curr_j = json.dumps(save_dict)
            self._vm.storage.write(
                "picoware/settings/file_browser_state.json", curr_j, "w"
            )
            del curr_j
            return True
        except Exception as e:
            self._vm.log(f"Failed to save settings: {e}", 2)
            return False

    def run(self) -> bool:
        """
        Run the app
        Returns:
            bool: True to continue running, False to exit the app.
        """
        from picoware.system.buttons import (
            BUTTON_NONE,
            BUTTON_UP,
            BUTTON_DOWN,
            BUTTON_LEFT,
            BUTTON_RIGHT,
            BUTTON_CENTER,
            BUTTON_BACK,
            BUTTON_ESCAPE,
            BUTTON_BACKSPACE,
            BUTTON_SPACE,
            BUTTON_D,
            BUTTON_H,
            BUTTON_I,
            BUTTON_M,
            BUTTON_N,
            BUTTON_O,
            BUTTON_SHIFT,
            BUTTON_CAPS_LOCK,
            KEY_MOD_SHL,
            KEY_MOD_SHR,
            KEY_CAPS_LOCK,
        )

        inp = self._vm.input_manager
        btn = inp.button

        if btn is None or btn == BUTTON_NONE:
            if self._needs_redraw:
                self.__render()
            return True

        # --- Sub-View: Image Viewer Input ---
        if self._is_viewing_image:
            if btn in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER):
                inp.reset()
                self._is_viewing_image = False
                self._image_path = ""
                self._needs_redraw = True

        # --- Sub-View: Text Viewer Input ---
        elif self._is_viewing_text:
            if btn in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER):
                inp.reset()
                self._is_viewing_text = False
                if self._text_viewer_box:
                    self._text_viewer_box.clear()
                    del self._text_viewer_box
                    self._text_viewer_box = None
                self._needs_redraw = True
            elif btn == BUTTON_UP:
                inp.reset()
                if self._text_viewer_box:
                    self._text_viewer_box.scroll_up()
            elif btn == BUTTON_DOWN:
                inp.reset()
                if self._text_viewer_box:
                    self._text_viewer_box.scroll_down()

        # --- Sub-View: Text Editor Input ---
        elif (
            self._is_editing
            and self._editor_state == self.MODE_EDITING
            and self._confirm_menu is None
        ):
            if btn in (BUTTON_BACK, BUTTON_ESCAPE):
                inp.reset()
                menu_title = "Unsaved Changes!" if self._edit_unsaved else "Editor Menu"

                self._context_menu = self.__menu_spawn(
                    menu_title, ("Save", "Save & Exit", "Exit", "Cancel")
                )
                self._editor_state = self.MODE_MENU
                self._needs_redraw = True
            elif self._text_editor is not None:
                prev_text_len = len(self._text_editor.current_text)
                self._text_editor.run()
                if len(self._text_editor.current_text) != prev_text_len:
                    self._edit_unsaved = True

        # --- Sub-View: Information Dialog Input ---
        elif self._show_info:
            if btn in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER):
                inp.reset()
                self._show_info = False
                self._info_data = ""
                if self._info_box:
                    del self._info_box
                    self._info_box = None
                self._needs_redraw = True
            elif btn == BUTTON_UP:
                inp.reset()
                if self._info_box:
                    self._info_box.scroll_up()
            elif btn == BUTTON_DOWN:
                inp.reset()
                if self._info_box:
                    self._info_box.scroll_down()

        # --- Sub-View: Text Entry (Rename/Make Folder) Input ---
        elif self._input_active:
            if btn in (BUTTON_BACK, BUTTON_ESCAPE):
                inp.reset()
                self._input_active = False
                self._is_shift = False
                self._is_caps = False
                self._needs_redraw = True
            elif btn == BUTTON_CENTER:
                inp.reset()
                new_name = self._input_text.strip()
                rn = False

                if new_name:
                    td = (
                        self._app_state["left_path"]
                        if self._app_state["active_pane"] == self.PANE_LEFT
                        else self._app_state["right_path"]
                    )
                    np = f"/{new_name}" if td == "/" else f"{td}/{new_name}"

                    storage = self._vm.storage

                    if (
                        self._input_mode in (self.MODE_RENAME, self.MODE_COPY_SAME)
                        and np != self._context_target_path
                    ):
                        if storage.exists(np):
                            self._pending_dest_path = np
                            self._pending_action = (
                                self.ACT_RENAME
                                if self._input_mode == self.MODE_RENAME
                                else self.ACT_COPY
                            )
                            self._confirm_menu = self.__menu_spawn(
                                "Overwrite?", ("No", "Yes")
                            )
                            self._input_active = False
                            self._is_shift = False
                            self._is_caps = False
                            self._needs_redraw = True
                            return True

                        if self._input_mode == self.MODE_RENAME:
                            self.__loading_run("Renaming...", 0.0)
                            if storage.move(self._context_target_path, np):
                                rn = True
                            self.__loading_run("Renamed", 1.0)
                        elif self._input_mode == self.MODE_COPY_SAME:
                            self.__loading_run("Copying...", 0.0)
                            if storage.copy(self._context_target_path, np):
                                rn = True
                            self.__loading_run("Copied", 1.0)
                    elif self._input_mode == self.MODE_MKDIR:
                        if not storage.exists(np):
                            if storage.mkdir(np):
                                rn = True
                if rn:
                    self.__refresh_panes()

                if not self._confirm_menu:
                    self._input_active = False
                    self._is_shift = False
                    self._is_caps = False
                    self._context_target_path = ""
                    self._needs_redraw = True
            elif btn in (BUTTON_SHIFT, KEY_MOD_SHL, KEY_MOD_SHR):
                inp.reset()
                self._is_shift = not self._is_shift
                self._needs_redraw = True
            elif btn in (BUTTON_CAPS_LOCK, KEY_CAPS_LOCK):
                inp.reset()
                self._is_caps = not self._is_caps
                self._is_shift = False
                self._needs_redraw = True
            elif btn == BUTTON_LEFT:
                inp.reset()
                if self._input_cursor > 0:
                    self._input_cursor -= 1
                    self._needs_redraw = True
            elif btn == BUTTON_RIGHT:
                inp.reset()
                if self._input_cursor < len(self._input_text):
                    self._input_cursor += 1
                    self._needs_redraw = True
            elif btn == BUTTON_BACKSPACE:
                inp.reset()
                if self._input_cursor > 0:
                    self._input_text = (
                        self._input_text[: self._input_cursor - 1]
                        + self._input_text[self._input_cursor :]
                    )
                    self._input_cursor -= 1
                    self._needs_redraw = True
            else:
                is_cap = inp.was_capitalized
                inp.reset()
                c = inp.button_to_char(btn)
                if c and len(self._input_text) < 35:
                    if is_cap or self._is_shift or self._is_caps:
                        c = c.upper()
                    self._input_text = (
                        self._input_text[: self._input_cursor]
                        + c
                        + self._input_text[self._input_cursor :]
                    )
                    self._input_cursor += 1
                    if self._is_shift:
                        self._is_shift = False
                    self._needs_redraw = True

        # --- Main File Browser Input: Marking items ---
        elif (
            btn == BUTTON_SPACE
            and not self._is_help_screen
            and not self._show_options
            and self._confirm_menu is None
            and self._context_menu is None
            and not self._input_active
            and not self._show_info
        ):
            inp.reset()
            if self._mode == FILE_BROWSER_MANAGER:
                ap = self._app_state["active_pane"]
                cp = (
                    self._app_state["left_path"]
                    if ap == self.PANE_LEFT
                    else self._app_state["right_path"]
                )
                fl = (
                    self._app_state["left_files"]
                    if ap == self.PANE_LEFT
                    else self._app_state["right_files"]
                )
                ix = (
                    self._app_state["left_index"]
                    if ap == self.PANE_LEFT
                    else self._app_state["right_index"]
                )

                if len(fl) > 0:
                    sf = fl[ix]
                    if sf != "..":
                        fp = f"/{sf}" if cp == "/" else f"{cp}/{sf}"
                        if fp in self._app_state["marked"]:
                            self._app_state["marked"].remove(fp)
                        else:
                            self._app_state["marked"].append(fp)

                        if ap == self.PANE_LEFT:
                            self._app_state["left_index"] = (ix + 1) % len(fl)
                        else:
                            self._app_state["right_index"] = (ix + 1) % len(fl)
                        self._needs_redraw = True

        # --- Main File Browser Input: Hotkeys ---
        elif (
            btn == BUTTON_M
            and not self._is_help_screen
            and not self._show_options
            and self._confirm_menu is None
            and self._context_menu is None
            and not self._input_active
        ):
            inp.reset()
            self._app_state["dir_menu"] = not self._app_state.get("dir_menu", True)
            self._needs_redraw = True

        elif (
            btn == BUTTON_H
            and self._confirm_menu is None
            and self._context_menu is None
            and not self._input_active
            and not self._show_options
        ):
            inp.reset()
            self._is_help_screen = not self._is_help_screen
            self._needs_redraw = True

        elif (
            btn == BUTTON_O
            and not self._is_help_screen
            and self._confirm_menu is None
            and self._context_menu is None
            and not self._input_active
        ):
            inp.reset()
            self._show_options = True
            self._opt_idx = 0
            self._needs_redraw = True

        elif (
            btn == BUTTON_N
            and not self._is_help_screen
            and not self._show_options
            and self._confirm_menu is None
            and self._context_menu is None
        ):
            inp.reset()
            if self._mode == FILE_BROWSER_MANAGER:
                self._input_active = True
                self._input_mode = self.MODE_MKDIR
                self._input_text = ""
                self._input_cursor = 0
                self._is_shift = False
                self._is_caps = False
                self._needs_redraw = True

        elif (
            btn == BUTTON_I
            and not self._is_help_screen
            and not self._show_options
            and self._confirm_menu is None
            and self._context_menu is None
            and not self._show_info
        ):
            inp.reset()
            ap = self._app_state["active_pane"]
            cp = (
                self._app_state["left_path"]
                if ap == self.PANE_LEFT
                else self._app_state["right_path"]
            )
            fl = (
                self._app_state["left_files"]
                if ap == self.PANE_LEFT
                else self._app_state["right_files"]
            )
            ix = (
                self._app_state["left_index"]
                if ap == self.PANE_LEFT
                else self._app_state["right_index"]
            )

            if len(fl) > 0:
                sf = fl[ix]
                if sf != "..":
                    storage = self._vm.storage
                    fp = f"/{sf}" if cp == "/" else f"{cp}/{sf}"
                    isd = False
                    fz = 0
                    if fp in self._stat_cache:
                        isd = self._stat_cache[fp][0]
                        fz = storage.size(fp)
                    else:
                        isd = storage.is_directory(fp)
                        fz = storage.size(fp)

                    self._info_data = (
                        f"Name: {sf}\n"
                        f"Type: {'Directory' if isd else 'File'}\n"
                        f"Size: {fz} bytes"
                    )
                    self._show_info = True
                    self._needs_redraw = True

        elif (
            btn == BUTTON_D
            and not self._is_help_screen
            and not self._show_options
            and self._confirm_menu is None
            and self._context_menu is None
        ):
            inp.reset()
            if self._mode == FILE_BROWSER_MANAGER:
                mk = self._app_state["marked"]
                if len(mk) > 0:
                    self._pending_action = self.ACT_DELETE
                    self._confirm_menu = self.__menu_spawn(
                        f"Delete {len(mk)} items?", ("No", "Yes")
                    )
                else:
                    ap = self._app_state["active_pane"]
                    cp = (
                        self._app_state["left_path"]
                        if ap == self.PANE_LEFT
                        else self._app_state["right_path"]
                    )
                    fl = (
                        self._app_state["left_files"]
                        if ap == self.PANE_LEFT
                        else self._app_state["right_files"]
                    )
                    ix = (
                        self._app_state["left_index"]
                        if ap == self.PANE_LEFT
                        else self._app_state["right_index"]
                    )

                    if len(fl) > 0:
                        sf = fl[ix]
                        if sf != "..":
                            self._context_target_path = (
                                f"/{sf}" if cp == "/" else f"{cp}/{sf}"
                            )
                            self._pending_action = self.ACT_DELETE
                            self._confirm_menu = self.__menu_spawn(
                                "Confirm Delete?", ("No", "Yes")
                            )
            self._needs_redraw = True

        # --- Sub-View: Options Menu Input ---
        elif self._show_options:
            if btn in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER):
                inp.reset()
                self._show_options = False
                self.__refresh_panes()
                self._needs_redraw = True
            elif btn == BUTTON_UP:
                inp.reset()
                self._opt_idx = (self._opt_idx - 1) % len(self.OPTIONS_LABELS)
                self._needs_redraw = True
            elif btn == BUTTON_DOWN:
                inp.reset()
                self._opt_idx = (self._opt_idx + 1) % len(self.OPTIONS_LABELS)
                self._needs_redraw = True
            elif btn in (BUTTON_LEFT, BUTTON_RIGHT):
                inp.reset()
                self._needs_redraw = True
                idx = self._opt_idx
                if idx == 0:
                    self._app_state["show_hidden"] = not self._app_state.get(
                        "show_hidden", False
                    )
                elif idx == 1:
                    self._app_state["dir_menu"] = not self._app_state.get(
                        "dir_menu", True
                    )

        # --- Sub-View: Confirm Overwrite/Delete Dialog Input ---
        elif self._confirm_menu is not None:
            if btn in (BUTTON_BACK, BUTTON_ESCAPE):
                inp.reset()
                del self._confirm_menu
                self._confirm_menu = None
                self._pending_action = self.ACT_NONE
                self._pending_dest_path = ""
                self._needs_redraw = True
            elif btn == BUTTON_UP:
                inp.reset()
                self._confirm_menu.scroll_up()
                self._needs_redraw = True
            elif btn == BUTTON_DOWN:
                inp.reset()
                self._confirm_menu.scroll_down()
                self._needs_redraw = True
            elif btn == BUTTON_CENTER:
                inp.reset()
                sl = self._confirm_menu.current_item

                if sl == "Yes":
                    storage = self._vm.storage
                    mk = self._app_state["marked"]
                    targets = mk if len(mk) > 0 else [self._context_target_path]

                    if self._pending_action == self.ACT_DELETE:
                        total = len(targets)
                        for i, t in enumerate(targets):
                            self.__loading_run(
                                f"Deleting {int((i/total)*100)}%", i / total
                            )
                            if not storage.remove(t):
                                self._vm.log(f"Delete Error on: {t}", 2)
                        self.__loading_run("Deleted", 1.0)

                    elif self._pending_action in (self.ACT_COPY, self.ACT_MOVE):
                        total = len(targets)
                        act_name = (
                            "Copying"
                            if self._pending_action == self.ACT_COPY
                            else "Moving"
                        )

                        if total == 1:
                            self.__loading_run(f"{act_name}...", 0.5)

                        for i, t in enumerate(targets):
                            if total > 1:
                                self.__loading_run(
                                    f"Batch {act_name} {int((i/total)*100)}%", i / total
                                )

                            dp = self._pending_dest_path
                            if len(mk) > 0:
                                dp = f"{dp}/{t.split('/')[-1]}".replace("//", "/")

                            if t != dp:
                                if storage.exists(dp):
                                    storage.remove(dp)

                                if self._pending_action == self.ACT_COPY:
                                    if not storage.copy(t, dp):
                                        self._vm.log(f"Copy Error on: {t}", 2)
                                else:
                                    if not storage.move(t, dp):
                                        self._vm.log(f"Move Error on: {t}", 2)

                        self.__loading_run("Done", 1.0)

                    elif self._pending_action == self.ACT_RENAME:
                        self.__loading_run("Renaming...", 0.0)
                        if storage.exists(self._pending_dest_path):
                            storage.remove(self._pending_dest_path)
                        if not storage.move(
                            self._context_target_path, self._pending_dest_path
                        ):
                            self._vm.log(
                                f"Rename Error on: {self._context_target_path}", 2
                            )
                        self.__loading_run("Renamed", 1.0)

                    if len(mk) > 0:
                        self._app_state["marked"].clear()
                    if self._pending_action != self.ACT_NONE:
                        self.__refresh_panes()

                del self._confirm_menu
                self._confirm_menu = None
                self._pending_action = self.ACT_NONE
                self._context_target_path = self._pending_dest_path = ""
                self._needs_redraw = True

        # --- Sub-View: Context Menu Input ---
        elif self._context_menu is not None:
            if btn in (BUTTON_BACK, BUTTON_ESCAPE):
                inp.reset()
                del self._context_menu
                self._context_menu = None
                self._editor_state = self.MODE_EDITING
                self._needs_redraw = True
            elif btn == BUTTON_UP:
                inp.reset()
                self._context_menu.scroll_up()
                self._needs_redraw = True
            elif btn == BUTTON_DOWN:
                inp.reset()
                self._context_menu.scroll_down()
                self._needs_redraw = True
            elif btn == BUTTON_CENTER:
                inp.reset()
                ac = self._context_menu.current_item

                if self._is_editing:
                    if ac in ("Save", "Save & Exit"):
                        self.__loading_run("Saving...", 0.5)

                        data = self._text_editor.current_text

                        if self._vm.storage.write(self._edit_file, data, "w"):
                            self._edit_unsaved = False
                        del data  # Plug memory leak right after save
                        self.__loading_run("Saved", 1.0)
                        if ac == "Save & Exit":
                            self._is_editing = False
                            self._is_shift = False
                            self._is_caps = False
                            self._text_editor = None
                        else:
                            self._text_editor.refresh()
                    elif ac in ("Exit", "Exit without Saving"):
                        self._is_editing = False
                        self._is_shift = False
                        self._is_caps = False
                        self._text_editor = None

                    del self._context_menu
                    self._context_menu = None
                    self._editor_state = self.MODE_EDITING
                    self._needs_redraw = True
                else:
                    if ac == "Cancel":
                        pass
                    elif ac == "Clear Marks":
                        self._app_state["marked"].clear()
                        self.__refresh_panes()
                    elif ac == "Open":
                        if self._app_state["active_pane"] == self.PANE_LEFT:
                            self._app_state["left_path"] = self._context_target_path
                            self._app_state["left_index"] = 0
                        else:
                            self._app_state["right_path"] = self._context_target_path
                            self._app_state["right_index"] = 0
                        self.__refresh_panes()
                    elif ac == "View":
                        self.__file_view(self._context_target_path)
                    elif ac == "Edit":
                        self.__file_edit(self._context_target_path)
                    elif ac == "Delete":
                        self._pending_action = self.ACT_DELETE
                        mk = self._app_state["marked"]
                        msg = (
                            f"Delete {len(mk)} items?"
                            if len(mk) > 0
                            else "Confirm Delete?"
                        )
                        self._confirm_menu = self.__menu_spawn(msg, ("No", "Yes"))
                    elif ac == "Rename":
                        self._input_active = True
                        self._input_text = self._context_target_path.split("/")[-1]
                        self._input_cursor = len(self._input_text)
                        self._input_mode = self.MODE_RENAME
                        self._is_shift = False
                        self._is_caps = False
                    elif ac in ("Copy", "Move"):
                        ap = self._app_state["active_pane"]
                        td = (
                            self._app_state["right_path"]
                            if ap == self.PANE_LEFT
                            else self._app_state["left_path"]
                        )
                        mk = self._app_state["marked"]

                        if len(mk) > 0:
                            self._pending_action = (
                                self.ACT_COPY if ac == "Copy" else self.ACT_MOVE
                            )
                            self._pending_dest_path = td
                            self._confirm_menu = self.__menu_spawn(
                                f"Confirm {ac}?", ("No", "Yes")
                            )
                        else:
                            fn = self._context_target_path.split("/")[-1]
                            dp = (
                                f"/{fn}"
                                if td == "/"
                                else f"/{td}/{fn}".replace("//", "/")
                            )

                            if dp == self._context_target_path:
                                self._input_active = True
                                self._input_text = fn
                                self._input_cursor = len(self._input_text)
                                self._input_mode = (
                                    self.MODE_COPY_SAME
                                    if ac == "Copy"
                                    else self.MODE_RENAME
                                )
                                self._is_shift = False
                                self._is_caps = False
                            else:
                                self._pending_action = (
                                    self.ACT_COPY if ac == "Copy" else self.ACT_MOVE
                                )
                                self._pending_dest_path = dp
                                ex = self._vm.storage.exists(dp)
                                msg = "Overwrite?" if ex else f"Confirm {ac}?"
                                self._confirm_menu = self.__menu_spawn(
                                    msg, ("No", "Yes")
                                )
                    del self._context_menu
                    self._context_menu = None
                    self._needs_redraw = True

        # --- Main File Browser Input: Navigation and Exiting ---
        elif btn in (BUTTON_BACK, BUTTON_ESCAPE):
            inp.reset()
            if self._is_help_screen:
                self._is_help_screen = False
                self._needs_redraw = True
            else:
                self.__save_settings()
                self._vm.draw.set_scaling(self._scale_og.x, self._scale_og.y, False)
                return False

        elif btn == BUTTON_LEFT and not self._is_help_screen:
            inp.reset()
            self._app_state["active_pane"] = self.PANE_LEFT
            self._needs_redraw = True

        elif btn == BUTTON_RIGHT and not self._is_help_screen:
            inp.reset()
            self._app_state["active_pane"] = self.PANE_RIGHT
            self._needs_redraw = True

        elif btn == BUTTON_UP and not self._is_help_screen:
            inp.reset()
            ap = self._app_state["active_pane"]
            fl = (
                self._app_state["left_files"]
                if ap == self.PANE_LEFT
                else self._app_state["right_files"]
            )
            ix = (
                self._app_state["left_index"]
                if ap == self.PANE_LEFT
                else self._app_state["right_index"]
            )

            fln = len(fl)
            if fln > 0:
                if ap == self.PANE_LEFT:
                    self._app_state["left_index"] = (ix - 1) % fln
                else:
                    self._app_state["right_index"] = (ix - 1) % fln
                self._needs_redraw = True

        elif btn == BUTTON_DOWN and not self._is_help_screen:
            inp.reset()
            ap = self._app_state["active_pane"]
            fl = (
                self._app_state["left_files"]
                if ap == self.PANE_LEFT
                else self._app_state["right_files"]
            )
            ix = (
                self._app_state["left_index"]
                if ap == self.PANE_LEFT
                else self._app_state["right_index"]
            )

            fln = len(fl)
            if fln > 0:
                if ap == self.PANE_LEFT:
                    self._app_state["left_index"] = (ix + 1) % fln
                else:
                    self._app_state["right_index"] = (ix + 1) % fln
                self._needs_redraw = True

        elif btn == BUTTON_CENTER and not self._is_help_screen:
            inp.reset()
            ap = self._app_state["active_pane"]
            cp = (
                self._app_state["left_path"]
                if ap == self.PANE_LEFT
                else self._app_state["right_path"]
            )
            fl = (
                self._app_state["left_files"]
                if ap == self.PANE_LEFT
                else self._app_state["right_files"]
            )
            ix = (
                self._app_state["left_index"]
                if ap == self.PANE_LEFT
                else self._app_state["right_index"]
            )

            if len(fl) > 0:
                sf = fl[ix]
                if sf == "..":
                    pts = cp.rstrip("/").split("/")
                    fe = pts[-1] if len(pts) > 1 else ""
                    pr = "/" + "/".join(pts[1:-1])
                    if pr in ("//", ""):
                        pr = "/"

                    if ap == self.PANE_LEFT:
                        self._app_state["left_path"] = pr
                    else:
                        self._app_state["right_path"] = pr

                    self.__refresh_panes()

                    nf = (
                        self._app_state["left_files"]
                        if ap == self.PANE_LEFT
                        else self._app_state["right_files"]
                    )
                    try:
                        nix = nf.index(fe)
                    except ValueError:
                        nix = 0

                    if ap == self.PANE_LEFT:
                        self._app_state["left_index"] = nix
                    else:
                        self._app_state["right_index"] = nix
                else:
                    np = f"/{sf}" if cp == "/" else f"{cp}/{sf}"

                    isd = False
                    if np in self._stat_cache:
                        isd = self._stat_cache[np][0]
                    else:
                        isd = self._vm.storage.is_directory(np)

                    if self._mode == FILE_BROWSER_SELECTOR and not isd:
                        self.__save_settings()
                        self._vm.draw.set_scaling(
                            self._scale_og.x, self._scale_og.y, False
                        )
                        return False

                    mk = self._app_state["marked"]

                    if (
                        isd
                        and not self._app_state.get("dir_menu", True)
                        and len(mk) == 0
                    ):
                        if ap == self.PANE_LEFT:
                            self._app_state["left_path"] = np
                            self._app_state["left_index"] = 0
                        else:
                            self._app_state["right_path"] = np
                            self._app_state["right_index"] = 0
                        self.__refresh_panes()
                    elif self._mode == FILE_BROWSER_MANAGER and len(mk) > 0:
                        self._context_target_path = np
                        items = ["Open"] if isd else []
                        items.extend(
                            ["Copy", "Move", "Delete", "Clear Marks", "Cancel"]
                        )
                        self._context_menu = self.__menu_spawn(
                            f"{len(mk)} Marked", items
                        )
                    else:
                        self._context_target_path = np

                        if isd:
                            items = ["Open"]
                        else:
                            is_img = np.lower().endswith((".jpg", ".jpeg", ".bmp"))
                            items = ["View"] if is_img else ["View", "Edit"]

                        if self._mode == FILE_BROWSER_MANAGER:
                            items.extend(["Copy", "Move", "Rename", "Delete"])
                        items.append("Cancel")
                        self._context_menu = self.__menu_spawn(sf[:14], items)
                self._needs_redraw = True

        if self._needs_redraw:
            self.__render()

        return True
