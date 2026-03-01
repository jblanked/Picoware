import time
import json
import gc
import os

from picoware.system.system import System
from picoware.system.vector import Vector
from picoware.system.colors import (
    TFT_ORANGE, TFT_DARKGREY, TFT_LIGHTGREY, TFT_WHITE,
    TFT_BLACK, TFT_BLUE, TFT_YELLOW, TFT_GREEN, TFT_RED
)

from picoware.system.buttons import (
    BUTTON_BACK, BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_CENTER,
    BUTTON_0, BUTTON_1, BUTTON_2, BUTTON_3, BUTTON_4, 
    BUTTON_5, BUTTON_6, BUTTON_7, BUTTON_8, BUTTON_9,
    BUTTON_PERIOD, BUTTON_BACKSPACE,
    BUTTON_C, BUTTON_F, BUTTON_T, BUTTON_V, BUTTON_H, BUTTON_ESCAPE,
    BUTTON_M, BUTTON_O
)

_SETTINGS_FILE = "/picoware/settings/unit_converter_settings.json" 
_VERSION = "1.95"

_THEMES = (
    ("Green", TFT_GREEN),
    ("Red", TFT_RED),
    ("Blue", TFT_BLUE),
    ("Yellow", TFT_YELLOW),
    ("Orange", TFT_ORANGE)
)

_CONVERSIONS = (
    ("Length", (("um", 0.000001), ("thou", 0.0000254), ("mm", 0.001), ("cm", 0.01), ("m", 1.0), ("in", 0.0254), ("ft", 0.3048), ("yd", 0.9144))),
    ("Weight", (("mg", 0.000001), ("g", 0.001), ("kg", 1.0), ("oz", 0.0283495), ("lb", 0.453592))),
    ("Volume", (("ml", 0.001), ("L", 1.0), ("gal", 3.78541), ("fl oz", 0.0295735))),
    ("Kitchen", (("ml", 1.0), ("tsp", 4.92892), ("tbsp", 14.7868), ("fl oz", 29.5735), ("cup", 236.588), ("pint", 473.176), ("L", 1000.0))),
    ("Area", (("cm2", 0.0001), ("m2", 1.0), ("sq in", 0.00064516), ("sq ft", 0.092903))),
    ("Speed", (("mm/s", 0.001), ("m/s", 1.0), ("km/h", 0.277778), ("mph", 0.44704))),
    ("Press", (("Pa", 1.0), ("kPa", 1000.0), ("bar", 100000.0), ("psi", 6894.76))),
    ("Torque", (("Nmm", 0.001), ("Nm", 1.0), ("in-lb", 0.1129848), ("ft-lb", 1.355818))),
    ("Power", (("W", 1.0), ("kW", 1000.0), ("hp", 745.7))),
    ("Angle", (("deg", 1.0), ("rad", 57.2957795))),
    ("Temp", (("C", 0), ("F", 0), ("K", 0)))
)

# --- VIEW MODE CONSTANTS ---
MODE_MAIN = 0
MODE_OPTIONS = 1
MODE_HELP = 2
MODE_TYPING = 3

state = {
    "category_idx": 0, "from_idx": 0, "to_idx": 1, "input_val": "1.0",
    "cursor_idx": 0, "theme_idx": 0, "bg_r": 0, "bg_g": 0, "bg_b": 0,
    "options_cursor_idx": 0
}

# Volatile state
current_mode = MODE_MAIN
conv_result = "0.0"
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
        f"UNIT CONVERTER v{_VERSION}",
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
        "CATEGORIES:",
        "- Len, Area, Vol",
        "- Kitch, Wgt, Spd",
        "- Press, Torq, Pwr",
        "- Ang, Temp",
        "",
        "SHORTCUTS:",
        "[C] Cycle Cat",
        "[F] Edit From",
        "[T] Edit To",
        "[V] Edit Value (Clears)",
        "[H] Open Help",
        "[O] Open Options",
        "[M] Toggle +/-",
        "[ESC] Exit App",
        "",
        "CONTROLS:",
        "[UP/DN]: Cursor Nav",
        "[L/R]: Select / Edit",
        "[ENTER]: Confirm",
        "[BACK]: Exit App"
    ]
    return _cached_help_lines

