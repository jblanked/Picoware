import gc
import time
import json
import os

from picoware.system.vector import Vector
from picoware.system.colors import TFT_WHITE, TFT_BLACK, TFT_BLUE, TFT_YELLOW, TFT_CYAN, TFT_DARKGREY, TFT_LIGHTGREY, TFT_RED
from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_CENTER, BUTTON_BACK, BUTTON_H, BUTTON_O, BUTTON_BACKSPACE
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

PANE_LEFT = 0
PANE_RIGHT = 1
SORT_NAME = 0
SORT_DATE = 1

MODE_NONE = 0
MODE_MKDIR = 1
MODE_RENAME = 2
MODE_COPY_SAME = 3

ACT_NONE = 0
ACT_DELETE = 1
ACT_COPY = 2
ACT_MOVE = 3
ACT_RENAME = 4

_app_state = None
_last_saved_json = "{}"
_last_save_time = 0
_is_help_screen = False
_is_disclaimer_screen = False
show_options = False
opt_idx = 0
_context_menu = None
_confirm_menu = None
_input_active = False
_input_text = ""
_input_cursor = 0
_input_mode = MODE_NONE
_context_target_path = ""
_pending_action = ACT_NONE
_pending_dest_path = "" 
_sys = None
_needs_redraw = True 
_char_map = None 
_show_info = False
_info_data = []

OPTIONS_LABELS = ("Theme", "BG R (0-255)", "BG G (0-255)", "BG B (0-255)", "Bar R (0-255)", "Bar G (0-255)", "Bar B (0-255)", "Sort Mode", "Hidden Files", "Dir Enter")

def rgb_to_565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

def _get_theme(state):
    th = state.get("theme", 0)
    if th == 0:
        return TFT_BLUE, TFT_CYAN, TFT_WHITE, TFT_YELLOW, TFT_BLACK
    elif th == 1:
        return TFT_BLACK, TFT_WHITE, TFT_WHITE, TFT_WHITE, TFT_BLACK
    else:
        c_bg = rgb_to_565(state.get("bg_r", 0), state.get("bg_g", 0), state.get("bg_b", 170))
        c_bar = rgb_to_565(state.get("bar_r", 0), state.get("bar_g", 170), state.get("bar_b", 170))
        return c_bg, c_bar, TFT_WHITE, TFT_YELLOW, TFT_BLACK

def _force_sync(vm):
    time.sleep(0.3)
    try:
        os.sync()
    except Exception:
        pass

def _exists(vm, path):
    if path in ("/", ""):
        return True
    
    storage = vm.storage
    try:
        if storage.exists(path):
            return True
    except Exception:
        pass
        
    try:
        target_dir = path[:path.rfind("/")]
        if target_dir == "": target_dir = "/"
        target_file = path[path.rfind("/")+1:]
        
        if _app_state is not None:
            if target_dir == _app_state.get("left_path"):
                for f in _app_state.get("left_files", []):
                    if f[0] == target_file:
                        return True
            if target_dir == _app_state.get("right_path"):
                for f in _app_state.get("right_files", []):
                    if f[0] == target_file:
                        return True
    except Exception:
        pass
        
    return False

def _init_state(vm):
    global _app_state, _last_saved_json
    storage = vm.storage
    try:
        storage.mkdir("/picoware")
    except Exception:
        pass
    try:
        storage.mkdir("/picoware/settings")
    except Exception:
        pass
        
    _app_state = {
        "left_path": "/",
        "right_path": "/",
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
        "bg_r": 0,
        "bg_g": 0,
        "bg_b": 170,
        "bar_r": 0,
        "bar_g": 170,
        "bar_b": 170,
        "marked": []
    }
    
    try:
        data = storage.read("/picoware/settings/picocmd_state.json", "r")
        if data:
            saved_state = json.loads(data)
            _app_state["left_path"] = saved_state.get("left_path", "/")
            _app_state["right_path"] = saved_state.get("right_path", "/")
            
            sm = saved_state.get("sort_mode", SORT_NAME)
            _app_state["sort_mode"] = SORT_NAME if sm in ("name", SORT_NAME) else SORT_DATE
            
            ap = saved_state.get("active_pane", PANE_LEFT)
            _app_state["active_pane"] = PANE_LEFT if ap in ("left", PANE_LEFT) else PANE_RIGHT
            
            _app_state["show_hidden"] = saved_state.get("show_hidden", False)
            _app_state["dir_menu"] = saved_state.get("dir_menu", True)
            _app_state["disclaimer_accepted"] = saved_state.get("disclaimer_accepted", False)
            _app_state["theme"] = saved_state.get("theme", 0)
            _app_state["bg_r"] = saved_state.get("bg_r", 0)
            _app_state["bg_g"] = saved_state.get("bg_g", 0)
            _app_state["bg_b"] = saved_state.get("bg_b", 170)
            _app_state["bar_r"] = saved_state.get("bar_r", 0)
            _app_state["bar_g"] = saved_state.get("bar_g", 170)
            _app_state["bar_b"] = saved_state.get("bar_b", 170)
            
            _last_saved_json = json.dumps(_app_state)
            del data
            del saved_state
            gc.collect() 
    except Exception:
        pass

def _rmtree(vm, path):
    storage = vm.storage
    try:
        is_dir = False
        try:
            is_dir = storage.is_directory(path)
        except Exception:
            pass
            
        if is_dir:
            try:
                items = storage.listdir(path)
                for item in items:
                    if item in (".", ".."):
                        continue
                    full_path = "/" + item if path == "/" else path + "/" + item
                    _rmtree(vm, full_path)
            except Exception:
                pass
            try:
                storage.rmdir(path)
            except Exception:
                try:
                    storage.remove(path)
                except Exception:
                    pass
        else:
            storage.remove(path)
    except Exception:
        pass
    gc.collect()

def _draw_progress(vm, title, percentage):
    c_bg, c_bar, _, _, _ = _get_theme(_app_state)
    draw = vm.draw
    fill_rect = draw.fill_rectangle
    d_rect = draw.rect
    d_text = draw.text
    
    screen_w = draw.size.x
    screen_h = draw.size.y
    box_w = 200
    box_h = 60
    x = (screen_w - box_w) // 2
    y = (screen_h - box_h) // 2
    
    fill_rect(Vector(x, y), Vector(box_w, box_h), c_bg)
    d_rect(Vector(x, y), Vector(box_w, box_h), c_bar)
    d_text(Vector(x + 10, y + 10), title, TFT_WHITE)
    
    bar_w = box_w - 20
    d_rect(Vector(x + 10, y + 30), Vector(bar_w, 15), TFT_WHITE)
    fill_w = int((bar_w - 2) * percentage)
    if fill_w > 0:
        fill_rect(Vector(x + 11, y + 31), Vector(fill_w, 13), c_bar)
        
    draw.swap()

