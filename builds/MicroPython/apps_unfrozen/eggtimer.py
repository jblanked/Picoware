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
    BUTTON_BACK, BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT,
    BUTTON_CENTER, BUTTON_BACKSPACE, BUTTON_H, BUTTON_ESCAPE, BUTTON_O
)

from picoware.system.wifi import (
    WIFI_STATE_CONNECTED, WIFI_STATE_CONNECTING,
    WIFI_STATE_ISSUE, WIFI_STATE_TIMEOUT
)

try:
    from picoware.system.buttons import BUTTON_A, BUTTON_Z, BUTTON_0, BUTTON_9, BUTTON_SPACE, BUTTON_N, BUTTON_T, BUTTON_S, BUTTON_C, BUTTON_M, BUTTON_R, BUTTON_D
except ImportError:
    BUTTON_A = BUTTON_Z = BUTTON_0 = BUTTON_9 = BUTTON_SPACE = BUTTON_N = BUTTON_T = BUTTON_S = BUTTON_C = BUTTON_M = BUTTON_R = BUTTON_D = -99

try:
    from machine import Pin, PWM
    buzzer_l = PWM(Pin(28))
    buzzer_r = PWM(Pin(27))
    buzzer_l.duty_u16(0)
    buzzer_r.duty_u16(0)
    buzzer = (buzzer_l, buzzer_r)
except Exception:
    buzzer = None

def track_ram(func):
    def wrapper(*args, **kwargs):
        import gc
        gc.collect()  # Clean up before starting
        start_mem = gc.mem_alloc()
        
        result = func(*args, **kwargs)  # Run your actual function
        
        end_mem = gc.mem_alloc()
        diff = end_mem - start_mem
        print(f"[RAM TRACKER] {func.__name__} added: {diff} bytes")
        
        return result
    return wrapper

show_options = False
help_scroll = 0
_last_saved_json = ""

_SETTINGS_FILE = "/picoware/settings/eggtimer_settings.json"

_THEMES = (
    ("Green", TFT_GREEN),
    ("Red", TFT_RED),
    ("Blue", TFT_BLUE),
    ("Yellow", TFT_YELLOW),
    ("Orange", TFT_ORANGE)
)

_EGG_PRESETS = (
    (0, "Off / Deactivate"),
    (4, "Soft (4m)"),
    (6, "Medium (6m)"),
    (8, "Hard (8m)"),
    (10, "Hard+ (10m)")
)

_VERSION = "0.12"

_cached_help_lines = []

def get_help_lines():
    global board_name, _cached_help_lines
    import gc
    
    # Sweep temporary garbage to get an accurate live baseline
    gc.collect() 
    ram_str = f"RAM: {gc.mem_alloc() // 1024}KB / {gc.mem_free() // 1024}KB"
    
    # If the cache exists, just surgically update the RAM line (Index 5)
    if _cached_help_lines:
        _cached_help_lines[5] = ram_str
        return _cached_help_lines
        
    b_name = board_name[:18]
    hw_fw = os.uname().release if hasattr(os, "uname") else "Unknown FW"
        
    _cached_help_lines = [
        f"EGGTIMER v{_VERSION}",
        "--------------------",
        "DEBUG INFO:",
        f"Board: {b_name}",
        f"FW: {hw_fw}",
        ram_str, # <--- Live RAM sits at Index 5
        "",
        "CREDITS:",
        "made by Slasher006",
        "with the help of jBlanked and Gemini",
        "Date: 2026-02-28",
        "",
        "SHORTCUTS:",
        "[L/R] Tgl ON/OFF",
        "[T] Tgl Audio",
        "[C] Clear Past",
        "[BS] Delete Alarm",
        "[H] Help Overlay",
        "[O] Options Menu",
        "[N] New Alarm",
        "[M] Alarm List",
        "[R] Reset Timers",
        "[D] Diagnostics",
        "[ESC] Exit App",
        "",
        "CONTROLS:",
        "[UP/DN] Navigate",
        "[ENTER] Select/Save"
    ]
    return _cached_help_lines

# --- VIEW MODE CONSTANTS ---
MODE_MAIN = 0
MODE_ALARMS = 1
MODE_EGG = 2
MODE_STOPWATCH = 3
MODE_COUNTDOWN = 4
MODE_OPTIONS = 5
MODE_HELP = 6
MODE_DIAGNOSTIC = 7
MODE_RING = 8
MODE_EDIT_TYPE = 10
MODE_EDIT_DATE = 11
MODE_EDIT_H = 12
MODE_EDIT_M = 13
MODE_EDIT_L = 14
MODE_EDIT_AUD = 15
MODE_CONFIRM_DEL = 20
MODE_CONFIRM_CLR = 21
MODE_ERR_TIME = 22
MODE_ERR_DATE = 23

# --- PERSISTENT SETTINGS ---
settings = {
    "theme_idx": 0, "bg_r": 0, "bg_g": 0, "bg_b": 0,
    "use_12h": False, "snooze_min": 5, "show_diagnostics": False, "alarms": []
}

# --- VOLATILE UI GLOBALS ---
current_mode = MODE_MAIN
origin_mode = MODE_MAIN
msg_origin = MODE_MAIN

dirty_ui = True
dirty_save = False
save_timer = 0

cursor_idx = 0
options_cursor_idx = 0
date_cursor = 0

sw_run = False
sw_start = 0
sw_accum = 0
last_sw_ms = 0

egg_preset = 1
egg_end = 0
cd_end = 0
snooze_epoch = 0

# Initialize the countdown timer hours variable to zero
cd_h = 0
# Initialize the countdown timer minutes variable to zero
cd_m = 0
# Initialize the countdown timer seconds variable to zero
cd_s = 0
# Initialize the countdown cursor position to the first slot (hours)
cd_cursor = 0

last_s = -1
last_trig_m = -1
ringing_idx = -1
ring_flash = False
snooze_idx = -1
snooze_count = 0

has_hardware = True
board_name = "Unknown"

# Editor Temporary State
edit_idx = -1
tmp_daily = False
tmp_y = 2026; tmp_mo = 1; tmp_d = 1
tmp_h = 12; tmp_m = 0
tmp_label = ""
tmp_audible = True
del_confirm_yes = False
clear_confirm_yes = False

# Core system references
storage = None
show_help = False
show_options = False
sys_time = time # Create a global fallback mapping to the standard time module


def profile_ram(func_name, target_function, *args, **kwargs):
    # Force a deep cleanup to get a completely flat baseline
    gc.collect()
    
    # Record the exact number of bytes currently allocated in the heap
    start_mem = gc.mem_alloc()
    
    # Execute the target view function
    target_function(*args, **kwargs)
    
    # Record the exact number of bytes allocated after the function finishes
    end_mem = gc.mem_alloc()
    
    # Calculate the total bytes added to RAM by this function
    diff = end_mem - start_mem
    
    # Print the result to the Thonny console
    print(f"[RAM LOG] View '{func_name}' consumed: {diff} bytes")


def rgb_to_565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

def queue_save():
    global dirty_save, save_timer
    dirty_save = True
    save_timer = 60

@track_ram
def save_settings():
    global settings, storage, dirty_save
    if not storage or not dirty_save: return
    try:
        json_str = json.dumps(settings)
        storage.write(_SETTINGS_FILE, json_str, "w")
        dirty_save = False
        del json_str
        import gc
        gc.collect()
    except Exception: pass

@track_ram
def validate_and_load_settings():
    global settings, storage
    if storage and storage.exists(_SETTINGS_FILE):
        try:
            raw_data = storage.read(_SETTINGS_FILE, "r")
            loaded = json.loads(raw_data)
            for key in settings:
                if key in loaded: settings[key] = loaded[key]
            
            t = sys_time.localtime()
            for i in range(len(settings["alarms"])):
                a = settings["alarms"][i]
                if len(a) == 3: settings["alarms"][i] = [t[0], t[1], t[2], a[0], a[1], a[2], "ALARM", True, False]
                elif len(a) == 4: settings["alarms"][i] = [t[0], t[1], t[2], a[0], a[1], a[2], a[3], True, False]
                elif len(a) == 7: settings["alarms"][i] = [a[0], a[1], a[2], a[3], a[4], a[5], a[6], True, False]
                elif len(a) == 8: settings["alarms"][i] = [a[0], a[1], a[2], a[3], a[4], a[5], a[6], a[7], False]
                
        except Exception: pass