def rgb_to_565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

def queue_save():
    global pending_save, save_timer
    pending_save = True
    save_timer = 150

def save_settings():
    global storage, _last_saved_json
    if not storage: return
    try:
        json_str = json.dumps(state)
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

def calculate_conversion():
    try:
        val = float(state["input_val"])
        c_idx, f_idx, t_idx = state["category_idx"], state["from_idx"], state["to_idx"]
        cat_name = _CONVERSIONS[c_idx][0]
        
        if cat_name == "Temp":
            from_name = _CONVERSIONS[c_idx][1][f_idx][0]
            to_name = _CONVERSIONS[c_idx][1][t_idx][0]
            celsius_val = 0.0
            
            if from_name == "C": celsius_val = val
            elif from_name == "F": celsius_val = (val - 32) * 5.0 / 9.0
            elif from_name == "K": celsius_val = val - 273.15
            
            if to_name == "C": final_val = celsius_val
            elif to_name == "F": final_val = (celsius_val * 9.0 / 5.0) + 32
            elif to_name == "K": final_val = celsius_val + 273.15
            return f"{final_val:.3f}"
            
        else:
            from_mult = _CONVERSIONS[c_idx][1][f_idx][1]
            to_mult = _CONVERSIONS[c_idx][1][t_idx][1]
            base_val = val * from_mult
            final_val = base_val / to_mult
            
            if final_val < 0.0001 and final_val > 0: return f"{final_val:.2e}"
            return f"{final_val:.4f}"
    except Exception:
        return "Error"

def clamp_unit_indices():
    c_idx = state["category_idx"]
    max_units = len(_CONVERSIONS[c_idx][1])
    if state["from_idx"] >= max_units: state["from_idx"] = max_units - 1
    if state["to_idx"] >= max_units: state["to_idx"] = max_units - 1
    
    if _CONVERSIONS[c_idx][0] not in ("Temp", "Angle", "Torque"):
        if state["input_val"].startswith("-"):
            state["input_val"] = state["input_val"][1:]
            if state["input_val"] == "": state["input_val"] = "0"

def handle_input_typing(button, input_mgr, view_manager):
    global current_mode, dirty_ui, cursor_visible, blink_counter
    
    if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER):
        current_mode = MODE_MAIN; dirty_ui = True; return
        
    current_val = state["input_val"]
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
        if current_val in ("0", "0.0"): state["input_val"] = str(digit)
        elif current_val in ("-0", "-0.0"): state["input_val"] = "-" + str(digit)
        else: state["input_val"] += str(digit)
        dirty_ui = True
        
    elif button == BUTTON_PERIOD:
        if "." not in current_val:
            state["input_val"] += "."
            dirty_ui = True
            
    elif button == BUTTON_BACKSPACE:
        if len(current_val) > 0:
            state["input_val"] = current_val[:-1]
            if state["input_val"] in ("", "-"): state["input_val"] = "0"
            dirty_ui = True
            
    elif button == BUTTON_M:
        if _CONVERSIONS[state["category_idx"]][0] in ("Temp", "Angle", "Torque"):
            if current_val.startswith("-"): state["input_val"] = current_val[1:]
            else: state["input_val"] = "-" + current_val
            dirty_ui = True

    if dirty_ui:
        cursor_visible = True
        blink_counter = 0

