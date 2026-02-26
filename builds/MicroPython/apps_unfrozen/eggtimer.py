from micropython import const
import time
from picoware.system.vector import Vector
from picoware.system.colors import (
    TFT_ORANGE, TFT_DARKGREY, TFT_LIGHTGREY, TFT_WHITE,
    TFT_BLACK, TFT_BLUE, TFT_YELLOW, TFT_CYAN, TFT_GREEN, TFT_RED
)
from picoware.system.buttons import (
    BUTTON_BACK, BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT,
    BUTTON_CENTER, BUTTON_BACKSPACE, BUTTON_H, BUTTON_ESCAPE, BUTTON_O
)

try:
    from picoware.system.buttons import BUTTON_A, BUTTON_Z, BUTTON_0, BUTTON_9, BUTTON_SPACE, BUTTON_N, BUTTON_T, BUTTON_S, BUTTON_C, BUTTON_M, BUTTON_R
except ImportError:
    BUTTON_A = BUTTON_Z = BUTTON_0 = BUTTON_9 = BUTTON_SPACE = BUTTON_N = BUTTON_T = BUTTON_S = BUTTON_C = BUTTON_M = BUTTON_R = -99

try:
    from machine import Pin, PWM
    buzzer_l = PWM(Pin(28))
    buzzer_r = PWM(Pin(27))
    buzzer_l.duty_u16(0)
    buzzer_r.duty_u16(0)
    buzzer = (buzzer_l, buzzer_r)
except:
    buzzer = None

from picoware.gui.textbox import TextBox
import json
import gc

_SETTINGS_FILE = "/picoware/apps/eggtimer_settings.json"

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

_VERSION = "0.06"

_HELP_TEXT = f"EGGTIMER\nVersion {_VERSION}\n----------------\nAlarms, egg timer,\nstopwatch & countdown.\n\nCREDITS:\nmade by Slasher006\nwith the help of Gemini\nDate: 2026-02-26\n\nSHORTCUTS:\n[L/R] Toggle ON/OFF\n[T] Toggle Audio\n[C] Clear Past\n[BS] Delete Alarm\n[H] Help Overlay\n[O] Options Menu\n[N] New Alarm\n[M] Alarm List\n[R] Reset Timers\n[ESC] Exit App\n\nCONTROLS:\n[UP/DN] Navigate\n[ENTER] Select/Save"

DEFAULT_STATE = {
    "theme_idx": 0,
    "bg_r": 0,
    "bg_g": 0,
    "bg_b": 0,
    "use_12h": False,
    "snooze_min": 5,
    "alarms": [],
    "egg_preset": 1,
    "egg_end": 0,
    "sw_run": False,
    "sw_start": 0,
    "sw_accum": 0,
    "last_sw_ms": 0,
    "cd_h": 0,
    "cd_m": 0,
    "cd_s": 0,
    "cd_cursor": 0,
    "cd_end": 0,
    "mode": "main",
    "origin": "main",
    "msg_origin": "main",
    "cursor_idx": 0,
    "options_cursor_idx": 0,
    "edit_idx": -1,
    "tmp_daily": False,
    "tmp_y": 2026,
    "tmp_mo": 1,
    "tmp_d": 1,
    "date_cursor": 0,
    "tmp_h": 12,
    "tmp_m": 0,
    "tmp_label": "",
    "tmp_audible": True,
    "ringing_idx": -1,
    "snooze_epoch": 0,
    "snooze_idx": -1,
    "snooze_count": 0,
    "last_s": -1,
    "last_trig_m": -1,
    "dirty_ui": True,
    "ring_flash": False,
    "dirty_save": False,
    "save_timer": 0,
    "del_confirm_yes": False,
    "clear_confirm_yes": False
}

state = DEFAULT_STATE.copy()
storage = None
show_help = False
show_options = False
help_box = None
_last_saved_json = ""

def rgb_to_565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

def queue_save():
    global state
    state["dirty_save"] = True
    state["save_timer"] = 60

def save_settings():
    global _last_saved_json, state
    if not storage: return
    try:
        exclude_keys = ("dirty_ui", "mode", "cursor_idx", "options_cursor_idx", "tmp_y", "tmp_mo", "tmp_d", "date_cursor", "tmp_h", "tmp_m", "tmp_label", "tmp_audible", "edit_idx", "ringing_idx", "last_s", "ring_flash", "dirty_save", "save_timer", "origin", "del_confirm_yes", "clear_confirm_yes", "snooze_epoch", "snooze_idx", "last_trig_m", "snooze_count", "msg_origin", "tmp_daily", "egg_end", "sw_run", "sw_start", "sw_accum", "last_sw_ms", "cd_end", "cd_cursor")
        save_data = {k: v for k, v in state.items() if k not in exclude_keys}
        json_str = json.dumps(save_data)
        if json_str == _last_saved_json:
            state["dirty_save"] = False
            return
        storage.write(_SETTINGS_FILE, json_str, "w")
        _last_saved_json = json_str
        state["dirty_save"] = False
    except Exception: pass

def validate_and_load_settings():
    global state, _last_saved_json
    if storage.exists(_SETTINGS_FILE):
        try:
            raw_data = storage.read(_SETTINGS_FILE, "r")
            loaded = json.loads(raw_data)
            exclude_keys = ("dirty_ui", "mode", "cursor_idx", "options_cursor_idx", "tmp_y", "tmp_mo", "tmp_d", "date_cursor", "tmp_h", "tmp_m", "tmp_label", "tmp_audible", "edit_idx", "ringing_idx", "last_s", "ring_flash", "dirty_save", "save_timer", "origin", "del_confirm_yes", "clear_confirm_yes", "snooze_epoch", "snooze_idx", "last_trig_m", "snooze_count", "msg_origin", "tmp_daily", "egg_end", "sw_run", "sw_start", "sw_accum", "last_sw_ms", "cd_end", "cd_cursor")
            for key in loaded:
                if key in state and key not in exclude_keys: state[key] = loaded[key]
            
            t = time.localtime()
            for i in range(len(state["alarms"])):
                a = state["alarms"][i]
                if len(a) == 3: state["alarms"][i] = [t[0], t[1], t[2], a[0], a[1], a[2], "ALARM", True, False]
                elif len(a) == 4: state["alarms"][i] = [t[0], t[1], t[2], a[0], a[1], a[2], a[3], True, False]
                elif len(a) == 7: state["alarms"][i] = [a[0], a[1], a[2], a[3], a[4], a[5], a[6], True, False]
                elif len(a) == 8: state["alarms"][i] = [a[0], a[1], a[2], a[3], a[4], a[5], a[6], a[7], False]
            
            save_data = {k: v for k, v in state.items() if k not in exclude_keys}
            _last_saved_json = json.dumps(save_data)
        except Exception: pass

def handle_audio_silence():
    if buzzer:
        try:
            for b in buzzer: b.duty_u16(0)
        except: pass