def handle_audio_silence():
    if buzzer:
        try:
            for b in buzzer: b.duty_u16(0)
        except Exception: pass

def validate_hardware_and_time(view_manager):
    global board_name, has_hardware
    sys_inst = System()
    
    # Try SDK board name, fallback to standard MicroPython if the SDK crashes
    try:
        b_name = sys_inst.board_name
        if callable(b_name): b_name = b_name()
    except Exception:
        b_name = os.uname().machine if hasattr(os, "uname") else "Unknown Board"
        
    board_name = str(b_name)
    
    # Try SDK has_wifi, fallback to False if the SDK crashes
    try:
        hw = sys_inst.has_wifi
        if callable(hw): hw = hw()
    except Exception:
        hw = False
        
    has_hardware = bool(hw)

def check_time_and_alarms(t, c_sec):
    global current_mode, sw_run, last_sw_ms, dirty_ui, last_s, egg_end
    global ringing_idx, cd_end, snooze_epoch, snooze_idx, last_trig_m
    global snooze_count, ring_flash, settings
    
    cy, cmo, cd, ch, cm, cs = t[0], t[1], t[2], t[3], t[4], t[5]
    
    if current_mode == MODE_STOPWATCH and sw_run:
        now_ms = time.ticks_ms()
        if time.ticks_diff(now_ms, last_sw_ms) > 100:
            last_sw_ms = now_ms
            dirty_ui = True
            
    if cs != last_s:
        last_s = cs
        dirty_ui = True
        if current_mode != MODE_RING:
            if egg_end > 0 and c_sec >= egg_end:
                current_mode = MODE_RING
                ringing_idx = -2
                egg_end = 0
            elif cd_end > 0 and c_sec >= cd_end:
                current_mode = MODE_RING
                ringing_idx = -3
                cd_end = 0
            elif snooze_epoch > 0 and c_sec >= snooze_epoch:
                current_mode = MODE_RING
                ringing_idx = snooze_idx
                snooze_epoch = 0
                last_trig_m = cm
            elif cs == 0 and last_trig_m != cm:
                for i in range(len(settings["alarms"])):
                    a = settings["alarms"][i]
                    if a[5] and a[3] == ch and a[4] == cm and (a[8] or (a[0] == cy and a[1] == cmo and a[2] == cd)):
                        current_mode = MODE_RING
                        ringing_idx = i
                        snooze_count = 0
                        last_trig_m = cm
                        break

    if current_mode == MODE_RING and dirty_ui:
        ring_flash = not ring_flash
        is_audible = True if ringing_idx in (-2, -3) else settings["alarms"][ringing_idx][7]
        if buzzer and is_audible:
            try:
                for b in buzzer:
                    b.freq(1000) if ring_flash else None
                    b.duty_u16(32768 if ring_flash else 0)
            except Exception: pass

def handle_input_diagnostic(button, input_mgr, view_manager, t, c_sec):
    global current_mode, dirty_ui
    if button in (BUTTON_BACK, BUTTON_ESCAPE):
        dirty_ui = False
        view_manager.back()
        return
    elif button == BUTTON_CENTER:
        current_mode = MODE_MAIN
        dirty_ui = True

def handle_input_modals(button, input_mgr, view_manager, t, c_sec):
    global current_mode, dirty_ui, msg_origin, del_confirm_yes, clear_confirm_yes, settings, cursor_idx, snooze_idx, snooze_epoch, snooze_count, sys_time
    if current_mode in (MODE_ERR_TIME, MODE_ERR_DATE):
        if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP, BUTTON_DOWN):
            current_mode = msg_origin; dirty_ui = True
    elif current_mode == MODE_CONFIRM_DEL:
        if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = MODE_ALARMS; dirty_ui = True
        elif button in (BUTTON_LEFT, BUTTON_RIGHT): del_confirm_yes = not del_confirm_yes; dirty_ui = True
        elif button == BUTTON_CENTER:
            if del_confirm_yes:
                if snooze_idx == cursor_idx: snooze_epoch = snooze_count = 0
                elif snooze_idx > cursor_idx: snooze_idx -= 1
                settings["alarms"].pop(cursor_idx); cursor_idx = max(0, cursor_idx - 1); queue_save()
            current_mode = MODE_ALARMS; dirty_ui = True
    elif current_mode == MODE_CONFIRM_CLR:
        if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = MODE_ALARMS; dirty_ui = True
        elif button in (BUTTON_LEFT, BUTTON_RIGHT): clear_confirm_yes = not clear_confirm_yes; dirty_ui = True
        elif button == BUTTON_CENTER:
            if clear_confirm_yes:
                for i in range(len(settings["alarms"]) - 1, -1, -1):
                    a = settings["alarms"][i]
                    if not a[8] and sys_time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) < c_sec:
                        if snooze_idx == i: snooze_epoch = snooze_count = 0
                        elif snooze_idx > i: snooze_idx -= 1
                        settings["alarms"].pop(i)
                cursor_idx = 0; queue_save()
            current_mode = MODE_ALARMS; dirty_ui = True

def handle_input_ring(button, input_mgr, view_manager, t, c_sec):
    global current_mode, dirty_ui, ringing_idx, snooze_count, snooze_epoch, snooze_idx, settings
    if ringing_idx in (-2, -3):
        if button in (BUTTON_CENTER, BUTTON_O, BUTTON_BACK, BUTTON_ESCAPE):
            current_mode = MODE_EGG if ringing_idx == -2 else MODE_COUNTDOWN; ringing_idx = -1; dirty_ui = True; handle_audio_silence()
    else:
        if button in (BUTTON_S, BUTTON_CENTER):
            if snooze_count < 5:
                snooze_epoch = c_sec + (settings["snooze_min"] * 60); snooze_idx = ringing_idx; snooze_count += 1; queue_save()
            else:
                if 0 <= ringing_idx < len(settings["alarms"]) and not settings["alarms"][ringing_idx][8]: settings["alarms"][ringing_idx][5] = False; queue_save()
                snooze_epoch = snooze_count = 0
            current_mode = MODE_MAIN; ringing_idx = -1; dirty_ui = True; handle_audio_silence()
        elif button in (BUTTON_O, BUTTON_BACK, BUTTON_ESCAPE):
            current_mode = MODE_MAIN
            if 0 <= ringing_idx < len(settings["alarms"]) and not settings["alarms"][ringing_idx][8]: settings["alarms"][ringing_idx][5] = False; queue_save()
            ringing_idx = -1; snooze_epoch = snooze_count = 0; dirty_ui = True; handle_audio_silence()

def handle_input_main(button, input_mgr, view_manager, t, c_sec):
    global current_mode, dirty_ui, show_help, show_options, cursor_idx, origin_mode, edit_idx, tmp_daily, tmp_y, tmp_mo, tmp_d, date_cursor, tmp_h, tmp_m, tmp_label, tmp_audible, settings
    cy, cmo, cd, ch, cm = t[0], t[1], t[2], t[3], t[4]
    if button in (BUTTON_BACK, BUTTON_ESCAPE):
        dirty_ui = False; view_manager.back(); return
    elif button == BUTTON_H: show_help = True; dirty_ui = True
    elif button == BUTTON_O: show_options = True; dirty_ui = True
    elif button == BUTTON_D and settings.get("show_diagnostics", False): current_mode = MODE_DIAGNOSTIC; dirty_ui = True
    elif button == BUTTON_M: current_mode = MODE_ALARMS; cursor_idx = 0; dirty_ui = True
    elif button == BUTTON_N: 
        current_mode = MODE_EDIT_TYPE; origin_mode = MODE_MAIN; edit_idx = -1; tmp_daily = False; tmp_y = cy; tmp_mo = cmo; tmp_d = cd; date_cursor = 0; tmp_h = ch; tmp_m = cm; tmp_label = ""; tmp_audible = True; dirty_ui = True
    elif button == BUTTON_DOWN: cursor_idx = (cursor_idx + 1) % 6; dirty_ui = True
    elif button == BUTTON_UP: cursor_idx = (cursor_idx - 1) % 6; dirty_ui = True
    elif button == BUTTON_CENTER:
        if cursor_idx == 0: current_mode = MODE_ALARMS; cursor_idx = 0
        elif cursor_idx == 1: current_mode = MODE_EGG
        elif cursor_idx == 2: current_mode = MODE_STOPWATCH
        elif cursor_idx == 3: current_mode = MODE_COUNTDOWN
        elif cursor_idx == 4: show_options = True
        elif cursor_idx == 5: show_help = True
        dirty_ui = True