def handle_input_options(button, input_mgr, view_manager):
    global current_mode, dirty_ui
    if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER):
        current_mode = MODE_MAIN; dirty_ui = True; queue_save()
    elif button == BUTTON_DOWN: state["options_cursor_idx"] = (state["options_cursor_idx"] + 1) % 4; dirty_ui = True
    elif button == BUTTON_UP: state["options_cursor_idx"] = (state["options_cursor_idx"] - 1) % 4; dirty_ui = True
    elif button == BUTTON_RIGHT:
        o_idx = state["options_cursor_idx"]
        if o_idx == 0: state["theme_idx"] = (state["theme_idx"] + 1) % len(_THEMES)
        elif o_idx == 1: state["bg_r"] = (state["bg_r"] + 5) % 256
        elif o_idx == 2: state["bg_g"] = (state["bg_g"] + 5) % 256
        elif o_idx == 3: state["bg_b"] = (state["bg_b"] + 5) % 256
        dirty_ui = True; queue_save()
    elif button == BUTTON_LEFT:
        o_idx = state["options_cursor_idx"]
        if o_idx == 0: state["theme_idx"] = (state["theme_idx"] - 1) % len(_THEMES)
        elif o_idx == 1: state["bg_r"] = (state["bg_r"] - 5) % 256
        elif o_idx == 2: state["bg_g"] = (state["bg_g"] - 5) % 256
        elif o_idx == 3: state["bg_b"] = (state["bg_b"] - 5) % 256
        dirty_ui = True; queue_save()

def handle_input_help(button, input_mgr, view_manager):
    global current_mode, help_scroll, dirty_ui
    if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_H): 
        current_mode = MODE_MAIN; help_scroll = 0; dirty_ui = True
    elif button == BUTTON_DOWN: help_scroll += 1; dirty_ui = True
    elif button == BUTTON_UP: help_scroll = max(0, help_scroll - 1); dirty_ui = True

def handle_input_main(button, input_mgr, view_manager):
    global current_mode, dirty_ui, cursor_visible, blink_counter
    
    if button in (BUTTON_BACK, BUTTON_ESCAPE):
        save_settings(); input_mgr.reset(); view_manager.back(); return
        
    elif button == BUTTON_C:
        state["cursor_idx"] = 0
        state["category_idx"] = (state["category_idx"] + 1) % len(_CONVERSIONS)
        clamp_unit_indices(); dirty_ui = True
    elif button == BUTTON_F:
        state["cursor_idx"] = 1
        state["from_idx"] = (state["from_idx"] + 1) % len(_CONVERSIONS[state["category_idx"]][1]); dirty_ui = True
    elif button == BUTTON_T:
        state["cursor_idx"] = 2
        state["to_idx"] = (state["to_idx"] + 1) % len(_CONVERSIONS[state["category_idx"]][1]); dirty_ui = True
    elif button == BUTTON_V:
        state["cursor_idx"] = 3; current_mode = MODE_TYPING; state["input_val"] = "0"
        blink_counter = 0; cursor_visible = True; dirty_ui = True
    elif button == BUTTON_H: current_mode = MODE_HELP; state["cursor_idx"] = 4; dirty_ui = True
    elif button == BUTTON_O: current_mode = MODE_OPTIONS; state["cursor_idx"] = 5; dirty_ui = True
        
    elif button == BUTTON_M:
        if _CONVERSIONS[state["category_idx"]][0] in ("Temp", "Angle", "Torque"):
            if state["input_val"].startswith("-"): state["input_val"] = state["input_val"][1:]
            else: state["input_val"] = "-" + state["input_val"]
            dirty_ui = True
            
    elif button == BUTTON_DOWN: state["cursor_idx"] = (state["cursor_idx"] + 1) % 6; dirty_ui = True
    elif button == BUTTON_UP: state["cursor_idx"] = (state["cursor_idx"] - 1) % 6; dirty_ui = True
        
    elif button in (BUTTON_LEFT, BUTTON_RIGHT):
        c_idx = state["cursor_idx"]
        if c_idx == 0:
            if button == BUTTON_RIGHT: state["category_idx"] = (state["category_idx"] + 1) % len(_CONVERSIONS)
            else: state["category_idx"] = (state["category_idx"] - 1) % len(_CONVERSIONS)
            clamp_unit_indices(); dirty_ui = True
        elif c_idx == 1:
            max_u = len(_CONVERSIONS[state["category_idx"]][1])
            if button == BUTTON_RIGHT: state["from_idx"] = (state["from_idx"] + 1) % max_u
            else: state["from_idx"] = (state["from_idx"] - 1) % max_u
            dirty_ui = True
        elif c_idx == 2:
            max_u = len(_CONVERSIONS[state["category_idx"]][1])
            if button == BUTTON_RIGHT: state["to_idx"] = (state["to_idx"] + 1) % max_u
            else: state["to_idx"] = (state["to_idx"] - 1) % max_u
            dirty_ui = True
            
    elif button == BUTTON_CENTER:
        c_idx = state["cursor_idx"]
        if c_idx == 0: state["category_idx"] = (state["category_idx"] + 1) % len(_CONVERSIONS); clamp_unit_indices()
        elif c_idx == 1: state["from_idx"] = (state["from_idx"] + 1) % len(_CONVERSIONS[state["category_idx"]][1])
        elif c_idx == 2: state["to_idx"] = (state["to_idx"] + 1) % len(_CONVERSIONS[state["category_idx"]][1])
        elif c_idx == 3: current_mode = MODE_TYPING; state["input_val"] = "0"; blink_counter = 0; cursor_visible = True
        elif c_idx == 4: current_mode = MODE_HELP
        elif c_idx == 5: current_mode = MODE_OPTIONS
        dirty_ui = True

