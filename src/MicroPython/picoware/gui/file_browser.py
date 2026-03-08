# ==============================================================================
# File Browser Application for Picoware OS
# Designed for Picocalc 2.0 Hardware
# ==============================================================================

import gc
import time
import json
import os
from micropython import const
from picoware.system.vector import Vector
from picoware.system.colors import TFT_WHITE, TFT_BLACK, TFT_BLUE, TFT_YELLOW, TFT_CYAN, TFT_DARKGREY, TFT_LIGHTGREY, TFT_RED
from picoware.gui.menu import Menu
from picoware.system.system import System

from picoware.system.buttons import (
    BUTTON_NONE, BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_CENTER, BUTTON_BACK, 
    BUTTON_ESCAPE, BUTTON_BACKSPACE, BUTTON_SPACE, BUTTON_PERIOD, BUTTON_MINUS, BUTTON_UNDERSCORE,
    BUTTON_A, BUTTON_B, BUTTON_C, BUTTON_D, BUTTON_E, BUTTON_F, BUTTON_G, BUTTON_H, BUTTON_I,
    BUTTON_J, BUTTON_K, BUTTON_L, BUTTON_M, BUTTON_N, BUTTON_O, BUTTON_P, BUTTON_Q, BUTTON_R,
    BUTTON_S, BUTTON_T, BUTTON_U, BUTTON_V, BUTTON_W, BUTTON_X, BUTTON_Y, BUTTON_Z,
    BUTTON_0, BUTTON_1, BUTTON_2, BUTTON_3, BUTTON_4, BUTTON_5, BUTTON_6, BUTTON_7, BUTTON_8, BUTTON_9,
    BUTTON_SHIFT, BUTTON_CAPS_LOCK, KEY_MOD_SHL, KEY_MOD_SHR, KEY_CAPS_LOCK
)

FILE_BROWSER_VIEWER = const(0)
FILE_BROWSER_MANAGER = const(1)
FILE_BROWSER_SELECTOR = const(2)

def rgb_to_565(r, g, b):
    # Helper to convert standard RGB colors to the display's 16-bit color format
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