def handle_input_egg_timer(button, input_mgr, view_manager, t, c_sec):
    global current_mode, dirty_ui, egg_preset, egg_end
    if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = MODE_MAIN; dirty_ui = True
    elif button == BUTTON_DOWN: egg_preset = (egg_preset + 1) % len(_EGG_PRESETS); dirty_ui = True
    elif button == BUTTON_UP: egg_preset = (egg_preset - 1) % len(_EGG_PRESETS); dirty_ui = True
    elif button == BUTTON_CENTER:
        m = _EGG_PRESETS[egg_preset][0]
        if m == 0: egg_end = 0
        else: egg_end = c_sec + (m * 60)
        queue_save(); dirty_ui = True

def handle_input_stopwatch(button, input_mgr, view_manager, t, c_sec):
    global current_mode, dirty_ui, sw_run, sw_accum, sw_start
    if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = MODE_MAIN; dirty_ui = True
    elif button == BUTTON_CENTER:
        if sw_run: sw_accum += time.ticks_diff(time.ticks_ms(), sw_start); sw_run = False
        else: sw_start = time.ticks_ms(); sw_run = True
        dirty_ui = True
    elif button == BUTTON_R: sw_accum = 0; sw_run = False; dirty_ui = True

def handle_input_countdown(button, input_mgr, view_manager, t, c_sec):
    global current_mode, dirty_ui, cd_end, cd_cursor, cd_h, cd_m, cd_s
    if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = MODE_MAIN; dirty_ui = True
    elif cd_end == 0:
        if button == BUTTON_LEFT: cd_cursor = (cd_cursor - 1) % 3; dirty_ui = True
        elif button == BUTTON_RIGHT: cd_cursor = (cd_cursor + 1) % 3; dirty_ui = True
        elif button == BUTTON_UP:
            if cd_cursor == 0: cd_h = (cd_h + 1) % 100
            elif cd_cursor == 1: cd_m = (cd_m + 1) % 60
            elif cd_cursor == 2: cd_s = (cd_s + 1) % 60
            dirty_ui = True; queue_save()
        elif button == BUTTON_DOWN:
            if cd_cursor == 0: cd_h = (cd_h - 1) % 100
            elif cd_cursor == 1: cd_m = (cd_m - 1) % 60
            elif cd_cursor == 2: cd_s = (cd_s - 1) % 60
            dirty_ui = True; queue_save()
        elif button == BUTTON_CENTER:
            total_s = cd_h * 3600 + cd_m * 60 + cd_s
            if total_s > 0: cd_end = c_sec + total_s; dirty_ui = True
        elif button == BUTTON_R: cd_h = cd_m = cd_s = 0; dirty_ui = True; queue_save()
    else:
        if button in (BUTTON_CENTER, BUTTON_R): cd_end = 0; dirty_ui = True

def handle_input_alarms(button, input_mgr, view_manager, t, c_sec):
    global current_mode, dirty_ui, cursor_idx, settings, sys_time, msg_origin, clear_confirm_yes, del_confirm_yes, origin_mode, edit_idx, tmp_daily, tmp_y, tmp_mo, tmp_d, date_cursor, tmp_h, tmp_m, tmp_label, tmp_audible, snooze_idx, snooze_epoch, snooze_count
    cy, cmo, cd, ch, cm = t[0], t[1], t[2], t[3], t[4]
    list_len = len(settings["alarms"]) + 1
    if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = MODE_MAIN; cursor_idx = 0; dirty_ui = True
    elif button == BUTTON_DOWN and cursor_idx < list_len - 1: cursor_idx += 1; dirty_ui = True
    elif button == BUTTON_UP and cursor_idx > 0: cursor_idx -= 1; dirty_ui = True
    elif button in (BUTTON_LEFT, BUTTON_RIGHT) and cursor_idx < len(settings["alarms"]):
        a = settings["alarms"][cursor_idx]
        if not a[5]:
            if not a[8] and sys_time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) <= c_sec: current_mode = MODE_ERR_TIME; msg_origin = MODE_ALARMS; dirty_ui = True
            else: a[5] = True; queue_save(); dirty_ui = True
        else:
            a[5] = False
            if snooze_idx == cursor_idx: snooze_epoch = snooze_count = 0
            queue_save(); dirty_ui = True
    elif button == BUTTON_T and cursor_idx < len(settings["alarms"]): settings["alarms"][cursor_idx][7] = not settings["alarms"][cursor_idx][7]; queue_save(); dirty_ui = True
    elif button == BUTTON_C:
        has_past = any(not a[8] and sys_time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) < c_sec for a in settings["alarms"])
        if has_past: current_mode = MODE_CONFIRM_CLR; clear_confirm_yes = False; dirty_ui = True
    elif button == BUTTON_BACKSPACE and cursor_idx < len(settings["alarms"]): current_mode = MODE_CONFIRM_DEL; del_confirm_yes = False; dirty_ui = True
    elif button == BUTTON_CENTER:
        current_mode = MODE_EDIT_TYPE; origin_mode = MODE_ALARMS; date_cursor = 0; dirty_ui = True
        if cursor_idx == len(settings["alarms"]):
            edit_idx = -1; tmp_daily = False; tmp_y = cy; tmp_mo = cmo; tmp_d = cd; tmp_h = ch; tmp_m = cm; tmp_label = ""; tmp_audible = True
        else:
            a = settings["alarms"][cursor_idx]; edit_idx = cursor_idx
            tmp_y = a[0]; tmp_mo = a[1]; tmp_d = a[2]; tmp_h = a[3]; tmp_m = a[4]; tmp_label = a[6]; tmp_audible = a[7]; tmp_daily = a[8]