def _copy_item(vm, src, dst):
    storage = vm.storage
    is_dir = False
    try:
        is_dir = storage.is_directory(src)
    except Exception:
        pass
        
    if is_dir:
        try:
            storage.mkdir(dst)
        except Exception:
            pass
        try:
            items = storage.listdir(src)
            for item in items:
                if item in (".", ".."): 
                    continue
                s_path = src + "/" + item if src != "/" else "/" + item
                d_path = dst + "/" + item if dst != "/" else "/" + item
                _copy_item(vm, s_path, d_path)
        except Exception:
            pass
    else:
        try:
            f_size = storage.size(src)
            pos = 0
            while pos < f_size:
                try:
                    chunk = storage.read_chunked(src, pos, 2048)
                except Exception:
                    break
                if not chunk: 
                    break
                storage.write(dst, chunk, "ab" if pos > 0 else "wb")
                pos += len(chunk)
                if f_size > 0:
                    _draw_progress(vm, f"Copying {int((pos/f_size)*100)}%", min(1.0, pos / f_size))
                gc.collect()
        except Exception:
            pass
    gc.collect()

def _load_dir(vm, path):
    items = []
    storage = vm.storage
    show_hid = _app_state.get("show_hidden", False)
    sort_m = _app_state["sort_mode"]
    
    try:
        dir_list = storage.listdir(path)
        for item in dir_list:
            if item in (".", ".."):
                continue
            if not show_hid and item.startswith("."):
                continue
                
            full_path = "/" + item if path == "/" else path + "/" + item
            is_dir = False
            mtime = 0
            size = 0
            
            try:
                is_dir = storage.is_directory(full_path)
            except Exception:
                pass
                
            try:
                if not is_dir:
                    size = storage.size(full_path)
            except Exception:
                pass
                
            if sort_m == SORT_DATE:
                try:
                    mtime = os.stat(full_path)[8]
                except Exception:
                    pass
                    
            items.append((item, is_dir, mtime, size))
        del dir_list
        
        if sort_m == SORT_NAME:
            items.sort(key=lambda x: (not x[1], x[0].lower()))
        else:
            items.sort(key=lambda x: (not x[1], x[0].lower() if x[1] else -x[2]))
            
        for i in range(len(items)):
            items[i] = (items[i][0], items[i][1], items[i][3])
    except Exception:
        items = [("<ERROR>", False, 0)]
    gc.collect()
    
    if path != "/":
        return [("..", True, 0)] + items
    return items

def _refresh_panes(vm):
    global _app_state
    if _app_state is None:
        return
        
    _app_state["left_files"] = _load_dir(vm, _app_state["left_path"])
    if _app_state["left_index"] >= len(_app_state["left_files"]):
        _app_state["left_index"] = max(0, len(_app_state["left_files"]) - 1)
        
    _app_state["right_files"] = _load_dir(vm, _app_state["right_path"])
    if _app_state["right_index"] >= len(_app_state["right_files"]):
        _app_state["right_index"] = max(0, len(_app_state["right_files"]) - 1)