INPUT_DISPATCH = {
    MODE_MAIN: handle_input_main,
    MODE_OPTIONS: handle_input_options,
    MODE_HELP: handle_input_help,
    MODE_TYPING: handle_input_typing
}

def draw_options(view_manager, draw, screen_w, screen_h, theme_color, bg_color):
    draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), TFT_DARKGREY)
    draw.fill_rectangle(Vector(0, 0), Vector(screen_w, 30), theme_color)
    draw.text(Vector(10, 10), "OPTIONS MENU", TFT_WHITE)

    o_idx = state["options_cursor_idx"]
    opt_r_height = 24

    if o_idx == 0: draw.fill_rectangle(Vector(0, 46), Vector(screen_w, opt_r_height), TFT_BLACK)
    c0 = theme_color if o_idx == 0 else TFT_LIGHTGREY
    draw.text(Vector(15, 50), "Theme Color:", c0)
    draw.text(Vector(140, 50), f"< {_THEMES[state['theme_idx']][0]} >", c0)
    
    if o_idx == 1: draw.fill_rectangle(Vector(0, 76), Vector(screen_w, opt_r_height), TFT_BLACK)
    c1 = theme_color if o_idx == 1 else TFT_LIGHTGREY
    draw.text(Vector(15, 80), "Back R (0-255):", c1)
    draw.text(Vector(140, 80), f"< {state['bg_r']} >", c1)
    
    if o_idx == 2: draw.fill_rectangle(Vector(0, 106), Vector(screen_w, opt_r_height), TFT_BLACK)
    c2 = theme_color if o_idx == 2 else TFT_LIGHTGREY
    draw.text(Vector(15, 110), "Back G (0-255):", c2)
    draw.text(Vector(140, 110), f"< {state['bg_g']} >", c2)
    
    if o_idx == 3: draw.fill_rectangle(Vector(0, 136), Vector(screen_w, opt_r_height), TFT_BLACK)
    c3 = theme_color if o_idx == 3 else TFT_LIGHTGREY
    draw.text(Vector(15, 140), "Back B (0-255):", c3)
    draw.text(Vector(140, 140), f"< {state['bg_b']} >", c3)
    
    draw.text(Vector(15, 180), "Background Preview:", TFT_LIGHTGREY)
    draw.rect(Vector(15, 200), Vector(screen_w - 30, 40), theme_color)
    draw.fill_rectangle(Vector(16, 201), Vector(screen_w - 32, 38), bg_color)

    draw.text(Vector(5, screen_h - 20), "[L/R] Edit  [ENT] Close", TFT_WHITE)