def handle_input_editor(button, input_mgr, view_manager, t, c_sec):
    global current_mode, dirty_ui, settings, origin_mode, msg_origin, tmp_daily, tmp_y, tmp_mo, tmp_d, date_cursor, tmp_h, tmp_m, tmp_label, tmp_audible, edit_idx, cursor_idx, sys_time
    cy, cmo, cd, ch, cm = t[0], t[1], t[2], t[3], t[4]
    if current_mode == MODE_EDIT_TYPE:
        if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = origin_mode; dirty_ui = True
        elif button in (BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP, BUTTON_DOWN): tmp_daily = not tmp_daily; dirty_ui = True
        elif button == BUTTON_CENTER: current_mode = MODE_EDIT_H if tmp_daily else MODE_EDIT_DATE; dirty_ui = True
    elif current_mode == MODE_EDIT_DATE:
        if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = MODE_EDIT_TYPE; dirty_ui = True
        elif button == BUTTON_LEFT: date_cursor = (date_cursor - 1) % 3; dirty_ui = True
        elif button == BUTTON_RIGHT: date_cursor = (date_cursor + 1) % 3; dirty_ui = True
        elif button == BUTTON_UP:
            if date_cursor == 0: tmp_y += 1 if settings["use_12h"] else 0; tmp_d = tmp_d + 1 if tmp_d < 31 and not settings["use_12h"] else (1 if not settings["use_12h"] else tmp_d)
            elif date_cursor == 1: tmp_mo = tmp_mo + 1 if tmp_mo < 12 else 1
            elif date_cursor == 2: tmp_d = tmp_d + 1 if tmp_d < 31 and settings["use_12h"] else (1 if settings["use_12h"] else tmp_d); tmp_y += 1 if not settings["use_12h"] else 0
            dirty_ui = True
        elif button == BUTTON_DOWN:
            if date_cursor == 0: tmp_y = max(2024, tmp_y - 1) if settings["use_12h"] else tmp_y; tmp_d = tmp_d - 1 if tmp_d > 1 and not settings["use_12h"] else (31 if not settings["use_12h"] else tmp_d)
            elif date_cursor == 1: tmp_mo = tmp_mo - 1 if tmp_mo > 1 else 12
            elif date_cursor == 2: tmp_d = tmp_d - 1 if tmp_d > 1 and settings["use_12h"] else (31 if settings["use_12h"] else tmp_d); tmp_y = max(2024, tmp_y - 1) if not settings["use_12h"] else tmp_y
            dirty_ui = True
        elif button == BUTTON_CENTER:
            leap = 1 if (tmp_y % 4 == 0 and (tmp_y % 100 != 0 or tmp_y % 400 == 0)) else 0
            dim = [31, 28 + leap, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][tmp_mo - 1]
            if tmp_d > dim: current_mode = MODE_ERR_DATE; msg_origin = MODE_EDIT_DATE; dirty_ui = True; return
            if tmp_y < cy or (tmp_y == cy and tmp_mo < cmo) or (tmp_y == cy and tmp_mo == cmo and tmp_d < cd): current_mode = MODE_ERR_TIME; msg_origin = MODE_EDIT_DATE; dirty_ui = True; return
            current_mode = MODE_EDIT_H; dirty_ui = True
    elif current_mode == MODE_EDIT_H:
        if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = MODE_EDIT_TYPE if tmp_daily else MODE_EDIT_DATE; dirty_ui = True
        elif button == BUTTON_DOWN: tmp_h = (tmp_h - 1) % 24; dirty_ui = True
        elif button == BUTTON_UP: tmp_h = (tmp_h + 1) % 24; dirty_ui = True
        elif button == BUTTON_CENTER:
            if not tmp_daily and tmp_y == cy and tmp_mo == cmo and tmp_d == cd and tmp_h < ch: current_mode = MODE_ERR_TIME; msg_origin = MODE_EDIT_H; dirty_ui = True; return
            current_mode = MODE_EDIT_M; dirty_ui = True
    elif current_mode == MODE_EDIT_M:
        if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = MODE_EDIT_H; dirty_ui = True
        elif button == BUTTON_DOWN: tmp_m = (tmp_m - 1) % 60; dirty_ui = True
        elif button == BUTTON_UP: tmp_m = (tmp_m + 1) % 60; dirty_ui = True
        elif button == BUTTON_CENTER:
            if not tmp_daily and tmp_y == cy and tmp_mo == cmo and tmp_d == cd and tmp_h == ch and tmp_m <= cm: current_mode = MODE_ERR_TIME; msg_origin = MODE_EDIT_M; dirty_ui = True; return
            current_mode = MODE_EDIT_L; dirty_ui = True
    elif current_mode == MODE_EDIT_L:
        if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = MODE_EDIT_M; dirty_ui = True
        elif button == BUTTON_CENTER: current_mode = MODE_EDIT_AUD; dirty_ui = True
        elif button == BUTTON_BACKSPACE and len(tmp_label) > 0: tmp_label = tmp_label[:-1]; dirty_ui = True
        elif button == BUTTON_SPACE and len(tmp_label) < 50: tmp_label += " "; dirty_ui = True
        elif button >= BUTTON_A and button <= BUTTON_Z and len(tmp_label) < 50: tmp_label += chr(button - BUTTON_A + ord('A')); dirty_ui = True
        elif button >= BUTTON_0 and button <= BUTTON_9 and len(tmp_label) < 50: tmp_label += chr(button - BUTTON_0 + ord('0')); dirty_ui = True
    elif current_mode == MODE_EDIT_AUD:
        if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = MODE_EDIT_L; dirty_ui = True
        elif button in (BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP, BUTTON_DOWN): tmp_audible = not tmp_audible; dirty_ui = True
        elif button == BUTTON_CENTER:
            final_lbl = tmp_label.strip() or "ALARM"
            if not tmp_daily and sys_time.mktime((tmp_y, tmp_mo, tmp_d, tmp_h, tmp_m, 0, 0, 0)) <= c_sec: current_mode = MODE_ERR_TIME; msg_origin = MODE_EDIT_AUD; dirty_ui = True; return
            new_a = [tmp_y, tmp_mo, tmp_d, tmp_h, tmp_m, True, final_lbl, tmp_audible, tmp_daily]
            if edit_idx == -1: settings["alarms"].append(new_a)
            else: settings["alarms"][edit_idx] = new_a
            queue_save(); current_mode = origin_mode; dirty_ui = True
            if origin_mode == MODE_MAIN: cursor_idx = 0

INPUT_DISPATCH = {
    MODE_DIAGNOSTIC: handle_input_diagnostic,
    MODE_MAIN: handle_input_main,
    MODE_EGG: handle_input_egg_timer,
    MODE_STOPWATCH: handle_input_stopwatch,
    MODE_COUNTDOWN: handle_input_countdown,
    MODE_ALARMS: handle_input_alarms,
    MODE_RING: handle_input_ring,
    MODE_EDIT_TYPE: handle_input_editor,
    MODE_EDIT_DATE: handle_input_editor,
    MODE_EDIT_H: handle_input_editor,
    MODE_EDIT_M: handle_input_editor,
    MODE_EDIT_L: handle_input_editor,
    MODE_EDIT_AUD: handle_input_editor,
    MODE_CONFIRM_DEL: handle_input_modals,
    MODE_CONFIRM_CLR: handle_input_modals,
    MODE_ERR_TIME: handle_input_modals,
    MODE_ERR_DATE: handle_input_modals
}

def draw_diagnostic(view_manager, draw, screen_w, screen_h, theme_color, bg_color):
    global board_name, has_hardware, settings
    import gc
    
    draw.text(Vector(10, 10), "SYSTEM DIAGNOSTICS", TFT_WHITE)
    draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), TFT_WHITE)
    
    fw_ver = os.uname().release[:16] if hasattr(os, "uname") else "Unknown"
    b_name = board_name[:16] 
    
    draw.text(Vector(10, 40), f"App Ver : v{_VERSION}", TFT_LIGHTGREY)
    draw.text(Vector(10, 56), f"Firmware: {fw_ver}", TFT_LIGHTGREY)
    
    # Force a garbage sweep and grab the exact, live Python heap numbers
    gc.collect()
    ram_u = gc.mem_alloc() // 1024
    ram_f = gc.mem_free() // 1024
        
    draw.text(Vector(10, 72), f"RAM: {ram_u}KB Used / {ram_f}KB Free", TFT_LIGHTGREY)
    
    hw_col = TFT_GREEN if has_hardware else TFT_RED
    hw_txt = f"HW: OK ({b_name})" if has_hardware else f"HW: MISSING ({b_name})"
    draw.text(Vector(10, 96), hw_txt, hw_col)
    
    draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color)
    draw.text(Vector(5, screen_h - 32), "[ENT] Start", TFT_WHITE)
    draw.text(Vector(5, screen_h - 15), "[ESC/BCK] Exit App", TFT_LIGHTGREY)