def _draw_ui(vm):
    global show_options, opt_idx, _input_active, _input_text, _input_cursor, _input_mode, _needs_redraw, _is_disclaimer_screen, _show_info, _info_data
    c_bg, c_bar, c_txt, c_dir, c_btxt = _get_theme(_app_state)
    
    draw = vm.draw
    fill_rect = draw.fill_rectangle
    d_rect = draw.rect
    d_text = draw.text
    d_swap = draw.swap
    
    draw.clear(color=c_bg)
    
    screen_w = draw.size.x
    screen_h = draw.size.y
    mid_x = screen_w // 2
    
    char_limit = (mid_x - 8) // 6
    name_limit = char_limit - 6
    max_items = (screen_h - 38) // 12
    
    if _is_disclaimer_screen:
        fill_rect(Vector(10, 50), Vector(screen_w - 20, 140), TFT_BLACK)
        d_rect(Vector(10, 50), Vector(screen_w - 20, 140), TFT_RED)
        fill_rect(Vector(10, 50), Vector(screen_w - 20, 20), TFT_RED)
        d_text(Vector(15, 54), "WARNING", TFT_WHITE)
        
        d_text(Vector(20, 85), "With this app it is", TFT_WHITE)
        d_text(Vector(20, 100), "possible to delete ANY", TFT_WHITE)
        d_text(Vector(20, 115), "file on the SD card.", TFT_WHITE)
        d_text(Vector(20, 130), "Please be careful!", TFT_WHITE)
        
        fill_rect(Vector(10, 170), Vector(screen_w - 20, 20), TFT_RED)
        d_text(Vector(15, 174), "[CENTER/ENT] I Understand", TFT_WHITE)
        d_swap()
        _needs_redraw = False
        return

    if _is_help_screen:
        d_text(Vector(10, 10), "PicoCommander Help", TFT_WHITE)
        d_text(Vector(10, 24), "SPC:Mark H:Help O:Opt", c_bar)
        d_text(Vector(10, 36), "I:Info N:NewFolder D:Del", c_bar)
        d_text(Vector(10, 48), "UP/DOWN: Scroll", TFT_WHITE)
        d_text(Vector(10, 60), "L/R: Switch Pane", TFT_WHITE)
        d_text(Vector(10, 72), "CENTER: Menu/Exec", TFT_WHITE)
        d_text(Vector(10, 84), "BACK: Exit App", TFT_WHITE)
        
        gc.collect()
        used_ram = gc.mem_alloc() // 1024
        free_ram = gc.mem_free() // 1024
        d_text(Vector(10, 126), f"RAM: {used_ram}KB used / {free_ram}KB free", TFT_YELLOW)
        
        if _sys and _sys.has_psram:
            used_psram = _sys.used_psram // 1024
            free_psram = _sys.free_psram // 1024
            d_text(Vector(10, 138), f"PSRAM: {used_psram}KB used / {free_psram}KB free", TFT_YELLOW)

        d_text(Vector(10, screen_h - 40), "made by Slasher006", c_bar)
        d_text(Vector(10, screen_h - 30), "with the help of Gemini", c_bar)
        d_text(Vector(10, screen_h - 20), "Date: 2026-03-04 | v1.10", c_bar)
        d_swap()
        _needs_redraw = False
        return

    if _show_info:
        box_w = 200
        box_h = 100
        x = (screen_w - box_w) // 2
        y = (screen_h - box_h) // 2
        fill_rect(Vector(x, y), Vector(box_w, box_h), TFT_BLACK)
        d_rect(Vector(x, y), Vector(box_w, box_h), c_bar)
        fill_rect(Vector(x, y), Vector(box_w, 16), c_bar)
        d_text(Vector(x + 5, y + 2), "FILE INFORMATION", c_btxt)
        for i, line in enumerate(_info_data):
            d_text(Vector(x + 10, y + 25 + (i * 15)), line, TFT_WHITE)
        d_text(Vector(x + 10, y + box_h - 15), "[ESC/ENT] Close", TFT_LIGHTGREY)
        d_swap()
        _needs_redraw = False
        return

    if show_options:
        fill_rect(Vector(10, 10), Vector(screen_w - 20, screen_h - 20), TFT_BLACK)
        d_rect(Vector(10, 10), Vector(screen_w - 20, screen_h - 20), c_bar)
        fill_rect(Vector(10, 10), Vector(screen_w - 20, 20), c_bar)
        d_text(Vector(15, 14), "OPTIONS MENU", c_btxt)
        
        for i, lbl in enumerate(OPTIONS_LABELS):
            y_pos = 35 + (i * 15)
            t_col = c_bar if i == opt_idx else TFT_WHITE
            if i == opt_idx:
                fill_rect(Vector(12, y_pos - 2), Vector(screen_w - 24, 13), TFT_DARKGREY)
            d_text(Vector(20, y_pos), lbl + ":", t_col)
            
            if i == 0: val = ("Classic", "Dark", "Custom")[_app_state.get("theme", 0)]
            elif i == 1: val = str(_app_state.get("bg_r", 0))
            elif i == 2: val = str(_app_state.get("bg_g", 0))
            elif i == 3: val = str(_app_state.get("bg_b", 170))
            elif i == 4: val = str(_app_state.get("bar_r", 0))
            elif i == 5: val = str(_app_state.get("bar_g", 170))
            elif i == 6: val = str(_app_state.get("bar_b", 170))
            elif i == 7: val = "Name" if _app_state.get("sort_mode", SORT_NAME) == SORT_NAME else "Date"
            elif i == 8: val = "Show" if _app_state.get("show_hidden", False) else "Hide"
            elif i == 9: val = "Menu" if _app_state.get("dir_menu", True) else "Open"
            
            d_text(Vector(130, y_pos), f"< {val} >", t_col)
            
        prv_bg = rgb_to_565(_app_state.get("bg_r",0), _app_state.get("bg_g",0), _app_state.get("bg_b",170))
        prv_bar = rgb_to_565(_app_state.get("bar_r",0), _app_state.get("bar_g",170), _app_state.get("bar_b",170))
        d_text(Vector(20, 185), "Custom Preview:", TFT_LIGHTGREY)
        fill_rect(Vector(140, 183), Vector(60, 20), prv_bg)
        d_rect(Vector(140, 183), Vector(60, 20), prv_bar)
        
        fill_rect(Vector(10, screen_h - 30), Vector(screen_w - 20, 20), c_bar)
        d_text(Vector(15, screen_h - 26), "[L/R] Edit   [ESC/ENT] Save", c_btxt)
        d_swap()
        _needs_redraw = False
        return

    if _input_active:
        box_h = 70
        box_y = (screen_h - box_h) // 2
        fill_rect(Vector(10, box_y), Vector(screen_w - 20, box_h), TFT_BLACK)
        d_rect(Vector(10, box_y), Vector(screen_w - 20, box_h), c_bar)
        fill_rect(Vector(10, box_y), Vector(screen_w - 20, 16), c_bar)
        
        if _input_mode == MODE_RENAME:
            title_str = "RENAME FILE:"
        elif _input_mode == MODE_COPY_SAME:
            title_str = "COPY AS:"
        else:
            title_str = "NEW FOLDER:"
            
        d_text(Vector(15, box_y + 2), title_str, c_btxt)
        d_text(Vector(15, box_y + 24), _input_text, TFT_WHITE)
        
        if int(time.time() * 3) % 2 == 0:
            cur_x = 15 + (_input_cursor * 6)
            fill_rect(Vector(cur_x, box_y + 35), Vector(6, 2), TFT_CYAN)
            _needs_redraw = True 
            
        d_text(Vector(15, box_y + 48), "[ENT] Save  [ESC] Cancel", TFT_LIGHTGREY)
        d_swap()
        if not _needs_redraw: _needs_redraw = False
        return

    if _confirm_menu is not None:
        _confirm_menu.draw()
        d_swap()
        _needs_redraw = False
        return

    if _context_menu is not None:
        _context_menu.draw()
        d_swap()
        _needs_redraw = False
        return

    fill_rect(Vector(0, 0), Vector(screen_w, 12), c_bar)
    sort_str = "Name" if _app_state["sort_mode"] == SORT_NAME else "Date"
    header_text = f"PicoCalcCommander v1.10  [{sort_str}]"
    d_text(Vector(2, 2), header_text, c_btxt)

    fill_rect(Vector(mid_x, 12), Vector(1, screen_h - 24), c_bar)
    
    act_pane = _app_state["active_pane"]

    if act_pane == PANE_LEFT:
        fill_rect(Vector(0, 12), Vector(mid_x, 12), c_bar)
    d_text(Vector(2, 14), _app_state["left_path"][:char_limit], c_btxt if act_pane == PANE_LEFT else c_txt)
    left_start = max(0, _app_state["left_index"] - (max_items - 1))
    y_offset = 26
    for i, item_data in enumerate(_app_state["left_files"][left_start : left_start + max_items]):
        f_name, is_dir, f_size = item_data
        actual_idx = i + left_start
        display_name = "/" + f_name if is_dir else f_name
        
        full_p = "/" + f_name if _app_state["left_path"] == "/" else _app_state["left_path"] + "/" + f_name
        is_marked = full_p in _app_state["marked"]
        
        base_color = TFT_RED if is_marked else (c_dir if is_dir else c_txt)
        text_color = base_color if act_pane == PANE_RIGHT or actual_idx != _app_state["left_index"] else c_btxt
        if act_pane == PANE_LEFT and actual_idx == _app_state["left_index"]:
            fill_rect(Vector(0, y_offset-1), Vector(mid_x - 2, 10), c_bar)
            
        if is_dir:
            sz_str = "<DIR>"
        elif f_size < 1024:
            sz_str = f"{f_size}B"
        elif f_size < 1048576:
            sz_str = f"{f_size//1024}K"
        else:
            sz_str = f"{f_size//1048576}M"
            
        pad_len = max(0, char_limit - len(display_name[:name_limit]) - len(sz_str))
        full_str = display_name[:name_limit] + (" " * pad_len) + sz_str
            
        d_text(Vector(2, y_offset), full_str, text_color)
        y_offset += 12
        
    if act_pane == PANE_RIGHT:
        fill_rect(Vector(mid_x + 1, 12), Vector(mid_x - 1, 12), c_bar)
    d_text(Vector(mid_x + 4, 14), _app_state["right_path"][:char_limit], c_btxt if act_pane == PANE_RIGHT else c_txt)
    right_start = max(0, _app_state["right_index"] - (max_items - 1))
    y_offset = 26
    for i, item_data in enumerate(_app_state["right_files"][right_start : right_start + max_items]):
        f_name, is_dir, f_size = item_data
        actual_idx = i + right_start
        display_name = "/" + f_name if is_dir else f_name
        
        full_p = "/" + f_name if _app_state["right_path"] == "/" else _app_state["right_path"] + "/" + f_name
        is_marked = full_p in _app_state["marked"]
        
        base_color = TFT_RED if is_marked else (c_dir if is_dir else c_txt)
        text_color = base_color if act_pane == PANE_LEFT or actual_idx != _app_state["right_index"] else c_btxt
        if act_pane == PANE_RIGHT and actual_idx == _app_state["right_index"]:
            fill_rect(Vector(mid_x + 2, y_offset-1), Vector(mid_x - 4, 10), c_bar)
            
        if is_dir:
            sz_str = "<DIR>"
        elif f_size < 1024:
            sz_str = f"{f_size}B"
        elif f_size < 1048576:
            sz_str = f"{f_size//1024}K"
        else:
            sz_str = f"{f_size//1048576}M"
            
        pad_len = max(0, char_limit - len(display_name[:name_limit]) - len(sz_str))
        full_str = display_name[:name_limit] + (" " * pad_len) + sz_str
            
        d_text(Vector(mid_x + 4, y_offset), full_str, text_color)
        y_offset += 12

    fill_rect(Vector(0, screen_h - 12), Vector(screen_w, 12), c_bar)
    d_text(Vector(2, screen_h - 10), "SPC:Mark ENT:Menu O:Opt I:Info H:Help ESC:Exit", c_btxt)

    d_swap()
    _needs_redraw = False

