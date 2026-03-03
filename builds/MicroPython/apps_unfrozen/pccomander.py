import gc
import time
import json

from picoware.system.vector import Vector
from picoware.system.colors import TFT_WHITE, TFT_BLACK, TFT_BLUE, TFT_YELLOW, TFT_CYAN
from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_CENTER, BUTTON_BACK, BUTTON_H
from picoware.gui.menu import Menu
from picoware.system.system import System

_app_state = None
_last_saved_json = "{}"
_last_save_time = 0
_is_help_screen = False
_context_menu = None
_confirm_menu = None
_context_target_path = ""
_pending_action = ""
_sys = None

def _init_state():
    global _app_state
    _app_state = {
        "left_path": "/",
        "right_path": "/",
        "left_files": [],
        "right_files": [],
        "left_index": 0,
        "right_index": 0,
        "active_pane": "left"
    }

def _load_dir(vm, path):
    items = []
    if path != "/":
        items.append(("..", True))
    try:
        dir_list = vm.storage.listdir(path)
        for item in dir_list:
            if item == "." or item == "..":
                continue
            full_path = "/" + item if path == "/" else path + "/" + item
            is_dir = False
            try:
                if vm.storage.is_directory(full_path):
                    is_dir = True
            except Exception:
                pass
            items.append((item, is_dir))
        del dir_list
    except Exception:
        items.append(("<ERROR>", False))
    gc.collect()
    return items

def _draw_ui(vm):
    draw = vm.draw
    draw.clear(color=TFT_BLUE)
    
    screen_w = draw.size.x
    screen_h = draw.size.y
    mid_x = screen_w // 2
    
    char_limit = (mid_x - 8) // 8
    max_items = (screen_h - 38) // 12
    
    if _is_help_screen:
        draw.text(Vector(10, 10), "PicoCommander Help", TFT_WHITE)
        draw.text(Vector(10, 30), "H: Toggle Help", TFT_CYAN)
        draw.text(Vector(10, 42), "UP/DOWN: Scroll", TFT_WHITE)
        draw.text(Vector(10, 54), "L/R: Switch Pane", TFT_WHITE)
        draw.text(Vector(10, 66), "CENTER: Enter/Menu", TFT_WHITE)
        draw.text(Vector(10, 78), "BACK: Exit App", TFT_WHITE)
        
        used_ram = _sys.used_heap // 1024
        free_ram = _sys.free_heap // 1024
        draw.text(Vector(10, 102), f"RAM: {used_ram}KB used / {free_ram}KB free", TFT_YELLOW)
        
        if _sys.has_psram:
            used_psram = _sys.used_psram // 1024
            free_psram = _sys.free_psram // 1024
            draw.text(Vector(10, 114), f"PSRAM: {used_psram}KB used / {free_psram}KB free", TFT_YELLOW)

        draw.text(Vector(10, screen_h - 40), "made by Slasher006", TFT_CYAN)
        draw.text(Vector(10, screen_h - 30), "with the help of Gemini", TFT_CYAN)
        draw.text(Vector(10, screen_h - 20), "Date: 2026-03-03", TFT_CYAN)
        draw.swap()
        return

    if _confirm_menu is not None:
        _confirm_menu.draw()
        draw.swap()
        return

    if _context_menu is not None:
        _context_menu.draw()
        draw.swap()
        return

    draw.fill_rectangle(Vector(0, 0), Vector(screen_w, 12), TFT_CYAN)
    draw.text(Vector(2, 2), " Left    File    Command    Options    Right", TFT_BLACK)

    draw.fill_rectangle(Vector(mid_x, 12), Vector(1, screen_h - 24), TFT_CYAN)

    if _app_state["active_pane"] == "left":
        draw.fill_rectangle(Vector(0, 12), Vector(mid_x, 12), TFT_CYAN)
    draw.text(Vector(2, 14), _app_state["left_path"][:char_limit], TFT_BLACK if _app_state["active_pane"] == "left" else TFT_WHITE)
    left_start = max(0, _app_state["left_index"] - (max_items - 1))
    y_offset = 26
    for i, item_data in enumerate(_app_state["left_files"][left_start : left_start + max_items]):
        f_name, is_dir = item_data
        actual_idx = i + left_start
        display_name = "/" + f_name if is_dir else f_name
        base_color = TFT_YELLOW if is_dir else TFT_WHITE
        text_color = base_color if _app_state["active_pane"] == "right" or actual_idx != _app_state["left_index"] else TFT_BLACK
        if _app_state["active_pane"] == "left" and actual_idx == _app_state["left_index"]:
            draw.fill_rectangle(Vector(0, y_offset-1), Vector(mid_x - 2, 10), TFT_CYAN)
        draw.text(Vector(2, y_offset), display_name[:char_limit], text_color)
        y_offset += 12
        
    if _app_state["active_pane"] == "right":
        draw.fill_rectangle(Vector(mid_x + 1, 12), Vector(mid_x - 1, 12), TFT_CYAN)
    draw.text(Vector(mid_x + 4, 14), _app_state["right_path"][:char_limit], TFT_BLACK if _app_state["active_pane"] == "right" else TFT_WHITE)
    right_start = max(0, _app_state["right_index"] - (max_items - 1))
    y_offset = 26
    for i, item_data in enumerate(_app_state["right_files"][right_start : right_start + max_items]):
        f_name, is_dir = item_data
        actual_idx = i + right_start
        display_name = "/" + f_name if is_dir else f_name
        base_color = TFT_YELLOW if is_dir else TFT_WHITE
        text_color = base_color if _app_state["active_pane"] == "left" or actual_idx != _app_state["right_index"] else TFT_BLACK
        if _app_state["active_pane"] == "right" and actual_idx == _app_state["right_index"]:
            draw.fill_rectangle(Vector(mid_x + 2, y_offset-1), Vector(mid_x - 4, 10), TFT_CYAN)
        draw.text(Vector(mid_x + 4, y_offset), display_name[:char_limit], text_color)
        y_offset += 12

    draw.fill_rectangle(Vector(0, screen_h - 12), Vector(screen_w, 12), TFT_CYAN)
    draw.text(Vector(2, screen_h - 10), "H Help 3View 4Edit 5Copy 6RenMov 8Delete", TFT_BLACK)

    draw.swap()