def draw_modals(view_manager, draw, screen_w, screen_h, theme_color, bg_color):
    global current_mode, cursor_idx, settings, del_confirm_yes, clear_confirm_yes
    if current_mode in (MODE_ERR_DATE, MODE_ERR_TIME):
        draw.text(Vector(10, 10), "ERROR", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), TFT_RED)
        draw.fill_rectangle(Vector(15, 60), Vector(screen_w - 30, 80), TFT_DARKGREY); draw.rect(Vector(15, 60), Vector(screen_w - 30, 80), TFT_RED)
        if current_mode == MODE_ERR_DATE: draw.text(Vector(25, 75), "INVALID DATE", TFT_RED); draw.text(Vector(25, 100), "This date does not", TFT_WHITE); draw.text(Vector(25, 115), "exist in calendar.", TFT_WHITE)
        elif current_mode == MODE_ERR_TIME: draw.text(Vector(25, 75), "INVALID DATE/TIME", TFT_RED); draw.text(Vector(25, 100), "Alarm must be set", TFT_WHITE); draw.text(Vector(25, 115), "in the future.", TFT_WHITE)
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), TFT_RED); draw.text(Vector(5, screen_h - 32), "[Any Key] Go Back", TFT_RED)
    else:
        draw.text(Vector(10, 10), f"MODE: {'DELETE' if current_mode == MODE_CONFIRM_DEL else 'CLEAR'} ALARM(S)", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color)
        draw.fill_rectangle(Vector(15, 60), Vector(screen_w - 30, 80), TFT_DARKGREY); draw.rect(Vector(15, 60), Vector(screen_w - 30, 80), theme_color)
        draw.text(Vector(25, 70), "Delete this alarm?" if current_mode == MODE_CONFIRM_DEL else "Clear past alarms?", TFT_WHITE)
        if current_mode == MODE_CONFIRM_DEL:
            a = settings["alarms"][cursor_idx]; lbl = a[6][:10]; adh = a[3] % 12 if settings["use_12h"] else a[3]; adh = 12 if settings["use_12h"] and adh == 0 else adh
            aampm = ("AM" if a[3] < 12 else "PM") if settings["use_12h"] else ""; dt_str = "DAILY" if a[8] else (f"{a[1]:02d}/{a[2]:02d}" if settings["use_12h"] else f"{a[2]:02d}.{a[1]:02d}.{a[0]:04d}")
            draw.text(Vector(25, 90), f"{dt_str} {adh:02d}:{a[4]:02d} {aampm} [{lbl}]", theme_color)
        else: draw.text(Vector(25, 90), "This cannot be undone.", TFT_LIGHTGREY)
        is_yes = del_confirm_yes if current_mode == MODE_CONFIRM_DEL else clear_confirm_yes
        draw.fill_rectangle(Vector(30, 115), Vector(60, 20), TFT_BLACK if is_yes else TFT_DARKGREY); draw.text(Vector(45, 118), "YES", theme_color if is_yes else TFT_LIGHTGREY)
        draw.fill_rectangle(Vector(140, 115), Vector(60, 20), TFT_BLACK if not is_yes else TFT_DARKGREY); draw.text(Vector(160, 118), "NO", theme_color if not is_yes else TFT_LIGHTGREY)
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color); draw.text(Vector(5, screen_h - 32), "[L/R] Select [ENT] Confirm", theme_color); draw.text(Vector(5, screen_h - 15), "[ESC] Cancel", TFT_LIGHTGREY)

def draw_ring(view_manager, draw, screen_w, screen_h, theme_color, bg_color):
    global ringing_idx, snooze_count, ring_flash, settings
    if ringing_idx == -2: display_lbl = "EGG READY!"; hint_str = "[ENT/O] Dismiss"
    elif ringing_idx == -3: display_lbl = "TIME'S UP!"; hint_str = "[ENT/O] Dismiss"
    else: display_lbl = settings["alarms"][ringing_idx][6][:15] + "..." if len(settings["alarms"][ringing_idx][6]) > 15 else settings["alarms"][ringing_idx][6]; hint_str = f"[S/ENT]Snooze({5-snooze_count}) [O]Off" if snooze_count < 5 else "[O]Off (Max Snooze)"
    draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), TFT_WHITE if ring_flash else TFT_BLACK)
    draw.text(Vector(30, 60), "ALARM!", TFT_BLACK if ring_flash else theme_color, 3)
    draw.text(Vector(10, 100), display_lbl, TFT_BLACK if ring_flash else theme_color, 2)
    draw.text(Vector(10, 150), hint_str, TFT_BLACK if ring_flash else theme_color)

def draw_egg_timer(view_manager, draw, screen_w, screen_h, theme_color, bg_color):
    global egg_end, egg_preset, sys_time
    draw.text(Vector(10, 10), "MODE: EGG TIMER", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color)
    if egg_end > 0:
        rem = max(0, egg_end - int(sys_time.time())); m, s = divmod(rem, 60)
        draw.text(Vector(15, 40), f"Run: {m:02d}:{s:02d}", TFT_GREEN, 2)
    else: draw.text(Vector(15, 45), "Status: Inactive", TFT_LIGHTGREY)
    draw.text(Vector(15, 70), "Select Preset:", TFT_LIGHTGREY)
    for i, (_, lbl) in enumerate(_EGG_PRESETS):
        c = theme_color if egg_preset == i else TFT_LIGHTGREY
        if egg_preset == i: draw.text(Vector(10, 90 + i*20), ">", theme_color)
        draw.text(Vector(25, 90 + i*20), lbl, c)
    draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color)
    draw.text(Vector(5, screen_h - 32), "[UP/DN] Nav [ENT] Apply", theme_color)