def _auto_save(vm):
    global _last_saved_json, _last_save_time
    current_time = time.time()
    if current_time - _last_save_time > 5:
        current_state = {
            "left_path": _app_state["left_path"],
            "right_path": _app_state["right_path"],
            "sort_mode": _app_state["sort_mode"],
            "active_pane": _app_state.get("active_pane", PANE_LEFT),
            "show_hidden": _app_state.get("show_hidden", False),
            "dir_menu": _app_state.get("dir_menu", True),
            "disclaimer_accepted": _app_state.get("disclaimer_accepted", False),
            "theme": _app_state.get("theme", 0),
            "bg_r": _app_state.get("bg_r", 0),
            "bg_g": _app_state.get("bg_g", 0),
            "bg_b": _app_state.get("bg_b", 170),
            "bar_r": _app_state.get("bar_r", 0),
            "bar_g": _app_state.get("bar_g", 170),
            "bar_b": _app_state.get("bar_b", 170)
        }
        current_json = json.dumps(current_state)
        if current_json != _last_saved_json:
            try:
                vm.storage.write("/picoware/settings/picocmd_state.json", current_json, "w")
                _last_saved_json = current_json
            except Exception:
                pass
        del current_json
        del current_state
        gc.collect()
        _last_save_time = current_time

def start(vm):
    global _sys, _needs_redraw, _char_map, _is_disclaimer_screen
    
    vm.draw.clear(color=TFT_BLACK)
    vm.draw.text(Vector(10, 10), "Loading PicoCommander...", TFT_WHITE)
    vm.draw.swap()
    time.sleep(0.3)
    
    _sys = System()
    _init_state(vm)
    
    if not _app_state.get("disclaimer_accepted", False):
        _is_disclaimer_screen = True
    
    _char_map = {}
    try:
        import picoware.system.buttons as __btns
        for __i in range(26):
            __c = chr(97 + __i)
            __attr = "BUTTON_" + __c.upper()
            if hasattr(__btns, __attr):
                _char_map[getattr(__btns, __attr)] = __c
        for __i in range(10):
            __c = str(__i)
            __attr = "BUTTON_" + __c
            if hasattr(__btns, __attr):
                _char_map[getattr(__btns, __attr)] = __c
        for attr, char in [("BUTTON_SPACE", " "), ("BUTTON_PERIOD", "."), ("BUTTON_MINUS", "-"), ("BUTTON_UNDERSCORE", "_")]:
            if hasattr(__btns, attr):
                _char_map[getattr(__btns, attr)] = char
    except Exception:
        pass
    
    _refresh_panes(vm)
    _needs_redraw = True
    gc.collect()
    return True

