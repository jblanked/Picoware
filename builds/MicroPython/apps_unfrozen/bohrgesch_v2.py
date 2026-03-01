import time
import json
import gc
import os
import math

from picoware.system.system import System
from picoware.system.vector import Vector
from picoware.system.colors import (
    TFT_ORANGE, TFT_DARKGREY, TFT_LIGHTGREY, TFT_WHITE,
    TFT_BLACK, TFT_BLUE, TFT_YELLOW, TFT_GREEN, TFT_RED, TFT_CYAN
)

from picoware.system.buttons import (
    BUTTON_BACK, BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_CENTER,
    BUTTON_0, BUTTON_1, BUTTON_2, BUTTON_3, BUTTON_4, 
    BUTTON_5, BUTTON_6, BUTTON_7, BUTTON_8, BUTTON_9,
    BUTTON_PERIOD, BUTTON_BACKSPACE,
    BUTTON_S, BUTTON_M, BUTTON_D, BUTTON_V, BUTTON_R, BUTTON_H, BUTTON_ESCAPE
)

_SETTINGS_FILE = "/picoware/settings/drill_pro_settings.json" 
_VERSION = "1.8"

_MATERIALS = (
    ("Aluminium", 45, TFT_WHITE),
    ("Brass",     35, TFT_YELLOW),
    ("Wood",      28, TFT_ORANGE),
    ("Steel St37", 22, TFT_GREEN),
    ("Plastic",   18, TFT_CYAN),
    ("Stainless", 12, TFT_BLUE),
    ("Custom",    0,  TFT_RED)
)

MODE_MAIN = 0
MODE_HELP = 1
MODE_TYPING = 2

TYPING_NONE = -1
TYPING_DIA = 0
TYPING_VC = 1
TYPING_RPM = 2

state = {
    "mat_index": 3,
    "custom_vc": "30",
    "diameter_mm": "5.0",
    "max_rpm": "3500",
    "mode_sink": False,
    "cursor_idx": 0
}

current_mode = MODE_MAIN
active_typing_field = TYPING_NONE
rpm_result = "0"
is_capped = False
storage = None
help_scroll = 0
dirty_ui = True
blink_counter = 0
cursor_visible = True
pending_save = False
save_timer = 0
_last_saved_json = ""
_cached_help_lines = []
has_hardware = True
board_name = "Unknown"
sys_time = time

def get_help_lines():
    global board_name, _cached_help_lines
    import gc
    gc.collect() 
    ram_str = f"RAM: {gc.mem_alloc() // 1024}KB / {gc.mem_free() // 1024}KB"
    
    if _cached_help_lines:
        _cached_help_lines[5] = ram_str
        return _cached_help_lines
        
    b_name = board_name[:18]
    hw_fw = os.uname().release if hasattr(os, "uname") else "Unknown FW"
        
    _cached_help_lines = [
        f"DRILL SPEED PRO v{_VERSION}",
        "--------------------",
        "DEBUG INFO:",
        f"Board: {b_name}",
        f"FW: {hw_fw}",
        ram_str,
        "",
        "CREDITS:",
        "made by Slasher006",
        "with the help of Gemini",
        "Date: 2026-03-01",
        "",
        "ABOUT:",
        "Calculates safe spindle RPM.",
        "",
        "MODES:",
        "- DRILL: Standard calc.",
        "- SINK: Forces Dia to 20mm.",
        "",
        "SHORTCUTS:",
        "[S] Key: Toggle Mode",
        "[M] Key: Cycle Material",
        "[D] Key: Edit Diameter",
        "[V] Key: Edit Custom Vc",
        "[R] Key: Edit Max RPM",
        "[H] Key: Open Help",
        "[ESC] Key: Exit App",
        "",
        "CONTROLS:",
        "[UP/DN]: Move Cursor",
        "[L/R]: Change Mode/Material",
        "[CENTER]: Select / Confirm",
        "[BACK]/[ESC]: Cancel / Exit"
    ]
    return _cached_help_lines

def queue_save():
    global pending_save, save_timer
    pending_save = True
    save_timer = 150

def save_settings():
    global storage, _last_saved_json
    if not storage: return
    try:
        save_data = state.copy()
        json_str = json.dumps(save_data)
        if json_str == _last_saved_json: return
        storage.write(_SETTINGS_FILE, json_str, "w")
        _last_saved_json = json_str
        import gc
        gc.collect()
    except Exception: pass

def validate_and_load_settings():
    global state, storage, _last_saved_json
    if storage and storage.exists(_SETTINGS_FILE):
        try:
            raw_data = storage.read(_SETTINGS_FILE, "r")
            loaded = json.loads(raw_data)
            for key in state:
                if key in loaded: state[key] = loaded[key]
            _last_saved_json = json.dumps(state)
        except Exception: pass