def draw_stopwatch(view_manager, draw, screen_w, screen_h, theme_color, bg_color):
    global sw_accum, sw_run, sw_start
    draw.text(Vector(10, 10), "MODE: STOPWATCH", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color)
    current_ms = sw_accum
    if sw_run: current_ms += time.ticks_diff(time.ticks_ms(), sw_start)
    ms = (current_ms % 1000) // 100; sec = (current_ms // 1000) % 60; mins = (current_ms // 60000) % 60; hrs = (current_ms // 3600000)
    sw_text = f"{hrs:02d}:{mins:02d}:{sec:02d}" if hrs > 0 else f"{mins:02d}:{sec:02d}.{ms:01d}"
    draw.text(Vector((screen_w // 2) - 85, 70), sw_text, theme_color, 4)
    stat_str = "RUNNING" if sw_run else "STOPPED"
    draw.text(Vector((screen_w // 2) - 30, 130), stat_str, TFT_GREEN if sw_run else TFT_LIGHTGREY)
    draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color)
    draw.text(Vector(5, screen_h - 32), "[ENT] Start/Stop [R] Reset", theme_color)

def draw_countdown(view_manager, draw, screen_w, screen_h, theme_color, bg_color):
    global cd_end, cd_cursor, cd_h, cd_m, cd_s, sys_time
    draw.text(Vector(10, 10), "MODE: COUNTDOWN", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color)
    if cd_end > 0:
        rem = max(0, cd_end - int(sys_time.time())); h = rem // 3600; m = (rem % 3600) // 60; s = rem % 60
        draw.text(Vector((screen_w // 2) - 85, 70), f"{h:02d}:{m:02d}:{s:02d}", theme_color, 4)
        draw.text(Vector((screen_w // 2) - 30, 130), "RUNNING", TFT_GREEN)
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color); draw.text(Vector(5, screen_h - 32), "[ENT] Cancel", theme_color)
    else:
        draw.text(Vector(15, 45), "Set Duration:", TFT_LIGHTGREY)
        c0 = theme_color if cd_cursor == 0 else TFT_WHITE; c1 = theme_color if cd_cursor == 1 else TFT_WHITE; c2 = theme_color if cd_cursor == 2 else TFT_WHITE
        st_x = (screen_w // 2) - 85
        draw.text(Vector(st_x, 70), f"{cd_h:02d}", c0, 4); draw.text(Vector(st_x + 50, 70), ":", TFT_LIGHTGREY, 4)
        draw.text(Vector(st_x + 70, 70), f"{cd_m:02d}", c1, 4); draw.text(Vector(st_x + 120, 70), ":", TFT_LIGHTGREY, 4)
        draw.text(Vector(st_x + 140, 70), f"{cd_s:02d}", c2, 4)
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color); draw.text(Vector(5, screen_h - 32), "[L/R]Sel [U/D]Adj [ENT]Go [R]Rst", theme_color)

@track_ram
def draw_main(view_manager, draw, screen_w, screen_h, theme_color, bg_color):
    global cursor_idx, settings, sys_time, snooze_epoch, snooze_idx, egg_end, sw_run, cd_end
    c_idx = cursor_idx
    draw.text(Vector(10, 10), f"Eggtimer {_VERSION}", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color)
    draw.text(Vector(15, 42), "CURRENT TIME:", TFT_LIGHTGREY); draw.fill_rectangle(Vector(15, 55), Vector(screen_w - 30, 43), TFT_DARKGREY); draw.rect(Vector(15, 55), Vector(screen_w - 30, 43), theme_color)
    t = sys_time.localtime(); dh = t[3] % 12 if settings["use_12h"] else t[3]; dh = 12 if settings["use_12h"] and dh == 0 else dh
    time_str = "{:02d}:{:02d}:{:02d} {}".format(dh, t[4], t[5], "AM" if t[3] < 12 else "PM") if settings["use_12h"] else "{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5])
    draw.text(Vector(40 if not settings["use_12h"] else 20, 58), time_str, theme_color, 2)
    
    n_str = "Next: None Active"; min_d = 9999999999; c_sec = sys_time.time(); next_a = None; is_snooze_next = False
    for a in settings["alarms"]:
        if a[5]:
            a_sec = sys_time.mktime((t[0], t[1], t[2], a[3], a[4], 0, 0, 0)) + (86400 if a[8] and (a[3] < t[3] or (a[3] == t[3] and a[4] <= t[4])) else 0) if a[8] else sys_time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0))
            d = a_sec - c_sec
            if 0 < d < min_d: min_d = d; next_a = a; is_snooze_next = False
    if snooze_epoch > 0 and 0 < snooze_epoch - c_sec < min_d: next_a = settings["alarms"][snooze_idx]; is_snooze_next = True
    if next_a:
        lbl = next_a[6][:4] + "Zz" if is_snooze_next else next_a[6][:6]; nh, nm = (sys_time.localtime(snooze_epoch)[3:5] if is_snooze_next else next_a[3:5])
        nmo, nd = (sys_time.localtime(snooze_epoch)[1:3] if is_snooze_next else (next_a[1:3] if not next_a[8] else (t[1], t[2])))
        ny = sys_time.localtime(snooze_epoch)[0] if is_snooze_next else (next_a[0] if not next_a[8] else t[0])
        ndh = nh % 12 if settings["use_12h"] else nh; ndh = 12 if settings["use_12h"] and ndh == 0 else ndh; nampm = ("A" if nh < 12 else "P") if settings["use_12h"] else ""
        n_str = ("Next: DAILY " if next_a[8] and not is_snooze_next else f"Next: {nmo:02d}/{nd:02d} " if settings["use_12h"] else f"Next: {nd:02d}.{nmo:02d}.{ny:04d} ") + f"{ndh:02d}:{nm:02d}{nampm} [{lbl}]"
    
    draw.text(Vector(20, 80), n_str, TFT_WHITE)
    
    in_y = 102; r_height = 16; egg_str = "RUN" if egg_end > 0 else ""; sw_str = "RUN" if sw_run else ""; cd_str = "RUN" if cd_end > 0 else ""
    for i, (txt, cnt) in enumerate([("Manage Alarms", f"[{len(settings['alarms'])}]"), ("Egg Timer", egg_str), ("Stopwatch", sw_str), ("Countdown", cd_str), ("Options Menu", ""), ("View Help", "")]):
        r_y = in_y + (i * 16)
        col = theme_color if c_idx == i else TFT_LIGHTGREY; b_col = theme_color if c_idx == i else TFT_DARKGREY; badge_col = theme_color if c_idx == i else TFT_WHITE
        if c_idx == i: draw.fill_rectangle(Vector(0, r_y - 2), Vector(screen_w, r_height), TFT_DARKGREY); draw.text(Vector(screen_w - 20, r_y + 1), "<", theme_color)
        draw.text(Vector(15, r_y + 1), txt, col)
        if cnt: draw.rect(Vector(160, r_y - 2), Vector(60, r_height), b_col); draw.text(Vector(170, r_y + 1), cnt, badge_col)
            
    draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color)
    draw.text(Vector(5, screen_h - 32), "[M]List [N]New [O]Opt [ESC]Exit", theme_color)
    draw.text(Vector(5, screen_h - 15), "[UP/DN]Nav [ENT]Select" + ("  [D]Diag" if settings.get("show_diagnostics", False) else ""), TFT_LIGHTGREY)

@track_ram
def draw_alarms(view_manager, draw, screen_w, screen_h, theme_color, bg_color):
    global cursor_idx, settings, sys_time
    c_idx = cursor_idx; list_len = len(settings["alarms"]) + 1
    draw.text(Vector(10, 10), "MODE: ALARMS LIST", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color)
    c_sec = sys_time.time(); has_past = False
    for i in range(min(4, list_len)):
        idx = c_idx - (c_idx % 4) + i
        if idx < list_len:
            r_y = 50 + (i * 35)
            if idx == c_idx: draw.fill_rectangle(Vector(0, r_y - 4), Vector(screen_w, 30), TFT_DARKGREY)
            if idx < len(settings["alarms"]):
                a = settings["alarms"][idx]; is_past = not a[8] and sys_time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) < c_sec
                if is_past: has_past = True
                t_col = theme_color if idx == c_idx else TFT_LIGHTGREY; label_color = TFT_RED if is_past else t_col
                draw.text(Vector(5, r_y + 1), f"{a[6][:6]}:", label_color); draw.rect(Vector(65, r_y - 4), Vector(250, 30), theme_color if idx == c_idx else TFT_DARKGREY)
                stat_str = ("ON*" if a[7] else "ON ") if a[5] else ("OFF*" if a[7] else "OFF "); adh = a[3] % 12 if settings["use_12h"] else a[3]; adh = 12 if settings["use_12h"] and adh == 0 else adh
                aampm = ("A" if a[3] < 12 else "P") if settings["use_12h"] else ""; a_str = f"DAILY {adh:02d}:{a[4]:02d}{aampm} [{stat_str}]" if a[8] else (f"{a[1]:02d}/{a[2]:02d} " if settings["use_12h"] else f"{a[2]:02d}.{a[1]:02d}.{a[0]:04d} ") + f"{adh:02d}:{a[4]:02d}{aampm} [{stat_str}]"
                draw.text(Vector(70, r_y + 1), a_str, TFT_RED if is_past else (theme_color if idx == c_idx else TFT_WHITE))
            else: draw.text(Vector(15, r_y + 1), "+ Create New Alarm", theme_color if idx == c_idx else TFT_LIGHTGREY)
    draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color); draw.text(Vector(5, screen_h - 32), "[L/R]Tgl " + ("[C]Clr " if has_past else "") + "[N]New [ESC]Back", theme_color); draw.text(Vector(5, screen_h - 15), "[UP/DN]Nav [T]Snd [BS]Del [ENT]Edit", TFT_LIGHTGREY)

def draw_editor(view_manager, draw, screen_w, screen_h, theme_color, bg_color):
    global current_mode, edit_idx, tmp_daily, tmp_y, tmp_mo, tmp_d, date_cursor, tmp_h, tmp_m, tmp_label, tmp_audible, settings, sys_time
    draw.text(Vector(10, 10), "MODE: EDIT ALARM" if edit_idx != -1 else "MODE: ADD ALARM", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color)
    out_y = 45; draw.fill_rectangle(Vector(15, out_y + 25), Vector(screen_w - 30, 80 if current_mode == MODE_EDIT_L else 35), TFT_DARKGREY); draw.rect(Vector(15, out_y + 25), Vector(screen_w - 30, 80 if current_mode == MODE_EDIT_L else 35), theme_color)
    if current_mode == MODE_EDIT_TYPE: draw.text(Vector(15, out_y + 5), "ALARM TYPE:", TFT_LIGHTGREY); draw.text(Vector(40, out_y + 33), f"< {'DAILY' if tmp_daily else 'SPECIFIC DATE'} >", theme_color, 2)
    elif current_mode == MODE_EDIT_DATE:
        draw.text(Vector(15, out_y + 5), "SET DATE:", TFT_LIGHTGREY)
        cy, cm, cd = (tmp_y, tmp_mo, tmp_d) if settings["use_12h"] else (tmp_d, tmp_mo, tmp_y); c0, c1, c2 = (theme_color if date_cursor == i else TFT_WHITE for i in range(3))
        if settings["use_12h"]: draw.text(Vector(30, out_y+33), f"{cy:04d}", c0, 2); draw.text(Vector(100, out_y+33), "-", TFT_LIGHTGREY, 2); draw.text(Vector(120, out_y+33), f"{cm:02d}", c1, 2); draw.text(Vector(160, out_y+33), "-", TFT_LIGHTGREY, 2); draw.text(Vector(180, out_y+33), f"{cd:02d}", c2, 2)
        else: draw.text(Vector(30, out_y+33), f"{cy:02d}", c0, 2); draw.text(Vector(70, out_y+33), ".", TFT_LIGHTGREY, 2); draw.text(Vector(90, out_y+33), f"{cm:02d}", c1, 2); draw.text(Vector(130, out_y+33), ".", TFT_LIGHTGREY, 2); draw.text(Vector(150, out_y+33), f"{cd:04d}", c2, 2)
    elif current_mode in (MODE_EDIT_H, MODE_EDIT_M):
        draw.text(Vector(15, out_y + 5), "SET TIME:", TFT_LIGHTGREY); th = tmp_h % 12 if settings["use_12h"] else tmp_h; th = 12 if settings["use_12h"] and th == 0 else th
        draw.text(Vector(60, out_y + 33), f"{th:02d}", theme_color if current_mode == MODE_EDIT_H else TFT_WHITE, 2); draw.text(Vector(100, out_y + 33), ":", TFT_LIGHTGREY, 2); draw.text(Vector(120, out_y + 33), f"{tmp_m:02d}", theme_color if current_mode == MODE_EDIT_M else TFT_WHITE, 2)
        if settings["use_12h"]: draw.text(Vector(150, out_y + 33), "AM" if tmp_h < 12 else "PM", TFT_LIGHTGREY, 2)
    elif current_mode == MODE_EDIT_L:
        draw.text(Vector(15, out_y + 5), f"SET LABEL ({len(tmp_label)}/50):", TFT_LIGHTGREY); v_str = tmp_label + ("_" if (int(sys_time.time()) % 2 == 0) else "")
        for i in range(0, len(v_str), 18): draw.text(Vector(20, out_y + 30 + (i // 18) * 20), v_str[i:i+18], TFT_WHITE, 2)
    elif current_mode == MODE_EDIT_AUD: draw.text(Vector(15, out_y + 5), "AUDIBLE SOUND:", TFT_LIGHTGREY); draw.text(Vector(80, out_y + 33), f"< {'YES' if tmp_audible else 'NO '} >", theme_color, 2)
    draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color); draw.text(Vector(5, screen_h - 32), "[ESC] Cancel / Back", theme_color); draw.text(Vector(5, screen_h - 15), "[ENT] Next / Save", TFT_LIGHTGREY)

VIEW_DISPATCH = {
    MODE_DIAGNOSTIC: draw_diagnostic,
    MODE_MAIN: draw_main,
    MODE_ALARMS: draw_alarms,
    MODE_STOPWATCH: draw_stopwatch,
    MODE_COUNTDOWN: draw_countdown,
    MODE_EGG: draw_egg_timer,
    MODE_RING: draw_ring,
    MODE_EDIT_TYPE: draw_editor,
    MODE_EDIT_DATE: draw_editor,
    MODE_EDIT_H: draw_editor,
    MODE_EDIT_M: draw_editor,
    MODE_EDIT_L: draw_editor,
    MODE_EDIT_AUD: draw_editor,
    MODE_CONFIRM_DEL: draw_modals,
    MODE_CONFIRM_CLR: draw_modals,
    MODE_ERR_TIME: draw_modals,
    MODE_ERR_DATE: draw_modals
}

def process_input(button, input_mgr, view_manager, t, c_sec):
    global show_help, show_options, help_scroll, current_mode, dirty_ui, options_cursor_idx, settings
    if show_help:
        if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_H):
            show_help = False; help_scroll = 0; dirty_ui = True
        elif button == BUTTON_DOWN: help_scroll += 1; dirty_ui = True
        elif button == BUTTON_UP: help_scroll = max(0, help_scroll - 1); dirty_ui = True
        input_mgr.reset(); return
    elif show_options:
        if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER):
            show_options = False; dirty_ui = True; queue_save()
        elif button == BUTTON_DOWN: options_cursor_idx = (options_cursor_idx + 1) % 7; dirty_ui = True
        elif button == BUTTON_UP: options_cursor_idx = (options_cursor_idx - 1) % 7; dirty_ui = True
        elif button == BUTTON_RIGHT:
            if options_cursor_idx == 0: settings["theme_idx"] = (settings["theme_idx"] + 1) % len(_THEMES)
            elif options_cursor_idx == 1: settings["bg_r"] = (settings["bg_r"] + 5) % 256
            elif options_cursor_idx == 2: settings["bg_g"] = (settings["bg_g"] + 5) % 256
            elif options_cursor_idx == 3: settings["bg_b"] = (settings["bg_b"] + 5) % 256
            elif options_cursor_idx == 4: settings["use_12h"] = not settings["use_12h"]
            elif options_cursor_idx == 5: settings["snooze_min"] = settings["snooze_min"] + 1 if settings["snooze_min"] < 60 else 1
            elif options_cursor_idx == 6: settings["show_diagnostics"] = not settings.get("show_diagnostics", False)
            dirty_ui = True; queue_save()
        elif button == BUTTON_LEFT:
            if options_cursor_idx == 0: settings["theme_idx"] = (settings["theme_idx"] - 1) % len(_THEMES)
            elif options_cursor_idx == 1: settings["bg_r"] = (settings["bg_r"] - 5) % 256
            elif options_cursor_idx == 2: settings["bg_g"] = (settings["bg_g"] - 5) % 256
            elif options_cursor_idx == 3: settings["bg_b"] = (settings["bg_b"] - 5) % 256
            elif options_cursor_idx == 4: settings["use_12h"] = not settings["use_12h"]
            elif options_cursor_idx == 5: settings["snooze_min"] = settings["snooze_min"] - 1 if settings["snooze_min"] > 1 else 60
            elif options_cursor_idx == 6: settings["show_diagnostics"] = not settings.get("show_diagnostics", False)
            dirty_ui = True; queue_save()
        input_mgr.reset(); return

    handler = INPUT_DISPATCH.get(current_mode)
    if handler: handler(button, input_mgr, view_manager, t, c_sec)
    input_mgr.reset()

@track_ram
def draw_view(view_manager):
    global help_scroll, current_mode, show_options, show_help, options_cursor_idx, settings, dirty_ui
    draw = view_manager.draw; screen_w = draw.size.x; screen_h = draw.size.y
    bg_color = rgb_to_565(settings["bg_r"], settings["bg_g"], settings["bg_b"]); theme_color = _THEMES[settings["theme_idx"]][1]
    
    if not (show_options or current_mode == MODE_RING):
        draw.clear(); draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), bg_color)
        
    if show_help:
        lines = get_help_lines()
        max_scroll = max(0, len(lines) - 12)
        help_scroll = min(help_scroll, max_scroll)
        for i in range(12):
            if help_scroll + i < len(lines):
                draw.text(Vector(10, 10 + i * 20), lines[help_scroll + i], TFT_WHITE)
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 40), bg_color)
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color)
        draw.text(Vector(5, screen_h - 32), "[UP/DN] Scroll  [ESC/H] Close", theme_color)

    elif show_options:
        draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), TFT_DARKGREY); draw.fill_rectangle(Vector(0, 0), Vector(screen_w, 30), theme_color); draw.text(Vector(10, 10), "OPTIONS MENU", TFT_WHITE)
        o_idx = options_cursor_idx
        c0 = theme_color if o_idx == 0 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 36), Vector(screen_w, 22), TFT_BLACK) if o_idx == 0 else None; draw.text(Vector(15, 40), "Theme Color:", c0); draw.text(Vector(140, 40), f"< {_THEMES[settings['theme_idx']][0]} >", c0)
        c1 = theme_color if o_idx == 1 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 60), Vector(screen_w, 22), TFT_BLACK) if o_idx == 1 else None; draw.text(Vector(15, 64), "Back R (0-255):", c1); draw.text(Vector(140, 64), f"< {settings['bg_r']} >", c1)
        c2 = theme_color if o_idx == 2 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 84), Vector(screen_w, 22), TFT_BLACK) if o_idx == 2 else None; draw.text(Vector(15, 88), "Back G (0-255):", c2); draw.text(Vector(140, 88), f"< {settings['bg_g']} >", c2)
        c3 = theme_color if o_idx == 3 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 108), Vector(screen_w, 22), TFT_BLACK) if o_idx == 3 else None; draw.text(Vector(15, 112), "Back B (0-255):", c3); draw.text(Vector(140, 112), f"< {settings['bg_b']} >", c3)
        c4 = theme_color if o_idx == 4 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 132), Vector(screen_w, 22), TFT_BLACK) if o_idx == 4 else None; draw.text(Vector(15, 136), "Time Format:", c4); draw.text(Vector(140, 136), f"< {'12 Hour' if settings['use_12h'] else '24 Hour'} >", c4)
        c5 = theme_color if o_idx == 5 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 156), Vector(screen_w, 22), TFT_BLACK) if o_idx == 5 else None; draw.text(Vector(15, 160), "Snooze (Min):", c5); draw.text(Vector(140, 160), f"< {settings['snooze_min']} >", c5)
        c6 = theme_color if o_idx == 6 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 180), Vector(screen_w, 22), TFT_BLACK) if o_idx == 6 else None; draw.text(Vector(15, 184), "Boot Diag:", c6); draw.text(Vector(140, 184), f"< {'ON ' if settings.get('show_diagnostics', False) else 'OFF'} >", c6)
        draw.text(Vector(15, 204), "Preview:", TFT_LIGHTGREY); draw.rect(Vector(90, 202), Vector(135, 14), theme_color); draw.fill_rectangle(Vector(91, 203), Vector(133, 12), bg_color)
        draw.text(Vector(5, screen_h - 20), "[L/R] Edit  [ENT] Close", TFT_WHITE)
    else:
        handler = VIEW_DISPATCH.get(current_mode)
        if handler: 
            profile_ram(str(current_mode), handler, view_manager, draw, screen_w, screen_h, theme_color, bg_color)

    draw.swap(); dirty_ui = False