def run(vm):
    global _is_help_screen, _context_menu, _confirm_menu, show_options, opt_idx
    global _context_target_path, _pending_action, _pending_dest_path, _sys, _input_active, _input_text, _input_cursor, _input_mode, _needs_redraw
    global _is_disclaimer_screen, _show_info, _info_data
    
    input_mgr = vm.input_manager
    btn = input_mgr.button
    key = input_mgr.read_non_blocking()
    input_reset = input_mgr.reset
    storage = vm.storage
    
    c_bg, c_bar, _, _, _ = _get_theme(_app_state)

    if _is_disclaimer_screen:
        is_enter = (btn == BUTTON_CENTER) or key in ('\n', '\r') or btn in (10, 13)
        if is_enter:
            input_reset()
            _is_disclaimer_screen = False
            _app_state["disclaimer_accepted"] = True
            _needs_redraw = True
            time.sleep(0.3)

    elif _show_info:
        if btn in (BUTTON_BACK, BUTTON_CENTER) or key in ('\x1b', '\n', '\r') or btn in (10, 13):
            input_reset()
            _show_info = False
            _info_data = []
            _needs_redraw = True
            time.sleep(0.3)
            
    elif _input_active:
        is_printable = False
        char_to_add = ""
        
        if _char_map is not None and btn in _char_map:
            is_printable = True
            char_to_add = _char_map[btn]
            
        elif key and isinstance(key, str) and len(key) == 1 and 32 <= ord(key) <= 126:
            is_printable = True
            char_to_add = key
            
        is_enter = (btn == BUTTON_CENTER and not is_printable) or key in ('\n', '\r') or btn in (10, 13)
        is_esc = (btn == BUTTON_BACK and not is_printable) or key == '\x1b'
        is_bs = (btn == BUTTON_BACKSPACE and not is_printable) or key in ('\x08', '\x7f') or btn in (8, 127)
        is_left = (btn == BUTTON_LEFT and not is_printable)
        is_right = (btn == BUTTON_RIGHT and not is_printable)
        
        if is_esc:
            input_reset()
            _input_active = False
            _needs_redraw = True
            time.sleep(0.3)
        elif is_enter:
            input_reset()
            new_name = _input_text.strip()
            refresh_needed = False
            
            if new_name:
                t_dir = _app_state["left_path"] if _app_state["active_pane"] == PANE_LEFT else _app_state["right_path"]
                new_path = "/" + new_name if t_dir == "/" else t_dir + "/" + new_name
                
                if _input_mode in (MODE_RENAME, MODE_COPY_SAME) and new_path != _context_target_path:
                    exists = _exists(vm, new_path)
                    if exists:
                        _pending_dest_path = new_path
                        _pending_action = ACT_RENAME if _input_mode == MODE_RENAME else ACT_COPY
                        
                        screen_h = vm.draw.size.y
                        _confirm_menu = Menu(vm.draw, "Overwrite?", 0, screen_h, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2)
                        _confirm_menu.add_item("No")
                        _confirm_menu.add_item("Yes")
                        _confirm_menu.set_selected(0)
                        
                        _input_active = False
                        _needs_redraw = True
                        time.sleep(0.3)
                        return 
                    else:
                        if _input_mode == MODE_RENAME:
                            try:
                                storage.rename(_context_target_path, new_path)
                                refresh_needed = True
                            except Exception:
                                pass
                        elif _input_mode == MODE_COPY_SAME:
                            _draw_progress(vm, "Copying...", 0.0)
                            _copy_item(vm, _context_target_path, new_path)
                            _draw_progress(vm, "Copying 100%", 1.0)
                            refresh_needed = True
                            
                elif _input_mode == MODE_MKDIR:
                    exists = _exists(vm, new_path)
                    if not exists:
                        try:
                            storage.mkdir(new_path)
                            refresh_needed = True
                        except Exception:
                            pass
                            
            if refresh_needed:
                _force_sync(vm)
                _refresh_panes(vm)
            
            _input_active = False
            _context_target_path = ""
            _needs_redraw = True
            time.sleep(0.3)
        elif is_left:
            input_reset()
            if _input_cursor > 0:
                _input_cursor -= 1
                _needs_redraw = True
            time.sleep(0.15)
        elif is_right:
            input_reset()
            if _input_cursor < len(_input_text):
                _input_cursor += 1
                _needs_redraw = True
            time.sleep(0.15)
        elif is_bs:
            input_reset()
            if _input_cursor > 0:
                _input_text = _input_text[:_input_cursor - 1] + _input_text[_input_cursor:]
                _input_cursor -= 1
                _needs_redraw = True
            time.sleep(0.15)
        elif is_printable:
            input_reset()
            if len(_input_text) < 35:
                _input_text = _input_text[:_input_cursor] + char_to_add + _input_text[_input_cursor:]
                _input_cursor += 1
                _needs_redraw = True
            time.sleep(0.18)

    elif (btn == BUTTON_SPACE or key == ' ' or btn == 32) and not _is_help_screen and not show_options and _confirm_menu is None and _context_menu is None and not _input_active and not _show_info:
        input_reset()
        act_pane = _app_state["active_pane"]
        current_path = _app_state["left_path"] if act_pane == PANE_LEFT else _app_state["right_path"]
        files = _app_state["left_files"] if act_pane == PANE_LEFT else _app_state["right_files"]
        idx = _app_state["left_index"] if act_pane == PANE_LEFT else _app_state["right_index"]
        
        if len(files) > 0:
            selected_file, is_dir, _ = files[idx]
            if selected_file != "..":
                full_p = "/" + selected_file if current_path == "/" else current_path + "/" + selected_file
                if full_p in _app_state["marked"]:
                    _app_state["marked"].remove(full_p)
                else:
                    _app_state["marked"].append(full_p)
                
                if act_pane == PANE_LEFT:
                    _app_state["left_index"] = (idx + 1) % len(files)
                else:
                    _app_state["right_index"] = (idx + 1) % len(files)
                _needs_redraw = True
        time.sleep(0.15)
            
    elif btn == BUTTON_H or key in ('h', 'H', ord('h'), ord('H')) or btn in (ord('h'), ord('H')):
        input_reset()
        _is_help_screen = not _is_help_screen
        _needs_redraw = True

    elif (btn == BUTTON_O or key in ('o', 'O', ord('o'), ord('O')) or btn in (ord('o'), ord('O'))) and not _is_help_screen and _confirm_menu is None and _context_menu is None:
        input_reset()
        show_options = True
        opt_idx = 0
        _needs_redraw = True

    elif (btn == BUTTON_S or key in ('s', 'S', ord('s'), ord('S')) or btn in (ord('s'), ord('S'))) and not _is_help_screen and not show_options and _confirm_menu is None and _context_menu is None:
        input_reset()
        _app_state["sort_mode"] = SORT_DATE if _app_state["sort_mode"] == SORT_NAME else SORT_NAME
        _refresh_panes(vm)
        _app_state["left_index"] = 0
        _app_state["right_index"] = 0
        _needs_redraw = True

    elif (btn == BUTTON_N or key in ('n', 'N', ord('n'), ord('N')) or btn in (ord('n'), ord('N'))) and not _is_help_screen and not show_options and _confirm_menu is None and _context_menu is None:
        input_reset()
        _input_active = True
        _input_mode = MODE_MKDIR
        _input_text = ""
        _input_cursor = 0
        _needs_redraw = True
        time.sleep(0.3)
        
    elif (btn == BUTTON_I or key in ('i', 'I', ord('i'), ord('I')) or btn in (ord('i'), ord('I'))) and not _is_help_screen and not show_options and _confirm_menu is None and _context_menu is None and not _show_info:
        input_reset()
        act_pane = _app_state["active_pane"]
        files = _app_state["left_files"] if act_pane == PANE_LEFT else _app_state["right_files"]
        idx = _app_state["left_index"] if act_pane == PANE_LEFT else _app_state["right_index"]
        
        if len(files) > 0:
            selected_file, is_dir, f_size = files[idx]
            if selected_file != "..":
                _info_data = [
                    f"Name: {selected_file[:22]}",
                    f"Type: {'Directory' if is_dir else 'File'}",
                    f"Size: {f_size} bytes"
                ]
                _show_info = True
                _needs_redraw = True
        time.sleep(0.3)

    elif (btn in (BUTTON_D, ord('d'), ord('D')) or key in ('d', 'D') or (btn == BUTTON_BACKSPACE and btn not in (66, 98)) or btn in (8, 127) or key in ('\x08', '\x7f')) and not _is_help_screen and not show_options and _confirm_menu is None and _context_menu is None:
        input_reset()
        marked = _app_state["marked"]
        screen_h = vm.draw.size.y
        if len(marked) > 0:
            _pending_action = ACT_DELETE
            _confirm_menu = Menu(vm.draw, f"Delete {len(marked)} items?", 0, screen_h, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2)
            _confirm_menu.add_item("No")
            _confirm_menu.add_item("Yes")
            _confirm_menu.set_selected(0)
        else:
            act_pane = _app_state["active_pane"]
            current_path = _app_state["left_path"] if act_pane == PANE_LEFT else _app_state["right_path"]
            files = _app_state["left_files"] if act_pane == PANE_LEFT else _app_state["right_files"]
            idx = _app_state["left_index"] if act_pane == PANE_LEFT else _app_state["right_index"]
            
            if len(files) > 0:
                selected_file, is_dir, _ = files[idx]
                if selected_file != "..":
                    new_path = "/" + selected_file if current_path == "/" else current_path + "/" + selected_file
                    _context_target_path = new_path
                    _pending_action = ACT_DELETE
                    _confirm_menu = Menu(vm.draw, "Confirm Delete?", 0, screen_h, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2)
                    _confirm_menu.add_item("No")
                    _confirm_menu.add_item("Yes")
                    _confirm_menu.set_selected(0)
        _needs_redraw = True

    elif show_options:
        if btn in (BUTTON_BACK, BUTTON_CENTER) or key in (10, 13, '\n', '\r') or btn in (10, 13):
            input_reset()
            show_options = False
            _refresh_panes(vm)
            _needs_redraw = True
            time.sleep(0.3)
        elif btn == BUTTON_DOWN:
            input_reset()
            opt_idx = (opt_idx + 1) % 10
            _needs_redraw = True
        elif btn == BUTTON_RIGHT:
            input_reset()
            _needs_redraw = True
            if opt_idx == 0: _app_state["theme"] = (_app_state.get("theme", 0) + 1) % 3
            elif opt_idx == 1: _app_state["bg_r"] = (_app_state.get("bg_r", 0) + 15) % 256
            elif opt_idx == 2: _app_state["bg_g"] = (_app_state.get("bg_g", 0) + 15) % 256
            elif opt_idx == 3: _app_state["bg_b"] = (_app_state.get("bg_b", 0) + 15) % 256
            elif opt_idx == 4: _app_state["bar_r"] = (_app_state.get("bar_r", 0) + 15) % 256
            elif opt_idx == 5: _app_state["bar_g"] = (_app_state.get("bar_g", 0) + 15) % 256
            elif opt_idx == 6: _app_state["bar_b"] = (_app_state.get("bar_b", 0) + 15) % 256
            elif opt_idx == 7: _app_state["sort_mode"] = SORT_DATE if _app_state["sort_mode"] == SORT_NAME else SORT_NAME
            elif opt_idx == 8: _app_state["show_hidden"] = not _app_state.get("show_hidden", False)
            elif opt_idx == 9: _app_state["dir_menu"] = not _app_state.get("dir_menu", True)
        elif btn == BUTTON_LEFT:
            input_reset()
            _needs_redraw = True
            if opt_idx == 0: _app_state["theme"] = (_app_state.get("theme", 0) - 1) % 3
            elif opt_idx == 1: _app_state["bg_r"] = (_app_state.get("bg_r", 0) - 15) % 256
            elif opt_idx == 2: _app_state["bg_g"] = (_app_state.get("bg_g", 0) - 15) % 256
            elif opt_idx == 3: _app_state["bg_b"] = (_app_state.get("bg_b", 0) - 15) % 256
            elif opt_idx == 4: _app_state["bar_r"] = (_app_state.get("bar_r", 0) - 15) % 256
            elif opt_idx == 5: _app_state["bar_g"] = (_app_state.get("bar_g", 0) - 15) % 256
            elif opt_idx == 6: _app_state["bar_b"] = (_app_state.get("bar_b", 0) - 15) % 256
            elif opt_idx == 7: _app_state["sort_mode"] = SORT_NAME if _app_state["sort_mode"] == SORT_DATE else SORT_DATE
            elif opt_idx == 8: _app_state["show_hidden"] = not _app_state.get("show_hidden", False)
            elif opt_idx == 9: _app_state["dir_menu"] = not _app_state.get("dir_menu", True)

    elif _confirm_menu is not None:
        if btn == BUTTON_BACK:
            input_reset()
            _confirm_menu = None
            _pending_action = ACT_NONE
            _pending_dest_path = ""
            _needs_redraw = True
            time.sleep(0.3)
        elif btn == BUTTON_UP:
            input_reset()
            _confirm_menu.scroll_up()
            _needs_redraw = True
        elif btn == BUTTON_DOWN:
            input_reset()
            _confirm_menu.scroll_down()
            _needs_redraw = True
        elif btn == BUTTON_CENTER or key in (10, 13, '\n', '\r') or btn in (10, 13):
            input_reset()
            selection = _confirm_menu.current_item
            if selection == "Yes":
                marked = _app_state["marked"]
                is_batch = len(marked) > 0
                
                if _pending_action == ACT_DELETE:
                    if is_batch:
                        total = len(marked)
                        _draw_progress(vm, "Deleting...", 0.0)
                        for i, m_path in enumerate(marked):
                            _rmtree(vm, m_path)
                            _draw_progress(vm, "Deleting...", (i+1)/total)
                    else:
                        _draw_progress(vm, "Deleting...", 0.0)
                        _rmtree(vm, _context_target_path)
                        _draw_progress(vm, "Deleting...", 1.0)
                        
                elif _pending_action == ACT_COPY:
                    if is_batch:
                        total = len(marked)
                        for i, m_path in enumerate(marked):
                            f_name = m_path.split("/")[-1]
                            d_path = "/" + f_name if _pending_dest_path == "/" else _pending_dest_path + "/" + f_name
                            if _exists(vm, d_path):
                                _rmtree(vm, d_path)
                                time.sleep(0.1)
                            _copy_item(vm, m_path, d_path)
                            _draw_progress(vm, "Batch Copy...", (i+1)/total)
                    else:
                        if _pending_dest_path != _context_target_path:
                            _draw_progress(vm, "Copying...", 0.0)
                            if _exists(vm, _pending_dest_path):
                                _rmtree(vm, _pending_dest_path) 
                                time.sleep(0.1)
                            _copy_item(vm, _context_target_path, _pending_dest_path)
                            _draw_progress(vm, "Copying 100%", 1.0)
                            
                elif _pending_action == ACT_MOVE:
                    if is_batch:
                        total = len(marked)
                        for i, m_path in enumerate(marked):
                            f_name = m_path.split("/")[-1]
                            d_path = "/" + f_name if _pending_dest_path == "/" else _pending_dest_path + "/" + f_name
                            if _exists(vm, d_path):
                                _rmtree(vm, d_path)
                                time.sleep(0.1)
                            try:
                                storage.rename(m_path, d_path)
                            except Exception:
                                _copy_item(vm, m_path, d_path)
                                _rmtree(vm, m_path)
                            _draw_progress(vm, "Batch Move...", (i+1)/total)
                    else:
                        if _pending_dest_path != _context_target_path:
                            _draw_progress(vm, "Moving...", 0.0)
                            if _exists(vm, _pending_dest_path):
                                _rmtree(vm, _pending_dest_path)
                                time.sleep(0.1)
                            try:
                                storage.rename(_context_target_path, _pending_dest_path)
                            except Exception:
                                _copy_item(vm, _context_target_path, _pending_dest_path)
                                _rmtree(vm, _context_target_path)
                            _draw_progress(vm, "Moving...", 1.0)
                            
                elif _pending_action == ACT_RENAME:
                    if not is_batch and _pending_dest_path != _context_target_path:
                        _draw_progress(vm, "Renaming...", 0.0)
                        if _exists(vm, _pending_dest_path):
                            _rmtree(vm, _pending_dest_path)
                            time.sleep(0.1)
                        try:
                            storage.rename(_context_target_path, _pending_dest_path)
                        except Exception:
                            pass
                        _draw_progress(vm, "Renaming...", 1.0)
                
                if is_batch:
                    _app_state["marked"].clear()
                    
                if _pending_action in (ACT_DELETE, ACT_COPY, ACT_MOVE, ACT_RENAME):
                    _force_sync(vm)
                    _refresh_panes(vm)

            _confirm_menu = None
            _pending_action = ACT_NONE
            _context_target_path = ""
            _pending_dest_path = ""
            _needs_redraw = True
            time.sleep(0.3)

    elif _context_menu is not None:
        if btn == BUTTON_BACK:
            input_reset()
            _context_menu = None
            _needs_redraw = True
            time.sleep(0.3)
        elif btn == BUTTON_UP:
            input_reset()
            _context_menu.scroll_up()
            _needs_redraw = True
        elif btn == BUTTON_DOWN:
            input_reset()
            _context_menu.scroll_down()
            _needs_redraw = True
        elif btn == BUTTON_CENTER or key in (10, 13, '\n', '\r') or btn in (10, 13):
            input_reset()
            action = _context_menu.current_item
            if action == "Cancel":
                pass
            elif action == "Clear Marks":
                _app_state["marked"].clear()
                _refresh_panes(vm)
            elif action == "Open":
                act_pane = _app_state["active_pane"]
                if act_pane == PANE_LEFT:
                    _app_state["left_path"] = _context_target_path
                    _app_state["left_index"] = 0
                else:
                    _app_state["right_path"] = _context_target_path
                    _app_state["right_index"] = 0
                _refresh_panes(vm)
            elif action == "Delete":
                screen_h = vm.draw.size.y
                _pending_action = ACT_DELETE
                marked = _app_state["marked"]
                if len(marked) > 0:
                    _confirm_menu = Menu(vm.draw, f"Delete {len(marked)} items?", 0, screen_h, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2)
                else:
                    _confirm_menu = Menu(vm.draw, "Confirm Delete?", 0, screen_h, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2)
                _confirm_menu.add_item("No")
                _confirm_menu.add_item("Yes")
                _confirm_menu.set_selected(0)
            elif action == "Rename":
                _input_active = True
                _input_text = _context_target_path.split("/")[-1]
                _input_cursor = len(_input_text)
                _input_mode = MODE_RENAME
            elif action in ("Copy", "Move"):
                act_pane = _app_state["active_pane"]
                t_dir = _app_state["right_path"] if act_pane == PANE_LEFT else _app_state["left_path"]
                marked = _app_state["marked"]
                
                if len(marked) > 0:
                    screen_h = vm.draw.size.y
                    _pending_action = ACT_COPY if action == "Copy" else ACT_MOVE
                    _pending_dest_path = t_dir
                    _confirm_menu = Menu(vm.draw, f"Confirm {action}?", 0, screen_h, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2)
                    _confirm_menu.add_item("No")
                    _confirm_menu.add_item("Yes")
                    _confirm_menu.set_selected(0)
                else:
                    f_name = _context_target_path.split("/")[-1]
                    d_path = "/" + f_name if t_dir == "/" else t_dir + "/" + f_name
                    
                    if d_path == _context_target_path:
                        _input_active = True
                        _input_text = f_name
                        _input_cursor = len(_input_text)
                        _input_mode = MODE_COPY_SAME if action == "Copy" else MODE_RENAME
                    else:
                        screen_h = vm.draw.size.y
                        _pending_action = ACT_COPY if action == "Copy" else ACT_MOVE
                        _pending_dest_path = d_path
                        
                        exists = _exists(vm, d_path)
                        msg = "Overwrite?" if exists else f"Confirm {action}?"
                        
                        _confirm_menu = Menu(vm.draw, msg, 0, screen_h, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2)
                        _confirm_menu.add_item("No")
                        _confirm_menu.add_item("Yes")
                        _confirm_menu.set_selected(0)
                    
            _context_menu = None
            _needs_redraw = True
            time.sleep(0.3)

    elif btn == BUTTON_BACK:
        input_reset()
        if _is_help_screen:
            _is_help_screen = False
            _needs_redraw = True
        else:
            vm.back()
            return
        
    elif btn == BUTTON_LEFT and _is_help_screen == False:
        input_reset()
        _app_state["active_pane"] = PANE_LEFT
        _needs_redraw = True
        
    elif btn == BUTTON_RIGHT and _is_help_screen == False:
        input_reset()
        _app_state["active_pane"] = PANE_RIGHT
        _needs_redraw = True
        
    elif btn == BUTTON_UP and _is_help_screen == False:
        input_reset()
        act_pane = _app_state["active_pane"]
        files = _app_state["left_files"] if act_pane == PANE_LEFT else _app_state["right_files"]
        idx = _app_state["left_index"] if act_pane == PANE_LEFT else _app_state["right_index"]
        
        f_len = len(files)
        if f_len > 0:
            if act_pane == PANE_LEFT:
                _app_state["left_index"] = (idx - 1) % f_len
            else:
                _app_state["right_index"] = (idx - 1) % f_len
            _needs_redraw = True
        
    elif btn == BUTTON_DOWN and _is_help_screen == False:
        input_reset()
        act_pane = _app_state["active_pane"]
        files = _app_state["left_files"] if act_pane == PANE_LEFT else _app_state["right_files"]
        idx = _app_state["left_index"] if act_pane == PANE_LEFT else _app_state["right_index"]
        
        f_len = len(files)
        if f_len > 0:
            if act_pane == PANE_LEFT:
                _app_state["left_index"] = (idx + 1) % f_len
            else:
                _app_state["right_index"] = (idx + 1) % f_len
            _needs_redraw = True

    elif btn == BUTTON_CENTER and _is_help_screen == False:
        input_reset()
        act_pane = _app_state["active_pane"]
        current_path = _app_state["left_path"] if act_pane == PANE_LEFT else _app_state["right_path"]
        files = _app_state["left_files"] if act_pane == PANE_LEFT else _app_state["right_files"]
        idx = _app_state["left_index"] if act_pane == PANE_LEFT else _app_state["right_index"]
        
        if len(files) > 0:
            selected_file, is_dir, _ = files[idx]
            if selected_file == "..":
                parts = current_path.rstrip("/").split("/")
                folder_exited = parts[-1] if len(parts) > 1 else ""
                parent = "/" + "/".join(parts[1:-1])
                if parent == "//" or parent == "":
                    parent = "/"
                    
                if act_pane == PANE_LEFT:
                    _app_state["left_path"] = parent
                else:
                    _app_state["right_path"] = parent
                
                _refresh_panes(vm)
                
                new_files = _app_state["left_files"] if act_pane == PANE_LEFT else _app_state["right_files"]
                new_cursor_idx = 0
                for i, item_data in enumerate(new_files):
                    if item_data[0] == folder_exited:
                        new_cursor_idx = i
                        break
                        
                if act_pane == PANE_LEFT:
                    _app_state["left_index"] = new_cursor_idx
                else:
                    _app_state["right_index"] = new_cursor_idx
            else:
                new_path = "/" + selected_file if current_path == "/" else current_path + "/" + selected_file
                screen_h = vm.draw.size.y
                
                marked = _app_state["marked"]
                if is_dir and not _app_state.get("dir_menu", True) and len(marked) == 0:
                    if act_pane == PANE_LEFT:
                        _app_state["left_path"] = new_path
                        _app_state["left_index"] = 0
                    else:
                        _app_state["right_path"] = new_path
                        _app_state["right_index"] = 0
                    _refresh_panes(vm)
                elif len(marked) > 0:
                    _context_menu = Menu(vm.draw, f"{len(marked)} Marked", 0, screen_h, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2)
                    if is_dir:
                        _context_target_path = new_path
                        _context_menu.add_item("Open")
                    _context_menu.add_item("Copy")
                    _context_menu.add_item("Move")
                    _context_menu.add_item("Delete")
                    _context_menu.add_item("Clear Marks")
                    _context_menu.add_item("Cancel")
                    _context_menu.set_selected(0)
                    time.sleep(0.3)
                else:
                    _context_target_path = new_path
                    _context_menu = Menu(vm.draw, selected_file[:14], 0, screen_h, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2)
                    if is_dir:
                        _context_menu.add_item("Open")
                    _context_menu.add_item("Copy")
                    _context_menu.add_item("Move")
                    _context_menu.add_item("Rename")
                    _context_menu.add_item("Delete")
                    _context_menu.add_item("Cancel")
                    _context_menu.set_selected(0)
                    time.sleep(0.3)
            _needs_redraw = True

    if _needs_redraw:
        _draw_ui(vm)
        
    _auto_save(vm)
    gc.collect()

