import gc
import time
import json
import os
from micropython import const
from picoware.system.vector import Vector
from picoware.system.colors import TFT_WHITE, TFT_BLACK, TFT_BLUE, TFT_YELLOW, TFT_CYAN, TFT_DARKGREY, TFT_LIGHTGREY, TFT_RED
from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_CENTER, BUTTON_BACK, BUTTON_H, BUTTON_O, BUTTON_BACKSPACE, BUTTON_ESCAPE
from picoware.gui.menu import Menu
from picoware.system.system import System

try:
    from picoware.system.buttons import BUTTON_S, BUTTON_A, BUTTON_Z, BUTTON_0, BUTTON_9, BUTTON_SPACE, BUTTON_N, BUTTON_D, BUTTON_I
except ImportError:
    BUTTON_S = -99
    BUTTON_A = 97
    BUTTON_Z = 122
    BUTTON_0 = 48
    BUTTON_9 = 57
    BUTTON_SPACE = 32
    BUTTON_N = 110
    BUTTON_D = 100
    BUTTON_I = 105

FILE_BROWSER_VIEWER = const(0)
FILE_BROWSER_MANAGER = const(1)
FILE_BROWSER_SELECTOR = const(2)

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

def rgb_to_565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

class FileBrowser:
    
    def __init__(self, view_manager, mode=FILE_BROWSER_SELECTOR, start_directory=""):
        self._vm = view_manager
        self._mode = mode
        self._storage = view_manager.storage
        self._draw = view_manager.draw
        self._input_manager = view_manager.input_manager
        self._sys = System()
        self._last_saved_json = "{}"
        self._last_save_time = 0
        self._is_help_screen = False
        self._is_disclaimer_screen = False
        self._show_options = False
        self._opt_idx = 0
        self._context_menu = None
        self._confirm_menu = None
        self._input_active = False
        self._input_text = ""
        self._input_cursor = 0
        self._input_mode = MODE_NONE
        self._context_target_path = ""
        self._pending_action = ACT_NONE
        self._pending_dest_path = ""
        self._needs_redraw = True
        self._show_info = False
        self._info_data = []
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
        self._image_path = ""
        self._jpeg_vec = Vector(0, 0)
        self._char_map = {}
        self._app_state = {
            "left_path": start_directory if start_directory else "/",
            "right_path": start_directory if start_directory else "/",
            "left_files": [],
            "right_files": [],
            "left_index": 0,
            "right_index": 0,
            "active_pane": PANE_LEFT,
            "sort_mode": SORT_NAME,
            "show_hidden": False,
            "dir_menu": True,
            "disclaimer_accepted": False,
            "theme": 0,
            "bg_r": 0, "bg_g": 0, "bg_b": 170,
            "bar_r": 0, "bar_g": 170, "bar_b": 170,
            "marked": []
        }
        self.start()

    def __del__(self):
        self._auto_save()
        if self._context_menu:
            del self._context_menu
        if self._confirm_menu:
            del self._confirm_menu
        self._app_state["left_files"].clear()
        self._app_state["right_files"].clear()
        self._app_state["marked"].clear()
        self._app_state.clear()
        self._edit_text.clear()
        self._char_map.clear()
        self._sys = None
        gc.collect()

    @property
    def directory(self) -> str:
        _dir = self._app_state["left_path"] if self._app_state["active_pane"] == PANE_LEFT else self._app_state["right_path"]
        if _dir.startswith("/sd/"):
            _dir = _dir[3:]
        return _dir

    @property
    def path(self) -> str:
        act = self._app_state["active_pane"]
        p_dir = self._app_state["left_path"] if act == PANE_LEFT else self._app_state["right_path"]
        f_lst = self._app_state["left_files"] if act == PANE_LEFT else self._app_state["right_files"]
        idx = self._app_state["left_index"] if act == PANE_LEFT else self._app_state["right_index"]
        if len(f_lst) == 0:
            return p_dir
        fname = f_lst[idx][0]
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
        th = self._app_state.get("theme", 0)
        if th == 0:
            return TFT_BLUE, TFT_CYAN, TFT_WHITE, TFT_YELLOW, TFT_BLACK
        elif th == 1:
            return TFT_BLACK, TFT_WHITE, TFT_WHITE, TFT_WHITE, TFT_BLACK
        else:
            c_bg = rgb_to_565(self._app_state.get("bg_r", 0), self._app_state.get("bg_g", 0), self._app_state.get("bg_b", 170))
            c_bar = rgb_to_565(self._app_state.get("bar_r", 0), self._app_state.get("bar_g", 170), self._app_state.get("bar_b", 170))
            return c_bg, c_bar, TFT_WHITE, TFT_YELLOW, TFT_BLACK

    def _force_sync(self):
        time.sleep(0.3)
        try:
            os.sync()
        except Exception:
            pass

    def _exists(self, path):
        if path in ("/", ""):
            return True
        try:
            if self._storage.exists(path):
                return True
        except Exception:
            pass
        try:
            target_dir = path[:path.rfind("/")]
            if target_dir == "": target_dir = "/"
            target_file = path[path.rfind("/")+1:]
            if target_dir == self._app_state.get("left_path"):
                for f in self._app_state.get("left_files", []):
                    if f[0] == target_file:
                        return True
            if target_dir == self._app_state.get("right_path"):
                for f in self._app_state.get("right_files", []):
                    if f[0] == target_file:
                        return True
        except Exception:
            pass
        return False

    def _auto_save(self):
        curr_t = time.time()
        if curr_t - self._last_save_time > 5:
            save_dict = {k: self._app_state[k] for k in ["left_path", "right_path", "sort_mode", "active_pane", "show_hidden", "dir_menu", "disclaimer_accepted", "theme", "bg_r", "bg_g", "bg_b", "bar_r", "bar_g", "bar_b"]}
            curr_j = json.dumps(save_dict)
            if curr_j != self._last_saved_json:
                try:
                    self._storage.write("/picoware/settings/picocmd_state.json", curr_j, "w")
                    self._last_saved_json = curr_j
                except Exception:
                    pass
            del curr_j
            del save_dict
            gc.collect()
            self._last_save_time = curr_t

    def start(self):
        for d in ("/picoware", "/picoware/settings"):
            try:
                self._storage.mkdir(d)
            except Exception:
                pass
        try:
            data = self._storage.read("/picoware/settings/picocmd_state.json", "r")
            if data:
                loaded = json.loads(data)
                self._app_state.update({k: loaded.get(k, self._app_state[k]) for k in self._app_state})
                self._last_saved_json = json.dumps(self._app_state)
                del loaded
            del data
        except Exception:
            pass
        if not self._app_state["disclaimer_accepted"]:
            self._is_disclaimer_screen = True
        try:
            import picoware.system.buttons as __btns
            for i in range(26):
                c = chr(97 + i)
                if hasattr(__btns, f"BUTTON_{c.upper()}"): self._char_map[getattr(__btns, f"BUTTON_{c.upper()}")] = c
            for i in range(10):
                c = str(i)
                if hasattr(__btns, f"BUTTON_{c}"): self._char_map[getattr(__btns, f"BUTTON_{c}")] = c
            for a, ch in [("BUTTON_SPACE", " "), ("BUTTON_PERIOD", "."), ("BUTTON_MINUS", "-"), ("BUTTON_UNDERSCORE", "_")]:
                if hasattr(__btns, a): self._char_map[getattr(__btns, a)] = ch
        except Exception:
            pass
        self._refresh_panes()
        self._needs_redraw = True
        gc.collect()
        return True

    def _rmtree(self, path):
        try:
            is_d = False
            try: is_d = self._storage.is_directory(path)
            except Exception: pass
            if is_d:
                for itm in self._storage.listdir(path):
                    if itm not in (".", ".."):
                        self._rmtree(f"/{itm}" if path == "/" else f"{path}/{itm}")
                try: self._storage.rmdir(path)
                except Exception:
                    try: self._storage.remove(path)
                    except Exception: pass
            else:
                self._storage.remove(path)
        except Exception: pass
        gc.collect()

    def _draw_progress(self, title, percentage):
        c_bg, c_bar, _, _, _ = self._get_theme()
        sw, sh = self._draw.size.x, self._draw.size.y
        bw, bh = 200, 60
        x, y = (sw - bw) // 2, (sh - bh) // 2
        self._draw.fill_rectangle(Vector(x, y), Vector(bw, bh), c_bg)
        self._draw.rect(Vector(x, y), Vector(bw, bh), c_bar)
        self._draw.text(Vector(x + 10, y + 10), title, TFT_WHITE)
        self._draw.rect(Vector(x + 10, y + 30), Vector(bw - 20, 15), TFT_WHITE)
        fill_w = int((bw - 22) * percentage)
        if fill_w > 0: self._draw.fill_rectangle(Vector(x + 11, y + 31), Vector(fill_w, 13), c_bar)
        self._draw.swap()

    def _copy_item(self, src, dst):
        is_d = False
        try: is_d = self._storage.is_directory(src)
        except Exception: pass
        if is_d:
            try: self._storage.mkdir(dst)
            except Exception: pass
            try:
                for itm in self._storage.listdir(src):
                    if itm not in (".", ".."):
                        self._copy_item(f"{src}/{itm}" if src != "/" else f"/{itm}", f"{dst}/{itm}" if dst != "/" else f"/{itm}")
            except Exception: pass
        else:
            try:
                f_sz = self._storage.size(src)
                pos = 0
                while pos < f_sz:
                    try: chk = self._storage.read_chunked(src, pos, 2048)
                    except Exception: break
                    if not chk: break
                    self._storage.write(dst, chk, "ab" if pos > 0 else "wb")
                    pos += len(chk)
                    del chk
                    if f_sz > 0: self._draw_progress(f"Copying {int((pos/f_sz)*100)}%", min(1.0, pos / f_sz))
                    gc.collect()
            except Exception: pass
        gc.collect()

    def _load_dir(self, path):
        items = []
        show_hid = self._app_state.get("show_hidden", False)
        sort_m = self._app_state["sort_mode"]
        try:
            d_list = self._storage.listdir(path)
            for itm in d_list:
                if itm in (".", "..") or (not show_hid and itm.startswith(".")): continue
                f_p = f"/{itm}" if path == "/" else f"{path}/{itm}"
                is_d, mt, sz = False, 0, 0
                try: is_d = self._storage.is_directory(f_p)
                except Exception: pass
                if not is_d:
                    try: sz = self._storage.size(f_p)
                    except Exception: pass
                if sort_m == SORT_DATE:
                    try: mt = os.stat(f_p)[8]
                    except Exception: pass
                items.append((itm, is_d, mt, sz))
            del d_list
            if sort_m == SORT_NAME: items.sort(key=lambda x: (not x[1], x[0].lower()))
            else: items.sort(key=lambda x: (not x[1], x[0].lower() if x[1] else -x[2]))
            for i in range(len(items)): items[i] = (items[i][0], items[i][1], items[i][3])
        except Exception:
            items = [("<ERROR>", False, 0)]
        gc.collect()
        return [("..", True, 0)] + items if path != "/" else items

    def _refresh_panes(self):
        self._app_state["left_files"].clear()
        self._app_state["left_files"] = self._load_dir(self._app_state["left_path"])
        self._app_state["left_index"] = max(0, min(self._app_state["left_index"], len(self._app_state["left_files"]) - 1))
        self._app_state["right_files"].clear()
        self._app_state["right_files"] = self._load_dir(self._app_state["right_path"])
        self._app_state["right_index"] = max(0, min(self._app_state["right_index"], len(self._app_state["right_files"]) - 1))

    def _open_viewer(self, path):
        ext = path.split(".")[-1].lower() if "." in path else ""
        if ext in ("jpg", "jpeg", "bmp"):
            self._is_viewing_image = True
            self._image_path = path
            self._needs_redraw = True
        else:
            self._open_editor(path, read_only=True)

    def _open_editor(self, path, read_only=False):
        self._edit_text.clear()
        try:
            data = self._storage.read(path, "r")
            if data: self._edit_text.extend(data.split('\n'))
            del data
        except Exception: pass
        gc.collect()
        if not self._edit_text: self._edit_text.append("")
        self._edit_file = path
        self._edit_read_only = read_only
        self._edit_cx = self._edit_cy = self._edit_sx = self._edit_sy = 0
        self._edit_unsaved = False
        self._is_editing = True
        self._needs_redraw = True

    def _draw_ui(self):
        c_bg, c_bar, c_txt, c_dir, c_btxt = self._get_theme()
        d_clr, f_rect, d_rect, d_txt, d_swp = self._draw.clear, self._draw.fill_rectangle, self._draw.rect, self._draw.text, self._draw.swap
        sw, sh, mx = self._draw.size.x, self._draw.size.y, self._draw.size.x // 2

        if self._is_viewing_image:
            d_clr(color=TFT_BLACK)
            if self._image_path.lower().endswith("bmp"):
                self._draw.image_bmp(self._jpeg_vec, self._image_path, self._storage)
            else:
                self._draw.image_jpeg(self._jpeg_vec, self._image_path, self._storage)
            f_rect(Vector(0, sh - 12), Vector(sw, 12), c_bar)
            d_txt(Vector(2, sh - 10), "ESC / BACK : Close Image", c_btxt)
            d_swp()
            self._needs_redraw = False
            return

        if self._is_editing:
            d_clr(color=c_bg)
            f_rect(Vector(0, 0), Vector(sw, 12), c_bar)
            mode_s = "View" if self._edit_read_only else "Edit"
            mod_s = "*" if self._edit_unsaved and not self._edit_read_only else ""
            d_txt(Vector(2, 2), f"{mode_s}: {self._edit_file.split('/')[-1]}{mod_s}", c_btxt)
            m_lin, m_chr = (sh - 24) // 12, (sw - 4) // 6
            for i in range(m_lin):
                idx = self._edit_sy + i
                if idx < len(self._edit_text):
                    d_txt(Vector(2, 14 + i * 12), self._edit_text[idx][self._edit_sx : self._edit_sx + m_chr], c_txt)
            if not self._edit_read_only and (time.ticks_ms() // 500) % 2 == 0:
                cx, cy = 2 + (self._edit_cx - self._edit_sx) * 6, 14 + (self._edit_cy - self._edit_sy) * 12
                if 0 <= cx < sw and 12 < cy < sh - 12:
                    f_rect(Vector(cx, cy - 1), Vector(6, 11), TFT_CYAN)
                    try: d_txt(Vector(cx, cy), self._edit_text[self._edit_cy][self._edit_cx], TFT_BLACK)
                    except IndexError: pass
            if not self._edit_read_only:
                self._needs_redraw = True
                
            f_rect(Vector(0, sh - 12), Vector(sw, 12), c_bar)
            d_txt(Vector(2, sh - 10), "UP/DWN:Scroll ESC:Close" if self._edit_read_only else "ENT:Menu ESC:Close", c_btxt)
            if self._context_menu:
                self._context_menu.draw()
                self._needs_redraw = False
            d_swp()
            return

        d_clr(color=c_bg)
        
        if self._is_disclaimer_screen:
            f_rect(Vector(10, 50), Vector(sw - 20, 140), TFT_BLACK)
            d_rect(Vector(10, 50), Vector(sw - 20, 140), TFT_RED)
            f_rect(Vector(10, 50), Vector(sw - 20, 20), TFT_RED)
            d_txt(Vector(15, 54), "WARNING", TFT_WHITE)
            d_txt(Vector(20, 85), "With this app it is", TFT_WHITE)
            d_txt(Vector(20, 100), "possible to delete ANY", TFT_WHITE)
            d_txt(Vector(20, 115), "file on the SD card.", TFT_WHITE)
            d_txt(Vector(20, 130), "Please be careful!", TFT_WHITE)
            f_rect(Vector(10, 170), Vector(sw - 20, 20), TFT_RED)
            d_txt(Vector(15, 174), "[CENTER/ENT] I Understand", TFT_WHITE)
            d_swp()
            self._needs_redraw = False
            return

        if self._is_help_screen:
            d_txt(Vector(10, 10), "PicoCommander Help", TFT_WHITE)
            d_txt(Vector(10, 24), "SPC:Mark H:Help O:Opt", c_bar)
            d_txt(Vector(10, 36), "I:Info N:NewFolder D:Del", c_bar)
            d_txt(Vector(10, 48), "UP/DOWN: Scroll", TFT_WHITE)
            d_txt(Vector(10, 60), "L/R: Switch Pane", TFT_WHITE)
            d_txt(Vector(10, 72), "CENTER: Menu (View/Edit...)", TFT_WHITE)
            d_txt(Vector(10, 84), "BACK: Exit App", TFT_WHITE)
            d_txt(Vector(10, 126), f"RAM: {gc.mem_alloc() // 1024}KB used / {gc.mem_free() // 1024}KB free", TFT_YELLOW)
            if self._sys and self._sys.has_psram:
                d_txt(Vector(10, 138), f"PSRAM: {self._sys.used_psram // 1024}KB used / {self._sys.free_psram // 1024}KB free", TFT_YELLOW)
            d_txt(Vector(10, sh - 40), "made by Slasher006", c_bar)
            d_txt(Vector(10, sh - 30), "with the help of Gemini", c_bar)
            d_txt(Vector(10, sh - 20), "Date: 2026-03-06 | v1.17", c_bar)
            d_swp()
            self._needs_redraw = False
            return

        if self._show_info:
            bx, by, bw, bh = (sw - 200) // 2, (sh - 100) // 2, 200, 100
            f_rect(Vector(bx, by), Vector(bw, bh), TFT_BLACK)
            d_rect(Vector(bx, by), Vector(bw, bh), c_bar)
            f_rect(Vector(bx, by), Vector(bw, 16), c_bar)
            d_txt(Vector(bx + 5, by + 2), "FILE INFORMATION", c_btxt)
            for i, ln in enumerate(self._info_data): d_txt(Vector(bx + 10, by + 25 + (i * 15)), ln, TFT_WHITE)
            d_txt(Vector(bx + 10, by + bh - 15), "[ESC/ENT] Close", TFT_LIGHTGREY)
            d_swp()
            self._needs_redraw = False
            return

        if self._show_options:
            f_rect(Vector(10, 10), Vector(sw - 20, sh - 20), TFT_BLACK)
            d_rect(Vector(10, 10), Vector(sw - 20, sh - 20), c_bar)
            f_rect(Vector(10, 10), Vector(sw - 20, 20), c_bar)
            d_txt(Vector(15, 14), "OPTIONS MENU", c_btxt)
            for i, l in enumerate(OPTIONS_LABELS):
                yp = 35 + (i * 15)
                tc = c_bar if i == self._opt_idx else TFT_WHITE
                if i == self._opt_idx: f_rect(Vector(12, yp - 2), Vector(sw - 24, 13), TFT_DARKGREY)
                d_txt(Vector(20, yp), l + ":", tc)
                v = ""
                if i == 0: v = ("Classic", "Dark", "Custom")[self._app_state.get("theme", 0)]
                elif i in range(1, 7): v = str(self._app_state.get(["", "bg_r", "bg_g", "bg_b", "bar_r", "bar_g", "bar_b"][i], 0 if i not in (3,5,6) else 170))
                elif i == 7: v = "Name" if self._app_state.get("sort_mode", SORT_NAME) == SORT_NAME else "Date"
                elif i == 8: v = "Show" if self._app_state.get("show_hidden", False) else "Hide"
                elif i == 9: v = "Menu" if self._app_state.get("dir_menu", True) else "Open"
                d_txt(Vector(130, yp), f"< {v} >", tc)
            pbg = rgb_to_565(self._app_state.get("bg_r",0), self._app_state.get("bg_g",0), self._app_state.get("bg_b",170))
            pbr = rgb_to_565(self._app_state.get("bar_r",0), self._app_state.get("bar_g",170), self._app_state.get("bar_b",170))
            d_txt(Vector(20, 185), "Custom Preview:", TFT_LIGHTGREY)
            f_rect(Vector(140, 183), Vector(60, 20), pbg)
            d_rect(Vector(140, 183), Vector(60, 20), pbr)
            f_rect(Vector(10, sh - 30), Vector(sw - 20, 20), c_bar)
            d_txt(Vector(15, sh - 26), "[L/R] Edit   [ESC/ENT] Save", c_btxt)
            d_swp()
            self._needs_redraw = False
            return

        if self._input_active:
            by = (sh - 70) // 2
            f_rect(Vector(10, by), Vector(sw - 20, 70), TFT_BLACK)
            d_rect(Vector(10, by), Vector(sw - 20, 70), c_bar)
            f_rect(Vector(10, by), Vector(sw - 20, 16), c_bar)
            ts = "RENAME FILE:" if self._input_mode == MODE_RENAME else "COPY AS:" if self._input_mode == MODE_COPY_SAME else "NEW FOLDER:"
            d_txt(Vector(15, by + 2), ts, c_btxt)
            d_txt(Vector(15, by + 24), self._input_text, TFT_WHITE)
            if (time.ticks_ms() // 500) % 2 == 0:
                f_rect(Vector(15 + (self._input_cursor * 6), by + 35), Vector(6, 2), TFT_CYAN)
            self._needs_redraw = True
            d_txt(Vector(15, by + 48), "[ENT] Save  [ESC] Cancel", TFT_LIGHTGREY)
            d_swp()
            return

        if self._confirm_menu:
            self._confirm_menu.draw()
            d_swp()
            self._needs_redraw = False
            return

        if self._context_menu:
            self._context_menu.draw()
            d_swp()
            self._needs_redraw = False
            return

        f_rect(Vector(0, 0), Vector(sw, 12), c_bar)
        ss = "Name" if self._app_state["sort_mode"] == SORT_NAME else "Date"
        ms = "Viewer" if self._mode == FILE_BROWSER_VIEWER else "Select" if self._mode == FILE_BROWSER_SELECTOR else "Manager"
        d_txt(Vector(2, 2), f"PicoCmd v1.17 [{ms}] [{ss}]", c_btxt)
        f_rect(Vector(mx, 12), Vector(1, sh - 24), c_bar)
        
        c_lim, n_lim, m_itm = (mx - 8) // 6, ((mx - 8) // 6) - 6, (sh - 38) // 12
        ap = self._app_state["active_pane"]

        for pn in (PANE_LEFT, PANE_RIGHT):
            il = pn == PANE_LEFT
            xb = 0 if il else mx + 1
            ps = self._app_state["left_path"] if il else self._app_state["right_path"]
            fl = self._app_state["left_files"] if il else self._app_state["right_files"]
            ix = self._app_state["left_index"] if il else self._app_state["right_index"]
            si = max(0, ix - (m_itm - 1))
            
            if ap == pn: f_rect(Vector(xb, 12), Vector(mx - (0 if il else 1), 12), c_bar)
            d_txt(Vector(xb + 2, 14), ps[:c_lim], c_btxt if ap == pn else c_txt)
            
            yo = 26
            for i, idt in enumerate(fl[si : si + m_itm]):
                fn, idr, fz = idt
                ai = i + si
                dn = f"/{fn}" if idr else fn
                fp = f"/{fn}" if ps == "/" else f"{ps}/{fn}"
                im = fp in self._app_state["marked"]
                
                bc = TFT_RED if im else (c_dir if idr else c_txt)
                tc = bc if ap != pn or ai != ix else c_btxt
                
                if ap == pn and ai == ix: f_rect(Vector(xb + (0 if il else 1), yo - 1), Vector(mx - (2 if il else 3), 10), c_bar)
                
                if idr: szs = "<DIR>"
                elif fz < 1024: szs = f"{fz}B"
                elif fz < 1048576: szs = f"{fz//1024}K"
                else: szs = f"{fz//1048576}M"
                    
                pl = max(0, c_lim - len(dn[:n_lim]) - len(szs))
                d_txt(Vector(xb + 2, yo), dn[:n_lim] + (" " * pl) + szs, tc)
                yo += 12

        f_rect(Vector(0, sh - 12), Vector(sw, 12), c_bar)
        if self._mode == FILE_BROWSER_SELECTOR:
            d_txt(Vector(2, sh - 10), "ENT:Select O:Opt H:Help ESC:Exit", c_btxt)
        else:
            d_txt(Vector(2, sh - 10), "ENT:Menu O:Opt H:Help ESC:Exit", c_btxt)
        d_swp()
        self._needs_redraw = False

    def run(self):
        btn = self._input_manager.button
        key = self._input_manager.read_non_blocking()
        irs = self._input_manager.reset
        c_bg, c_bar, _, _, _ = self._get_theme()
        sh = self._draw.size.y

        isp = False
        cta = ""
        if self._char_map is not None and btn in self._char_map:
            isp = True
            cta = self._char_map[btn]
        elif key and isinstance(key, str) and len(key) == 1 and 32 <= ord(key) <= 126:
            isp = True
            cta = key
            
        ien = (btn == BUTTON_CENTER and not isp) or key in ('\n', '\r') or btn in (10, 13)
        ies = (btn in (BUTTON_BACK, BUTTON_ESCAPE) and not isp) or key == '\x1b'
        ibs = (btn == BUTTON_BACKSPACE and not isp) or key in ('\x08', '\x7f') or btn in (8, 127)
        ilf = (btn == BUTTON_LEFT and not isp) or key == '\x1b[D'
        irt = (btn == BUTTON_RIGHT and not isp) or key == '\x1b[C'
        iup = (btn == BUTTON_UP and not isp) or key == '\x1b[A'
        idn = (btn == BUTTON_DOWN and not isp) or key == '\x1b[B'

        if self._is_viewing_image:
            if ies or ien:
                irs()
                self._is_viewing_image = False
                self._image_path = ""
                self._needs_redraw = True
                time.sleep(0.3)

        elif self._is_editing and self._context_menu is None and self._confirm_menu is None:
            if ies:
                irs()
                if self._edit_unsaved and not self._edit_read_only:
                    self._context_menu = Menu(self._draw, "Unsaved Changes!", 0, sh, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2)
                    self._context_menu.add_item("Save & Exit")
                    self._context_menu.add_item("Exit without Saving")
                    self._context_menu.add_item("Cancel")
                    self._context_menu.set_selected(0)
                else:
                    self._is_editing = False
                self._needs_redraw = True
                time.sleep(0.3)
            elif iup:
                irs()
                if self._edit_read_only:
                    if self._edit_sy > 0: self._edit_sy -= 1
                elif self._edit_cy > 0:
                    self._edit_cy -= 1
                    self._edit_cx = min(self._edit_cx, len(self._edit_text[self._edit_cy]))
                self._needs_redraw = True
                time.sleep(0.1)
            elif idn:
                irs()
                if self._edit_read_only:
                    ml = (sh - 24) // 12
                    if self._edit_sy + ml < len(self._edit_text): self._edit_sy += 1
                elif self._edit_cy < len(self._edit_text) - 1:
                    self._edit_cy += 1
                    self._edit_cx = min(self._edit_cx, len(self._edit_text[self._edit_cy]))
                self._needs_redraw = True
                time.sleep(0.1)
            elif ilf:
                irs()
                if self._edit_read_only:
                    if self._edit_sx > 0: self._edit_sx -= 1
                elif self._edit_cx > 0:
                    self._edit_cx -= 1
                elif self._edit_cy > 0:
                    self._edit_cy -= 1
                    self._edit_cx = len(self._edit_text[self._edit_cy])
                self._needs_redraw = True
                time.sleep(0.1)
            elif irt:
                irs()
                if self._edit_read_only:
                    if self._edit_sx < 500: self._edit_sx += 1
                elif self._edit_cx < len(self._edit_text[self._edit_cy]):
                    self._edit_cx += 1
                elif self._edit_cy < len(self._edit_text) - 1:
                    self._edit_cy += 1
                    self._edit_cx = 0
                self._needs_redraw = True
                time.sleep(0.1)
            elif not self._edit_read_only:
                if ien:
                    irs()
                    line = self._edit_text[self._edit_cy]
                    self._edit_text.insert(self._edit_cy + 1, line[self._edit_cx:])
                    self._edit_text[self._edit_cy] = line[:self._edit_cx]
                    self._edit_cy += 1
                    self._edit_cx = 0
                    self._edit_unsaved = True
                    self._needs_redraw = True
                    time.sleep(0.1)
                elif btn == BUTTON_CENTER:
                    irs()
                    self._context_menu = Menu(self._draw, "Editor Menu", 0, sh, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2)
                    self._context_menu.add_item("Save")
                    self._context_menu.add_item("Save & Exit")
                    self._context_menu.add_item("Exit without Saving")
                    self._context_menu.add_item("Cancel")
                    self._context_menu.set_selected(0)
                    self._needs_redraw = True
                    time.sleep(0.3)
                elif ibs:
                    irs()
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
                    time.sleep(0.1)
                elif isp:
                    irs()
                    line = self._edit_text[self._edit_cy]
                    self._edit_text[self._edit_cy] = line[:self._edit_cx] + cta + line[self._edit_cx:]
                    self._edit_cx += 1
                    self._edit_unsaved = True
                    self._needs_redraw = True
                    time.sleep(0.1)
                
            if self._needs_redraw and not self._edit_read_only:
                ml = (sh - 24) // 12
                mc = (self._draw.size.x - 4) // 6
                if self._edit_cy < self._edit_sy: self._edit_sy = self._edit_cy
                if self._edit_cy >= self._edit_sy + ml: self._edit_sy = self._edit_cy - ml + 1
                if self._edit_cx < self._edit_sx: self._edit_sx = max(0, self._edit_cx - 5)
                if self._edit_cx >= self._edit_sx + mc: self._edit_sx = self._edit_cx - mc + 1

        elif self._is_disclaimer_screen:
            if ien:
                irs()
                self._is_disclaimer_screen = False
                self._app_state["disclaimer_accepted"] = True
                self._needs_redraw = True
                time.sleep(0.3)

        elif self._show_info:
            if ies or ien:
                irs()
                self._show_info = False
                self._info_data = []
                self._needs_redraw = True
                time.sleep(0.3)
                
        elif self._input_active:
            if ies:
                irs()
                self._input_active = False
                self._needs_redraw = True
                time.sleep(0.3)
            elif ien:
                irs()
                new_name = self._input_text.strip()
                rn = False
                
                if new_name:
                    td = self._app_state["left_path"] if self._app_state["active_pane"] == PANE_LEFT else self._app_state["right_path"]
                    np = f"/{new_name}" if td == "/" else f"{td}/{new_name}"
                    
                    if self._input_mode in (MODE_RENAME, MODE_COPY_SAME) and np != self._context_target_path:
                        if self._exists(np):
                            self._pending_dest_path = np
                            self._pending_action = ACT_RENAME if self._input_mode == MODE_RENAME else ACT_COPY
                            self._confirm_menu = Menu(self._draw, "Overwrite?", 0, sh, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2)
                            self._confirm_menu.add_item("No")
                            self._confirm_menu.add_item("Yes")
                            self._confirm_menu.set_selected(0)
                            self._input_active = False
                            self._needs_redraw = True
                            time.sleep(0.3)
                        else:
                            if self._input_mode == MODE_RENAME:
                                try:
                                    self._storage.rename(self._context_target_path, np)
                                    rn = True
                                except Exception: pass
                            elif self._input_mode == MODE_COPY_SAME:
                                self._draw_progress("Copying...", 0.0)
                                self._copy_item(self._context_target_path, np)
                                self._draw_progress("Copying 100%", 1.0)
                                rn = True
                    elif self._input_mode == MODE_MKDIR:
                        if not self._exists(np):
                            try:
                                self._storage.mkdir(np)
                                rn = True
                            except Exception: pass
                                
                if rn:
                    self._force_sync()
                    self._refresh_panes()
                
                if not self._confirm_menu:
                    self._input_active = False
                    self._context_target_path = ""
                    self._needs_redraw = True
                time.sleep(0.3)
            elif ilf:
                irs()
                if self._input_cursor > 0:
                    self._input_cursor -= 1
                    self._needs_redraw = True
                time.sleep(0.15)
            elif irt:
                irs()
                if self._input_cursor < len(self._input_text):
                    self._input_cursor += 1
                    self._needs_redraw = True
                time.sleep(0.15)
            elif ibs:
                irs()
                if self._input_cursor > 0:
                    self._input_text = self._input_text[:self._input_cursor - 1] + self._input_text[self._input_cursor:]
                    self._input_cursor -= 1
                    self._needs_redraw = True
                time.sleep(0.15)
            elif isp:
                irs()
                if len(self._input_text) < 35:
                    self._input_text = self._input_text[:self._input_cursor] + cta + self._input_text[self._input_cursor:]
                    self._input_cursor += 1
                    self._needs_redraw = True
                time.sleep(0.18)

        elif (btn == BUTTON_SPACE or key == ' ' or btn == 32) and not self._is_help_screen and not self._show_options and self._confirm_menu is None and self._context_menu is None and not self._input_active and not self._show_info:
            irs()
            if self._mode == FILE_BROWSER_MANAGER:
                ap = self._app_state["active_pane"]
                cp = self._app_state["left_path"] if ap == PANE_LEFT else self._app_state["right_path"]
                fl = self._app_state["left_files"] if ap == PANE_LEFT else self._app_state["right_files"]
                ix = self._app_state["left_index"] if ap == PANE_LEFT else self._app_state["right_index"]
                
                if len(fl) > 0:
                    sf, isd, _ = fl[ix]
                    if sf != "..":
                        fp = f"/{sf}" if cp == "/" else f"{cp}/{sf}"
                        if fp in self._app_state["marked"]: self._app_state["marked"].remove(fp)
                        else: self._app_state["marked"].append(fp)
                        
                        if ap == PANE_LEFT: self._app_state["left_index"] = (ix + 1) % len(fl)
                        else: self._app_state["right_index"] = (ix + 1) % len(fl)
                        self._needs_redraw = True
            time.sleep(0.15)
                
        elif btn == BUTTON_H or key in ('h', 'H', ord('h'), ord('H')) or btn in (ord('h'), ord('H')):
            irs()
            self._is_help_screen = not self._is_help_screen
            self._needs_redraw = True

        elif (btn == BUTTON_O or key in ('o', 'O', ord('o'), ord('O')) or btn in (ord('o'), ord('O'))) and not self._is_help_screen and self._confirm_menu is None and self._context_menu is None:
            irs()
            self._show_options = True
            self._opt_idx = 0
            self._needs_redraw = True

        elif (btn == BUTTON_S or key in ('s', 'S', ord('s'), ord('S')) or btn in (ord('s'), ord('S'))) and not self._is_help_screen and not self._show_options and self._confirm_menu is None and self._context_menu is None:
            irs()
            self._app_state["sort_mode"] = SORT_DATE if self._app_state["sort_mode"] == SORT_NAME else SORT_NAME
            self._refresh_panes()
            self._app_state["left_index"] = self._app_state["right_index"] = 0
            self._needs_redraw = True

        elif (btn == BUTTON_N or key in ('n', 'N', ord('n'), ord('N')) or btn in (ord('n'), ord('N'))) and not self._is_help_screen and not self._show_options and self._confirm_menu is None and self._context_menu is None:
            if self._mode == FILE_BROWSER_MANAGER:
                irs()
                self._input_active = True
                self._input_mode = MODE_MKDIR
                self._input_text = ""
                self._input_cursor = 0
                self._needs_redraw = True
                time.sleep(0.3)
            
        elif (btn == BUTTON_I or key in ('i', 'I', ord('i'), ord('I')) or btn in (ord('i'), ord('I'))) and not self._is_help_screen and not self._show_options and self._confirm_menu is None and self._context_menu is None and not self._show_info:
            irs()
            ap = self._app_state["active_pane"]
            fl = self._app_state["left_files"] if ap == PANE_LEFT else self._app_state["right_files"]
            ix = self._app_state["left_index"] if ap == PANE_LEFT else self._app_state["right_index"]
            
            if len(fl) > 0:
                sf, isd, fz = fl[ix]
                if sf != "..":
                    self._info_data = [
                        f"Name: {sf[:22]}",
                        f"Type: {'Directory' if isd else 'File'}",
                        f"Size: {fz} bytes"
                    ]
                    self._show_info = True
                    self._needs_redraw = True
            time.sleep(0.3)

        elif (btn in (BUTTON_D, ord('d'), ord('D')) or key in ('d', 'D') or ibs) and not self._is_help_screen and not self._show_options and self._confirm_menu is None and self._context_menu is None:
            irs()
            if self._mode == FILE_BROWSER_MANAGER:
                mk = self._app_state["marked"]
                if len(mk) > 0:
                    self._pending_action = ACT_DELETE
                    self._confirm_menu = Menu(self._draw, f"Delete {len(mk)} items?", 0, sh, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2)
                    self._confirm_menu.add_item("No")
                    self._confirm_menu.add_item("Yes")
                    self._confirm_menu.set_selected(0)
                else:
                    ap = self._app_state["active_pane"]
                    cp = self._app_state["left_path"] if ap == PANE_LEFT else self._app_state["right_path"]
                    fl = self._app_state["left_files"] if ap == PANE_LEFT else self._app_state["right_files"]
                    ix = self._app_state["left_index"] if ap == PANE_LEFT else self._app_state["right_index"]
                    
                    if len(fl) > 0:
                        sf, isd, _ = fl[ix]
                        if sf != "..":
                            self._context_target_path = f"/{sf}" if cp == "/" else f"{cp}/{sf}"
                            self._pending_action = ACT_DELETE
                            self._confirm_menu = Menu(self._draw, "Confirm Delete?", 0, sh, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2)
                            self._confirm_menu.add_item("No")
                            self._confirm_menu.add_item("Yes")
                            self._confirm_menu.set_selected(0)
            self._needs_redraw = True

        elif self._show_options:
            if ies or ien:
                irs()
                self._show_options = False
                self._refresh_panes()
                self._needs_redraw = True
                time.sleep(0.3)
            elif iup:
                irs()
                self._opt_idx = (self._opt_idx - 1) % 10
                self._needs_redraw = True
            elif idn:
                irs()
                self._opt_idx = (self._opt_idx + 1) % 10
                self._needs_redraw = True
            elif irt:
                irs()
                self._needs_redraw = True
                if self._opt_idx == 0: self._app_state["theme"] = (self._app_state.get("theme", 0) + 1) % 3
                elif self._opt_idx == 1: self._app_state["bg_r"] = (self._app_state.get("bg_r", 0) + 15) % 256
                elif self._opt_idx == 2: self._app_state["bg_g"] = (self._app_state.get("bg_g", 0) + 15) % 256
                elif self._opt_idx == 3: self._app_state["bg_b"] = (self._app_state.get("bg_b", 0) + 15) % 256
                elif self._opt_idx == 4: self._app_state["bar_r"] = (self._app_state.get("bar_r", 0) + 15) % 256
                elif self._opt_idx == 5: self._app_state["bar_g"] = (self._app_state.get("bar_g", 0) + 15) % 256
                elif self._opt_idx == 6: self._app_state["bar_b"] = (self._app_state.get("bar_b", 0) + 15) % 256
                elif self._opt_idx == 7: self._app_state["sort_mode"] = SORT_DATE if self._app_state["sort_mode"] == SORT_NAME else SORT_NAME
                elif self._opt_idx == 8: self._app_state["show_hidden"] = not self._app_state.get("show_hidden", False)
                elif self._opt_idx == 9: self._app_state["dir_menu"] = not self._app_state.get("dir_menu", True)
            elif ilf:
                irs()
                self._needs_redraw = True
                if self._opt_idx == 0: self._app_state["theme"] = (self._app_state.get("theme", 0) - 1) % 3
                elif self._opt_idx == 1: self._app_state["bg_r"] = (self._app_state.get("bg_r", 0) - 15) % 256
                elif self._opt_idx == 2: self._app_state["bg_g"] = (self._app_state.get("bg_g", 0) - 15) % 256
                elif self._opt_idx == 3: self._app_state["bg_b"] = (self._app_state.get("bg_b", 0) - 15) % 256
                elif self._opt_idx == 4: self._app_state["bar_r"] = (self._app_state.get("bar_r", 0) - 15) % 256
                elif self._opt_idx == 5: self._app_state["bar_g"] = (self._app_state.get("bar_g", 0) - 15) % 256
                elif self._opt_idx == 6: self._app_state["bar_b"] = (self._app_state.get("bar_b", 0) - 15) % 256
                elif self._opt_idx == 7: self._app_state["sort_mode"] = SORT_NAME if self._app_state["sort_mode"] == SORT_DATE else SORT_DATE
                elif self._opt_idx == 8: self._app_state["show_hidden"] = not self._app_state.get("show_hidden", False)
                elif self._opt_idx == 9: self._app_state["dir_menu"] = not self._app_state.get("dir_menu", True)

        elif self._confirm_menu is not None:
            if ies:
                irs()
                self._confirm_menu = None
                self._pending_action = ACT_NONE
                self._pending_dest_path = ""
                self._needs_redraw = True
                time.sleep(0.3)
            elif iup:
                irs()
                self._confirm_menu.scroll_up()
                self._needs_redraw = True
            elif idn:
                irs()
                self._confirm_menu.scroll_down()
                self._needs_redraw = True
            elif ien:
                irs()
                sl = self._confirm_menu.current_item
                if sl == "Yes":
                    mk = self._app_state["marked"]
                    ib = len(mk) > 0
                    
                    if self._pending_action == ACT_DELETE:
                        if ib:
                            tl = len(mk)
                            self._draw_progress("Deleting...", 0.0)
                            for i, mp in enumerate(mk):
                                self._rmtree(mp)
                                self._draw_progress("Deleting...", (i+1)/tl)
                        else:
                            self._draw_progress("Deleting...", 0.0)
                            self._rmtree(self._context_target_path)
                            self._draw_progress("Deleting...", 1.0)
                            
                    elif self._pending_action == ACT_COPY:
                        if ib:
                            tl = len(mk)
                            for i, mp in enumerate(mk):
                                fn = mp.split("/")[-1]
                                dp = f"/{fn}" if self._pending_dest_path == "/" else f"{self._pending_dest_path}/{fn}"
                                if self._exists(dp):
                                    self._rmtree(dp)
                                    time.sleep(0.1)
                                self._copy_item(mp, dp)
                                self._draw_progress("Batch Copy...", (i+1)/tl)
                        else:
                            if self._pending_dest_path != self._context_target_path:
                                self._draw_progress("Copying...", 0.0)
                                if self._exists(self._pending_dest_path):
                                    self._rmtree(self._pending_dest_path) 
                                    time.sleep(0.1)
                                self._copy_item(self._context_target_path, self._pending_dest_path)
                                self._draw_progress("Copying 100%", 1.0)
                                
                    elif self._pending_action == ACT_MOVE:
                        if ib:
                            tl = len(mk)
                            for i, mp in enumerate(mk):
                                fn = mp.split("/")[-1]
                                dp = f"/{fn}" if self._pending_dest_path == "/" else f"{self._pending_dest_path}/{fn}"
                                if self._exists(dp):
                                    self._rmtree(dp)
                                    time.sleep(0.1)
                                try: self._storage.rename(mp, dp)
                                except Exception:
                                    self._copy_item(mp, dp)
                                    self._rmtree(mp)
                                self._draw_progress("Batch Move...", (i+1)/tl)
                        else:
                            if self._pending_dest_path != self._context_target_path:
                                self._draw_progress("Moving...", 0.0)
                                if self._exists(self._pending_dest_path):
                                    self._rmtree(self._pending_dest_path)
                                    time.sleep(0.1)
                                try: self._storage.rename(self._context_target_path, self._pending_dest_path)
                                except Exception:
                                    self._copy_item(self._context_target_path, self._pending_dest_path)
                                    self._rmtree(self._context_target_path)
                                self._draw_progress("Moving...", 1.0)
                                
                    elif self._pending_action == ACT_RENAME:
                        if not ib and self._pending_dest_path != self._context_target_path:
                            self._draw_progress("Renaming...", 0.0)
                            if self._exists(self._pending_dest_path):
                                self._rmtree(self._pending_dest_path)
                                time.sleep(0.1)
                            try: self._storage.rename(self._context_target_path, self._pending_dest_path)
                            except Exception: pass
                            self._draw_progress("Renaming...", 1.0)
                    
                    if ib: self._app_state["marked"].clear()
                    if self._pending_action in (ACT_DELETE, ACT_COPY, ACT_MOVE, ACT_RENAME):
                        self._force_sync()
                        self._refresh_panes()

                self._confirm_menu = None
                self._pending_action = ACT_NONE
                self._context_target_path = self._pending_dest_path = ""
                self._needs_redraw = True
                time.sleep(0.3)

        elif self._context_menu is not None:
            if ies:
                irs()
                self._context_menu = None
                self._needs_redraw = True
                time.sleep(0.3)
            elif iup:
                irs()
                self._context_menu.scroll_up()
                self._needs_redraw = True
            elif idn:
                irs()
                self._context_menu.scroll_down()
                self._needs_redraw = True
            elif ien:
                irs()
                ac = self._context_menu.current_item
                
                if self._is_editing:
                    if ac in ("Save", "Save & Exit"):
                        self._draw_progress("Saving...", 0.5)
                        try:
                            data = "\n".join(self._edit_text)
                            self._storage.write(self._edit_file, data, "w")
                            del data
                            self._edit_unsaved = False
                        except Exception: pass
                        gc.collect()
                        if ac == "Save & Exit": self._is_editing = False
                    elif ac == "Exit without Saving":
                        self._is_editing = False
                    self._context_menu = None
                    self._needs_redraw = True
                    time.sleep(0.3)
                else:
                    if ac == "Cancel":
                        pass
                    elif ac == "Clear Marks":
                        self._app_state["marked"].clear()
                        self._refresh_panes()
                    elif ac == "Open":
                        if self._app_state["active_pane"] == PANE_LEFT:
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
                        self._pending_action = ACT_DELETE
                        mk = self._app_state["marked"]
                        msg = f"Delete {len(mk)} items?" if len(mk) > 0 else "Confirm Delete?"
                        self._confirm_menu = Menu(self._draw, msg, 0, sh, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2)
                        self._confirm_menu.add_item("No")
                        self._confirm_menu.add_item("Yes")
                        self._confirm_menu.set_selected(0)
                    elif ac == "Rename":
                        self._input_active = True
                        self._input_text = self._context_target_path.split("/")[-1]
                        self._input_cursor = len(self._input_text)
                        self._input_mode = MODE_RENAME
                    elif ac in ("Copy", "Move"):
                        ap = self._app_state["active_pane"]
                        td = self._app_state["right_path"] if ap == PANE_LEFT else self._app_state["left_path"]
                        mk = self._app_state["marked"]
                        
                        if len(mk) > 0:
                            self._pending_action = ACT_COPY if ac == "Copy" else ACT_MOVE
                            self._pending_dest_path = td
                            self._confirm_menu = Menu(self._draw, f"Confirm {ac}?", 0, sh, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2)
                            self._confirm_menu.add_item("No")
                            self._confirm_menu.add_item("Yes")
                            self._confirm_menu.set_selected(0)
                        else:
                            fn = self._context_target_path.split("/")[-1]
                            dp = f"/{fn}" if td == "/" else f"{td}/{fn}"
                            
                            if dp == self._context_target_path:
                                self._input_active = True
                                self._input_text = fn
                                self._input_cursor = len(self._input_text)
                                self._input_mode = MODE_COPY_SAME if ac == "Copy" else MODE_RENAME
                            else:
                                self._pending_action = ACT_COPY if ac == "Copy" else ACT_MOVE
                                self._pending_dest_path = dp
                                
                                ex = self._exists(dp)
                                msg = "Overwrite?" if ex else f"Confirm {ac}?"
                                
                                self._confirm_menu = Menu(self._draw, msg, 0, sh, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2)
                                self._confirm_menu.add_item("No")
                                self._confirm_menu.add_item("Yes")
                                self._confirm_menu.set_selected(0)
                            
                    self._context_menu = None
                    self._needs_redraw = True
                    time.sleep(0.3)

        elif ies:
            irs()
            if self._is_help_screen:
                self._is_help_screen = False
                self._needs_redraw = True
            else:
                return False
            
        elif ilf and not self._is_help_screen:
            irs()
            self._app_state["active_pane"] = PANE_LEFT
            self._needs_redraw = True
            
        elif irt and not self._is_help_screen:
            irs()
            self._app_state["active_pane"] = PANE_RIGHT
            self._needs_redraw = True
            
        elif iup and not self._is_help_screen:
            irs()
            ap = self._app_state["active_pane"]
            fl = self._app_state["left_files"] if ap == PANE_LEFT else self._app_state["right_files"]
            ix = self._app_state["left_index"] if ap == PANE_LEFT else self._app_state["right_index"]
            
            fln = len(fl)
            if fln > 0:
                if ap == PANE_LEFT: self._app_state["left_index"] = (ix - 1) % fln
                else: self._app_state["right_index"] = (ix - 1) % fln
                self._needs_redraw = True
            
        elif idn and not self._is_help_screen:
            irs()
            ap = self._app_state["active_pane"]
            fl = self._app_state["left_files"] if ap == PANE_LEFT else self._app_state["right_files"]
            ix = self._app_state["left_index"] if ap == PANE_LEFT else self._app_state["right_index"]
            
            fln = len(fl)
            if fln > 0:
                if ap == PANE_LEFT: self._app_state["left_index"] = (ix + 1) % fln
                else: self._app_state["right_index"] = (ix + 1) % fln
                self._needs_redraw = True

        elif ien and not self._is_help_screen:
            irs()
            ap = self._app_state["active_pane"]
            cp = self._app_state["left_path"] if ap == PANE_LEFT else self._app_state["right_path"]
            fl = self._app_state["left_files"] if ap == PANE_LEFT else self._app_state["right_files"]
            ix = self._app_state["left_index"] if ap == PANE_LEFT else self._app_state["right_index"]
            
            if len(fl) > 0:
                sf, isd, _ = fl[ix]
                if sf == "..":
                    pts = cp.rstrip("/").split("/")
                    fe = pts[-1] if len(pts) > 1 else ""
                    pr = "/" + "/".join(pts[1:-1])
                    if pr in ("//", ""): pr = "/"
                        
                    if ap == PANE_LEFT: self._app_state["left_path"] = pr
                    else: self._app_state["right_path"] = pr
                    
                    self._refresh_panes()
                    
                    nf = self._app_state["left_files"] if ap == PANE_LEFT else self._app_state["right_files"]
                    nix = next((i for i, itm in enumerate(nf) if itm[0] == fe), 0)
                            
                    if ap == PANE_LEFT: self._app_state["left_index"] = nix
                    else: self._app_state["right_index"] = nix
                else:
                    np = f"/{sf}" if cp == "/" else f"{cp}/{sf}"
                    
                    if self._mode == FILE_BROWSER_SELECTOR and not isd:
                        return False

                    mk = self._app_state["marked"]
                    
                    if isd and not self._app_state.get("dir_menu", True) and len(mk) == 0:
                        if ap == PANE_LEFT:
                            self._app_state["left_path"] = np
                            self._app_state["left_index"] = 0
                        else:
                            self._app_state["right_path"] = np
                            self._app_state["right_index"] = 0
                        self._refresh_panes()
                    elif self._mode == FILE_BROWSER_MANAGER and len(mk) > 0:
                        self._context_menu = Menu(self._draw, f"{len(mk)} Marked", 0, sh, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2)
                        if isd:
                            self._context_target_path = np
                            self._context_menu.add_item("Open")
                        self._context_menu.add_item("Copy")
                        self._context_menu.add_item("Move")
                        self._context_menu.add_item("Delete")
                        self._context_menu.add_item("Clear Marks")
                        self._context_menu.add_item("Cancel")
                        self._context_menu.set_selected(0)
                        time.sleep(0.3)
                    else:
                        self._context_target_path = np
                        self._context_menu = Menu(self._draw, sf[:14], 0, sh, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2)
                        if isd:
                            self._context_menu.add_item("Open")
                        else:
                            self._context_menu.add_item("View")
                            self._context_menu.add_item("Edit")
                            
                        if self._mode == FILE_BROWSER_MANAGER:
                            self._context_menu.add_item("Copy")
                            self._context_menu.add_item("Move")
                            self._context_menu.add_item("Rename")
                            self._context_menu.add_item("Delete")
                        self._context_menu.add_item("Cancel")
                        self._context_menu.set_selected(0)
                        time.sleep(0.3)
                self._needs_redraw = True

        if self._needs_redraw:
            self._draw_ui()
            
        self._auto_save()
        gc.collect()
        return True

def start(view_manager):
    global _test_browser
    _test_browser = FileBrowser(view_manager, FILE_BROWSER_MANAGER)
    return True

def run(view_manager):
    if not _test_browser.run():
        view_manager.back()

def stop(view_manager):
    global _test_browser
    if _test_browser:
        del _test_browser
        _test_browser = None
    gc.collect()