# Define the start function that executes when the app is launched
def start(view_manager):
# Declare standard global variables needed for UI overlays and storage
    global storage, show_help, show_options
    # Declare global state variables needed to boot the main loop, including the new cursor
    global settings, current_mode, dirty_ui, last_s, cd_cursor
    
    # Re-initialize the lightweight settings dictionary fresh on boot
    settings = {
        # Default highlight theme index
        "theme_idx": 0, 
        # Default background red color value (0-255)
        "bg_r": 0, 
        # Default background green color value (0-255)
        "bg_g": 0, 
        # Default background blue color value (0-255)
        "bg_b": 0,
        # Default to 24-hour time display
        "use_12h": False, 
        # Default snooze duration is set to 5 minutes
        "snooze_min": 5, 
        # By default, bypass the hardware diagnostic screen
        "show_diagnostics": False, 
        # Initialize an empty list to hold alarm arrays
        "alarms": []
    }
    
    # Ensure the help overlay is hidden when the app opens
    show_help = False
    # Ensure the options menu is hidden when the app opens
    show_options = False
    # Bind the Picoware storage API reference to our global variable
    storage = view_manager.storage
    
    # Validate the board name and hardware capabilities
    validate_hardware_and_time(view_manager)
    # Read the JSON file from the SD card and populate the settings dictionary
    validate_and_load_settings()
    
    # Check if the user previously enabled the diagnostic boot screen
    if settings.get("show_diagnostics", False):
        # Set the starting integer mode to the diagnostics screen
        current_mode = MODE_DIAGNOSTIC
    # If the diagnostic screen is disabled
    else:
        # Set the starting integer mode to the main menu
        current_mode = MODE_MAIN
        
    # Flag the UI as dirty so the screen immediately renders on tick 1
    dirty_ui = True
    # Reset the last second tracker so the clock logic fires immediately
    last_s = -1
    # Reset the countdown cursor to the first slot so it is fresh on boot
    cd_cursor = 0
    # Return True to signal to the OS that the app started successfully
    return True