def draw_help(view_manager, draw, screen_w, screen_h, theme_color, bg_color):
    global help_scroll
    lines = get_help_lines()
    max_scroll = max(0, len(lines) - 12)
    help_scroll = min(help_scroll, max_scroll)
    
    for i in range(12):
        if help_scroll + i < len(lines):
            draw.text(Vector(10, 10 + i * 20), lines[help_scroll + i], TFT_WHITE)
            
    draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 40), bg_color)
    draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color)
    draw.text(Vector(5, screen_h - 32), "[UP/DN] Scroll  [ESC/H] Close", theme_color)

def draw_main(view_manager, draw, screen_w, screen_h, theme_color, bg_color):
    cat = _CONVERSIONS[state["category_idx"]]
    c_idx = state["cursor_idx"]
    f_name = cat[1][state["from_idx"]][0]
    t_name = cat[1][state["to_idx"]][0]
    
    cat_text = f"MODE: {cat[0].upper()}"
    draw.text(Vector(10, 10), cat_text, theme_color if c_idx == 0 else TFT_WHITE)
    if c_idx == 0: draw.text(Vector(screen_w - 20, 10), "<", theme_color)
    draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color)
    
    out_y = 45
    draw.text(Vector(15, out_y + 5), f"RESULT ({t_name}):", TFT_LIGHTGREY)
    draw.fill_rectangle(Vector(15, out_y + 25), Vector(screen_w - 30, 35), TFT_DARKGREY)
    draw.rect(Vector(15, out_y + 25), Vector(screen_w - 30, 35), theme_color)
    draw.text(Vector(25, out_y + 33), f"{conv_result}", theme_color, 2)

    in_y = 120; r_height = 24
    
    if c_idx == 1: draw.fill_rectangle(Vector(0, in_y - 4), Vector(screen_w, r_height), TFT_DARKGREY)
    draw.text(Vector(15, in_y + 1), "From Unit:", theme_color if c_idx == 1 else TFT_LIGHTGREY)
    draw.rect(Vector(110, in_y - 4), Vector(110, r_height), theme_color if c_idx == 1 else TFT_DARKGREY)
    draw.text(Vector(120, in_y + 1), f"{f_name}", theme_color if c_idx == 1 else TFT_WHITE)
    if c_idx == 1: draw.text(Vector(screen_w - 20, in_y + 1), "<", theme_color)
    
    r2_y = in_y + 28
    if c_idx == 2: draw.fill_rectangle(Vector(0, r2_y - 4), Vector(screen_w, r_height), TFT_DARKGREY)
    draw.text(Vector(15, r2_y + 1), "To Unit:", theme_color if c_idx == 2 else TFT_LIGHTGREY)
    draw.rect(Vector(110, r2_y - 4), Vector(110, r_height), theme_color if c_idx == 2 else TFT_DARKGREY)
    draw.text(Vector(120, r2_y + 1), f"{t_name}", theme_color if c_idx == 2 else TFT_WHITE)
    if c_idx == 2: draw.text(Vector(screen_w - 20, r2_y + 1), "<", theme_color)
    
    r3_y = in_y + 56
    if c_idx == 3: draw.fill_rectangle(Vector(0, r3_y - 4), Vector(screen_w, r_height), TFT_DARKGREY)
    draw.text(Vector(15, r3_y + 1), "Value:", theme_color if c_idx == 3 else TFT_LIGHTGREY)
    draw.rect(Vector(110, r3_y - 4), Vector(110, r_height), theme_color if c_idx == 3 else TFT_DARKGREY)
    val_cursor = "_" if (current_mode == MODE_TYPING and cursor_visible) else ""
    draw.text(Vector(120, r3_y + 1), f"{state['input_val']}{val_cursor}", theme_color if c_idx == 3 else TFT_WHITE)
    if c_idx == 3: draw.text(Vector(screen_w - 20, r3_y + 1), "<", theme_color)

    r4_y = in_y + 84
    if c_idx == 4: draw.fill_rectangle(Vector(0, r4_y - 4), Vector(screen_w, r_height), TFT_DARKGREY)
    draw.text(Vector(15, r4_y + 1), "View Help / Manual", theme_color if c_idx == 4 else TFT_LIGHTGREY)
    if c_idx == 4: draw.text(Vector(screen_w - 20, r4_y + 1), "<", theme_color)
    
    r5_y = in_y + 112
    if c_idx == 5: draw.fill_rectangle(Vector(0, r5_y - 4), Vector(screen_w, r_height), TFT_DARKGREY)
    draw.text(Vector(15, r5_y + 1), "Options", theme_color if c_idx == 5 else TFT_LIGHTGREY)
    if c_idx == 5: draw.text(Vector(screen_w - 20, r5_y + 1), "<", theme_color)

    draw.fill_rectangle(Vector(0, screen_h - 55), Vector(screen_w, 2), theme_color)
    draw.text(Vector(5, screen_h - 47), "[C]Cat [F]From [T]To [V]Val", theme_color)
    
    if cat[0] in ("Temp", "Angle", "Torque"): footer_row_2 = "[H]Help [O]Opt [M]+/- [ESC]Exit"
    else: footer_row_2 = "[H]Help [O]Opt [ESC]Exit"
        
    draw.text(Vector(5, screen_h - 32), footer_row_2, theme_color)
    draw.text(Vector(5, screen_h - 15), "[UP/DN]Nav [ENT]Select", TFT_LIGHTGREY)