def check_time_and_alarms(t, c_sec):
    global state
    cy, cmo, cd, ch, cm, cs = t[0], t[1], t[2], t[3], t[4], t[5]
    
    if state["mode"] == "stopwatch" and state["sw_run"]:
        now_ms = time.ticks_ms()
        if time.ticks_diff(now_ms, state["last_sw_ms"]) > 100:
            state["last_sw_ms"] = now_ms
            state["dirty_ui"] = True
            
    if state["mode"] != "error_time":
        if cs != state["last_s"]:
            state["last_s"] = cs
            state["dirty_ui"] = True
            if state["mode"] != "ring":
                if state["egg_end"] > 0 and c_sec >= state["egg_end"]:
                    state["mode"] = "ring"
                    state["ringing_idx"] = -2
                    state["egg_end"] = 0
                elif state["cd_end"] > 0 and c_sec >= state["cd_end"]:
                    state["mode"] = "ring"
                    state["ringing_idx"] = -3
                    state["cd_end"] = 0
                elif state["snooze_epoch"] > 0 and c_sec >= state["snooze_epoch"]:
                    state["mode"] = "ring"
                    state["ringing_idx"] = state["snooze_idx"]
                    state["snooze_epoch"] = 0
                    state["last_trig_m"] = cm
                elif cs == 0 and state["last_trig_m"] != cm:
                    for i in range(len(state["alarms"])):
                        a = state["alarms"][i]
                        if a[5] and a[3] == ch and a[4] == cm and (a[8] or (a[0] == cy and a[1] == cmo and a[2] == cd)):
                            state["mode"] = "ring"
                            state["ringing_idx"] = i
                            state["snooze_count"] = 0
                            state["last_trig_m"] = cm
                            break

        if state["mode"] == "ring" and state["dirty_ui"]:
            state["ring_flash"] = not state["ring_flash"]
            is_audible = True if state["ringing_idx"] in (-2, -3) else state["alarms"][state["ringing_idx"]][7]
            if buzzer and is_audible:
                try:
                    for b in buzzer:
                        b.freq(1000) if state["ring_flash"] else None
                        b.duty_u16(32768 if state["ring_flash"] else 0)
                except: pass