def run(view_manager):
    global settings, dirty_ui, dirty_save, save_timer, sys_time
    
    draw = view_manager.draw; input_mgr = view_manager.input_manager; button = input_mgr.button
    t = sys_time.localtime(); c_sec = sys_time.time()
    
    check_time_and_alarms(t, c_sec)
    
    if button == -1 and not dirty_ui and not dirty_save: return
    if button != -1: process_input(button, input_mgr, view_manager, t, c_sec)
    
    if settings is None: return
    
    if dirty_save and button == -1:
        if save_timer > 0: 
            save_timer -= 1
        else: 
            # Send the save function through our RAM profiler
            profile_ram("save_settings", save_settings)
        
    if dirty_ui: draw_view(view_manager)

def stop(view_manager):
    # 1. System and Settings
    global settings, storage, _cached_help_lines
    # 2. Large Static Dispatchers and Hardware
    global _EGG_PRESETS, _THEMES, buzzer_l, buzzer_r, INPUT_DISPATCH, VIEW_DISPATCH
    # 3. Volatile Strings and Memory
    global tmp_label, board_name
    # 4. Timers and Accumulators
    global sw_run, sw_start, sw_accum, last_sw_ms, egg_end, cd_end, snooze_epoch
    global cd_h, cd_m, cd_s, egg_preset
    # 5. UI Cursors and Trackers
    global show_help, show_options, help_scroll, current_mode, origin_mode, msg_origin
    global dirty_ui, dirty_save, save_timer, cursor_idx, options_cursor_idx, date_cursor, cd_cursor
    global last_s, last_trig_m, ringing_idx, ring_flash, snooze_idx, snooze_count, edit_idx
    global tmp_daily, tmp_y, tmp_mo, tmp_d, tmp_h, tmp_m, tmp_audible, del_confirm_yes, clear_confirm_yes
    
    save_settings()
    handle_audio_silence()
    
    # Tear down the settings dictionary
    if settings is not None: settings.clear()
    settings = None
    storage = None
    
    # Clear string caches (The most important step for freeing RAM)
    _cached_help_lines = []
    tmp_label = ""
    board_name = ""
    
    # Zero out all integer accumulators, timers, and trackers
    sw_start = sw_accum = last_sw_ms = egg_end = cd_end = snooze_epoch = 0
    cd_h = cd_m = cd_s = save_timer = help_scroll = 0
    cursor_idx = options_cursor_idx = date_cursor = cd_cursor = 0
    current_mode = origin_mode = msg_origin = 0
    last_s = last_trig_m = ringing_idx = snooze_idx = edit_idx = -1
    snooze_count = 0
    egg_preset = 1
    tmp_y = 2026; tmp_mo = 1; tmp_d = 1; tmp_h = 12; tmp_m = 0
    
    # Reset booleans
    sw_run = dirty_ui = dirty_save = ring_flash = show_help = show_options = False
    tmp_daily = del_confirm_yes = clear_confirm_yes = False
    tmp_audible = True
    
    # Tear down massive global structures to free RAM for the main OS
    _EGG_PRESETS = None
    _THEMES = None
    buzzer_l = None
    buzzer_r = None
    INPUT_DISPATCH = None
    VIEW_DISPATCH = None
    
    import gc
    gc.collect()