def stop(vm):
    global _app_state, _last_saved_json, _context_menu, _confirm_menu, show_options, opt_idx
    global _pending_action, _pending_dest_path, _sys, _input_active, _input_text, _input_cursor, _input_mode, _needs_redraw
    global _char_map, _is_disclaimer_screen, _show_info, _info_data
    
    _auto_save(vm)
    
    if _app_state is not None:
        if "marked" in _app_state:
            _app_state["marked"].clear()
        _app_state.clear()
    _app_state = None
    
    _last_saved_json = ""
    
    if _context_menu is not None:
        _context_menu.clear()
    _context_menu = None
    
    if _confirm_menu is not None:
        _confirm_menu.clear()
    _confirm_menu = None
    
    if _char_map is not None:
        _char_map.clear()
    _char_map = None
    
    show_options = False
    opt_idx = 0
    _pending_action = ACT_NONE
    _pending_dest_path = ""
    _input_active = False
    _input_text = ""
    _input_cursor = 0
    _input_mode = MODE_NONE
    _is_disclaimer_screen = False
    _show_info = False
    _info_data = []
    _needs_redraw = True
    _sys = None
    
    gc.collect()

from picoware.system.view_manager import ViewManager
from picoware.system.view import View

vm = None

try:
    vm = ViewManager()
    vm.add(
        View(
            "app_tester",
            run,
            start,
            stop,
        )
    )
    vm.switch_to("app_tester")
    while True:
        vm.run()
except Exception as e:
    print("Error during testing:", e)
finally:
    del vm
    vm = None