VIEW_DISPATCH = {
    MODE_MAIN: draw_main,
    MODE_OPTIONS: draw_options,
    MODE_HELP: draw_help,
    MODE_TYPING: draw_main
}

def start(view_manager):
    global conv_result, storage, dirty_ui, current_mode
    current_mode = MODE_MAIN
    storage = view_manager.storage
    validate_hardware_and_time(view_manager)
    validate_and_load_settings()
    clamp_unit_indices()
    conv_result = calculate_conversion()
    dirty_ui = True
    return True

def run(view_manager):
    global conv_result, current_mode, dirty_ui, blink_counter, cursor_visible, pending_save, save_timer
    
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
        conv_result = calculate_conversion()

    if dirty_ui:
        bg_color = rgb_to_565(state["bg_r"], state["bg_g"], state["bg_b"])
        theme_color = _THEMES[state["theme_idx"]][1]

        if current_mode != MODE_OPTIONS:
            draw.clear()
            draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), bg_color)
        
        handler = VIEW_DISPATCH.get(current_mode)
        if handler: handler(view_manager, draw, screen_w, screen_h, theme_color, bg_color)
        
        draw.swap(); dirty_ui = False

def stop(view_manager):
    global state, _CONVERSIONS, _THEMES, _last_saved_json, _cached_help_lines
    global INPUT_DISPATCH, VIEW_DISPATCH
    global conv_result, storage, current_mode
    global dirty_ui, blink_counter, cursor_visible, pending_save, save_timer, help_scroll
    
    save_settings()
    
    if state is not None: state.clear()
    state = None
    
    _CONVERSIONS = None
    _THEMES = None
    INPUT_DISPATCH = None
    VIEW_DISPATCH = None
    _last_saved_json = ""
    _cached_help_lines = []
    
    conv_result = "0.0"
    storage = None
    current_mode = MODE_MAIN
    
    dirty_ui = pending_save = False
    blink_counter = save_timer = help_scroll = 0
    cursor_visible = True
    
    import gc
    gc.collect()