def process_input(button, input_mgr, view_manager, t, c_sec):
    global show_help, show_options, help_box, state
    cy, cmo, cd, ch, cm = t[0], t[1], t[2], t[3], t[4]

    if state["mode"] == "error_time":
        if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER):
            view_manager.back()
            
    elif state["mode"] in ("invalid_time", "invalid_date_format"):
        if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP, BUTTON_DOWN):
            state["mode"] = state.get("msg_origin", "main")
            state["dirty_ui"] = True

    elif state["mode"] == "ring":
        if state["ringing_idx"] in (-2, -3):
            if button in (BUTTON_CENTER, BUTTON_O, BUTTON_BACK, BUTTON_ESCAPE):
                state["mode"] = "egg_timer" if state["ringing_idx"] == -2 else "countdown"
                state["ringing_idx"] = -1
                state["dirty_ui"] = True
                handle_audio_silence()
        else:
            if button in (BUTTON_S, BUTTON_CENTER):
                if state["snooze_count"] < 5:
                    state["snooze_epoch"] = c_sec + (state["snooze_min"] * 60)
                    state["snooze_idx"] = state["ringing_idx"]
                    state["snooze_count"] += 1
                    queue_save()
                else:
                    if 0 <= state["ringing_idx"] < len(state["alarms"]) and not state["alarms"][state["ringing_idx"]][8]:
                        state["alarms"][state["ringing_idx"]][5] = False
                        queue_save()
                    state["snooze_epoch"] = state["snooze_count"] = 0
                state["mode"] = "main"
                state["ringing_idx"] = -1
                state["dirty_ui"] = True
                handle_audio_silence()
            elif button in (BUTTON_O, BUTTON_BACK, BUTTON_ESCAPE):
                state["mode"] = "main"
                if 0 <= state["ringing_idx"] < len(state["alarms"]) and not state["alarms"][state["ringing_idx"]][8]:
                    state["alarms"][state["ringing_idx"]][5] = False
                    queue_save()
                state["ringing_idx"] = -1
                state["snooze_epoch"] = state["snooze_count"] = 0
                state["dirty_ui"] = True
                handle_audio_silence()

    elif show_options:
        if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER):
            show_options = False
            state["dirty_ui"] = True
            queue_save()
        elif button == BUTTON_DOWN: state["options_cursor_idx"] = (state["options_cursor_idx"] + 1) % 6; state["dirty_ui"] = True
        elif button == BUTTON_UP: state["options_cursor_idx"] = (state["options_cursor_idx"] - 1) % 6; state["dirty_ui"] = True
        elif button == BUTTON_RIGHT:
            if state["options_cursor_idx"] == 0: state["theme_idx"] = (state["theme_idx"] + 1) % len(_THEMES)
            elif state["options_cursor_idx"] == 1: state["bg_r"] = (state["bg_r"] + 5) % 256
            elif state["options_cursor_idx"] == 2: state["bg_g"] = (state["bg_g"] + 5) % 256
            elif state["options_cursor_idx"] == 3: state["bg_b"] = (state["bg_b"] + 5) % 256
            elif state["options_cursor_idx"] == 4: state["use_12h"] = not state["use_12h"]
            elif state["options_cursor_idx"] == 5: state["snooze_min"] = state["snooze_min"] + 1 if state["snooze_min"] < 60 else 1
            state["dirty_ui"] = True
            queue_save()
        elif button == BUTTON_LEFT:
            if state["options_cursor_idx"] == 0: state["theme_idx"] = (state["theme_idx"] - 1) % len(_THEMES)
            elif state["options_cursor_idx"] == 1: state["bg_r"] = (state["bg_r"] - 5) % 256
            elif state["options_cursor_idx"] == 2: state["bg_g"] = (state["bg_g"] - 5) % 256
            elif state["options_cursor_idx"] == 3: state["bg_b"] = (state["bg_b"] - 5) % 256
            elif state["options_cursor_idx"] == 4: state["use_12h"] = not state["use_12h"]
            elif state["options_cursor_idx"] == 5: state["snooze_min"] = state["snooze_min"] - 1 if state["snooze_min"] > 1 else 60
            state["dirty_ui"] = True
            queue_save()
            
    elif show_help:
        if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_H):
            show_help = False
            if help_box is not None:
                del help_box
                help_box = None
                gc.collect()
            state["dirty_ui"] = True
        elif button == BUTTON_DOWN and help_box: help_box.scroll_down(); state["dirty_ui"] = True
        elif button == BUTTON_UP and help_box: help_box.scroll_up(); state["dirty_ui"] = True

    elif state["mode"] == "main":
        if button in (BUTTON_BACK, BUTTON_ESCAPE):
            save_settings(); view_manager.back()
        elif button == BUTTON_H: show_help = True; state["dirty_ui"] = True
        elif button == BUTTON_O: show_options = True; state["dirty_ui"] = True
        elif button == BUTTON_M: state["mode"] = "alarms"; state["cursor_idx"] = 0; state["dirty_ui"] = True
        elif button == BUTTON_N:
            state["mode"] = "edit_type"; state["origin"] = "main"; state["edit_idx"] = -1; state["tmp_daily"] = False
            state["tmp_y"] = cy; state["tmp_mo"] = cmo; state["tmp_d"] = cd; state["date_cursor"] = 0
            state["tmp_h"] = ch; state["tmp_m"] = cm; state["tmp_label"] = ""; state["tmp_audible"] = True; state["dirty_ui"] = True
        elif button == BUTTON_DOWN: state["cursor_idx"] = (state["cursor_idx"] + 1) % 6; state["dirty_ui"] = True
        elif button == BUTTON_UP: state["cursor_idx"] = (state["cursor_idx"] - 1) % 6; state["dirty_ui"] = True
        elif button == BUTTON_CENTER:
            if state["cursor_idx"] == 0: state["mode"] = "alarms"; state["cursor_idx"] = 0
            elif state["cursor_idx"] == 1: state["mode"] = "egg_timer"
            elif state["cursor_idx"] == 2: state["mode"] = "stopwatch"
            elif state["cursor_idx"] == 3: state["mode"] = "countdown"
            elif state["cursor_idx"] == 4: show_options = True
            elif state["cursor_idx"] == 5: show_help = True
            state["dirty_ui"] = True

    elif state["mode"] == "egg_timer":
        if button in (BUTTON_BACK, BUTTON_ESCAPE):
            state["mode"] = "main"
            state["dirty_ui"] = True
        elif button == BUTTON_DOWN:
            state["egg_preset"] = (state["egg_preset"] + 1) % len(_EGG_PRESETS)
            state["dirty_ui"] = True
        elif button == BUTTON_UP:
            state["egg_preset"] = (state["egg_preset"] - 1) % len(_EGG_PRESETS)
            state["dirty_ui"] = True
        elif button == BUTTON_CENTER:
            m = _EGG_PRESETS[state["egg_preset"]][0]
            if m == 0:
                state["egg_end"] = 0
            else:
                state["egg_end"] = c_sec + (m * 60)
            queue_save()
            state["mode"] = "main"
            state["dirty_ui"] = True

    elif state["mode"] == "stopwatch":
        if button in (BUTTON_BACK, BUTTON_ESCAPE):
            state["mode"] = "main"
            state["dirty_ui"] = True
        elif button == BUTTON_CENTER:
            if state["sw_run"]:
                state["sw_accum"] += time.ticks_diff(time.ticks_ms(), state["sw_start"])
                state["sw_run"] = False
            else:
                state["sw_start"] = time.ticks_ms()
                state["sw_run"] = True
            state["dirty_ui"] = True
        elif button == BUTTON_R:
            state["sw_accum"] = 0
            state["sw_run"] = False
            state["dirty_ui"] = True
            
    elif state["mode"] == "countdown":
        if button in (BUTTON_BACK, BUTTON_ESCAPE):
            state["mode"] = "main"
            state["dirty_ui"] = True
        elif state["cd_end"] == 0:
            if button == BUTTON_LEFT:
                state["cd_cursor"] = (state["cd_cursor"] - 1) % 3
                state["dirty_ui"] = True
            elif button == BUTTON_RIGHT:
                state["cd_cursor"] = (state["cd_cursor"] + 1) % 3
                state["dirty_ui"] = True
            elif button == BUTTON_UP:
                if state["cd_cursor"] == 0: state["cd_h"] = (state["cd_h"] + 1) % 100
                elif state["cd_cursor"] == 1: state["cd_m"] = (state["cd_m"] + 1) % 60
                elif state["cd_cursor"] == 2: state["cd_s"] = (state["cd_s"] + 1) % 60
                state["dirty_ui"] = True
                queue_save()
            elif button == BUTTON_DOWN:
                if state["cd_cursor"] == 0: state["cd_h"] = (state["cd_h"] - 1) % 100
                elif state["cd_cursor"] == 1: state["cd_m"] = (state["cd_m"] - 1) % 60
                elif state["cd_cursor"] == 2: state["cd_s"] = (state["cd_s"] - 1) % 60
                state["dirty_ui"] = True
                queue_save()
            elif button == BUTTON_CENTER:
                total_s = state["cd_h"] * 3600 + state["cd_m"] * 60 + state["cd_s"]
                if total_s > 0:
                    state["cd_end"] = c_sec + total_s
                    state["dirty_ui"] = True
            elif button == BUTTON_R:
                state["cd_h"] = state["cd_m"] = state["cd_s"] = 0
                state["dirty_ui"] = True
                queue_save()
        else:
            if button in (BUTTON_CENTER, BUTTON_R):
                state["cd_end"] = 0
                state["dirty_ui"] = True

    elif state["mode"] == "alarms":
        list_len = len(state["alarms"]) + 1
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "main"; state["cursor_idx"] = 0; state["dirty_ui"] = True
        elif button == BUTTON_DOWN and state["cursor_idx"] < list_len - 1: state["cursor_idx"] += 1; state["dirty_ui"] = True
        elif button == BUTTON_UP and state["cursor_idx"] > 0: state["cursor_idx"] -= 1; state["dirty_ui"] = True
        elif button in (BUTTON_LEFT, BUTTON_RIGHT) and state["cursor_idx"] < len(state["alarms"]):
            a = state["alarms"][state["cursor_idx"]]
            if not a[5]:
                if not a[8] and time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) <= c_sec:
                    state["mode"] = "invalid_time"; state["msg_origin"] = "alarms"; state["dirty_ui"] = True
                else: 
                    a[5] = True; queue_save(); state["dirty_ui"] = True
            else:
                a[5] = False
                if state["snooze_idx"] == state["cursor_idx"]: state["snooze_epoch"] = state["snooze_count"] = 0
                queue_save(); state["dirty_ui"] = True
        elif button == BUTTON_T and state["cursor_idx"] < len(state["alarms"]): 
            state["alarms"][state["cursor_idx"]][7] = not state["alarms"][state["cursor_idx"]][7]; queue_save(); state["dirty_ui"] = True
        elif button == BUTTON_C:
            has_past = any(not a[8] and time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) < c_sec for a in state["alarms"])
            if has_past: state["mode"] = "confirm_clear"; state["clear_confirm_yes"] = False; state["dirty_ui"] = True
        elif button == BUTTON_BACKSPACE and state["cursor_idx"] < len(state["alarms"]): 
            state["mode"] = "confirm_delete"; state["del_confirm_yes"] = False; state["dirty_ui"] = True
        elif button == BUTTON_CENTER:
            state["mode"] = "edit_type"; state["origin"] = "alarms"; state["date_cursor"] = 0; state["dirty_ui"] = True
            if state["cursor_idx"] == len(state["alarms"]):
                state["edit_idx"] = -1; state["tmp_daily"] = False; state["tmp_y"] = cy; state["tmp_mo"] = cmo; state["tmp_d"] = cd
                state["tmp_h"] = ch; state["tmp_m"] = cm; state["tmp_label"] = ""; state["tmp_audible"] = True
            else:
                a = state["alarms"][state["cursor_idx"]]; state["edit_idx"] = state["cursor_idx"]
                state["tmp_y"] = a[0]; state["tmp_mo"] = a[1]; state["tmp_d"] = a[2]; state["tmp_h"] = a[3]; state["tmp_m"] = a[4]
                state["tmp_label"] = a[6]; state["tmp_audible"] = a[7]; state["tmp_daily"] = a[8]

    elif state["mode"] == "confirm_delete":
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "alarms"; state["dirty_ui"] = True
        elif button in (BUTTON_LEFT, BUTTON_RIGHT): state["del_confirm_yes"] = not state["del_confirm_yes"]; state["dirty_ui"] = True
        elif button == BUTTON_CENTER:
            if state["del_confirm_yes"]:
                if state["snooze_idx"] == state["cursor_idx"]: state["snooze_epoch"] = state["snooze_count"] = 0
                elif state["snooze_idx"] > state["cursor_idx"]: state["snooze_idx"] -= 1
                state["alarms"].pop(state["cursor_idx"]); state["cursor_idx"] = max(0, state["cursor_idx"] - 1); queue_save()
            state["mode"] = "alarms"; state["dirty_ui"] = True
            
    elif state["mode"] == "confirm_clear":
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "alarms"; state["dirty_ui"] = True
        elif button in (BUTTON_LEFT, BUTTON_RIGHT): state["clear_confirm_yes"] = not state["clear_confirm_yes"]; state["dirty_ui"] = True
        elif button == BUTTON_CENTER:
            if state["clear_confirm_yes"]:
                for i in range(len(state["alarms"]) - 1, -1, -1):
                    a = state["alarms"][i]
                    if not a[8] and time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) < c_sec:
                        if state["snooze_idx"] == i: state["snooze_epoch"] = state["snooze_count"] = 0
                        elif state["snooze_idx"] > i: state["snooze_idx"] -= 1
                        state["alarms"].pop(i)
                state["cursor_idx"] = 0; queue_save()
            state["mode"] = "alarms"; state["dirty_ui"] = True

    elif state["mode"] == "edit_type":
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = state.get("origin", "main"); state["dirty_ui"] = True
        elif button in (BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP, BUTTON_DOWN): state["tmp_daily"] = not state["tmp_daily"]; state["dirty_ui"] = True
        elif button == BUTTON_CENTER: state["mode"] = "edit_h" if state["tmp_daily"] else "edit_date"; state["dirty_ui"] = True
        
    elif state["mode"] == "edit_date":
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "edit_type"; state["dirty_ui"] = True
        elif button == BUTTON_LEFT: state["date_cursor"] = (state["date_cursor"] - 1) % 3; state["dirty_ui"] = True
        elif button == BUTTON_RIGHT: state["date_cursor"] = (state["date_cursor"] + 1) % 3; state["dirty_ui"] = True
        elif button == BUTTON_UP:
            if state["date_cursor"] == 0: state["tmp_y"] += 1 if state["use_12h"] else 0; state["tmp_d"] = state["tmp_d"] + 1 if state["tmp_d"] < 31 and not state["use_12h"] else (1 if not state["use_12h"] else state["tmp_d"])
            elif state["date_cursor"] == 1: state["tmp_mo"] = state["tmp_mo"] + 1 if state["tmp_mo"] < 12 else 1
            elif state["date_cursor"] == 2: state["tmp_d"] = state["tmp_d"] + 1 if state["tmp_d"] < 31 and state["use_12h"] else (1 if state["use_12h"] else state["tmp_d"]); state["tmp_y"] += 1 if not state["use_12h"] else 0
            state["dirty_ui"] = True
        elif button == BUTTON_DOWN:
            if state["date_cursor"] == 0: state["tmp_y"] = max(2024, state["tmp_y"] - 1) if state["use_12h"] else state["tmp_y"]; state["tmp_d"] = state["tmp_d"] - 1 if state["tmp_d"] > 1 and not state["use_12h"] else (31 if not state["use_12h"] else state["tmp_d"])
            elif state["date_cursor"] == 1: state["tmp_mo"] = state["tmp_mo"] - 1 if state["tmp_mo"] > 1 else 12
            elif state["date_cursor"] == 2: state["tmp_d"] = state["tmp_d"] - 1 if state["tmp_d"] > 1 and state["use_12h"] else (31 if state["use_12h"] else state["tmp_d"]); state["tmp_y"] = max(2024, state["tmp_y"] - 1) if not state["use_12h"] else state["tmp_y"]
            state["dirty_ui"] = True
        elif button == BUTTON_CENTER:
            leap = 1 if (state["tmp_y"] % 4 == 0 and (state["tmp_y"] % 100 != 0 or state["tmp_y"] % 400 == 0)) else 0
            dim = [31, 28 + leap, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][state["tmp_mo"] - 1]
            if state["tmp_d"] > dim: state["mode"] = "invalid_date_format"; state["msg_origin"] = "edit_date"; state["dirty_ui"] = True; input_mgr.reset(); return
            if state["tmp_y"] < cy or (state["tmp_y"] == cy and state["tmp_mo"] < cmo) or (state["tmp_y"] == cy and state["tmp_mo"] == cmo and state["tmp_d"] < cd): state["mode"] = "invalid_time"; state["msg_origin"] = "edit_date"; state["dirty_ui"] = True; input_mgr.reset(); return
            state["mode"] = "edit_h"; state["dirty_ui"] = True

    elif state["mode"] == "edit_h":
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "edit_type" if state["tmp_daily"] else "edit_date"; state["dirty_ui"] = True
        elif button == BUTTON_DOWN: state["tmp_h"] = (state["tmp_h"] - 1) % 24; state["dirty_ui"] = True
        elif button == BUTTON_UP: state["tmp_h"] = (state["tmp_h"] + 1) % 24; state["dirty_ui"] = True
        elif button == BUTTON_CENTER:
            if not state["tmp_daily"] and state["tmp_y"] == cy and state["tmp_mo"] == cmo and state["tmp_d"] == cd and state["tmp_h"] < ch: state["mode"] = "invalid_time"; state["msg_origin"] = "edit_h"; state["dirty_ui"] = True; input_mgr.reset(); return
            state["mode"] = "edit_m"; state["dirty_ui"] = True

    elif state["mode"] == "edit_m":
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "edit_h"; state["dirty_ui"] = True
        elif button == BUTTON_DOWN: state["tmp_m"] = (state["tmp_m"] - 1) % 60; state["dirty_ui"] = True
        elif button == BUTTON_UP: state["tmp_m"] = (state["tmp_m"] + 1) % 60; state["dirty_ui"] = True
        elif button == BUTTON_CENTER:
            if not state["tmp_daily"] and state["tmp_y"] == cy and state["tmp_mo"] == cmo and state["tmp_d"] == cd and state["tmp_h"] == ch and state["tmp_m"] <= cm: state["mode"] = "invalid_time"; state["msg_origin"] = "edit_m"; state["dirty_ui"] = True; input_mgr.reset(); return
            state["mode"] = "edit_l"; state["dirty_ui"] = True

    elif state["mode"] == "edit_l":
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "edit_m"; state["dirty_ui"] = True
        elif button == BUTTON_CENTER: state["mode"] = "edit_aud"; state["dirty_ui"] = True
        elif button == BUTTON_BACKSPACE and len(state["tmp_label"]) > 0: state["tmp_label"] = state["tmp_label"][:-1]; state["dirty_ui"] = True
        elif button == BUTTON_SPACE and len(state["tmp_label"]) < 50: state["tmp_label"] += " "; state["dirty_ui"] = True
        elif button >= BUTTON_A and button <= BUTTON_Z and len(state["tmp_label"]) < 50: state["tmp_label"] += chr(button - BUTTON_A + ord('A')); state["dirty_ui"] = True
        elif button >= BUTTON_0 and button <= BUTTON_9 and len(state["tmp_label"]) < 50: state["tmp_label"] += chr(button - BUTTON_0 + ord('0')); state["dirty_ui"] = True

    elif state["mode"] == "edit_aud":
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "edit_l"; state["dirty_ui"] = True
        elif button in (BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP, BUTTON_DOWN): state["tmp_audible"] = not state["tmp_audible"]; state["dirty_ui"] = True
        elif button == BUTTON_CENTER:
            final_lbl = state["tmp_label"].strip() or "ALARM"
            if not state["tmp_daily"] and time.mktime((state["tmp_y"], state["tmp_mo"], state["tmp_d"], state["tmp_h"], state["tmp_m"], 0, 0, 0)) <= c_sec: state["mode"] = "invalid_time"; state["msg_origin"] = "edit_aud"; state["dirty_ui"] = True; input_mgr.reset(); return
            new_a = [state["tmp_y"], state["tmp_mo"], state["tmp_d"], state["tmp_h"], state["tmp_m"], True, final_lbl, state["tmp_audible"], state["tmp_daily"]]
            if state["edit_idx"] == -1: state["alarms"].append(new_a)
            else: state["alarms"][state["edit_idx"]] = new_a
            queue_save(); state["mode"] = state.get("origin", "main"); state["dirty_ui"] = True
            if state["origin"] == "main": state["cursor_idx"] = 0

    input_mgr.reset()