def validate_hardware_and_time(view_manager):
    global board_name, has_hardware
    sys_inst = System()
    try:
        b_name = sys_inst.board_name
        if callable(b_name): b_name = b_name()
    except Exception:
        b_name = os.uname().machine if hasattr(os, "uname") else "Unknown Board"
    board_name = str(b_name)
    try:
        hw = sys_inst.has_wifi
        if callable(hw): hw = hw()
    except Exception:
        hw = False
    has_hardware = bool(hw)

def calculate_rpm_metric():
    global is_capped
    try:
        d = 20.0 if state["mode_sink"] else float(state["diameter_mm"])
        mat = _MATERIALS[state["mat_index"]]
        vc = float(state["custom_vc"]) if mat[0] == "Custom" else mat[1]
        limit = float(state["max_rpm"])
        
        if d <= 0 or vc <= 0: return "0"
        
        rpm = (vc * 1000) / (math.pi * d)
        
        if rpm > limit:
            is_capped = True
            return str(int(limit))
        else:
            is_capped = False
            return str(int(rpm))
    except Exception:
        return "Error"

def handle_direct_input(button):
    global dirty_ui, cursor_visible, blink_counter
    
    if active_typing_field == TYPING_DIA: target_key = "diameter_mm"
    elif active_typing_field == TYPING_VC: target_key = "custom_vc"
    elif active_typing_field == TYPING_RPM: target_key = "max_rpm"
    else: return
    
    current_val = state[target_key]
    digit = -1
    
    if button == BUTTON_0: digit = 0
    elif button == BUTTON_1: digit = 1
    elif button == BUTTON_2: digit = 2
    elif button == BUTTON_3: digit = 3
    elif button == BUTTON_4: digit = 4
    elif button == BUTTON_5: digit = 5
    elif button == BUTTON_6: digit = 6
    elif button == BUTTON_7: digit = 7
    elif button == BUTTON_8: digit = 8
    elif button == BUTTON_9: digit = 9

    if digit != -1:
        if current_val in ("0", "0.0"): state[target_key] = str(digit)
        else: state[target_key] += str(digit)
        dirty_ui = True
        
    elif button == BUTTON_PERIOD:
        if "." not in current_val:
            state[target_key] += "."
            dirty_ui = True
            
    elif button == BUTTON_BACKSPACE:
        if len(current_val) > 0:
            state[target_key] = current_val[:-1]
            if state[target_key] == "": state[target_key] = "0"
            dirty_ui = True

    if dirty_ui:
        cursor_visible = True
        blink_counter = 0

def handle_input_typing(button, input_mgr, view_manager):
    global current_mode, active_typing_field, dirty_ui
    
    if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER):
        current_mode = MODE_MAIN; active_typing_field = TYPING_NONE; dirty_ui = True; return
        
    handle_direct_input(button)

def handle_input_help(button, input_mgr, view_manager):
    global current_mode, help_scroll, dirty_ui
    if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_H): 
        current_mode = MODE_MAIN; help_scroll = 0; dirty_ui = True
    elif button == BUTTON_DOWN: help_scroll += 1; dirty_ui = True
    elif button == BUTTON_UP: help_scroll = max(0, help_scroll - 1); dirty_ui = True

def handle_input_main(button, input_mgr, view_manager):
    global current_mode, active_typing_field, dirty_ui, cursor_visible, blink_counter
    
    if button in (BUTTON_BACK, BUTTON_ESCAPE):
        save_settings(); input_mgr.reset(); view_manager.back(); return

    elif button == BUTTON_S:
        state["cursor_idx"] = 0; state["mode_sink"] = not state["mode_sink"]; dirty_ui = True
    elif button == BUTTON_M:
        state["cursor_idx"] = 1; state["mat_index"] = (state["mat_index"] + 1) % len(_MATERIALS); dirty_ui = True
    elif button == BUTTON_D:
        state["cursor_idx"] = 2; current_mode = MODE_TYPING; active_typing_field = TYPING_DIA
        blink_counter = 0; cursor_visible = True; dirty_ui = True
    elif button == BUTTON_V:
        state["cursor_idx"] = 3; state["mat_index"] = 6
        current_mode = MODE_TYPING; active_typing_field = TYPING_VC
        blink_counter = 0; cursor_visible = True; dirty_ui = True
    elif button == BUTTON_R:
        state["cursor_idx"] = 4; current_mode = MODE_TYPING; active_typing_field = TYPING_RPM
        blink_counter = 0; cursor_visible = True; dirty_ui = True
    elif button == BUTTON_H:
        state["cursor_idx"] = 5; current_mode = MODE_HELP; dirty_ui = True

    elif button == BUTTON_DOWN: state["cursor_idx"] = (state["cursor_idx"] + 1) % 6; dirty_ui = True
    elif button == BUTTON_UP: state["cursor_idx"] = (state["cursor_idx"] - 1) % 6; dirty_ui = True

    elif button in (BUTTON_LEFT, BUTTON_RIGHT):
        c_idx = state["cursor_idx"]
        if c_idx == 0:
            state["mode_sink"] = not state["mode_sink"]; dirty_ui = True
        elif c_idx == 1:
            if button == BUTTON_RIGHT: state["mat_index"] = (state["mat_index"] + 1) % len(_MATERIALS)
            else: state["mat_index"] = (state["mat_index"] - 1) % len(_MATERIALS)
            dirty_ui = True

    elif button == BUTTON_CENTER:
        c_idx = state["cursor_idx"]
        if c_idx == 0: state["mode_sink"] = not state["mode_sink"]
        elif c_idx == 1: state["mat_index"] = (state["mat_index"] + 1) % len(_MATERIALS)
        elif c_idx == 2: current_mode = MODE_TYPING; active_typing_field = TYPING_DIA; blink_counter = 0; cursor_visible = True
        elif c_idx == 3: state["mat_index"] = 6; current_mode = MODE_TYPING; active_typing_field = TYPING_VC; blink_counter = 0; cursor_visible = True
        elif c_idx == 4: current_mode = MODE_TYPING; active_typing_field = TYPING_RPM; blink_counter = 0; cursor_visible = True
        elif c_idx == 5: current_mode = MODE_HELP
        dirty_ui = True