def _auto_save(vm):
    global _last_saved_json, _last_save_time
    current_time = time.time()
    if current_time - _last_save_time > 5:
        current_json = json.dumps({"left": _app_state["left_path"], "right": _app_state["right_path"]})
        if current_json != _last_saved_json:
            try:
                vm.storage.write("picocmd_state.json", current_json, "w")
                _last_saved_json = current_json
            except Exception:
                pass
        _last_save_time = current_time

def start(vm):
    global _sys
    _sys = System()
    _init_state()
    _app_state["left_files"] = _load_dir(vm, _app_state["left_path"])
    _app_state["right_files"] = _load_dir(vm, _app_state["right_path"])
    gc.collect()
    return True

def run(vm):
    global _is_help_screen, _context_menu, _confirm_menu, _context_target_path, _pending_action
    
    input_mgr = vm.input_manager
    btn = input_mgr.button
    
    if btn == BUTTON_H:
        input_mgr.reset()
        _is_help_screen = not _is_help_screen

    elif _confirm_menu is not None:
        if btn == BUTTON_BACK:
            input_mgr.reset()
            _confirm_menu = None
            _pending_action = ""
            gc.collect()
        elif btn == BUTTON_UP:
            input_mgr.reset()
            _confirm_menu.scroll_up()
        elif btn == BUTTON_DOWN:
            input_mgr.reset()
            _confirm_menu.scroll_down()
        elif btn == BUTTON_CENTER:
            input_mgr.reset()
            selection = _confirm_menu.current_item
            if selection == "Yes":
                if _pending_action == "delete":
                    try:
                        vm.storage.remove(_context_target_path)
                        _app_state["left_files"] = _load_dir(vm, _app_state["left_path"])
                        _app_state["right_files"] = _load_dir(vm, _app_state["right_path"])
                    except Exception:
                        pass
            _confirm_menu = None
            _pending_action = ""
            _context_target_path = ""
            gc.collect()

    elif _context_menu is not None:
        if btn == BUTTON_BACK:
            input_mgr.reset()
            _context_menu = None
            gc.collect()
        elif btn == BUTTON_UP:
            input_mgr.reset()
            _context_menu.scroll_up()
        elif btn == BUTTON_DOWN:
            input_mgr.reset()
            _context_menu.scroll_down()
        elif btn == BUTTON_CENTER:
            input_mgr.reset()
            action = _context_menu.current_item
            if action == "Cancel":
                pass
            elif action == "Delete":
                screen_h = vm.draw.size.y
                _pending_action = "delete"
                _confirm_menu = Menu(vm.draw, "Confirm Delete?", 0, screen_h, TFT_WHITE, TFT_BLUE, selected_color=TFT_CYAN, border_color=TFT_CYAN, border_width=2)
                _confirm_menu.add_item("No")
                _confirm_menu.add_item("Yes")
                _confirm_menu.set_selected(0)
            elif action == "Execute":
                pass
            elif action == "Copy":
                pass
            elif action == "Move":
                pass
            _context_menu = None
            gc.collect()

    elif btn == BUTTON_BACK:
        input_mgr.reset()
        if _is_help_screen:
            _is_help_screen = False
        else:
            vm.back()
            return
        
    elif btn == BUTTON_LEFT and _is_help_screen == False:
        input_mgr.reset()
        _app_state["active_pane"] = "left"
        
    elif btn == BUTTON_RIGHT and _is_help_screen == False:
        input_mgr.reset()
        _app_state["active_pane"] = "right"
        
    elif btn == BUTTON_UP and _is_help_screen == False:
        input_mgr.reset()
        pane = _app_state["active_pane"]
        idx_key = pane + "_index"
        if _app_state[idx_key] > 0:
            _app_state[idx_key] -= 1
        
    elif btn == BUTTON_DOWN and _is_help_screen == False:
        input_mgr.reset()
        pane = _app_state["active_pane"]
        idx_key = pane + "_index"
        files_key = pane + "_files"
        if _app_state[idx_key] < len(_app_state[files_key]) - 1:
            _app_state[idx_key] += 1

    elif btn == BUTTON_CENTER and _is_help_screen == False:
        input_mgr.reset()
        pane = _app_state["active_pane"]
        path_key = pane + "_path"
        files_key = pane + "_files"
        idx_key = pane + "_index"
        current_path = _app_state[path_key]
        
        if len(_app_state[files_key]) > 0:
            selected_file, is_dir = _app_state[files_key][_app_state[idx_key]]
            if selected_file == "..":
                parts = current_path.rstrip("/").split("/")
                folder_exited = parts[-1] if len(parts) > 1 else ""
                parent = "/" + "/".join(parts[1:-1])
                if parent == "//" or parent == "":
                    parent = "/"
                _app_state[path_key] = parent
                new_file_list = _load_dir(vm, parent)
                _app_state[files_key] = new_file_list
                new_cursor_idx = 0
                for i, item_data in enumerate(new_file_list):
                    if item_data[0] == folder_exited:
                        new_cursor_idx = i
                        break
                _app_state[idx_key] = new_cursor_idx
            else:
                new_path = "/" + selected_file if current_path == "/" else current_path + "/" + selected_file
                if is_dir:
                    _app_state[path_key] = new_path
                    _app_state[files_key] = _load_dir(vm, new_path)
                    _app_state[idx_key] = 0
                else:
                    screen_h = vm.draw.size.y
                    _context_target_path = new_path
                    _context_menu = Menu(vm.draw, selected_file[:14], 0, screen_h, TFT_WHITE, TFT_BLUE, selected_color=TFT_CYAN, border_color=TFT_CYAN, border_width=2)
                    _context_menu.add_item("Execute")
                    _context_menu.add_item("Copy")
                    _context_menu.add_item("Move")
                    _context_menu.add_item("Delete")
                    _context_menu.add_item("Cancel")
                    _context_menu.set_selected(0)

    _draw_ui(vm)
    _auto_save(vm)
    gc.collect()

def stop(vm):
    global _app_state, _last_saved_json, _context_menu, _confirm_menu, _pending_action, _sys
    _app_state.clear()
    _app_state = None
    _last_saved_json = None
    _context_menu = None
    _confirm_menu = None
    _pending_action = ""
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