def draw_view(view_manager):
    global help_box
    draw = view_manager.draw; screen_w = draw.size.x; screen_h = draw.size.y
    bg_color = rgb_to_565(state["bg_r"], state["bg_g"], state["bg_b"])
    theme_color = _THEMES[state["theme_idx"]][1]
    draw.clear(); draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), bg_color)
    
    if state["mode"] == "error_time":
        draw.text(Vector(30, 40), "NTP ERROR", theme_color, 2)
        draw.text(Vector(15, 90), "Cannot verify time.", TFT_LIGHTGREY)
        draw.text(Vector(15, 110), "Please connect Wi-Fi", TFT_WHITE)
        draw.text(Vector(15, 130), "and restart app.", TFT_WHITE)
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color)
        draw.text(Vector(5, screen_h - 25), "[ESC] Exit App", theme_color)
    elif state["mode"] == "invalid_date_format":
        draw.text(Vector(10, 10), "ERROR", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), TFT_RED)
        draw.fill_rectangle(Vector(15, 60), Vector(screen_w - 30, 80), TFT_DARKGREY); draw.rect(Vector(15, 60), Vector(screen_w - 30, 80), TFT_RED)
        draw.text(Vector(25, 75), "INVALID DATE", TFT_RED); draw.text(Vector(25, 100), "This date does not", TFT_WHITE); draw.text(Vector(25, 115), "exist in calendar.", TFT_WHITE)
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), TFT_RED); draw.text(Vector(5, screen_h - 32), "[Any Key] Go Back", TFT_RED)
    elif state["mode"] == "invalid_time":
        draw.text(Vector(10, 10), "ERROR", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), TFT_RED)
        draw.fill_rectangle(Vector(15, 60), Vector(screen_w - 30, 80), TFT_DARKGREY); draw.rect(Vector(15, 60), Vector(screen_w - 30, 80), TFT_RED)
        draw.text(Vector(25, 75), "INVALID DATE/TIME", TFT_RED); draw.text(Vector(25, 100), "Alarm must be set", TFT_WHITE); draw.text(Vector(25, 115), "in the future.", TFT_WHITE)
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), TFT_RED); draw.text(Vector(5, screen_h - 32), "[Any Key] Go Back", TFT_RED)
    elif state["mode"] == "ring":
        if state["ringing_idx"] == -2:
            display_lbl = "EGG READY!"
            hint_str = "[ENT/O] Dismiss"
        elif state["ringing_idx"] == -3:
            display_lbl = "TIME'S UP!"
            hint_str = "[ENT/O] Dismiss"
        else:
            display_lbl = state["alarms"][state["ringing_idx"]][6][:15] + "..." if len(state["alarms"][state["ringing_idx"]][6]) > 15 else state["alarms"][state["ringing_idx"]][6]
            hint_str = f"[S/ENT]Snooze({5-state['snooze_count']}) [O]Off" if state["snooze_count"] < 5 else "[O]Off (Max Snooze)"
        draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), TFT_WHITE if state["ring_flash"] else TFT_BLACK)
        draw.text(Vector(30, 60), "ALARM!", TFT_BLACK if state["ring_flash"] else theme_color, 3)
        draw.text(Vector(10, 100), display_lbl, TFT_BLACK if state["ring_flash"] else theme_color, 2)
        draw.text(Vector(10, 150), hint_str, TFT_BLACK if state["ring_flash"] else theme_color)
    elif state["mode"] == "egg_timer":
        draw.text(Vector(10, 10), "MODE: EGG TIMER", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color)
        if state["egg_end"] > 0:
            rem = max(0, state["egg_end"] - int(time.time()))
            m, s = divmod(rem, 60)
            draw.text(Vector(15, 40), f"Run: {m:02d}:{s:02d}", TFT_GREEN, 2)
        else:
            draw.text(Vector(15, 45), "Status: Inactive", TFT_LIGHTGREY)
        
        draw.text(Vector(15, 70), "Select Preset:", TFT_LIGHTGREY)
        for i, (m, lbl) in enumerate(_EGG_PRESETS):
            c = theme_color if state["egg_preset"] == i else TFT_LIGHTGREY
            if state["egg_preset"] == i: draw.text(Vector(10, 90 + i*20), ">", theme_color)
            draw.text(Vector(25, 90 + i*20), lbl, c)
            
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color)
        draw.text(Vector(5, screen_h - 32), "[UP/DN] Nav [ENT] Apply", theme_color)
    elif state["mode"] == "stopwatch":
        draw.text(Vector(10, 10), "MODE: STOPWATCH", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color)
        
        current_ms = state["sw_accum"]
        if state["sw_run"]:
            current_ms += time.ticks_diff(time.ticks_ms(), state["sw_start"])
            
        ms = (current_ms % 1000) // 100
        sec = (current_ms // 1000) % 60
        mins = (current_ms // 60000) % 60
        hrs = (current_ms // 3600000)
        
        if hrs > 0:
            sw_text = f"{hrs:02d}:{mins:02d}:{sec:02d}"
        else:
            sw_text = f"{mins:02d}:{sec:02d}.{ms:01d}"
            
        draw.text(Vector((screen_w // 2) - 85, 70), sw_text, theme_color, 4)
        
        stat_str = "RUNNING" if state["sw_run"] else "STOPPED"
        draw.text(Vector((screen_w // 2) - 30, 130), stat_str, TFT_GREEN if state["sw_run"] else TFT_LIGHTGREY)
        
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color)
        draw.text(Vector(5, screen_h - 32), "[ENT] Start/Stop [R] Reset", theme_color)
    elif state["mode"] == "countdown":
        draw.text(Vector(10, 10), "MODE: COUNTDOWN", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color)
        
        if state["cd_end"] > 0:
            rem = max(0, state["cd_end"] - int(time.time()))
            h = rem // 3600; m = (rem % 3600) // 60; s = rem % 60
            draw.text(Vector((screen_w // 2) - 85, 70), f"{h:02d}:{m:02d}:{s:02d}", theme_color, 4)
            draw.text(Vector((screen_w // 2) - 30, 130), "RUNNING", TFT_GREEN)
            draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color)
            draw.text(Vector(5, screen_h - 32), "[ENT] Cancel", theme_color)
        else:
            draw.text(Vector(15, 45), "Set Duration:", TFT_LIGHTGREY)
            c0 = theme_color if state["cd_cursor"] == 0 else TFT_WHITE
            c1 = theme_color if state["cd_cursor"] == 1 else TFT_WHITE
            c2 = theme_color if state["cd_cursor"] == 2 else TFT_WHITE
            
            st_x = (screen_w // 2) - 85
            draw.text(Vector(st_x, 70), f"{state['cd_h']:02d}", c0, 4)
            draw.text(Vector(st_x + 50, 70), ":", TFT_LIGHTGREY, 4)
            draw.text(Vector(st_x + 70, 70), f"{state['cd_m']:02d}", c1, 4)
            draw.text(Vector(st_x + 120, 70), ":", TFT_LIGHTGREY, 4)
            draw.text(Vector(st_x + 140, 70), f"{state['cd_s']:02d}", c2, 4)
            
            draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color)
            draw.text(Vector(5, screen_h - 32), "[L/R]Sel [U/D]Adj [ENT]Go [R]Rst", theme_color)
            
    elif show_options:
        draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), TFT_DARKGREY); draw.fill_rectangle(Vector(0, 0), Vector(screen_w, 30), theme_color); draw.text(Vector(10, 10), "OPTIONS MENU", TFT_WHITE)
        opt_r_height = 22; o_idx = state["options_cursor_idx"]
        
        c0 = theme_color if o_idx == 0 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 36), Vector(screen_w, opt_r_height), TFT_BLACK) if o_idx == 0 else None; draw.text(Vector(15, 40), "Theme Color:", c0); draw.text(Vector(140, 40), f"< {_THEMES[state['theme_idx']][0]} >", c0)
        c1 = theme_color if o_idx == 1 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 60), Vector(screen_w, opt_r_height), TFT_BLACK) if o_idx == 1 else None; draw.text(Vector(15, 64), "Back R (0-255):", c1); draw.text(Vector(140, 64), f"< {state['bg_r']} >", c1)
        c2 = theme_color if o_idx == 2 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 84), Vector(screen_w, opt_r_height), TFT_BLACK) if o_idx == 2 else None; draw.text(Vector(15, 88), "Back G (0-255):", c2); draw.text(Vector(140, 88), f"< {state['bg_g']} >", c2)
        c3 = theme_color if o_idx == 3 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 108), Vector(screen_w, opt_r_height), TFT_BLACK) if o_idx == 3 else None; draw.text(Vector(15, 112), "Back B (0-255):", c3); draw.text(Vector(140, 112), f"< {state['bg_b']} >", c3)
        c4 = theme_color if o_idx == 4 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 132), Vector(screen_w, opt_r_height), TFT_BLACK) if o_idx == 4 else None; draw.text(Vector(15, 136), "Time Format:", c4); draw.text(Vector(140, 136), f"< {'12 Hour' if state['use_12h'] else '24 Hour'} >", c4)
        c5 = theme_color if o_idx == 5 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 156), Vector(screen_w, opt_r_height), TFT_BLACK) if o_idx == 5 else None; draw.text(Vector(15, 160), "Snooze (Min):", c5); draw.text(Vector(140, 160), f"< {state['snooze_min']} >", c5)
        
        draw.text(Vector(15, 184), "Preview:", TFT_LIGHTGREY); draw.rect(Vector(90, 182), Vector(135, 14), theme_color); draw.fill_rectangle(Vector(91, 183), Vector(133, 12), bg_color)
        draw.text(Vector(5, screen_h - 20), "[L/R] Edit  [ENT] Close", TFT_WHITE)
    elif show_help:
        if help_box is None: help_box = TextBox(draw, 0, 240, theme_color, bg_color, True); help_box.set_text(_HELP_TEXT)
        help_box.refresh()
    elif state["mode"] == "main":
        c_idx = state["cursor_idx"]
        draw.text(Vector(10, 10), f"Eggtimer {_VERSION}", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color)
        
        draw.text(Vector(15, 42), "CURRENT TIME:", TFT_LIGHTGREY); draw.fill_rectangle(Vector(15, 55), Vector(screen_w - 30, 43), TFT_DARKGREY); draw.rect(Vector(15, 55), Vector(screen_w - 30, 43), theme_color)
        
        t = time.localtime()
        dh = t[3] % 12 if state["use_12h"] else t[3]
        dh = 12 if state["use_12h"] and dh == 0 else dh
        time_str = "{:02d}:{:02d}:{:02d} {}".format(dh, t[4], t[5], "AM" if t[3] < 12 else "PM") if state["use_12h"] else "{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5])
        draw.text(Vector(40 if not state["use_12h"] else 20, 58), time_str, theme_color, 2)
        
        n_str = "Next: None Active"
        min_d = 9999999999; c_sec = time.time(); next_a = None; is_snooze_next = False
        for a in state["alarms"]:
            if a[5]:
                a_sec = time.mktime((t[0], t[1], t[2], a[3], a[4], 0, 0, 0)) + (86400 if a[8] and (a[3] < t[3] or (a[3] == t[3] and a[4] <= t[4])) else 0) if a[8] else time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0))
                d = a_sec - c_sec
                if 0 < d < min_d: min_d = d; next_a = a; is_snooze_next = False
        if state["snooze_epoch"] > 0 and 0 < state["snooze_epoch"] - c_sec < min_d: next_a = state["alarms"][state["snooze_idx"]]; is_snooze_next = True
        
        if next_a:
            lbl = next_a[6][:4] + "Zz" if is_snooze_next else next_a[6][:6]
            nh, nm = (time.localtime(state["snooze_epoch"])[3:5] if is_snooze_next else next_a[3:5])
            nmo, nd = (time.localtime(state["snooze_epoch"])[1:3] if is_snooze_next else (next_a[1:3] if not next_a[8] else (t[1], t[2])))
            ny = time.localtime(state["snooze_epoch"])[0] if is_snooze_next else (next_a[0] if not next_a[8] else t[0])
            ndh = nh % 12 if state["use_12h"] else nh; ndh = 12 if state["use_12h"] and ndh == 0 else ndh
            nampm = ("A" if nh < 12 else "P") if state["use_12h"] else ""
            n_str = ("Next: DAILY " if next_a[8] and not is_snooze_next else f"Next: {nmo:02d}/{nd:02d} " if state["use_12h"] else f"Next: {nd:02d}.{nmo:02d}.{ny:04d} ") + f"{ndh:02d}:{nm:02d}{nampm} [{lbl}]"
            
        draw.text(Vector(20, 80), n_str, TFT_WHITE)
        
        in_y = 102; r_height = 16
        egg_str = "RUN" if state["egg_end"] > 0 else ""
        sw_str = "RUN" if state.get("sw_run", False) else ""
        cd_str = "RUN" if state.get("cd_end", 0) > 0 else ""
        
        for i, (txt, cnt) in enumerate([("Manage Alarms", f"[{len(state['alarms'])}]"), ("Egg Timer", egg_str), ("Stopwatch", sw_str), ("Countdown", cd_str), ("Options Menu", ""), ("View Help", "")]):
            r_y = in_y + (i * 16); col = theme_color if c_idx == i else TFT_LIGHTGREY; b_col = theme_color if c_idx == i else TFT_DARKGREY
            if c_idx == i: draw.fill_rectangle(Vector(0, r_y - 2), Vector(screen_w, r_height), TFT_DARKGREY); draw.text(Vector(screen_w - 20, r_y + 1), "<", theme_color)
            draw.text(Vector(15, r_y + 1), txt, col)
            if cnt: draw.rect(Vector(160, r_y - 2), Vector(60, r_height), b_col); draw.text(Vector(170, r_y + 1), cnt, theme_color if c_idx == i else TFT_WHITE)
            
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color); draw.text(Vector(5, screen_h - 32), "[M]List [N]New [O]Opt [ESC]Exit", theme_color); draw.text(Vector(5, screen_h - 15), "[UP/DN]Nav [ENT]Select", TFT_LIGHTGREY)
    elif state["mode"] == "alarms":
        c_idx = state["cursor_idx"]; list_len = len(state["alarms"]) + 1
        draw.text(Vector(10, 10), "MODE: ALARMS LIST", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color)
        
        c_sec = time.time(); has_past = False
        for i in range(min(4, list_len)):
            idx = c_idx - (c_idx % 4) + i
            if idx < list_len:
                r_y = 50 + (i * 35)
                if idx == c_idx: draw.fill_rectangle(Vector(0, r_y - 4), Vector(screen_w, 30), TFT_DARKGREY)
                if idx < len(state["alarms"]):
                    a = state["alarms"][idx]; is_past = not a[8] and time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) < c_sec
                    if is_past: has_past = True
                    t_col = theme_color if idx == c_idx else TFT_LIGHTGREY; label_color = TFT_RED if is_past else t_col
                    draw.text(Vector(5, r_y + 1), f"{a[6][:6]}:", label_color); draw.rect(Vector(65, r_y - 4), Vector(250, 30), theme_color if idx == c_idx else TFT_DARKGREY)
                    stat_str = ("ON*" if a[7] else "ON ") if a[5] else ("OFF*" if a[7] else "OFF ")
                    adh = a[3] % 12 if state["use_12h"] else a[3]; adh = 12 if state["use_12h"] and adh == 0 else adh
                    aampm = ("A" if a[3] < 12 else "P") if state["use_12h"] else ""
                    a_str = f"DAILY {adh:02d}:{a[4]:02d}{aampm} [{stat_str}]" if a[8] else (f"{a[1]:02d}/{a[2]:02d} " if state["use_12h"] else f"{a[2]:02d}.{a[1]:02d}.{a[0]:04d} ") + f"{adh:02d}:{a[4]:02d}{aampm} [{stat_str}]"
                    draw.text(Vector(70, r_y + 1), a_str, TFT_RED if is_past else (theme_color if idx == c_idx else TFT_WHITE))
                else: draw.text(Vector(15, r_y + 1), "+ Create New Alarm", theme_color if idx == c_idx else TFT_LIGHTGREY)
        
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color); draw.text(Vector(5, screen_h - 32), "[L/R]Tgl " + ("[C]Clr " if has_past else "") + "[N]New [ESC]Back", theme_color); draw.text(Vector(5, screen_h - 15), "[UP/DN]Nav [T]Snd [BS]Del [ENT]Edit", TFT_LIGHTGREY)
    elif state["mode"] in ("confirm_delete", "confirm_clear"):
        draw.text(Vector(10, 10), f"MODE: {'DELETE' if state['mode'] == 'confirm_delete' else 'CLEAR'} ALARM(S)", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color)
        draw.fill_rectangle(Vector(15, 60), Vector(screen_w - 30, 80), TFT_DARKGREY); draw.rect(Vector(15, 60), Vector(screen_w - 30, 80), theme_color)
        draw.text(Vector(25, 70), "Delete this alarm?" if state["mode"] == "confirm_delete" else "Clear past alarms?", TFT_WHITE)
        if state["mode"] == "confirm_delete":
            a = state["alarms"][state["cursor_idx"]]; lbl = a[6][:10]
            adh = a[3] % 12 if state["use_12h"] else a[3]; adh = 12 if state["use_12h"] and adh == 0 else adh
            aampm = ("AM" if a[3] < 12 else "PM") if state["use_12h"] else ""
            dt_str = "DAILY" if a[8] else (f"{a[1]:02d}/{a[2]:02d}" if state["use_12h"] else f"{a[2]:02d}.{a[1]:02d}.{a[0]:04d}")
            draw.text(Vector(25, 90), f"{dt_str} {adh:02d}:{a[4]:02d} {aampm} [{lbl}]", theme_color)
        else: draw.text(Vector(25, 90), "This cannot be undone.", TFT_LIGHTGREY)
        is_yes = state["del_confirm_yes"] if state["mode"] == "confirm_delete" else state["clear_confirm_yes"]
        draw.fill_rectangle(Vector(30, 115), Vector(60, 20), TFT_BLACK if is_yes else TFT_DARKGREY); draw.text(Vector(45, 118), "YES", theme_color if is_yes else TFT_LIGHTGREY)
        draw.fill_rectangle(Vector(140, 115), Vector(60, 20), TFT_BLACK if not is_yes else TFT_DARKGREY); draw.text(Vector(160, 118), "NO", theme_color if not is_yes else TFT_LIGHTGREY)
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color); draw.text(Vector(5, screen_h - 32), "[L/R] Select [ENT] Confirm", theme_color); draw.text(Vector(5, screen_h - 15), "[ESC] Cancel", TFT_LIGHTGREY)
    elif state["mode"] in ("edit_type", "edit_date", "edit_h", "edit_m", "edit_l", "edit_aud"):
        draw.text(Vector(10, 10), "MODE: EDIT ALARM" if state.get("edit_idx", -1) != -1 else "MODE: ADD ALARM", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color)
        out_y = 45; draw.fill_rectangle(Vector(15, out_y + 25), Vector(screen_w - 30, 80 if state["mode"] == "edit_l" else 35), TFT_DARKGREY); draw.rect(Vector(15, out_y + 25), Vector(screen_w - 30, 80 if state["mode"] == "edit_l" else 35), theme_color)
        if state["mode"] == "edit_type":
            draw.text(Vector(15, out_y + 5), "ALARM TYPE:", TFT_LIGHTGREY); draw.text(Vector(40, out_y + 33), f"< {'DAILY' if state['tmp_daily'] else 'SPECIFIC DATE'} >", theme_color, 2)
        elif state["mode"] == "edit_date":
            draw.text(Vector(15, out_y + 5), "SET DATE:", TFT_LIGHTGREY)
            cy, cm, cd = (state["tmp_y"], state["tmp_mo"], state["tmp_d"]) if state["use_12h"] else (state["tmp_d"], state["tmp_mo"], state["tmp_y"])
            c0, c1, c2 = (theme_color if state["date_cursor"] == i else TFT_WHITE for i in range(3))
            if state["use_12h"]: draw.text(Vector(30, out_y+33), f"{cy:04d}", c0, 2); draw.text(Vector(100, out_y+33), "-", TFT_LIGHTGREY, 2); draw.text(Vector(120, out_y+33), f"{cm:02d}", c1, 2); draw.text(Vector(160, out_y+33), "-", TFT_LIGHTGREY, 2); draw.text(Vector(180, out_y+33), f"{cd:02d}", c2, 2)
            else: draw.text(Vector(30, out_y+33), f"{cy:02d}", c0, 2); draw.text(Vector(70, out_y+33), ".", TFT_LIGHTGREY, 2); draw.text(Vector(90, out_y+33), f"{cm:02d}", c1, 2); draw.text(Vector(130, out_y+33), ".", TFT_LIGHTGREY, 2); draw.text(Vector(150, out_y+33), f"{cd:04d}", c2, 2)
        elif state["mode"] in ("edit_h", "edit_m"):
            draw.text(Vector(15, out_y + 5), "SET TIME:", TFT_LIGHTGREY)
            th = state["tmp_h"] % 12 if state["use_12h"] else state["tmp_h"]; th = 12 if state["use_12h"] and th == 0 else th
            draw.text(Vector(60, out_y + 33), f"{th:02d}", theme_color if state["mode"] == "edit_h" else TFT_WHITE, 2); draw.text(Vector(100, out_y + 33), ":", TFT_LIGHTGREY, 2); draw.text(Vector(120, out_y + 33), f"{state['tmp_m']:02d}", theme_color if state["mode"] == "edit_m" else TFT_WHITE, 2)
            if state["use_12h"]: draw.text(Vector(150, out_y + 33), "AM" if state["tmp_h"] < 12 else "PM", TFT_LIGHTGREY, 2)
        elif state["mode"] == "edit_l":
            draw.text(Vector(15, out_y + 5), f"SET LABEL ({len(state['tmp_label'])}/50):", TFT_LIGHTGREY)
            v_str = state["tmp_label"] + ("_" if (int(time.time()) % 2 == 0) else "")
            for i in range(0, len(v_str), 18): draw.text(Vector(20, out_y + 30 + (i // 18) * 20), v_str[i:i+18], TFT_WHITE, 2)
        elif state["mode"] == "edit_aud":
            draw.text(Vector(15, out_y + 5), "AUDIBLE SOUND:", TFT_LIGHTGREY); draw.text(Vector(80, out_y + 33), f"< {'YES' if state['tmp_audible'] else 'NO '} >", theme_color, 2)
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color); draw.text(Vector(5, screen_h - 32), "[ESC] Cancel / Back", theme_color); draw.text(Vector(5, screen_h - 15), "[ENT] Next / Save", TFT_LIGHTGREY)

    draw.swap(); state["dirty_ui"] = False

def start(view_manager):
    global storage
    storage = view_manager.storage
    validate_and_load_settings()
    
    draw = view_manager.draw; screen_w = draw.size.x; screen_h = draw.size.y
    draw.clear(); draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), rgb_to_565(state["bg_r"], state["bg_g"], state["bg_b"]))
    draw.text(Vector(10, 10), f"Eggtimer {_VERSION}", _THEMES[state["theme_idx"]][1]); draw.swap()
    
    state["dirty_ui"] = True; state["last_s"] = -1
    if time.localtime()[0] < 2024: state["mode"] = "error_time"
    return True

def run(view_manager):
    draw = view_manager.draw; input_mgr = view_manager.input_manager; button = input_mgr.button
    t = time.localtime(); c_sec = time.time()
    
    check_time_and_alarms(t, c_sec)
    
    if button == -1 and not state["dirty_ui"] and not state["dirty_save"]: return
    if button != -1: process_input(button, input_mgr, view_manager, t, c_sec)
    
    if state["dirty_save"] and button == -1:
        if state["save_timer"] > 0: state["save_timer"] -= 1
        else: save_settings()
        
    if state["dirty_ui"]: draw_view(view_manager)

def stop(view_manager):
    save_settings(); handle_audio_silence(); gc.collect()