INPUT_DISPATCH = {
    MODE_MAIN: handle_input_main,
    MODE_HELP: handle_input_help,
    MODE_TYPING: handle_input_typing
}

def draw_help(view_manager, draw, screen_w, screen_h):
    global help_scroll
    lines = get_help_lines()
    max_scroll = max(0, len(lines) - 12)
    help_scroll = min(help_scroll, max_scroll)
    
    for i in range(12):
        if help_scroll + i < len(lines):
            draw.text(Vector(10, 10 + i * 20), lines[help_scroll + i], TFT_WHITE)
            
    draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 40), TFT_BLACK)
    draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), TFT_GREEN)
    draw.text(Vector(5, screen_h - 32), "[UP/DN] Scroll  [ESC/H] Close", TFT_GREEN)

def draw_main(view_manager, draw, screen_w, screen_h):
    draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), TFT_DARKGREY)
    mat = _MATERIALS[state["mat_index"]]
    c_idx = state["cursor_idx"]
    
    draw.fill_rectangle(Vector(0, 0), Vector(screen_w, 30), TFT_BLACK)
    mode_text = "MODE: COUNTERSINK" if state["mode_sink"] else "MODE: DRILLING"
    mode_color = TFT_YELLOW if c_idx == 0 else (TFT_ORANGE if state["mode_sink"] else TFT_GREEN)
    draw.text(Vector(10, 10), mode_text, mode_color)
    if c_idx == 0: draw.text(Vector(screen_w - 20, 10), "<", TFT_YELLOW)
    draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), TFT_LIGHTGREY)
    
    out_y = 45
    draw.fill_round_rectangle(Vector(10, out_y), Vector(screen_w - 20, 60), 5, TFT_BLACK)
    draw.rect(Vector(10, out_y), Vector(screen_w - 20, 60), TFT_WHITE)
    draw.text(Vector(20, out_y + 10), "TARGET RPM:", TFT_LIGHTGREY)
    res_color = TFT_RED if is_capped else TFT_GREEN
    draw.text(Vector(20, out_y + 35), f"{rpm_result}", res_color)
    if is_capped: draw.text(Vector(120, out_y + 35), "(LIMIT)", TFT_RED)

    in_y = 120
    
    draw.text(Vector(15, in_y), "Material:", TFT_YELLOW if c_idx == 1 else TFT_LIGHTGREY)
    mat_color = TFT_YELLOW if c_idx == 1 else mat[2]
    draw.text(Vector(100, in_y), f"< {mat[0]} >", mat_color)
    if c_idx == 1: draw.text(Vector(screen_w - 20, in_y), "<", TFT_YELLOW)
    
    draw.text(Vector(15, in_y + 30), "Diameter:", TFT_YELLOW if c_idx == 2 else TFT_LIGHTGREY)
    dia_color = TFT_YELLOW if c_idx == 2 else TFT_WHITE
    if state["mode_sink"]: dia_color = TFT_LIGHTGREY 
    if active_typing_field == TYPING_DIA: dia_color = TFT_CYAN
    dia_cursor = "_" if (active_typing_field == TYPING_DIA and cursor_visible) else ""
    draw.text(Vector(100, in_y + 30), f"{state['diameter_mm']}{dia_cursor} mm", dia_color)
    if c_idx == 2: draw.text(Vector(screen_w - 20, in_y + 30), "<", TFT_YELLOW)
    
    draw.text(Vector(15, in_y + 60), "Vc (m/min):", TFT_YELLOW if c_idx == 3 else TFT_LIGHTGREY)
    vc_color = TFT_YELLOW if c_idx == 3 else TFT_WHITE
    if mat[0] != "Custom": vc_color = TFT_LIGHTGREY
    if active_typing_field == TYPING_VC: vc_color = TFT_CYAN
    vc_val = state["custom_vc"] if mat[0] == "Custom" else mat[1]
    vc_cursor = "_" if (active_typing_field == TYPING_VC and cursor_visible) else ""
    draw.text(Vector(100, in_y + 60), f"{vc_val}{vc_cursor}", vc_color)
    if c_idx == 3: draw.text(Vector(screen_w - 20, in_y + 60), "<", TFT_YELLOW)

    draw.text(Vector(15, in_y + 90), "Max Spindle:", TFT_YELLOW if c_idx == 4 else TFT_LIGHTGREY)
    rpm_color = TFT_YELLOW if c_idx == 4 else TFT_WHITE
    if active_typing_field == TYPING_RPM: rpm_color = TFT_CYAN
    rpm_cursor = "_" if (active_typing_field == TYPING_RPM and cursor_visible) else ""
    draw.text(Vector(100, in_y + 90), f"{state['max_rpm']}{rpm_cursor}", rpm_color)
    if c_idx == 4: draw.text(Vector(screen_w - 20, in_y + 90), "<", TFT_YELLOW)
    
    draw.text(Vector(15, in_y + 120), "View Help / Manual", TFT_YELLOW if c_idx == 5 else TFT_LIGHTGREY)
    if c_idx == 5: draw.text(Vector(screen_w - 20, in_y + 120), "<", TFT_YELLOW)

    draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), TFT_LIGHTGREY)
    draw.text(Vector(5, screen_h - 32), "[S]Mode [M]Mat [D]Dia [R]RPM", TFT_CYAN)
    draw.text(Vector(5, screen_h - 15), "[UP/DN] Move Cursor | [ENT] Edit", TFT_WHITE)