class FileBrowser:
    """
    Main File Browser application class. Handles dual-pane navigation, 
    file operations (copy/move/delete), and integrated text/image viewing.
    """
    PANE_LEFT = const(0)
    PANE_RIGHT = const(1)
    SORT_NAME = const(0)
    SORT_DATE = const(1)
    
    MODE_NONE = const(0)
    MODE_MKDIR = const(1)
    MODE_RENAME = const(2)
    MODE_COPY_SAME = const(3)
    
    ACT_NONE = const(0)
    ACT_DELETE = const(1)
    ACT_COPY = const(2)
    ACT_MOVE = const(3)
    ACT_RENAME = const(4)
    
    OPTIONS_LABELS = ("Theme", "BG R (0-255)", "BG G (0-255)", "BG B (0-255)", "Bar R (0-255)", "Bar G (0-255)", "Bar B (0-255)", "Sort Mode", "Hidden Files", "Dir Enter")
    
    def __init__(self, view_manager, mode=FILE_BROWSER_SELECTOR, start_directory=""):
        # Link to system managers
        self._vm = view_manager
        self._mode = mode
        self._storage = view_manager.storage
        self._draw = view_manager.draw
        self._input_manager = view_manager.input_manager
        self._sys = System()
        
        # State tracking and caching
        self._last_saved_json = "{}"
        self._last_save_time = 0
        self._stat_cache = {}
        
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
        self._input_mode = self.MODE_NONE
        self._context_target_path = ""
        self._pending_action = self.ACT_NONE
        self._pending_dest_path = ""
        
        self._is_shift = False
        self._is_caps = False
        
        # Text Editor and Image Viewer state
        self._is_editing = False
        self._edit_read_only = False
        self._edit_text = []
        self._edit_file = ""
        self._edit_cx = 0
        self._edit_cy = 0
        self._edit_sx = 0
        self._edit_sy = 0
        self._edit_unsaved = False
        
        self._is_viewing_image = False
        self._image_load_state = 0
        self._image_path = ""
        self._jpeg_vec = Vector(0, 0)
        
        self._char_map = {
            BUTTON_A: "a", BUTTON_B: "b", BUTTON_C: "c", BUTTON_D: "d", BUTTON_E: "e",
            BUTTON_F: "f", BUTTON_G: "g", BUTTON_H: "h", BUTTON_I: "i", BUTTON_J: "j",
            BUTTON_K: "k", BUTTON_L: "l", BUTTON_M: "m", BUTTON_N: "n", BUTTON_O: "o",
            BUTTON_P: "p", BUTTON_Q: "q", BUTTON_R: "r", BUTTON_S: "s", BUTTON_T: "t",
            BUTTON_U: "u", BUTTON_V: "v", BUTTON_W: "w", BUTTON_X: "x", BUTTON_Y: "y",
            BUTTON_Z: "z", BUTTON_0: "0", BUTTON_1: "1", BUTTON_2: "2", BUTTON_3: "3",
            BUTTON_4: "4", BUTTON_5: "5", BUTTON_6: "6", BUTTON_7: "7", BUTTON_8: "8",
            BUTTON_9: "9", BUTTON_SPACE: " ", BUTTON_PERIOD: ".", BUTTON_MINUS: "-", 
            BUTTON_UNDERSCORE: "_"
        }
        
        # Core application state to be saved/loaded
        self._app_state = {
            "left_path": start_directory if start_directory else "/",
            "right_path": start_directory if start_directory else "/",
            "left_files": [],
            "right_files": [],
            "left_index": 0,
            "right_index": 0,
            "left_top": 0,
            "right_top": 0,
            "active_pane": self.PANE_LEFT,
            "sort_mode": self.SORT_NAME,
            "show_hidden": False,
            "dir_menu": True,
            "theme": 0, # Defaults to 0 which is now the System theme
            "bg_r": 0, "bg_g": 0, "bg_b": 170,
            "bar_r": 0, "bar_g": 170, "bar_b": 170,
            "marked": []
        }
        
        # Load user settings if they exist
        try:
            data = self._storage.read("/picoware/settings/file_browser_state.json", "r")
            if data:
                loaded = json.loads(data)
                self._app_state.update({k: loaded.get(k, self._app_state[k]) for k in self._app_state})
                self._last_saved_json = json.dumps(self._app_state)
                del loaded
            del data
        except Exception:
            pass

        self._refresh_panes()
        self._needs_redraw = True

    def __del__(self):
        # Force a settings save and safely clear memory on exit
        self._auto_save()
        if self._loading:
            self._loading.stop()
            del self._loading
            self._loading = None
        if self._context_menu:
            del self._context_menu
        if self._confirm_menu:
            del self._confirm_menu
            
        self._app_state["left_files"].clear()
        self._app_state["right_files"].clear()
        self._app_state["marked"].clear()
        self._app_state.clear()
        self._stat_cache.clear()
        self._edit_text.clear()
        self._char_map.clear()
        self._sys = None

    @property
    def directory(self) -> str:
        _dir = self._app_state["left_path"] if self._app_state["active_pane"] == self.PANE_LEFT else self._app_state["right_path"]
        if _dir.startswith("/sd/"):
            _dir = _dir[3:]
        return _dir

    @property
    def path(self) -> str:
        # Resolves the full absolute path of the currently highlighted item
        act = self._app_state["active_pane"]
        p_dir = self._app_state["left_path"] if act == self.PANE_LEFT else self._app_state["right_path"]
        f_lst = self._app_state["left_files"] if act == self.PANE_LEFT else self._app_state["right_files"]
        idx = self._app_state["left_index"] if act == self.PANE_LEFT else self._app_state["right_index"]
        
        if len(f_lst) == 0:
            return p_dir
            
        fname = f_lst[idx]
        _path = f"/{fname}" if p_dir == "/" else f"{p_dir}/{fname}"
        
        if _path.startswith("/sd/"):
            _path = _path[3:]
        return _path

    @property
    def stats(self) -> dict:
        _p = self.path
        return {
            "directory": self.directory,
            "path": _p,
            "size": self._storage.size(_p) if not self._storage.is_directory(_p) else 0,
            "type": _p.split(".")[-1] if "." in _p else "unknown"
        }

    def _get_theme(self):
        # Maps the user's saved theme index to specific display colors
        # Output format: Background, Bar/Border, Standard Text, Directory Text, Bar Text
        th = self._app_state.get("theme", 0)
        if th == 0:
            # System Theme: Uses variables dynamically provided by ViewManager
            return self._vm.background_color, self._vm.selected_color, self._vm.foreground_color, self._vm.foreground_color, self._vm.background_color
        elif th == 1:
            # Classic Theme
            return TFT_BLUE, TFT_CYAN, TFT_WHITE, TFT_YELLOW, TFT_BLACK
        elif th == 2:
            # Dark Theme
            return TFT_BLACK, TFT_WHITE, TFT_WHITE, TFT_WHITE, TFT_BLACK
        else:
            # Custom Theme
            c_bg = rgb_to_565(self._app_state.get("bg_r", 0), self._app_state.get("bg_g", 0), self._app_state.get("bg_b", 170))
            c_bar = rgb_to_565(self._app_state.get("bar_r", 0), self._app_state.get("bar_g", 170), self._app_state.get("bar_b", 170))
            return c_bg, c_bar, TFT_WHITE, TFT_YELLOW, TFT_BLACK

    def _spawn_menu(self, title, items):
        # Helper to construct a pop-up context menu overlaid on the main interface
        c_bg, c_bar, _, _, _ = self._get_theme()
        m = Menu(self._draw, title, 0, self._draw.size.y, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2)
        for i in items:
            m.add_item(i)
        m.set_selected(0)
        return m

    def _auto_save(self):
        # Non-blocking delta check to silently save settings every 5 seconds if changed
        curr_t = time.time()
        if curr_t - self._last_save_time > 5:
            save_dict = {k: self._app_state[k] for k in ["left_path", "right_path", "active_pane", "sort_mode", "show_hidden", "dir_menu", "theme", "bg_r", "bg_g", "bg_b", "bar_r", "bar_g", "bar_b", "left_top", "right_top"]}
            curr_j = json.dumps(save_dict)
            if curr_j != self._last_saved_json:
                if self._storage.write("/picoware/settings/file_browser_state.json", curr_j, "w"):
                    self._last_saved_json = curr_j
            del curr_j
            del save_dict
            self._last_save_time = curr_t

    def _draw_progress(self, title, percentage):
        # Stop and clear the loading spinner when the task is done (100%)
        if percentage >= 1.0:
            if self._loading:
                self._loading.stop()
                self._loading = None
            return

        # Initialize the standard OS loading spinner if it isn't running yet
        if not self._loading:
            from picoware.gui.loading import Loading
            c_bg, _, _, _, _ = self._get_theme()
            self._loading = Loading(self._draw, background_color=c_bg)
            
        # Update the text (e.g., "Copying...") and tick the animation
        self._loading.set_text(title)
        self._loading.animate(swap=True)

    def _load_dir(self, path):
        # Reads directory contents and implements lazy caching for is_directory checks.
        # Only queries file sizes later during UI rendering to minimize RAM and SD reads.
        items = []
        show_hid = self._app_state.get("show_hidden", False)
        sort_m = self._app_state.get("sort_mode", self.SORT_NAME)
        
        try:
            d_list = self._storage.listdir(path)
            temp_list = []
            
            # Mount VFS explicitly so standard os library can see hardware paths for sorting by date
            if sort_m == self.SORT_DATE:
                try: self._storage.mount_vfs()
                except Exception: pass
            
            for itm in d_list:
                if itm in (".", "..") or (not show_hid and itm.startswith(".")): 
                    continue
                    
                fp = f"/{itm}" if path == "/" else f"{path}/{itm}"
                
                is_d = False
                if fp in self._stat_cache:
                    is_d = self._stat_cache[fp][0]
                else:
                    is_d = self._storage.is_directory(fp)
                    self._stat_cache[fp] = (is_d, -1)
                    
                if sort_m == self.SORT_DATE:
                    mt = 0
                    try: 
                        real_fp = fp
                        if not real_fp.startswith("sd") and not real_fp.startswith("/sd"):
                            real_fp = "/sd/" + real_fp.lstrip("/")
                        # os.stat[9] accesses creation time, [8] is last modified time
                        try: mt = os.stat(real_fp)[9] 
                        except Exception: mt = os.stat(real_fp)[8]
                    except Exception: 
                        pass
                    temp_list.append((itm, is_d, mt))
                else:
                    temp_list.append((itm, is_d))
                    
            del d_list
            
            # DO NOT unmount VFS here, unmounting crashes the OS.
            
            if sort_m == self.SORT_DATE:
                # Sort by: Folders first, then creation date (newest first), then name
                temp_list.sort(key=lambda x: (not x[1], -x[2], x[0].lower()))
            else:
                # Sort by: Folders first, then name
                temp_list.sort(key=lambda x: (not x[1], x[0].lower()))
                
            items = [x[0] for x in temp_list]
            del temp_list
        except Exception:
            items = ["<ERROR>"]
            
        return [".."] + items if path != "/" else items

    def _refresh_panes(self):
        # Wipes the lazy cache entirely to prevent memory leaks, then repopulates panes
        self._stat_cache.clear()
        self._app_state["left_files"].clear()
        self._app_state["left_files"] = self._load_dir(self._app_state["left_path"])
        self._app_state["left_index"] = max(0, min(self._app_state["left_index"], len(self._app_state["left_files"]) - 1))
        self._app_state["right_files"].clear()
        self._app_state["right_files"] = self._load_dir(self._app_state["right_path"])
        self._app_state["right_index"] = max(0, min(self._app_state["right_index"], len(self._app_state["right_files"]) - 1))

    def _open_viewer(self, path):
        # Determines if the file is an image or text and launches the appropriate viewer
        ext = path.split(".")[-1].lower() if "." in path else ""
        if ext in ("jpg", "jpeg", "bmp"):
            self._is_viewing_image = True
            self._image_load_state = 0
            self._image_path = path
            self._needs_redraw = True
        else:
            self._open_editor(path, read_only=True)

    def _open_editor(self, path, read_only=False):
        # Loads file contents into RAM for integrated text viewing or editing
        self._edit_text.clear()
        data = self._storage.read(path, "r")
        if data: 
            self._edit_text.extend(data.split('\n'))
        del data
        
        if not self._edit_text: self._edit_text.append("")
        self._edit_file = path
        self._edit_read_only = read_only
        self._edit_cx = self._edit_cy = self._edit_sx = self._edit_sy = 0
        self._edit_unsaved = False
        
        self._is_shift = False
        self._is_caps = False
        
        self._is_editing = True
        self._needs_redraw = True

    def _draw_ui(self):
        # ---------------------------------------------------------
        # Main Rendering Method
        # Resolves overlapping layers based on current active state
        # ---------------------------------------------------------
        c_bg, c_bar, c_txt, c_dir, c_btxt = self._get_theme()
        sw, sh, mx = self._draw.size.x, self._draw.size.y, self._draw.size.x // 2

        # 1. Image Viewer Overlay (State Machine for Loading Animation)
        if self._is_viewing_image:
            # Stage 1: Tick the loading spinner animation for 5 loops so the user actually sees it
            if self._image_load_state < 5:
                if not self._loading:
                    from picoware.gui.loading import Loading
                    self._loading = Loading(self._draw, background_color=TFT_BLACK)
                    self._loading.set_text("Loading Image...")
                
                self._loading.animate(swap=True)
                self._image_load_state += 1
                self._needs_redraw = True
                return
            
            # Stage 2: Stop the spinner, format the background, and execute hardware block
            elif self._image_load_state == 5:
                if self._loading:
                    self._loading.stop()
                    self._loading = None
                
                self._draw.clear(color=TFT_BLACK)
                self._draw.fill_rectangle(Vector(0, sh - 12), Vector(sw, 12), c_bar)
                self._draw.text(Vector(2, sh - 10), "BACK : Close Image", c_btxt)
                self._draw.swap()
                
                gc.collect() # Defragment RAM so C-decoder has a contiguous block
                
                # Mount VFS explicitly so standard python open() can find it, avoiding silent failures
                try:
                    self._storage.mount_vfs()
                except Exception:
                    pass
                
                try:
                    # Pass self._storage so the decoders have the VFS context they need to open the file
                    # We pass the original path to avoid case-sensitivity bugs within the VFS string checks
                    if self._image_path.lower().endswith("bmp"):
                        self._draw.image_bmp(self._jpeg_vec, self._image_path, self._storage)
                        self._draw.swap()
                    else:
                        # Safety Pre-Check: Scan the header for the "Progressive JPEG" marker (FF C2).
                        # We must intercept it here before the C-library caches it, or the device will completely hard freeze.
                        is_safe_jpeg = True
                        try:
                            # Read the first few KB where the image structure headers exist
                            header_chunk = self._storage.read_chunked(self._image_path, 0, 2048)
                            if header_chunk:
                                for j in range(len(header_chunk) - 1):
                                    if header_chunk[j] == 0xFF and header_chunk[j+1] == 0xC2:
                                        is_safe_jpeg = False
                                        break
                            del header_chunk
                        except Exception:
                            pass
                        
                        if not is_safe_jpeg:
                            raise ValueError("Progressive JPEG formats are unsupported by hardware.")
                            
                        self._draw.image_jpeg(self._jpeg_vec, self._image_path, self._storage)
                        # Push the newly decoded image from the backbuffer to the actual display
                        self._draw.swap()
                        
                except Exception as e:
                    # Catch un-decodable formats gracefully to prevent the app from freezing
                    self._draw.clear(color=TFT_BLACK)
                    self._draw.text(Vector(10, 30), "Format not supported", TFT_RED)
                    self._draw.text(Vector(10, 45), "or resolution too large.", TFT_RED)
                    self._draw.text(Vector(10, 60), "(Must be Baseline JPEG)", TFT_YELLOW)
                    self._draw.fill_rectangle(Vector(0, sh - 12), Vector(sw, 12), c_bar)
                    self._draw.text(Vector(2, sh - 10), "BACK : Close Image", c_btxt)
                    self._draw.swap()
                finally:
                    # CRITICAL FIX: jpeg.py forcefully unmounts the VFS when it is finished decoding. 
                    # We MUST immediately remount the VFS here, otherwise the OS crashes when reading directories.
                    try:
                        self._storage.mount_vfs()
                    except Exception:
                        pass
                        
                self._image_load_state = 6
                self._needs_redraw = False
                return
            else:
                # Stage 3: Keep the decoded image or error screen visible until user exits
                self._needs_redraw = False
                return

        # 2. Text Editor Overlay
        if self._is_editing:
            self._draw.clear(color=c_bg)
            self._draw.fill_rectangle(Vector(0, 0), Vector(sw, 12), c_bar)
            mode_s = "View" if self._edit_read_only else "Edit"
            mod_s = "*" if self._edit_unsaved and not self._edit_read_only else ""
            
            ind_s = ""
            if not self._edit_read_only:
                ind = 'A' if self._is_caps else ('^' if self._is_shift else 'a')
                ind_s = f" [{ind}]"
                
            self._draw.text(Vector(2, 2), f"{mode_s}: {self._edit_file.split('/')[-1]}{mod_s}{ind_s}", c_btxt)
            
            m_lin, m_chr = (sh - 24) // 12, (sw - 4) // 6
            for i in range(m_lin):
                idx = self._edit_sy + i
                if idx < len(self._edit_text):
                    self._draw.text(Vector(2, 14 + i * 12), self._edit_text[idx][self._edit_sx : self._edit_sx + m_chr], c_txt)
                    
            if not self._edit_read_only and (time.ticks_ms() // 500) % 2 == 0:
                cx, cy = 2 + (self._edit_cx - self._edit_sx) * 6, 14 + (self._edit_cy - self._edit_sy) * 12
                if 0 <= cx < sw and 12 < cy < sh - 12:
                    self._draw.fill_rectangle(Vector(cx, cy - 1), Vector(6, 11), TFT_CYAN)
                    try: self._draw.text(Vector(cx, cy), self._edit_text[self._edit_cy][self._edit_cx], TFT_BLACK)
                    except IndexError: pass
                    
            if not self._edit_read_only:
                self._needs_redraw = True
                
            self._draw.fill_rectangle(Vector(0, sh - 12), Vector(sw, 12), c_bar)
            self._draw.text(Vector(2, sh - 10), "UP/DWN:Scroll BACK:Close" if self._edit_read_only else "ENT:Menu BACK:Close", c_btxt)
            
            if self._context_menu:
                self._context_menu.draw()
                self._needs_redraw = False
            self._draw.swap()
            return

        self._draw.clear(color=c_bg)

        # 3. Help Screen Overlay
        if self._is_help_screen:
            self._draw.text(Vector(10, 10), "File Browser Help", TFT_WHITE)
            self._draw.text(Vector(10, 24), "SPC:Mrk H:Help O:Opt M:Mode", c_bar)
            self._draw.text(Vector(10, 36), "I:Info N:NewFolder D:Del", c_bar)
            self._draw.text(Vector(10, 48), "UP/DOWN: Scroll", TFT_WHITE)
            self._draw.text(Vector(10, 60), "L/R: Switch Pane", TFT_WHITE)
            self._draw.text(Vector(10, 72), "CENTER: Menu (View/Edit...)", TFT_WHITE)
            self._draw.text(Vector(10, 84), "BACK: Exit App", TFT_WHITE)
            self._draw.text(Vector(10, 126), f"RAM: {gc.mem_alloc() // 1024}KB used / {gc.mem_free() // 1024}KB free", TFT_YELLOW)
            if self._sys and self._sys.has_psram:
                self._draw.text(Vector(10, 138), f"PSRAM: {self._sys.used_psram // 1024}KB used / {self._sys.free_psram // 1024}KB free", TFT_YELLOW)
            self._draw.text(Vector(10, sh - 40), "made by Slasher006", c_bar)
            self._draw.text(Vector(10, sh - 30), "with the help of Gemini", c_bar)
            self._draw.text(Vector(10, sh - 20), "Date: 2026-03-07 | v1.32", c_bar)
            self._draw.swap()
            self._needs_redraw = False
            return

        # 4. File Info Window
        if self._show_info:
            bx, by, bw, bh = (sw - 200) // 2, (sh - 100) // 2, 200, 100
            self._draw.fill_rectangle(Vector(bx, by), Vector(bw, bh), TFT_BLACK)
            self._draw.rect(Vector(bx, by), Vector(bw, bh), c_bar)
            self._draw.fill_rectangle(Vector(bx, by), Vector(bw, 16), c_bar)
            self._draw.text(Vector(bx + 5, by + 2), "FILE INFORMATION", c_btxt)
            for i, ln in enumerate(self._info_data): 
                self._draw.text(Vector(bx + 10, by + 25 + (i * 15)), ln, TFT_WHITE)
            self._draw.text(Vector(bx + 10, by + bh - 15), "[BACK/ENT] Close", TFT_LIGHTGREY)
            self._draw.swap()
            self._needs_redraw = False
            return

        # 5. Options Menu
        if self._show_options:
            self._draw.fill_rectangle(Vector(10, 10), Vector(sw - 20, sh - 20), TFT_BLACK)
            self._draw.rect(Vector(10, 10), Vector(sw - 20, sh - 20), c_bar)
            self._draw.fill_rectangle(Vector(10, 10), Vector(sw - 20, 20), c_bar)
            self._draw.text(Vector(15, 14), "OPTIONS MENU", c_btxt)
            for i, l in enumerate(self.OPTIONS_LABELS):
                yp = 35 + (i * 15)
                tc = c_bar if i == self._opt_idx else TFT_WHITE
                if i == self._opt_idx: 
                    self._draw.fill_rectangle(Vector(12, yp - 2), Vector(sw - 24, 13), TFT_DARKGREY)
                self._draw.text(Vector(20, yp), l + ":", tc)
                v = ""
                if i == 0: v = ("System", "Classic", "Dark", "Custom")[self._app_state.get("theme", 0)]
                elif i in range(1, 7): v = str(self._app_state.get(["", "bg_r", "bg_g", "bg_b", "bar_r", "bar_g", "bar_b"][i], 0 if i not in (3,5,6) else 170))
                elif i == 7: v = "Name" if self._app_state.get("sort_mode", self.SORT_NAME) == self.SORT_NAME else "Date"
                elif i == 8: v = "Show" if self._app_state.get("show_hidden", False) else "Hide"
                elif i == 9: v = "Menu" if self._app_state.get("dir_menu", True) else "Open"
                self._draw.text(Vector(130, yp), f"< {v} >", tc)
            pbg = rgb_to_565(self._app_state.get("bg_r",0), self._app_state.get("bg_g",0), self._app_state.get("bg_b",170))
            pbr = rgb_to_565(self._app_state.get("bar_r",0), self._app_state.get("bar_g",170), self._app_state.get("bar_b",170))
            self._draw.text(Vector(20, 185), "Custom Preview:", TFT_LIGHTGREY)
            self._draw.fill_rectangle(Vector(140, 183), Vector(60, 20), pbg)
            self._draw.rect(Vector(140, 183), Vector(60, 20), pbr)
            self._draw.fill_rectangle(Vector(10, sh - 30), Vector(sw - 20, 20), c_bar)
            self._draw.text(Vector(15, sh - 26), "[L/R] Edit   [BACK/ENT] Save", c_btxt)
            self._draw.swap()
            self._needs_redraw = False
            return

        # 6. Text Input Overlay (for renaming/creating)
        if self._input_active:
            by = (sh - 70) // 2
            self._draw.fill_rectangle(Vector(10, by), Vector(sw - 20, 70), TFT_BLACK)
            self._draw.rect(Vector(10, by), Vector(sw - 20, 70), c_bar)
            self._draw.fill_rectangle(Vector(10, by), Vector(sw - 20, 16), c_bar)
            
            ts = "RENAME" if self._input_mode == self.MODE_RENAME else "COPY AS" if self._input_mode == self.MODE_COPY_SAME else "NEW DIR"
            ind = 'A' if self._is_caps else ('^' if self._is_shift else 'a')
            
            self._draw.text(Vector(15, by + 2), f"{ts} [{ind}]:", c_btxt)
            self._draw.text(Vector(15, by + 24), self._input_text, TFT_WHITE)
            if (time.ticks_ms() // 500) % 2 == 0:
                self._draw.fill_rectangle(Vector(15 + (self._input_cursor * 6), by + 35), Vector(6, 2), TFT_CYAN)
            self._needs_redraw = True
            self._draw.text(Vector(15, by + 48), "UP/DWN:Caps ENT:Save BACK:Cancel", TFT_LIGHTGREY)
            self._draw.swap()
            return

        # 7. Action Menus (Context and Confirmations)
        if self._confirm_menu:
            self._confirm_menu.draw()
            self._draw.swap()
            self._needs_redraw = False
            return

        if self._context_menu:
            self._context_menu.draw()
            self._draw.swap()
            self._needs_redraw = False
            return

        # 8. Main Dual-Pane Browser View
        self._draw.fill_rectangle(Vector(0, 0), Vector(sw, 12), c_bar)
        ss = "Name" if self._app_state.get("sort_mode", self.SORT_NAME) == self.SORT_NAME else "Date"
        dm = "Menu" if self._app_state.get("dir_menu", True) else "Open"
        
        mk_len = len(self._app_state["marked"])
        mk_str = f" [Sel:{mk_len}]" if mk_len > 0 else ""
        
        self._draw.text(Vector(2, 2), f"File Browser [{ss}] [Dir:{dm}]{mk_str}", c_btxt)
        self._draw.fill_rectangle(Vector(mx, 12), Vector(1, sh - 24), c_bar)
        
        c_lim, n_lim, m_itm = (mx - 8) // 6, ((mx - 8) // 6) - 6, (sh - 38) // 12
        ap = self._app_state["active_pane"]

        # Loop through left, then right pane to draw current directory listings
        for pn in (self.PANE_LEFT, self.PANE_RIGHT):
            il = pn == self.PANE_LEFT
            xb = 0 if il else mx + 1
            ps = self._app_state["left_path"] if il else self._app_state["right_path"]
            fl = self._app_state["left_files"] if il else self._app_state["right_files"]
            ix = self._app_state["left_index"] if il else self._app_state["right_index"]
            
            top_key = "left_top" if il else "right_top"
            si = self._app_state.get(top_key, 0)
            
            # Auto-scroll clamping logic
            if ix < si:
                si = ix
            elif ix >= si + m_itm:
                si = ix - m_itm + 1
                
            self._app_state[top_key] = si
            
            # Highlight currently active pane header
            if ap == pn: 
                self._draw.fill_rectangle(Vector(xb, 12), Vector(mx - (0 if il else 1), 12), c_bar)
            self._draw.text(Vector(xb + 2, 14), ps[:c_lim], c_btxt if ap == pn else c_txt)
            
            # Render visible files, polling sizes on-the-fly to save massive RAM buildup
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
                            fz = self._storage.size(fp)
                            self._stat_cache[fp] = (isd, fz)
                    else:
                        isd = self._storage.is_directory(fp)
                        fz = 0 if isd else self._storage.size(fp)
                        self._stat_cache[fp] = (isd, fz)
                
                im = fp in self._app_state["marked"]
                bc = TFT_RED if im else (c_dir if isd else c_txt)
                tc = bc if ap != pn or ai != ix else c_btxt
                
                if ap == pn and ai == ix: 
                    self._draw.fill_rectangle(Vector(xb + (0 if il else 1), yo - 1), Vector(mx - (2 if il else 3), 10), c_bar)
                
                if isd: szs = "<DIR>"
                elif fz < 1024: szs = f"{fz}B"
                elif fz < 1048576: szs = f"{fz//1024}K"
                else: szs = f"{fz//1048576}M"
                    
                dn = f"/{fn}" if isd else fn
                pl = max(0, c_lim - len(dn[:n_lim]) - len(szs))
                self._draw.text(Vector(xb + 2, yo), dn[:n_lim] + (" " * pl) + szs, tc)
                yo += 12

        self._draw.fill_rectangle(Vector(0, sh - 12), Vector(sw, 12), c_bar)
        if self._mode == FILE_BROWSER_SELECTOR:
            self._draw.text(Vector(2, sh - 10), "ENT:Sel M:DirMode O:Opt", c_btxt)
        else:
            self._draw.text(Vector(2, sh - 10), "ENT:Men SPC N:New S:Srt O:Opt M:Dir", c_btxt)
        self._draw.swap()
        self._needs_redraw = False

    def run(self):
        # ---------------------------------------------------------
        # Application Tick Loop
        # Processes user input contextual to the currently active UI overlay
        # ---------------------------------------------------------
        btn = self._input_manager.button
        
        # Reset input manager immediately at the top of the loop so inputs aren't missed between UI conditions
        self._input_manager.reset()
        
        if btn is None or btn == BUTTON_NONE:
            if self._needs_redraw:
                self._draw_ui()
            return True

        # --- Sub-View: Image Viewer Input ---
        if self._is_viewing_image:
            if btn in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER):
                self._is_viewing_image = False
                self._image_path = ""
                self._needs_redraw = True
                
        # --- Sub-View: Text Editor Input ---
        elif self._is_editing and self._context_menu is None and self._confirm_menu is None:
            if btn in (BUTTON_BACK, BUTTON_ESCAPE):
                if self._edit_unsaved and not self._edit_read_only:
                    self._context_menu = self._spawn_menu("Unsaved Changes!", ("Save & Exit", "Exit without Saving", "Cancel"))
                else:
                    self._is_editing = False
                    self._is_shift = False
                    self._is_caps = False
                self._needs_redraw = True
            elif btn == BUTTON_UP:
                if self._edit_read_only:
                    if self._edit_sy > 0: self._edit_sy -= 1
                elif self._edit_cy > 0:
                    self._edit_cy -= 1
                    self._edit_cx = min(self._edit_cx, len(self._edit_text[self._edit_cy]))
                self._needs_redraw = True
            elif btn == BUTTON_DOWN:
                if self._edit_read_only:
                    ml = (self._draw.size.y - 24) // 12
                    if self._edit_sy + ml < len(self._edit_text): self._edit_sy += 1
                elif self._edit_cy < len(self._edit_text) - 1:
                    self._edit_cy += 1
                    self._edit_cx = min(self._edit_cx, len(self._edit_text[self._edit_cy]))
                self._needs_redraw = True
            elif btn == BUTTON_LEFT:
                if self._edit_read_only:
                    if self._edit_sx > 0: self._edit_sx -= 1
                elif self._edit_cx > 0:
                    self._edit_cx -= 1
                elif self._edit_cy > 0:
                    self._edit_cy -= 1
                    self._edit_cx = len(self._edit_text[self._edit_cy])
                self._needs_redraw = True
            elif btn == BUTTON_RIGHT:
                if self._edit_read_only:
                    if self._edit_sx < 500: self._edit_sx += 1
                elif self._edit_cx < len(self._edit_text[self._edit_cy]):
                    self._edit_cx += 1
                elif self._edit_cy < len(self._edit_text) - 1:
                    self._edit_cy += 1
                    self._edit_cx = 0
                self._needs_redraw = True
            elif not self._edit_read_only:
                if btn == BUTTON_CENTER:
                    self._context_menu = self._spawn_menu("Editor Menu", ("Save", "Save & Exit", "Exit without Saving", "Cancel"))
                    self._needs_redraw = True
                elif btn in (BUTTON_SHIFT, KEY_MOD_SHL, KEY_MOD_SHR):
                    self._is_shift = not self._is_shift
                    self._needs_redraw = True
                elif btn in (BUTTON_CAPS_LOCK, KEY_CAPS_LOCK):
                    self._is_caps = not self._is_caps
                    self._is_shift = False
                    self._needs_redraw = True
                elif btn == BUTTON_BACKSPACE:
                    if self._edit_cx > 0:
                        line = self._edit_text[self._edit_cy]
                        self._edit_text[self._edit_cy] = line[:self._edit_cx-1] + line[self._edit_cx:]
                        self._edit_cx -= 1
                        self._edit_unsaved = True
                        self._needs_redraw = True
                    elif self._edit_cy > 0:
                        pl = len(self._edit_text[self._edit_cy-1])
                        self._edit_text[self._edit_cy-1] += self._edit_text[self._edit_cy]
                        self._edit_text.pop(self._edit_cy)
                        self._edit_cy -= 1
                        self._edit_cx = pl
                        self._edit_unsaved = True
                        self._needs_redraw = True
                elif btn in self._char_map:
                    c = self._char_map[btn]
                    if (self._is_shift or self._is_caps) and c.isalpha(): 
                        c = c.upper()
                    line = self._edit_text[self._edit_cy]
                    self._edit_text[self._edit_cy] = line[:self._edit_cx] + c + line[self._edit_cx:]
                    self._edit_cx += 1
                    self._edit_unsaved = True
                    if self._is_shift:
                        self._is_shift = False
                    self._needs_redraw = True
                
            # Restrict cursor viewport mathematically
            if self._needs_redraw and not self._edit_read_only:
                ml = (self._draw.size.y - 24) // 12
                mc = (self._draw.size.x - 4) // 6
                if self._edit_cy < self._edit_sy: self._edit_sy = self._edit_cy
                if self._edit_cy >= self._edit_sy + ml: self._edit_sy = self._edit_cy - ml + 1
                if self._edit_cx < self._edit_sx: self._edit_sx = max(0, self._edit_cx - 5)
                if self._edit_cx >= self._edit_sx + mc: self._edit_sx = self._edit_cx - mc + 1

        # --- Sub-View: Information Dialog Input ---
        elif self._show_info:
            if btn in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER):
                self._show_info = False
                self._info_data = []
                self._needs_redraw = True
                
        # --- Sub-View: Text Entry (Rename/Make Folder) Input ---
        elif self._input_active:
            if btn in (BUTTON_BACK, BUTTON_ESCAPE):
                self._input_active = False
                self._is_shift = False
                self._is_caps = False
                self._needs_redraw = True
            elif btn == BUTTON_CENTER:
                new_name = self._input_text.strip()
                rn = False
                
                if new_name:
                    td = self._app_state["left_path"] if self._app_state["active_pane"] == self.PANE_LEFT else self._app_state["right_path"]
                    np = f"/{new_name}" if td == "/" else f"{td}/{new_name}"
                    
                    if self._input_mode in (self.MODE_RENAME, self.MODE_COPY_SAME) and np != self._context_target_path:
                        if self._storage.exists(np):
                            self._pending_dest_path = np
                            self._pending_action = self.ACT_RENAME if self._input_mode == self.MODE_RENAME else self.ACT_COPY
                            self._confirm_menu = self._spawn_menu("Overwrite?", ("No", "Yes"))
                            self._input_active = False
                            self._is_shift = False
                            self._is_caps = False
                            self._needs_redraw = True
                            return True
                        else:
                            if self._input_mode == self.MODE_RENAME:
                                self._draw_progress("Renaming...", 0.0)
                                if self._storage.move(self._context_target_path, np):
                                    rn = True
                                else:
                                    print("Move Error")
                                self._draw_progress("Renamed", 1.0)
                            elif self._input_mode == self.MODE_COPY_SAME:
                                self._draw_progress("Copying...", 0.0)
                                if self._storage.copy(self._context_target_path, np):
                                    rn = True
                                else:
                                    print("Copy Error")
                                self._draw_progress("Copied", 1.0)
                    elif self._input_mode == self.MODE_MKDIR:
                        if not self._storage.exists(np):
                            if self._storage.mkdir(np):
                                rn = True
                            else:
                                print("Mkdir Error")
                if rn:
                    self._refresh_panes()
                
                if not self._confirm_menu:
                    self._input_active = False
                    self._is_shift = False
                    self._is_caps = False
                    self._context_target_path = ""
                    self._needs_redraw = True
            elif btn in (BUTTON_SHIFT, KEY_MOD_SHL, KEY_MOD_SHR, BUTTON_UP):
                self._is_shift = not self._is_shift
                self._needs_redraw = True
            elif btn in (BUTTON_CAPS_LOCK, KEY_CAPS_LOCK, BUTTON_DOWN):
                self._is_caps = not self._is_caps
                self._is_shift = False
                self._needs_redraw = True
            elif btn == BUTTON_LEFT:
                if self._input_cursor > 0:
                    self._input_cursor -= 1
                    self._needs_redraw = True
            elif btn == BUTTON_RIGHT:
                if self._input_cursor < len(self._input_text):
                    self._input_cursor += 1
                    self._needs_redraw = True
            elif btn == BUTTON_BACKSPACE:
                if self._input_cursor > 0:
                    self._input_text = self._input_text[:self._input_cursor - 1] + self._input_text[self._input_cursor:]
                    self._input_cursor -= 1
                    self._needs_redraw = True
            elif btn in self._char_map:
                if len(self._input_text) < 35:
                    c = self._char_map[btn]
                    if (self._is_shift or self._is_caps) and c.isalpha(): 
                        c = c.upper()
                    self._input_text = self._input_text[:self._input_cursor] + c + self._input_text[self._input_cursor:]
                    self._input_cursor += 1
                    if self._is_shift:
                        self._is_shift = False
                    self._needs_redraw = True
        
        # --- Main File Browser Input: Marking items ---
        elif btn == BUTTON_SPACE and not self._is_help_screen and not self._show_options and self._confirm_menu is None and self._context_menu is None and not self._input_active and not self._show_info:
            if self._mode == FILE_BROWSER_MANAGER:
                ap = self._app_state["active_pane"]
                cp = self._app_state["left_path"] if ap == self.PANE_LEFT else self._app_state["right_path"]
                fl = self._app_state["left_files"] if ap == self.PANE_LEFT else self._app_state["right_files"]
                ix = self._app_state["left_index"] if ap == self.PANE_LEFT else self._app_state["right_index"]
                
                if len(fl) > 0:
                    sf = fl[ix]
                    if sf != "..":
                        fp = f"/{sf}" if cp == "/" else f"{cp}/{sf}"
                        if fp in self._app_state["marked"]: self._app_state["marked"].remove(fp)
                        else: self._app_state["marked"].append(fp)
                        
                        if ap == self.PANE_LEFT: self._app_state["left_index"] = (ix + 1) % len(fl)
                        else: self._app_state["right_index"] = (ix + 1) % len(fl)
                        self._needs_redraw = True
            
        # --- Main File Browser Input: Hotkeys (Sort, Dir Mode, Help, Options, New, Info, Delete) ---
        elif btn == BUTTON_S and not self._is_help_screen and not self._show_options and self._confirm_menu is None and self._context_menu is None and not self._input_active:
            self._app_state["sort_mode"] = self.SORT_DATE if self._app_state.get("sort_mode", self.SORT_NAME) == self.SORT_NAME else self.SORT_NAME
            self._refresh_panes()
            self._app_state["left_index"] = self._app_state["right_index"] = 0
            self._needs_redraw = True
            
        elif btn == BUTTON_M and not self._is_help_screen and not self._show_options and self._confirm_menu is None and self._context_menu is None and not self._input_active:
            self._app_state["dir_menu"] = not self._app_state.get("dir_menu", True)
            self._needs_redraw = True
                
        elif btn == BUTTON_H and self._confirm_menu is None and self._context_menu is None and not self._input_active and not self._show_options:
            self._is_help_screen = not self._is_help_screen
            self._needs_redraw = True

        elif btn == BUTTON_O and not self._is_help_screen and self._confirm_menu is None and self._context_menu is None and not self._input_active:
            self._show_options = True
            self._opt_idx = 0
            self._needs_redraw = True

        elif btn == BUTTON_N and not self._is_help_screen and not self._show_options and self._confirm_menu is None and self._context_menu is None:
            if self._mode == FILE_BROWSER_MANAGER:
                self._input_active = True
                self._input_mode = self.MODE_MKDIR
                self._input_text = ""
                self._input_cursor = 0
                self._is_shift = False
                self._is_caps = False
                self._needs_redraw = True
            
        elif btn == BUTTON_I and not self._is_help_screen and not self._show_options and self._confirm_menu is None and self._context_menu is None and not self._show_info:
            ap = self._app_state["active_pane"]
            cp = self._app_state["left_path"] if ap == self.PANE_LEFT else self._app_state["right_path"]
            fl = self._app_state["left_files"] if ap == self.PANE_LEFT else self._app_state["right_files"]
            ix = self._app_state["left_index"] if ap == self.PANE_LEFT else self._app_state["right_index"]
            
            if len(fl) > 0:
                sf = fl[ix]
                if sf != "..":
                    fp = f"/{sf}" if cp == "/" else f"{cp}/{sf}"
                    isd = False
                    fz = 0
                    if fp in self._stat_cache:
                        isd = self._stat_cache[fp][0]
                        if not isd:
                            fz = self._storage.size(fp)
                    else:
                        isd = self._storage.is_directory(fp)
                        if not isd:
                            fz = self._storage.size(fp)
                        
                    self._info_data = [
                        f"Name: {sf[:22]}",
                        f"Type: {'Directory' if isd else 'File'}",
                        f"Size: {fz} bytes"
                    ]
                    self._show_info = True
                    self._needs_redraw = True

        elif btn == BUTTON_D and not self._is_help_screen and not self._show_options and self._confirm_menu is None and self._context_menu is None:
            if self._mode == FILE_BROWSER_MANAGER:
                mk = self._app_state["marked"]
                if len(mk) > 0:
                    self._pending_action = self.ACT_DELETE
                    self._confirm_menu = self._spawn_menu(f"Delete {len(mk)} items?", ("No", "Yes"))
                else:
                    ap = self._app_state["active_pane"]
                    cp = self._app_state["left_path"] if ap == self.PANE_LEFT else self._app_state["right_path"]
                    fl = self._app_state["left_files"] if ap == self.PANE_LEFT else self._app_state["right_files"]
                    ix = self._app_state["left_index"] if ap == self.PANE_LEFT else self._app_state["right_index"]
                    
                    if len(fl) > 0:
                        sf = fl[ix]
                        if sf != "..":
                            self._context_target_path = f"/{sf}" if cp == "/" else f"{cp}/{sf}"
                            self._pending_action = self.ACT_DELETE
                            self._confirm_menu = self._spawn_menu("Confirm Delete?", ("No", "Yes"))
            self._needs_redraw = True

        # --- Sub-View: Options Menu Input ---
        elif self._show_options:
            if btn in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER):
                self._show_options = False
                self._refresh_panes()
                self._needs_redraw = True
            elif btn == BUTTON_UP:
                self._opt_idx = (self._opt_idx - 1) % 10
                self._needs_redraw = True
            elif btn == BUTTON_DOWN:
                self._opt_idx = (self._opt_idx + 1) % 10
                self._needs_redraw = True
            elif btn in (BUTTON_LEFT, BUTTON_RIGHT):
                self._needs_redraw = True
                d = 1 if btn == BUTTON_RIGHT else -1
                idx = self._opt_idx
                if idx == 0: self._app_state["theme"] = (self._app_state.get("theme", 0) + d) % 4
                elif 1 <= idx <= 6:
                    k = ["", "bg_r", "bg_g", "bg_b", "bar_r", "bar_g", "bar_b"][idx]
                    self._app_state[k] = (self._app_state.get(k, 0) + (15 * d)) % 256
                elif idx == 7: self._app_state["sort_mode"] = self.SORT_DATE if self._app_state.get("sort_mode", self.SORT_NAME) == self.SORT_NAME else self.SORT_NAME
                elif idx == 8: self._app_state["show_hidden"] = not self._app_state.get("show_hidden", False)
                elif idx == 9: self._app_state["dir_menu"] = not self._app_state.get("dir_menu", True)

        # --- Sub-View: Confirm Overwrite/Delete Dialog Input ---
        elif self._confirm_menu is not None:
            if btn in (BUTTON_BACK, BUTTON_ESCAPE):
                self._confirm_menu = None
                self._pending_action = self.ACT_NONE
                self._pending_dest_path = ""
                self._needs_redraw = True
            elif btn == BUTTON_UP:
                self._confirm_menu.scroll_up()
                self._needs_redraw = True
            elif btn == BUTTON_DOWN:
                self._confirm_menu.scroll_down()
                self._needs_redraw = True
            elif btn == BUTTON_CENTER:
                sl = self._confirm_menu.current_item
                
                if sl == "Yes":
                    mk = self._app_state["marked"]
                    targets = mk if len(mk) > 0 else [self._context_target_path]
                    
                    if self._pending_action == self.ACT_DELETE:
                        total = len(targets)
                        for i, t in enumerate(targets):
                            self._draw_progress(f"Deleting {int((i/total)*100)}%", i/total)
                            if not self._storage.remove(t):
                                print("Delete Error on:", t)
                        self._draw_progress("Deleted", 1.0)
                            
                    elif self._pending_action in (self.ACT_COPY, self.ACT_MOVE):
                        total = len(targets)
                        act_name = "Copying" if self._pending_action == self.ACT_COPY else "Moving"
                        
                        if total == 1:
                            self._draw_progress(f"{act_name}...", 0.5)
                            
                        for i, t in enumerate(targets):
                            if total > 1:
                                self._draw_progress(f"Batch {act_name} {int((i/total)*100)}%", i/total)
                                
                            dp = self._pending_dest_path
                            if len(mk) > 0: 
                                dp = f"{dp}/{t.split('/')[-1]}".replace("//", "/")
                            
                            # Prevent crash from trying to copy a file over top of itself
                            if t != dp:
                                if self._storage.exists(dp):
                                    self._storage.remove(dp)
                                    
                                if self._pending_action == self.ACT_COPY:
                                    if not self._storage.copy(t, dp):
                                        print("Copy Error on:", t)
                                else:
                                    if not self._storage.move(t, dp):
                                        print("Move Error on:", t)
                        
                        self._draw_progress("Done", 1.0)
                                    
                    elif self._pending_action == self.ACT_RENAME:
                        self._draw_progress("Renaming...", 0.0)
                        if self._storage.exists(self._pending_dest_path):
                            self._storage.remove(self._pending_dest_path)
                        if not self._storage.move(self._context_target_path, self._pending_dest_path):
                            print("Rename Error")
                        self._draw_progress("Renamed", 1.0)
                    
                    if len(mk) > 0: self._app_state["marked"].clear()
                    if self._pending_action != self.ACT_NONE:
                        self._refresh_panes()

                self._confirm_menu = None
                self._pending_action = self.ACT_NONE
                self._context_target_path = self._pending_dest_path = ""
                self._needs_redraw = True
                
        # --- Sub-View: Context Menu (View, Edit, Copy, Delete) Input ---
        elif self._context_menu is not None:
            if btn in (BUTTON_BACK, BUTTON_ESCAPE):
                self._context_menu = None
                self._needs_redraw = True
            elif btn == BUTTON_UP:
                self._context_menu.scroll_up()
                self._needs_redraw = True
            elif btn == BUTTON_DOWN:
                self._context_menu.scroll_down()
                self._needs_redraw = True
            elif btn == BUTTON_CENTER:
                ac = self._context_menu.current_item
                
                if self._is_editing:
                    if ac in ("Save", "Save & Exit"):
                        self._draw_progress("Saving...", 0.5)
                        data = "\n".join(self._edit_text)
                        if self._storage.write(self._edit_file, data, "w"):
                            self._edit_unsaved = False
                        else:
                            print("Save Error")
                        del data
                        self._draw_progress("Saved", 1.0)
                        if ac == "Save & Exit": self._is_editing = False
                    elif ac == "Exit without Saving":
                        self._is_editing = False
                    self._context_menu = None
                    self._is_shift = False
                    self._is_caps = False
                    self._needs_redraw = True
                else:
                    if ac == "Cancel":
                        pass
                    elif ac == "Clear Marks":
                        self._app_state["marked"].clear()
                        self._refresh_panes()
                    elif ac == "Open":
                        if self._app_state["active_pane"] == self.PANE_LEFT:
                            self._app_state["left_path"] = self._context_target_path
                            self._app_state["left_index"] = 0
                        else:
                            self._app_state["right_path"] = self._context_target_path
                            self._app_state["right_index"] = 0
                        self._refresh_panes()
                    elif ac == "View":
                        self._open_viewer(self._context_target_path)
                    elif ac == "Edit":
                        self._open_editor(self._context_target_path, read_only=False)
                    elif ac == "Delete":
                        self._pending_action = self.ACT_DELETE
                        mk = self._app_state["marked"]
                        msg = f"Delete {len(mk)} items?" if len(mk) > 0 else "Confirm Delete?"
                        self._confirm_menu = self._spawn_menu(msg, ("No", "Yes"))
                    elif ac == "Rename":
                        self._input_active = True
                        self._input_text = self._context_target_path.split("/")[-1]
                        self._input_cursor = len(self._input_text)
                        self._input_mode = self.MODE_RENAME
                        self._is_shift = False
                        self._is_caps = False
                    elif ac in ("Copy", "Move"):
                        ap = self._app_state["active_pane"]
                        td = self._app_state["right_path"] if ap == self.PANE_LEFT else self._app_state["left_path"]
                        mk = self._app_state["marked"]
                        
                        if len(mk) > 0:
                            self._pending_action = self.ACT_COPY if ac == "Copy" else self.ACT_MOVE
                            self._pending_dest_path = td
                            self._confirm_menu = self._spawn_menu(f"Confirm {ac}?", ("No", "Yes"))
                        else:
                            fn = self._context_target_path.split("/")[-1]
                            dp = f"/{fn}" if td == "/" else f"/{td}/{fn}".replace("//", "/")
                            
                            if dp == self._context_target_path:
                                self._input_active = True
                                self._input_text = fn
                                self._input_cursor = len(self._input_text)
                                self._input_mode = self.MODE_COPY_SAME if ac == "Copy" else self.MODE_RENAME
                                self._is_shift = False
                                self._is_caps = False
                            else:
                                self._pending_action = self.ACT_COPY if ac == "Copy" else self.ACT_MOVE
                                self._pending_dest_path = dp
                                ex = self._storage.exists(dp)
                                msg = "Overwrite?" if ex else f"Confirm {ac}?"
                                self._confirm_menu = self._spawn_menu(msg, ("No", "Yes"))
                            
                    self._context_menu = None
                    self._needs_redraw = True

        # --- Main File Browser Input: Navigation and Exiting ---
        elif btn in (BUTTON_BACK, BUTTON_ESCAPE):
            if self._is_help_screen:
                self._is_help_screen = False
                self._needs_redraw = True
            else:
                return False
            
        elif btn == BUTTON_LEFT and not self._is_help_screen:
            self._app_state["active_pane"] = self.PANE_LEFT
            self._needs_redraw = True
            
        elif btn == BUTTON_RIGHT and not self._is_help_screen:
            self._app_state["active_pane"] = self.PANE_RIGHT
            self._needs_redraw = True
            
        elif btn == BUTTON_UP and not self._is_help_screen:
            ap = self._app_state["active_pane"]
            fl = self._app_state["left_files"] if ap == self.PANE_LEFT else self._app_state["right_files"]
            ix = self._app_state["left_index"] if ap == self.PANE_LEFT else self._app_state["right_index"]
            
            fln = len(fl)
            if fln > 0:
                if ap == self.PANE_LEFT: self._app_state["left_index"] = (ix - 1) % fln
                else: self._app_state["right_index"] = (ix - 1) % fln
                self._needs_redraw = True
            
        elif btn == BUTTON_DOWN and not self._is_help_screen:
            ap = self._app_state["active_pane"]
            fl = self._app_state["left_files"] if ap == self.PANE_LEFT else self._app_state["right_files"]
            ix = self._app_state["left_index"] if ap == self.PANE_LEFT else self._app_state["right_index"]
            
            fln = len(fl)
            if fln > 0:
                if ap == self.PANE_LEFT: self._app_state["left_index"] = (ix + 1) % fln
                else: self._app_state["right_index"] = (ix + 1) % fln
                self._needs_redraw = True

        elif btn == BUTTON_CENTER and not self._is_help_screen:
            ap = self._app_state["active_pane"]
            cp = self._app_state["left_path"] if ap == self.PANE_LEFT else self._app_state["right_path"]
            fl = self._app_state["left_files"] if ap == self.PANE_LEFT else self._app_state["right_files"]
            ix = self._app_state["left_index"] if ap == self.PANE_LEFT else self._app_state["right_index"]
            
            if len(fl) > 0:
                sf = fl[ix]
                if sf == "..":
                    pts = cp.rstrip("/").split("/")
                    fe = pts[-1] if len(pts) > 1 else ""
                    pr = "/" + "/".join(pts[1:-1])
                    if pr in ("//", ""): pr = "/"
                        
                    if ap == self.PANE_LEFT: self._app_state["left_path"] = pr
                    else: self._app_state["right_path"] = pr
                    
                    self._refresh_panes()
                    
                    nf = self._app_state["left_files"] if ap == self.PANE_LEFT else self._app_state["right_files"]
                    try: nix = nf.index(fe)
                    except ValueError: nix = 0
                            
                    if ap == self.PANE_LEFT: self._app_state["left_index"] = nix
                    else: self._app_state["right_index"] = nix
                else:
                    np = f"/{sf}" if cp == "/" else f"{cp}/{sf}"
                    
                    isd = False
                    if np in self._stat_cache:
                        isd = self._stat_cache[np][0]
                    else:
                        isd = self._storage.is_directory(np)
                    
                    if self._mode == FILE_BROWSER_SELECTOR and not isd:
                        self._auto_save()
                        return False

                    mk = self._app_state["marked"]
                    
                    if isd and not self._app_state.get("dir_menu", True) and len(mk) == 0:
                        if ap == self.PANE_LEFT:
                            self._app_state["left_path"] = np
                            self._app_state["left_index"] = 0
                        else:
                            self._app_state["right_path"] = np
                            self._app_state["right_index"] = 0
                        self._refresh_panes()
                    elif self._mode == FILE_BROWSER_MANAGER and len(mk) > 0:
                        self._context_target_path = np
                        items = ["Open"] if isd else []
                        items.extend(["Copy", "Move", "Delete", "Clear Marks", "Cancel"])
                        self._context_menu = self._spawn_menu(f"{len(mk)} Marked", items)
                    else:
                        self._context_target_path = np
                        
                        # Strip "Edit" option for images to prevent binary corruption/crashing
                        if isd:
                            items = ["Open"]
                        else:
                            is_img = np.lower().endswith((".jpg", ".jpeg", ".bmp"))
                            items = ["View"] if is_img else ["View", "Edit"]
                            
                        if self._mode == FILE_BROWSER_MANAGER:
                            items.extend(["Copy", "Move", "Rename", "Delete"])
                        items.append("Cancel")
                        self._context_menu = self._spawn_menu(sf[:14], items)
                self._needs_redraw = True

        if self._needs_redraw:
            self._draw_ui()
            
        self._auto_save()
        return True

_app_instance = None

def start(view_manager):
    global _app_instance
    _app_instance = FileBrowser(view_manager, FILE_BROWSER_MANAGER)
    return True

def run(view_manager):
    if not _app_instance.run():
        view_manager.back()

def stop(view_manager):
    global _app_instance
    if _app_instance:
        del _app_instance
        _app_instance = None
        gc.collect()