VIEW_DISPATCH = {
    MODE_MAIN: draw_main,
    MODE_HELP: draw_help,
    MODE_TYPING: draw_main
}

def start(view_manager):
    global rpm_result, storage, dirty_ui, current_mode, active_typing_field
    current_mode = MODE_MAIN
    active_typing_field = TYPING_NONE
    storage = view_manager.storage
    validate_hardware_and_time(view_manager)
    validate_and_load_settings()
    rpm_result = calculate_rpm_metric()
    dirty_ui = True
    return True

def run(view_manager):
    global rpm_result, current_mode, dirty_ui, blink_counter, cursor_visible, pending_save, save_timer
    
    draw = view_manager.draw; input_mgr = view_manager.input_manager; button = input_mgr.button
    screen_w = draw.size.x; screen_h = draw.size.y
    
    if current_mode == MODE_TYPING:
        blink_counter += 1
        if blink_counter > 15:
            blink_counter = 0; cursor_visible = not cursor_visible; dirty_ui = True

    if button == -1 and not dirty_ui and not pending_save: return

    if button != -1:
        handler = INPUT_DISPATCH.get(current_mode)
        if handler: handler(button, input_mgr, view_manager)
        
        input_mgr.reset()
        if dirty_ui: queue_save()

    if pending_save and button == -1:
        if save_timer > 0: save_timer -= 1
        else: save_settings(); pending_save = False

    if dirty_ui and current_mode in (MODE_MAIN, MODE_TYPING):
        rpm_result = calculate_rpm_metric()

    if dirty_ui:
        if current_mode == MODE_HELP:
            draw.clear()
            draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), TFT_BLACK)
        
        handler = VIEW_DISPATCH.get(current_mode)
        if handler: handler(view_manager, draw, screen_w, screen_h)
        
        draw.swap(); dirty_ui = False

def stop(view_manager):
    global state, _MATERIALS, _last_saved_json, _cached_help_lines
    global INPUT_DISPATCH, VIEW_DISPATCH
    global rpm_result, storage, current_mode, active_typing_field
    global dirty_ui, blink_counter, cursor_visible, pending_save, save_timer, help_scroll
    
    save_settings()
    
    if state is not None: state.clear()
    state = None
    
    _MATERIALS = None
    INPUT_DISPATCH = None
    VIEW_DISPATCH = None
    _last_saved_json = ""
    _cached_help_lines = []
    
    rpm_result = "0"
    storage = None
    current_mode = MODE_MAIN
    active_typing_field = TYPING_NONE
    
    dirty_ui = pending_save = False
    blink_counter = save_timer = help_scroll = 0
    cursor_visible = True
    
    import gc
    gc.collect()
