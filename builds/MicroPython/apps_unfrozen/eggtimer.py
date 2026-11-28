import time
import json
import gc

from picoware.system.vector import Vector
from picoware.system.font import FONT_XTRA_SMALL, FONT_SMALL, FONT_MEDIUM
from picoware.system.colors import (
    TFT_ORANGE, TFT_DARKGREY, TFT_LIGHTGREY, TFT_WHITE,
    TFT_BLACK, TFT_BLUE, TFT_YELLOW, TFT_GREEN, TFT_RED
)

from picoware.system.buttons import (
    BUTTON_BACK, BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT,
    BUTTON_CENTER, BUTTON_BACKSPACE, BUTTON_H, BUTTON_ESCAPE, BUTTON_O,
    BUTTON_A, BUTTON_Z, BUTTON_0, BUTTON_9, BUTTON_SPACE, BUTTON_N, BUTTON_T, BUTTON_S, BUTTON_C, BUTTON_M, BUTTON_R
)


# The ViewManager owns the audio device; this app only borrows it.
alarm_audio = None
alarm_note = None
alarm_audio_active = False

show_options = False
help_scroll = 0
_last_saved_json = ""

_SETTINGS_FILE = "picoware/settings/eggtimer_settings.json"
_SETTINGS_TEMP = _SETTINGS_FILE + ".tmp"
_SETTINGS_BACKUP = _SETTINGS_FILE + ".bak"
_home_manager = None
_previous_home_handler = None
_exit_to_home = False

def _rgb565(red, green, blue):
    return ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)


# Restrained industrial palette: powder-coated shell, green-grey LCD, amber focus.
COLOR_BG = _rgb565(15, 18, 19)
COLOR_EDGE = _rgb565(91, 101, 100)
COLOR_SHADOW = _rgb565(7, 9, 9)
COLOR_LCD = _rgb565(177, 193, 160)
COLOR_LCD_DARK = _rgb565(25, 38, 28)
COLOR_LCD_MID = _rgb565(72, 91, 72)
COLOR_KEY = _rgb565(54, 61, 62)
COLOR_KEY_TOP = _rgb565(77, 85, 85)
COLOR_KEY_FN = _rgb565(69, 73, 69)
COLOR_KEY_OP = _rgb565(139, 84, 30)
COLOR_AMBER = _rgb565(245, 166, 57)
COLOR_MUTED = _rgb565(161, 168, 164)
COLOR_ERROR = _rgb565(244, 102, 83)

_THEMES = (
    ("Amber", COLOR_AMBER), ("Sage", COLOR_LCD),
    ("Red", COLOR_ERROR), ("Steel", COLOR_MUTED),
    ("Orange", _rgb565(225, 137, 63))
)

_EGG_PRESETS = (
    (0, "Off / Deactivate"),
    (4, "Soft (4m)"),
    (6, "Medium (6m)"),
    (8, "Hard (8m)"),
    (10, "Hard+ (10m)")
)

_VERSION = "1.0"

_cached_help_lines = []

def get_help_lines():
    global _cached_help_lines
    if _touch_enabled:
        return [f"EGGTIMER v{_VERSION}", "", "TOUCH CONTROLS",
                "Tap a row to open or act.", "Tap a field, then -/+ to adjust.",
                "Up/Down selects hidden rows.", "OK confirms the selected field.",
                "Back returns or cancels.", "", "ALARMS",
                "Use + New alarm in the list.", "Select an alarm with Up/Down;",
                "-/+ toggles it on or off.", "Tap an alarm for Edit/Sound/Delete.",
                "", "TIMERS", "Timers run while app is open.",
                "Exiting the app stops timers.", "Tap Snooze or Dismiss when ringing."]
    if not _cached_help_lines:
        _cached_help_lines = [
            f"EGGTIMER v{_VERSION}",
            "",
            "CONTROLS",
            "[UP/DN] Select row / field",
            "[L/R] Adjust selected value",
            "[ENTER] Select / confirm",
            "[ESC] Back / cancel",
            "",
            "MAIN MENU",
            "[M] Alarm list  [N] New alarm",
            "[O] Options     [H] Help",
            "[ESC] Exit app",
            "",
            "ALARM LIST",
            "[L/R] Alarm ON / OFF",
            "[T] Toggle sound",
            "[BS] Delete  [C] Clear past",
            "[N] New      [ENTER] Actions",
            "",
            "TIMERS",
            "[ENTER] Apply selected action",
            "[R] Reset stopwatch / countdown",
            "Timers run while app is open.",
            "Exiting the app stops timers.",
            "",
            "RINGING ALARM",
            "[UP/DN] Select action",
            "[ENTER] Apply selected action",
            "[S] Snooze  [O/ESC] Dismiss"
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
MODE_RING = 8
MODE_ALARM_ACTIONS = 9
MODE_EDIT_TYPE = 10
MODE_EDIT_DATE = 11
MODE_EDIT_H = 12
MODE_EDIT_M = 13
MODE_EDIT_L = 14
MODE_EDIT_AUD = 15
MODE_EDIT_CANCEL = 16
MODE_SAVE_ERROR = 24
MODE_CONFIRM_DEL = 20
MODE_CONFIRM_CLR = 21
MODE_ERR_TIME = 22
MODE_ERR_DATE = 23

# --- PERSISTENT SETTINGS ---
settings = {
    "style_version": 1, "theme_idx": 0,
    "use_12h": False, "snooze_min": 5, "alarms": []
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
sw_cursor = 0
ring_cursor = 0

egg_preset = 1
egg_end = 0
cd_end = 0
snoozes = []  # [alarm reference, monotonic deadline in ms, repeat count]

# Initialize the countdown timer hours variable to zero
cd_h = 0
# Initialize the countdown timer minutes variable to zero
cd_m = 0
# Initialize the countdown timer seconds variable to zero
cd_s = 0
# Initialize the countdown cursor position to the first slot (hours)
cd_cursor = 0
cd_run_cursor = 0
alarm_action_cursor = 0
label_cursor = 3
label_char = 0
editor_action_cursor = 0
exit_cursor = 0
_ticks_ms = time.ticks_ms
_clock_last = _ticks_ms()
_clock_ms = 0
last_timer_second = -1
_LABEL_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -"

last_s = -1
last_alarm_check = None
pending_alarms = []
alarm_occurrences = []  # Alarm identity and latest scheduled occurrence queued.
ringing_idx = -1
ring_flash = False
snooze_count = 0


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

def _elapsed_ms():
    """Unwrapped monotonic time; called each frame, including during alarms."""
    global _clock_last, _clock_ms
    now = _ticks_ms()
    _clock_ms += max(0, time.ticks_diff(now, _clock_last))
    _clock_last = now
    return _clock_ms


def cancel_snooze(alarm):
    snoozes[:] = [entry for entry in snoozes if entry[0] is not alarm]


def _before_home(view_manager):
    global _exit_to_home, current_mode, exit_cursor, dirty_ui
    _exit_to_home = True
    if save_settings():
        return True
    current_mode = MODE_SAVE_ERROR
    exit_cursor = 0
    dirty_ui = True
    return False


def _leave(view_manager):
    if _exit_to_home:
        view_manager.go_home()
    else:
        view_manager.back()


def request_exit(view_manager):
    global current_mode, exit_cursor, dirty_ui
    if save_settings():
        _leave(view_manager)
    else:
        current_mode = MODE_SAVE_ERROR
        exit_cursor = 0
        dirty_ui = True


def handle_input_save_error(button, view_manager, t, c_sec):
    global current_mode, exit_cursor, dirty_ui, dirty_save, cursor_idx, _exit_to_home
    if button in (BUTTON_UP, BUTTON_DOWN):
        exit_cursor = (exit_cursor + (1 if button == BUTTON_DOWN else -1)) % 3
    elif button in (BUTTON_BACK, BUTTON_ESCAPE) or (button == BUTTON_CENTER and exit_cursor == 1):
        current_mode = MODE_MAIN
        cursor_idx = 0
        _exit_to_home = False
    elif button == BUTTON_CENTER:
        if exit_cursor == 0:
            request_exit(view_manager)
        else:
            dirty_save = False  # Explicit user choice to discard unsaved changes.
            _leave(view_manager)
    dirty_ui = True


def queue_save():
    global dirty_save, save_timer
    dirty_save = True
    save_timer = 60

def _read_settings_file(path):
    try:
        if not storage.exists(path):
            return None
        raw = storage.read(path, "r")
        loaded = json.loads(raw)
        return (raw, loaded) if isinstance(loaded, dict) else None
    except Exception:
        return None


def save_settings():
    global dirty_save, save_timer, _last_saved_json
    if not dirty_save:
        return True
    if not storage:
        return False
    save_timer = 60
    try:
        json_str = json.dumps(settings)
        current = _read_settings_file(_SETTINGS_FILE)
        if current is None or current[0] != json_str:
            # A failed/short write affects only the uncommitted temporary file.
            if not storage.write(_SETTINGS_TEMP, json_str, "w"):
                return False
            if storage.read(_SETTINGS_TEMP, "r") != json_str:
                return False
            if current is not None:
                if storage.exists(_SETTINGS_BACKUP) and not storage.remove(_SETTINGS_BACKUP):
                    return False
                if not storage.rename(_SETTINGS_FILE, _SETTINGS_BACKUP):
                    return False
            elif storage.exists(_SETTINGS_FILE):
                # Keep any valid backup when replacing a damaged primary file.
                if not storage.remove(_SETTINGS_FILE):
                    return False
            if not storage.rename(_SETTINGS_TEMP, _SETTINGS_FILE):
                return False  # Startup can recover the last committed backup.
        _last_saved_json = json_str
        dirty_save = False
        return True
    except Exception:
        return False


def valid_alarm(record, today):
    """Migrate supported records and reject malformed saved alarms."""
    if not isinstance(record, list):
        return None
    a = record[:]
    if len(a) in (3, 4):
        a = list(today[:3]) + a[:3] + [a[3] if len(a) == 4 else "ALARM", True, False]
    elif len(a) == 7:
        a += [True, False]
    elif len(a) == 8:
        a += [False]
    if len(a) != 9:
        return None
    if any(type(a[i]) is not int for i in range(5)):
        return None
    y, month, day, hour, minute = a[:5]
    if not (1 <= y <= 9999 and 1 <= month <= 12 and 0 <= hour < 24 and 0 <= minute < 60):
        return None
    leap = y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)
    days = (31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    if not 1 <= day <= days[month - 1]:
        return None
    if any(type(a[i]) is not bool for i in (5, 7, 8)) or not isinstance(a[6], str):
        return None
    try:
        time.mktime((y, month, day, hour, minute, 0, 0, 0))
    except (ValueError, OverflowError):
        return None
    a[6] = a[6][:50].strip() or "ALARM"
    return a


def validate_and_load_settings():
    global _last_saved_json
    if not storage:
        return
    try:
        saved = _read_settings_file(_SETTINGS_FILE) or _read_settings_file(_SETTINGS_BACKUP)
        if saved is None:
            return
        raw_data, loaded = saved
        for key, low, high in (("theme_idx", 0, len(_THEMES) - 1),
                               ("snooze_min", 1, 60)):
            # Older colors belong to the original neon theme.
            if key != "snooze_min" and loaded.get("style_version") != 1:
                continue
            value = loaded.get(key)
            if type(value) is int and low <= value <= high:
                settings[key] = value
        if type(loaded.get("use_12h")) is bool:
            settings["use_12h"] = loaded["use_12h"]
        records = loaded.get("alarms")
        if isinstance(records, list):
            today = time.localtime()
            alarms = []
            for record in records:
                alarm = valid_alarm(record, today)
                if alarm is not None:
                    alarms.append(alarm)
            settings["alarms"] = alarms
        _last_saved_json = raw_data
    except Exception:
        return


def collect_due_alarms(t, c_sec):
    """Queue elapsed occurrences even while another timer is ringing."""
    global last_alarm_check
    previous = last_alarm_check
    if previous is None:
        # On launch, accept this minute but do not replay older alarms.
        previous = c_sec - t[5] - 1
    last_alarm_check = c_sec
    if c_sec < previous:
        return
    alarm_occurrences[:] = [entry for entry in alarm_occurrences
                            if any(record is entry[0] for record in settings["alarms"])]
    for a in settings["alarms"]:
        if not a[5]:
            continue
        date = t[:3] if a[8] else a[:3]
        due = time.mktime((date[0], date[1], date[2], a[3], a[4], 0, 0, 0))
        if a[8] and due > c_sec:
            due -= 86400
        if previous < due <= c_sec:
            occurrence = next((entry for entry in alarm_occurrences if entry[0] is a), None)
            if occurrence is not None and due <= occurrence[1]:
                continue
            if occurrence is None:
                alarm_occurrences.append([a, due])
            else:
                occurrence[1] = due
            # Coalesce missed daily occurrences while an alarm remains pending.
            if not any(item is a for item in pending_alarms):
                pending_alarms.append(a)

def handle_audio_silence():
    global alarm_audio_active
    if alarm_audio is not None and alarm_audio_active:
        try:
            alarm_audio.stop()
        except Exception:
            pass
    alarm_audio_active = False


def play_alarm_beep():
    global alarm_audio_active
    if alarm_audio is None or alarm_note is None:
        return
    try:
        alarm_audio_active = True
        # play_note is blocking: keep the pulse short for responsive input.
        alarm_audio.play_note(alarm_note)
    except Exception:
        handle_audio_silence()

def check_time_and_alarms(t, c_sec):
    global current_mode, sw_run, last_sw_ms, dirty_ui, last_s, egg_end
    global ringing_idx, cd_end, last_timer_second
    global snooze_count, ring_flash, settings, show_help, show_options, ring_cursor
    
    if current_mode == MODE_STOPWATCH and sw_run:
        now_ms = time.ticks_ms()
        if time.ticks_diff(now_ms, last_sw_ms) > 100:
            last_sw_ms = now_ms
            dirty_ui = True
            
    elapsed = _elapsed_ms()
    timer_second = elapsed // 1000
    second_changed = c_sec != last_s or timer_second != last_timer_second
    last_timer_second = timer_second
    if second_changed:
        last_s = c_sec
        collect_due_alarms(t, c_sec)
        dirty_ui = True
        if current_mode != MODE_RING:
            ring_cursor = 0
            ring_flash = False
            if egg_end > 0 and elapsed >= egg_end:
                current_mode = MODE_RING
                ringing_idx = -2
                egg_end = 0
            elif cd_end > 0 and elapsed >= cd_end:
                current_mode = MODE_RING
                ringing_idx = -3
                cd_end = 0
            else:
                for entry in snoozes[:]:
                    alarm, deadline, count = entry
                    idx = next((i for i, record in enumerate(settings['alarms']) if record is alarm and record[5]), -1)
                    if idx < 0:
                        snoozes.remove(entry)
                    elif elapsed >= deadline:
                        snoozes.remove(entry)
                        ringing_idx = idx
                        snooze_count = count
                        current_mode = MODE_RING
                        break
                while current_mode != MODE_RING and pending_alarms:
                    alarm = pending_alarms.pop(0)
                    idx = next((i for i, a in enumerate(settings["alarms"])
                                if a is alarm and a[5]), -1)
                    if idx >= 0:
                        current_mode = MODE_RING
                        ringing_idx = idx
                        snooze_count = 0
                        break
        if current_mode == MODE_RING:
            show_help = show_options = False

    if current_mode == MODE_RING and second_changed:
        ring_flash = not ring_flash
        is_audible = True if ringing_idx in (-2, -3) else settings["alarms"][ringing_idx][7]
        if ring_flash and is_audible:
            play_alarm_beep()
        else:
            handle_audio_silence()

def handle_input_modals(button, view_manager, t, c_sec):
    global current_mode, dirty_ui, msg_origin, del_confirm_yes, clear_confirm_yes, settings, cursor_idx, sys_time
    if current_mode in (MODE_ERR_TIME, MODE_ERR_DATE):
        if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP, BUTTON_DOWN):
            current_mode = msg_origin; dirty_ui = True
    elif current_mode == MODE_CONFIRM_DEL:
        if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = MODE_ALARMS; dirty_ui = True
        elif button in (BUTTON_UP, BUTTON_DOWN): del_confirm_yes = button == BUTTON_DOWN; dirty_ui = True
        elif button == BUTTON_CENTER:
            if del_confirm_yes:
                cancel_snooze(settings["alarms"][cursor_idx])
                settings["alarms"].pop(cursor_idx); cursor_idx = max(0, cursor_idx - 1); queue_save()
            current_mode = MODE_ALARMS; dirty_ui = True
    elif current_mode == MODE_CONFIRM_CLR:
        if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = MODE_ALARMS; dirty_ui = True
        elif button in (BUTTON_UP, BUTTON_DOWN): clear_confirm_yes = button == BUTTON_DOWN; dirty_ui = True
        elif button == BUTTON_CENTER:
            if clear_confirm_yes:
                for i in range(len(settings["alarms"]) - 1, -1, -1):
                    a = settings["alarms"][i]
                    if not a[8] and time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) < c_sec:
                        cancel_snooze(a)
                        settings["alarms"].pop(i)
                cursor_idx = 0; queue_save()
            current_mode = MODE_ALARMS; dirty_ui = True

def handle_input_ring(button, view_manager, t, c_sec):
    global current_mode, dirty_ui, ringing_idx, snooze_count, settings, ring_cursor, cursor_idx
    if ringing_idx >= 0:
        if button in (BUTTON_UP, BUTTON_DOWN):
            ring_cursor = button == BUTTON_DOWN
            dirty_ui = True
            return
        if button == BUTTON_CENTER and ring_cursor == 1:
            button = BUTTON_O
    if ringing_idx in (-2, -3):
        if button in (BUTTON_CENTER, BUTTON_O, BUTTON_BACK, BUTTON_ESCAPE):
            current_mode = MODE_EGG if ringing_idx == -2 else MODE_COUNTDOWN; ringing_idx = -1; dirty_ui = True; handle_audio_silence()
    else:
        if button in (BUTTON_S, BUTTON_CENTER):
            if snooze_count < 5:
                alarm = settings['alarms'][ringing_idx]
                cancel_snooze(alarm)
                snooze_count += 1
                snoozes.append([alarm, _elapsed_ms() + settings['snooze_min'] * 60000, snooze_count])
            else:
                if 0 <= ringing_idx < len(settings["alarms"]) and not settings["alarms"][ringing_idx][8]: settings["alarms"][ringing_idx][5] = False; queue_save()
                cancel_snooze(settings["alarms"][ringing_idx])
                snooze_count = 0
            current_mode = MODE_MAIN; cursor_idx = 0; ringing_idx = -1; dirty_ui = True; handle_audio_silence()
        elif button in (BUTTON_O, BUTTON_BACK, BUTTON_ESCAPE):
            current_mode = MODE_MAIN
            cursor_idx = 0
            cancel_snooze(settings["alarms"][ringing_idx])
            if 0 <= ringing_idx < len(settings["alarms"]) and not settings["alarms"][ringing_idx][8]: settings["alarms"][ringing_idx][5] = False; queue_save()
            ringing_idx = -1; snooze_count = 0; dirty_ui = True; handle_audio_silence()

def handle_input_main(button, view_manager, t, c_sec):
    global current_mode, dirty_ui, show_help, show_options, cursor_idx, origin_mode, edit_idx, tmp_daily, tmp_y, tmp_mo, tmp_d, date_cursor, tmp_h, tmp_m, tmp_label, tmp_audible, settings
    cy, cmo, cd, ch, cm = t[0], t[1], t[2], t[3], t[4]
    if button in (BUTTON_BACK, BUTTON_ESCAPE):
        request_exit(view_manager); return
    elif button == BUTTON_H: show_help = True; dirty_ui = True
    elif button == BUTTON_O: show_options = True; dirty_ui = True
    elif button == BUTTON_M: current_mode = MODE_ALARMS; cursor_idx = 0; dirty_ui = True
    elif button == BUTTON_N:
        current_mode = MODE_EDIT_TYPE; origin_mode = MODE_MAIN; edit_idx = -1; tmp_daily = False; tmp_y = cy; tmp_mo = cmo; tmp_d = cd; date_cursor = 0; tmp_h = ch; tmp_m = cm; tmp_label = ""; tmp_audible = True; dirty_ui = True
    elif button == BUTTON_UP: cursor_idx = (cursor_idx - 1) % 7; dirty_ui = True
    elif button == BUTTON_DOWN: cursor_idx = (cursor_idx + 1) % 7; dirty_ui = True
    elif button == BUTTON_CENTER:
        if cursor_idx == 0: current_mode = MODE_ALARMS; cursor_idx = 0
        elif cursor_idx == 1: current_mode = MODE_EGG
        elif cursor_idx == 2: current_mode = MODE_STOPWATCH
        elif cursor_idx == 3: current_mode = MODE_COUNTDOWN
        elif cursor_idx == 4: show_options = True
        elif cursor_idx == 5: show_help = True
        elif cursor_idx == 6: request_exit(view_manager); return
        dirty_ui = True

def handle_input_egg_timer(button, view_manager, t, c_sec):
    global current_mode, dirty_ui, egg_preset, egg_end
    if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = MODE_MAIN; dirty_ui = True
    elif button == BUTTON_DOWN: egg_preset = (egg_preset + 1) % (len(_EGG_PRESETS) + 1); dirty_ui = True
    elif button == BUTTON_UP: egg_preset = (egg_preset - 1) % (len(_EGG_PRESETS) + 1); dirty_ui = True
    elif button == BUTTON_CENTER:
        if egg_preset == len(_EGG_PRESETS):
            current_mode = MODE_MAIN; dirty_ui = True; return
        m = _EGG_PRESETS[egg_preset][0]
        if m == 0: egg_end = 0
        else: egg_end = _elapsed_ms() + m * 60000
        dirty_ui = True

def handle_input_stopwatch(button, view_manager, t, c_sec):
    global current_mode, dirty_ui, sw_run, sw_accum, sw_start, sw_cursor
    if button == BUTTON_CENTER and sw_cursor == 2:
        button = BUTTON_BACK
    if button == BUTTON_CENTER and sw_cursor == 1:
        button = BUTTON_R
    if button in (BUTTON_UP, BUTTON_DOWN):
        sw_cursor = (sw_cursor + (1 if button == BUTTON_DOWN else -1)) % 3
        dirty_ui = True
    elif button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = MODE_MAIN; dirty_ui = True
    elif button == BUTTON_CENTER:
        if sw_run: sw_accum += time.ticks_diff(time.ticks_ms(), sw_start); sw_run = False
        else: sw_start = time.ticks_ms(); sw_run = True
        dirty_ui = True
    elif button == BUTTON_R: sw_accum = 0; sw_run = False; dirty_ui = True

def handle_input_countdown(button, view_manager, t, c_sec):
    global current_mode, dirty_ui, cd_end, cd_cursor, cd_h, cd_m, cd_s, cd_run_cursor
    if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = MODE_MAIN; dirty_ui = True
    elif cd_end == 0:
        if button == BUTTON_UP: cd_cursor = (cd_cursor - 1) % 5; dirty_ui = True
        elif button == BUTTON_DOWN: cd_cursor = (cd_cursor + 1) % 5; dirty_ui = True
        elif button == BUTTON_RIGHT:
            if cd_cursor == 0: cd_h = (cd_h + 1) % 100
            elif cd_cursor == 1: cd_m = (cd_m + 1) % 60
            elif cd_cursor == 2: cd_s = (cd_s + 1) % 60
            dirty_ui = True
        elif button == BUTTON_LEFT:
            if cd_cursor == 0: cd_h = (cd_h - 1) % 100
            elif cd_cursor == 1: cd_m = (cd_m - 1) % 60
            elif cd_cursor == 2: cd_s = (cd_s - 1) % 60
            dirty_ui = True
        elif button == BUTTON_CENTER:
            if cd_cursor == 4:
                current_mode = MODE_MAIN; dirty_ui = True; return
            total_s = cd_h * 3600 + cd_m * 60 + cd_s
            if total_s > 0: cd_end = _elapsed_ms() + total_s * 1000; dirty_ui = True
        elif button == BUTTON_R: cd_h = cd_m = cd_s = 0; dirty_ui = True
    else:
        if button in (BUTTON_UP, BUTTON_DOWN): cd_run_cursor = 1 - cd_run_cursor; dirty_ui = True
        elif button == BUTTON_CENTER and cd_run_cursor == 1: current_mode = MODE_MAIN; dirty_ui = True
        elif button in (BUTTON_CENTER, BUTTON_R): cd_end = 0; cd_run_cursor = 0; dirty_ui = True

def handle_input_alarms(button, view_manager, t, c_sec):
    global current_mode, dirty_ui, cursor_idx, settings, sys_time, msg_origin, clear_confirm_yes, del_confirm_yes, origin_mode, edit_idx, tmp_daily, tmp_y, tmp_mo, tmp_d, date_cursor, tmp_h, tmp_m, tmp_label, tmp_audible
    cy, cmo, cd, ch, cm = t[0], t[1], t[2], t[3], t[4]
    list_len = len(settings["alarms"]) + 3
    if button == BUTTON_CENTER:
        if cursor_idx == list_len - 1: button = BUTTON_BACK
        elif cursor_idx == list_len - 2: button = BUTTON_C
        elif cursor_idx < len(settings["alarms"]) and current_mode != MODE_ALARM_ACTIONS:
            current_mode = MODE_ALARM_ACTIONS; dirty_ui = True; return
    if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = MODE_MAIN; cursor_idx = 0; dirty_ui = True
    elif button == BUTTON_DOWN and cursor_idx < list_len - 1: cursor_idx += 1; dirty_ui = True
    elif button == BUTTON_UP and cursor_idx > 0: cursor_idx -= 1; dirty_ui = True
    elif button in (BUTTON_LEFT, BUTTON_RIGHT) and cursor_idx < len(settings["alarms"]):
        a = settings["alarms"][cursor_idx]
        if not a[5]:
            if not a[8] and time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) <= c_sec: current_mode = MODE_ERR_TIME; msg_origin = MODE_ALARMS; dirty_ui = True
            else: a[5] = True; queue_save(); dirty_ui = True
        else:
            a[5] = False
            cancel_snooze(a)
            queue_save(); dirty_ui = True
    elif button == BUTTON_T and cursor_idx < len(settings["alarms"]): settings["alarms"][cursor_idx][7] = not settings["alarms"][cursor_idx][7]; queue_save(); dirty_ui = True
    elif button == BUTTON_C:
        has_past = any(not a[8] and time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) < c_sec for a in settings["alarms"])
        if has_past: current_mode = MODE_CONFIRM_CLR; clear_confirm_yes = False; dirty_ui = True
    elif button == BUTTON_BACKSPACE and cursor_idx < len(settings["alarms"]): current_mode = MODE_CONFIRM_DEL; del_confirm_yes = False; dirty_ui = True
    elif button in (BUTTON_CENTER, BUTTON_N):
        current_mode = MODE_EDIT_TYPE; origin_mode = MODE_ALARMS; date_cursor = 0; dirty_ui = True
        if button == BUTTON_N or cursor_idx == len(settings["alarms"]):
            edit_idx = -1; tmp_daily = False; tmp_y = cy; tmp_mo = cmo; tmp_d = cd; tmp_h = ch; tmp_m = cm; tmp_label = ""; tmp_audible = True
        else:
            a = settings["alarms"][cursor_idx]; edit_idx = cursor_idx
            tmp_y = a[0]; tmp_mo = a[1]; tmp_d = a[2]; tmp_h = a[3]; tmp_m = a[4]; tmp_label = a[6]; tmp_audible = a[7]; tmp_daily = a[8]

def handle_input_alarm_actions(button, view_manager, t, c_sec):
    global current_mode, alarm_action_cursor, dirty_ui
    if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = MODE_ALARMS
    elif button in (BUTTON_UP, BUTTON_DOWN):
        alarm_action_cursor = (alarm_action_cursor + (1 if button == BUTTON_DOWN else -1)) % 4
    elif button in (BUTTON_LEFT, BUTTON_RIGHT) and alarm_action_cursor == 1:
        handle_input_alarms(BUTTON_T, view_manager, t, c_sec)
    elif button == BUTTON_CENTER:
        if alarm_action_cursor == 3: current_mode = MODE_ALARMS
        else: handle_input_alarms((BUTTON_CENTER, BUTTON_T, BUTTON_BACKSPACE)[alarm_action_cursor], view_manager, t, c_sec)
    dirty_ui = True


def handle_input_editor(button, view_manager, t, c_sec):
    global current_mode, dirty_ui, settings, origin_mode, msg_origin, tmp_daily, tmp_y, tmp_mo, tmp_d, date_cursor, tmp_h, tmp_m, tmp_label, tmp_audible, edit_idx, cursor_idx, sys_time
    global label_cursor, label_char, editor_action_cursor
    cy, cmo, cd, ch, cm = t[0], t[1], t[2], t[3], t[4]
    if current_mode in (MODE_EDIT_TYPE, MODE_EDIT_AUD):
        if button in (BUTTON_UP, BUTTON_DOWN):
            editor_action_cursor = 1 - editor_action_cursor
            dirty_ui = True
            return
        if button in (BUTTON_LEFT, BUTTON_RIGHT) and editor_action_cursor == 1:
            return
        if button == BUTTON_CENTER and editor_action_cursor == 1:
            current_mode = origin_mode
            editor_action_cursor = 0
            dirty_ui = True
            return
    if current_mode == MODE_EDIT_TYPE:
        if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = origin_mode; dirty_ui = True
        elif button in (BUTTON_LEFT, BUTTON_RIGHT): tmp_daily = not tmp_daily; dirty_ui = True
        elif button == BUTTON_CENTER: current_mode = MODE_EDIT_H if tmp_daily else MODE_EDIT_DATE; dirty_ui = True
    elif current_mode == MODE_EDIT_DATE:
        if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = MODE_EDIT_TYPE; dirty_ui = True
        elif button == BUTTON_UP: date_cursor = (date_cursor - 1) % 4; dirty_ui = True
        elif button == BUTTON_DOWN: date_cursor = (date_cursor + 1) % 4; dirty_ui = True
        elif button == BUTTON_RIGHT:
            if date_cursor == 0: tmp_y += 1 if settings["use_12h"] else 0; tmp_d = tmp_d + 1 if tmp_d < 31 and not settings["use_12h"] else (1 if not settings["use_12h"] else tmp_d)
            elif date_cursor == 1: tmp_mo = tmp_mo + 1 if tmp_mo < 12 else 1
            elif date_cursor == 2: tmp_d = tmp_d + 1 if tmp_d < 31 and settings["use_12h"] else (1 if settings["use_12h"] else tmp_d); tmp_y += 1 if not settings["use_12h"] else 0
            dirty_ui = True
        elif button == BUTTON_LEFT:
            if date_cursor == 0: tmp_y = max(2024, tmp_y - 1) if settings["use_12h"] else tmp_y; tmp_d = tmp_d - 1 if tmp_d > 1 and not settings["use_12h"] else (31 if not settings["use_12h"] else tmp_d)
            elif date_cursor == 1: tmp_mo = tmp_mo - 1 if tmp_mo > 1 else 12
            elif date_cursor == 2: tmp_d = tmp_d - 1 if tmp_d > 1 and settings["use_12h"] else (31 if settings["use_12h"] else tmp_d); tmp_y = max(2024, tmp_y - 1) if not settings["use_12h"] else tmp_y
            dirty_ui = True
        elif button == BUTTON_CENTER:
            if date_cursor == 3:
                current_mode = origin_mode; dirty_ui = True; return
            leap = 1 if (tmp_y % 4 == 0 and (tmp_y % 100 != 0 or tmp_y % 400 == 0)) else 0
            dim = [31, 28 + leap, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][tmp_mo - 1]
            if tmp_d > dim: current_mode = MODE_ERR_DATE; msg_origin = MODE_EDIT_DATE; dirty_ui = True; return
            if tmp_y < cy or (tmp_y == cy and tmp_mo < cmo) or (tmp_y == cy and tmp_mo == cmo and tmp_d < cd): current_mode = MODE_ERR_TIME; msg_origin = MODE_EDIT_DATE; dirty_ui = True; return
            current_mode = MODE_EDIT_H; dirty_ui = True
    elif current_mode == MODE_EDIT_H:
        if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = MODE_EDIT_TYPE if tmp_daily else MODE_EDIT_DATE; dirty_ui = True
        elif button in (BUTTON_UP, BUTTON_DOWN): current_mode = MODE_EDIT_M if button == BUTTON_DOWN else MODE_EDIT_CANCEL; dirty_ui = True
        elif button == BUTTON_LEFT: tmp_h = (tmp_h - 1) % 24; dirty_ui = True
        elif button == BUTTON_RIGHT: tmp_h = (tmp_h + 1) % 24; dirty_ui = True
        elif button == BUTTON_CENTER:
            if not tmp_daily and tmp_y == cy and tmp_mo == cmo and tmp_d == cd and tmp_h < ch: current_mode = MODE_ERR_TIME; msg_origin = MODE_EDIT_H; dirty_ui = True; return
            current_mode = MODE_EDIT_M; dirty_ui = True
    elif current_mode == MODE_EDIT_M:
        if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = MODE_EDIT_H; dirty_ui = True
        elif button in (BUTTON_UP, BUTTON_DOWN): current_mode = MODE_EDIT_H if button == BUTTON_UP else MODE_EDIT_CANCEL; dirty_ui = True
        elif button == BUTTON_LEFT: tmp_m = (tmp_m - 1) % 60; dirty_ui = True
        elif button == BUTTON_RIGHT: tmp_m = (tmp_m + 1) % 60; dirty_ui = True
        elif button == BUTTON_CENTER:
            if not tmp_daily and tmp_y == cy and tmp_mo == cmo and tmp_d == cd and tmp_h == ch and tmp_m <= cm: current_mode = MODE_ERR_TIME; msg_origin = MODE_EDIT_M; dirty_ui = True; return
            current_mode = MODE_EDIT_L; label_cursor = 3; dirty_ui = True
    elif current_mode == MODE_EDIT_CANCEL:
        if button == BUTTON_UP: current_mode = MODE_EDIT_M
        elif button == BUTTON_DOWN: current_mode = MODE_EDIT_H
        elif button in (BUTTON_CENTER, BUTTON_BACK, BUTTON_ESCAPE): current_mode = origin_mode
        dirty_ui = True
    elif current_mode == MODE_EDIT_L:
        if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = MODE_EDIT_M; dirty_ui = True
        elif button in (BUTTON_UP, BUTTON_DOWN): label_cursor = (label_cursor + (1 if button == BUTTON_DOWN else -1)) % 6; dirty_ui = True
        elif button in (BUTTON_LEFT, BUTTON_RIGHT): label_char = (label_char + (1 if button == BUTTON_RIGHT else -1)) % len(_LABEL_CHARS); dirty_ui = True
        elif button == BUTTON_CENTER:
            if label_cursor in (0, 1) and len(tmp_label) < 50: tmp_label += _LABEL_CHARS[label_char]
            elif label_cursor == 2: tmp_label = tmp_label[:-1]
            elif label_cursor == 3: current_mode = MODE_EDIT_AUD
            elif label_cursor == 4: current_mode = MODE_EDIT_M
            elif label_cursor == 5: current_mode = origin_mode
            dirty_ui = True
        elif button == BUTTON_BACKSPACE and len(tmp_label) > 0: tmp_label = tmp_label[:-1]; dirty_ui = True
        elif button == BUTTON_SPACE and len(tmp_label) < 50: tmp_label += " "; dirty_ui = True
        elif button >= BUTTON_A and button <= BUTTON_Z and len(tmp_label) < 50: tmp_label += chr(button - BUTTON_A + ord('A')); dirty_ui = True
        elif button >= BUTTON_0 and button <= BUTTON_9 and len(tmp_label) < 50: tmp_label += chr(button - BUTTON_0 + ord('0')); dirty_ui = True
    elif current_mode == MODE_EDIT_AUD:
        if button in (BUTTON_BACK, BUTTON_ESCAPE): current_mode = MODE_EDIT_L; dirty_ui = True
        elif button in (BUTTON_LEFT, BUTTON_RIGHT): tmp_audible = not tmp_audible; dirty_ui = True
        elif button == BUTTON_CENTER:
            final_lbl = tmp_label.strip() or "ALARM"
            if not tmp_daily and time.mktime((tmp_y, tmp_mo, tmp_d, tmp_h, tmp_m, 0, 0, 0)) <= c_sec: current_mode = MODE_ERR_TIME; msg_origin = MODE_EDIT_AUD; dirty_ui = True; return
            new_a = [tmp_y, tmp_mo, tmp_d, tmp_h, tmp_m, True, final_lbl, tmp_audible, tmp_daily]
            if edit_idx == -1: settings["alarms"].append(new_a)
            else:
                cancel_snooze(settings["alarms"][edit_idx])
                settings["alarms"][edit_idx] = new_a
            queue_save(); current_mode = origin_mode; dirty_ui = True
            if origin_mode == MODE_MAIN: cursor_idx = 0

INPUT_DISPATCH = {
    MODE_MAIN: handle_input_main,
    MODE_SAVE_ERROR: handle_input_save_error,
    MODE_EDIT_CANCEL: handle_input_editor,
    MODE_ALARM_ACTIONS: handle_input_alarm_actions,
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

class _Canvas:
    """Centered content area, with a safe rectangle inside round displays."""
    def __init__(self, raw):
        self.raw = raw
        width, height = int(raw.size.x), int(raw.size.y)
        from picoware.system.boards import BOARD_ID, BOARD_FLIPPER_ZERO, BOARD_WAVESHARE_1_28_RP2350, BOARD_WAVESHARE_1_43_RP2350
        self.mono = BOARD_ID == BOARD_FLIPPER_ZERO
        self.round = BOARD_ID in (BOARD_WAVESHARE_1_28_RP2350, BOARD_WAVESHARE_1_43_RP2350)
        if self.round:
            width = height = min(width, height) * 70 // 100
        # Keep the larger round display as readable as the 1.28: the same
        # compact layout with doubled bitmap pixels, rather than extra rows.
        self.scale = 2 if BOARD_ID == BOARD_WAVESHARE_1_43_RP2350 else 1
        self.size = Vector(min(640, width) // self.scale, min(600, height) // self.scale)
        self.x = (int(raw.size.x) - int(self.size.x) * self.scale) // 2
        self.y = (int(raw.size.y) - int(self.size.y) * self.scale) // 2

    def _color(self, color):
        if not self.mono:
            return color
        return 0 if color in (COLOR_BG, COLOR_SHADOW, COLOR_KEY, COLOR_LCD_DARK, COLOR_LCD_MID) else 0xFFFF

    def len(self, text, font=0):
        return self.raw.len(text, font)

    def text(self, pos, text, color, font=0):
        if self.scale == 1:
            self.raw.text(Vector(pos.x + self.x, pos.y + self.y), text, self._color(color), font)
            return
        from picoware.system.font import Font
        glyphs = Font()
        width, height = glyphs.get_width(font), glyphs.get_height(font)
        spacing = glyphs.get_spacing(font)
        stride = (width + 7) // 8
        x = int(pos.x)
        for char in text:
            data = glyphs.get_character(font, ord(char) if 32 <= ord(char) <= 126 else ord('?'))
            # Draw horizontal runs to avoid a framebuffer allocation and keep
            # the enlarged bitmap identical to the small display's font.
            for y in range(height):
                run = -1
                for col in range(width + 1):
                    lit = col < width and data[y * stride + col // 8] & (0x80 >> (col % 8))
                    if lit and run < 0:
                        run = col
                    elif not lit and run >= 0:
                        self.fill_rectangle(Vector(x + run, pos.y + y), Vector(col - run, 1), color)
                        run = -1
            x += width + spacing

    def fill_rectangle(self, pos, size, color):
        self.raw.fill_rectangle(Vector(pos.x * self.scale + self.x, pos.y * self.scale + self.y),
                                Vector(size.x * self.scale, size.y * self.scale), self._color(color))

    def rect(self, pos, size, color):
        if self.scale == 1:
            self.raw.rect(Vector(pos.x + self.x, pos.y + self.y), size, self._color(color))
            return
        self.fill_rectangle(pos, Vector(size.x, 1), color)
        self.fill_rectangle(Vector(pos.x, pos.y + size.y - 1), Vector(size.x, 1), color)
        self.fill_rectangle(pos, Vector(1, size.y), color)
        self.fill_rectangle(Vector(pos.x + size.x - 1, pos.y), Vector(1, size.y), color)


def _font_height(font):
    return (8, 12, 16, 20, 24)[font]


def _fit(draw, text, width, font=FONT_SMALL):
    text = str(text)
    while font > 0 and draw.len(text, font) > width:
        font -= 1
    if draw.len(text, font) > width:
        while text and draw.len(text + '..', font) > width:
            text = text[:-1]
        text += '..'
    return text, font


def _text(draw, x, y, text, color=COLOR_MUTED, font=FONT_SMALL, width=None):
    width = int(draw.size.x) - x - 4 if width is None else width
    text, font = _fit(draw, text, max(1, width), font)
    draw.text(Vector(x, y), text, color, font)


def _wrap(draw, text, width, font=0):
    lines, line = [], ''
    for char in text:
        if char == '\n' or (line and draw.len(line + char, font) > width):
            lines.append(line)
            line = ''
        if char != '\n':
            line += char
    lines.append(line)
    return lines


# Touch targets use the same logical coordinates as the responsive canvas.
_touch_enabled = False
_touch_held = False
_touch_targets = []
_touch_context = None


def _touch_selection():
    if show_options: return 'options_cursor_idx'
    return {
        MODE_MAIN: 'cursor_idx', MODE_ALARMS: 'cursor_idx',
        MODE_EGG: 'egg_preset', MODE_STOPWATCH: 'sw_cursor',
        MODE_COUNTDOWN: 'cd_run_cursor' if cd_end else 'cd_cursor',
        MODE_ALARM_ACTIONS: 'alarm_action_cursor', MODE_EDIT_DATE: 'date_cursor',
        MODE_EDIT_L: 'label_cursor', MODE_EDIT_TYPE: 'editor_action_cursor',
        MODE_EDIT_AUD: 'editor_action_cursor', MODE_RING: 'ring_cursor',
        MODE_SAVE_ERROR: 'exit_cursor', MODE_CONFIRM_DEL: 'del_confirm_yes',
        MODE_CONFIRM_CLR: 'clear_confirm_yes',
    }.get(current_mode)


def _touch_row(index, vm, t, c_sec):
    global current_mode, dirty_ui
    if not show_options and current_mode in (MODE_EDIT_H, MODE_EDIT_M, MODE_EDIT_CANCEL):
        current_mode = (MODE_EDIT_H, MODE_EDIT_M, MODE_EDIT_CANCEL)[index]
        if index == 2: process_input(BUTTON_CENTER, vm, t, c_sec)
    else:
        selection = _touch_selection()
        if selection: globals()[selection] = index
        # Editable fields select first; the visible -/+ controls change values.
        adjustable = (show_options and index < 3) or (not show_options and (
            (current_mode == MODE_COUNTDOWN and not cd_end and index < 3) or
            (current_mode == MODE_EDIT_DATE and index < 3) or
            (current_mode == MODE_EDIT_L and index == 0)))
        if not adjustable: process_input(BUTTON_CENTER, vm, t, c_sec)
    dirty_ui = True


def _handle_touch(vm, t, c_sec):
    global _touch_held
    inp = getattr(vm, 'input_manager', None)
    if inp is None: return False
    point, gesture = inp.point, inp.gesture
    down = getattr(inp, 'touch_down', False)
    if point == (0, 0):
        if not down: _touch_held = False
        return down
    if gesture:
        from waveshare_touch import TOUCH_GESTURE_CLICK
        if gesture != TOUCH_GESTURE_CLICK:
            inp.reset()
            return True
    if _touch_held:
        inp.reset()
        return True
    _touch_held = True
    inp.reset()
    # A timer can replace the screen with an alarm before this input is handled.
    if _touch_context != (current_mode, show_help, show_options): return True
    canvas = _Canvas(vm.draw)
    x, y = (point[0] - canvas.x) // canvas.scale, (point[1] - canvas.y) // canvas.scale
    for left, top, width, height, kind, value in _touch_targets:
        if left <= x < left + width and top <= y < top + height:
            if kind == 'row': _touch_row(value, vm, t, c_sec)
            else: process_input(value, vm, t, c_sec)
            break
    return True


def _geometry(draw, panel=True):
    w, h = int(draw.size.x), int(draw.size.y)
    tiny = h < 100
    top = 13 if tiny else (22 if h < 240 else 30)
    footer = 54 if _touch_enabled else (10 if tiny else 25)
    bottom = h - footer - 3
    margin = 3 if tiny else 8
    if not panel:
        return None, (margin, top, w - margin * 2, bottom - top)
    if not tiny and w > h * 3 // 2 and h < 240:
        pw = max(80, (w - 24) * 46 // 100)
        return (margin, top, pw, bottom - top), (margin + pw + 8, top, w - pw - margin * 2 - 8, bottom - top)
    ph = 15 if tiny else min(110, max(42, (bottom - top) * 34 // 100))
    return (margin, top, w - margin * 2, ph), (margin, top + ph + (3 if tiny else 10), w - margin * 2, bottom - top - ph - (3 if tiny else 10))


def _header(draw, title, accent, status=''):
    w, h = int(draw.size.x), int(draw.size.y)
    tiny = h < 100
    y = 1 if tiny else 5
    font = 0 if h < 240 or w < 200 else (2 if w >= 400 else 1)
    reserve = draw.len(status, 0) + 8 if status else 10
    _text(draw, 4 if tiny else 8, y, title, TFT_WHITE, font, w - reserve - 16)
    if status:
        _text(draw, w - draw.len(status, 0) - 4, y + 1, status, accent, 0)
    else:
        draw.fill_rectangle(Vector(w - 8, y + 2), Vector(3, 3), accent)
    top = _geometry(draw, False)[1][1]
    draw.fill_rectangle(Vector(3, top - 3), Vector(w - 6, 1), COLOR_EDGE)


def _footer(draw, first, second=''):
    h = int(draw.size.y)
    if _touch_enabled:
        width = int(draw.size.x)
        labels = ('Back', 'Up', 'Down', '-', '+', 'OK')
        buttons = (BUTTON_BACK, BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_CENTER)
        for i, (label, button) in enumerate(zip(labels, buttons)):
            x = 3 + (width - 6) * (i % 3) // 3
            right = 3 + (width - 6) * (i % 3 + 1) // 3
            y = h - 53 + (i // 3) * 26
            w = right - x - 2
            draw.fill_rectangle(Vector(x, y), Vector(w, 24), COLOR_KEY)
            draw.rect(Vector(x, y), Vector(w, 24), COLOR_EDGE)
            draw.text(Vector(x + (w - draw.len(label, 0)) // 2, y + 8), label, TFT_WHITE, 0)
            _touch_targets.append((x, y, w, 24, 'button', button))
        return
    y = h - (10 if h < 100 else 25)
    if h >= 100:
        draw.fill_rectangle(Vector(3, y), Vector(int(draw.size.x) - 6, 1), COLOR_EDGE)
        y += 4
    _text(draw, 4, y, first, COLOR_MUTED, 0)
    if h >= 100:
        _text(draw, 4, y + 11, second, COLOR_MUTED, 0)


def _panel(draw, box, title, value, detail='', preferred=3, flash=False):
    x, y, w, h = box
    draw.fill_rectangle(Vector(x, y), Vector(w, h), COLOR_EDGE)
    draw.fill_rectangle(Vector(x + 1, y + 1), Vector(w - 2, h - 2), COLOR_LCD)
    if h < 28:
        text, font = _fit(draw, value, w - 8, 0)
        draw.text(Vector(x + (w - draw.len(text, font)) // 2, y + (h - 8) // 2), text, COLOR_LCD_DARK, font)
        return
    _text(draw, x + 5, y + 5, title, COLOR_LCD_MID, 0, w - 10)
    font = min(preferred, 4)
    available = h - 23 - (12 if detail and h >= 55 else 0)
    while font > 0 and _font_height(font) > available:
        font -= 1
    text, font = _fit(draw, value, w - 12, font)
    value_y = y + 17 + max(0, (available - _font_height(font)) // 2)
    draw.text(Vector(x + (w - draw.len(text, font)) // 2, value_y), text, COLOR_LCD_DARK, font)
    if detail and h >= 55:
        _text(draw, x + 5, y + h - 12, detail, COLOR_LCD_MID, 0, w - 10)
    if flash:
        draw.rect(Vector(x, y), Vector(w, h), _THEMES[settings['theme_idx']][1])


def _rows(draw, box, rows, selected, accent):
    x, y, w, h = box
    gap = 2 if h < 70 else 4
    minimum = 13 if int(draw.size.y) < 160 else 22
    capacity = max(1, (h + gap) // (minimum + gap))
    count = min(len(rows), capacity)
    row_h = min(36 if int(draw.size.y) >= 400 else 28, (h - gap * (count - 1)) // count)
    start = selected // capacity * capacity
    for visible, idx in enumerate(range(start, min(len(rows), start + count))):
        label, badge = rows[idx]
        ry = y + visible * (row_h + gap)
        if _touch_enabled:
            _touch_targets.append((x, ry, w, row_h, 'row', idx))
        draw.fill_rectangle(Vector(x, ry), Vector(w, row_h), COLOR_KEY)
        draw.fill_rectangle(Vector(x + 1, ry + 1), Vector(w - 2, 1), COLOR_KEY_TOP)
        if idx == selected:
            draw.rect(Vector(x, ry), Vector(w, row_h), accent)
        font = 0 if row_h < 18 or w < (140 if draw.round else 150) else (2 if row_h >= 30 and w >= 400 else 1)
        badge, badge_font = _fit(draw, badge, max(20, w // 2 - 6), 0)
        badge_w = draw.len(badge, badge_font) if badge else 0
        label, font = _fit(draw, label, w - badge_w - (14 if badge else 10), font)
        draw.text(Vector(x + 5, ry + (row_h - _font_height(font)) // 2), label, TFT_WHITE, font)
        if badge:
            draw.text(Vector(x + w - badge_w - 5, ry + (row_h - 8) // 2), badge, accent if idx == selected else COLOR_MUTED, badge_font)


def _clock_text(hour, minute, second=None):
    shown_hour = (hour % 12 or 12) if settings['use_12h'] else hour
    value = '%02d:%02d' % (shown_hour, minute)
    if second is not None:
        value += ':%02d' % second
    if settings['use_12h']:
        value += ' AM' if hour < 12 else ' PM'
    return value


def _next_alarm_text():
    now = time.time()
    today = time.localtime(now)
    nearest, label = None, 'None scheduled'
    for a in settings['alarms']:
        if not a[5]:
            continue
        date = today[:3] if a[8] else a[:3]
        due = time.mktime((date[0], date[1], date[2], a[3], a[4], 0, 0, 0))
        if a[8] and due <= now:
            due += 86400
        if due > now and (nearest is None or due < nearest):
            nearest, label = due, _clock_text(a[3], a[4]) + ' ' + a[6]
    elapsed = _elapsed_ms()
    for alarm, deadline, count in snoozes:
        if not any(record is alarm and record[5] for record in settings['alarms']):
            continue
        due = now + max(0, (deadline - elapsed + 999) // 1000)
        if nearest is None or due < nearest:
            nearest = due
            t = time.localtime(due)
            label = _clock_text(t[3], t[4]) + ' SNOOZED'
    return label


def draw_main(vm, draw, w, h, accent, bg):
    _header(draw, 'Eggtimer', accent, '%d/7' % (cursor_idx + 1))
    panel, rows = _geometry(draw)
    t = time.localtime()
    _panel(draw, panel, 'LOCAL TIME', _clock_text(t[3], t[4], t[5]), 'NEXT ' + _next_alarm_text())
    _rows(draw, rows, (('Alarms', str(len(settings['alarms']))), ('Egg timer', 'RUN' if egg_end else ''),
          ('Stopwatch', 'RUN' if sw_run else ''), ('Countdown', 'RUN' if cd_end else ''),
          ('Options', ''), ('Help', ''), ('Exit', '')), cursor_idx, accent)
    _footer(draw, 'U/D select  OK open', 'BACK exit  M alarms')


def draw_egg_timer(vm, draw, w, h, accent, bg):
    _header(draw, 'EGG TIMER', accent, '%d/6' % (egg_preset + 1))
    panel, rows = _geometry(draw)
    rem = max(0, (egg_end - _elapsed_ms() + 999) // 1000) if egg_end else 0
    _panel(draw, panel, 'REMAINING' if egg_end else 'READY', '%02d:%02d' % divmod(rem, 60))
    items = [(label, '') for _, label in _EGG_PRESETS] + [('Back', '')]
    _rows(draw, rows, items, egg_preset, accent)
    _footer(draw, 'U/D select  OK apply', 'BACK menu')


def draw_stopwatch(vm, draw, w, h, accent, bg):
    _header(draw, 'STOPWATCH', accent, '%d/3' % (sw_cursor + 1))
    panel, rows = _geometry(draw)
    elapsed = sw_accum + (time.ticks_diff(time.ticks_ms(), sw_start) if sw_run else 0)
    seconds = elapsed // 1000
    value = '%02d:%02d:%02d' % (seconds // 3600, seconds // 60 % 60, seconds % 60)
    _panel(draw, panel, 'RUNNING' if sw_run else 'STOPPED', value, '.%d SEC' % (elapsed % 1000 // 100), 4)
    _rows(draw, rows, (('Pause' if sw_run else 'Start / Resume', ''), ('Reset', 'R'), ('Back', '')), sw_cursor, accent)
    _footer(draw, 'U/D select  OK act', 'R reset  BACK menu')


def draw_countdown(vm, draw, w, h, accent, bg):
    _header(draw, 'COUNTDOWN', accent, '%d/5' % (cd_cursor + 1) if not cd_end else '')
    panel, rows = _geometry(draw)
    remaining = max(0, (cd_end - _elapsed_ms() + 999) // 1000) if cd_end else cd_h * 3600 + cd_m * 60 + cd_s
    _panel(draw, panel, 'REMAINING' if cd_end else 'SET DURATION', '%02d:%02d:%02d' % (remaining // 3600, remaining // 60 % 60, remaining % 60), preferred=4)
    if cd_end:
        _rows(draw, rows, (('Cancel', 'OK / R'), ('Back', '')), cd_run_cursor, accent)
        _footer(draw, 'U/D select  OK act', 'BACK menu')
    else:
        items = []
        for i, label in enumerate(('Hours', 'Minutes', 'Seconds')):
            value = '%02d' % (cd_h, cd_m, cd_s)[i]
            items.append((label, '< ' + value + ' >' if cd_cursor == i else value))
        items += [('Start', 'OK'), ('Back', '')]
        _rows(draw, rows, items, cd_cursor, accent)
        _footer(draw, 'U/D field  L/R value', 'OK start  BACK menu')


def _alarm_rows():
    return [(a[6], ('< ON >' if a[5] else '< OFF >') if i == cursor_idx else ('ON' if a[5] else 'OFF'))
            for i, a in enumerate(settings['alarms'])] + [('+ New alarm', ''), ('Clear past', ''), ('Back', '')]


def draw_alarms(vm, draw, w, h, accent, bg):
    _header(draw, 'ALARMS', accent, '%d/%d' % (cursor_idx + 1, len(settings['alarms']) + 3))
    panel, rows = _geometry(draw)
    if cursor_idx < len(settings['alarms']):
        a = settings['alarms'][cursor_idx]
        date = 'DAILY' if a[8] else '%02d.%02d.%04d' % (a[2], a[1], a[0])
        _panel(draw, panel, date, _clock_text(a[3], a[4]), a[6], 2)
    else:
        _panel(draw, panel, 'ALARMS', str(len(settings['alarms'])) + ' SAVED')
    _rows(draw, rows, _alarm_rows(), cursor_idx, accent)
    _footer(draw, 'U/D select  OK menu', 'L/R on/off  BACK menu')


def draw_alarm_actions(vm, draw, w, h, accent, bg):
    a = settings['alarms'][cursor_idx]
    _header(draw, 'ALARM ACTIONS', accent, '%d/4' % (alarm_action_cursor + 1))
    panel, rows = _geometry(draw)
    _panel(draw, panel, a[6], _clock_text(a[3], a[4]), 'DAILY' if a[8] else '%02d.%02d.%04d' % (a[2], a[1], a[0]))
    _rows(draw, rows, (('Edit', ''), ('Sound', '< ON >' if a[7] else '< OFF >'), ('Delete', ''), ('Back', '')), alarm_action_cursor, accent)
    _footer(draw, 'U/D select  OK act', 'L/R sound  BACK list')


def _editor_value():
    if current_mode == MODE_EDIT_TYPE:
        return 'ALARM TYPE:', '< DAILY >' if tmp_daily else '< SPECIFIC DATE >'
    if current_mode == MODE_EDIT_DATE:
        names = ('Year', 'Month', 'Day') if settings['use_12h'] else ('Day', 'Month', 'Year')
        parts = ['%04d' % tmp_y, '%02d' % tmp_mo, '%02d' % tmp_d] if settings['use_12h'] else ['%02d' % tmp_d, '%02d' % tmp_mo, '%04d' % tmp_y]
        return (names[date_cursor].upper() if date_cursor < 3 else "CANCEL"), ' '.join(parts)
    if current_mode in (MODE_EDIT_H, MODE_EDIT_M, MODE_EDIT_CANCEL):
        return ('CANCEL' if current_mode == MODE_EDIT_CANCEL else ('HOUR' if current_mode == MODE_EDIT_H else 'MINUTE')), _clock_text(tmp_h, tmp_m)
    if current_mode == MODE_EDIT_L:
        return 'LABEL %d/50' % len(tmp_label), tmp_label or 'ALARM'
    return 'AUDIBLE SOUND', '< ON >' if tmp_audible else '< SILENT >'


def draw_editor(vm, draw, w, h, accent, bg):
    title, value = _editor_value()
    _header(draw, 'NEW ALARM' if edit_idx == -1 else 'EDIT ALARM', accent)
    panel, rows = _geometry(draw)
    if current_mode == MODE_EDIT_L:
        # Show the insertion end on small panels; the whole label wraps in Help-sized views.
        shown = value
        while shown and draw.len(shown + '_', 0) > panel[2] - 12:
            shown = shown[1:]
        _panel(draw, panel, title, shown + '_', preferred=1)
        items = [('Character', '< ' + _LABEL_CHARS[label_char] + ' >'), ('Add character', ''), ('Erase last', ''), ('Continue', ''), ('Back', ''), ('Cancel', '')]
        selected = label_cursor
    elif current_mode == MODE_EDIT_DATE:
        names = ('Year', 'Month', 'Day') if settings['use_12h'] else ('Day', 'Month', 'Year')
        values = (tmp_y, tmp_mo, tmp_d) if settings['use_12h'] else (tmp_d, tmp_mo, tmp_y)
        items = [(names[i], '< %d >' % values[i] if date_cursor == i else str(values[i])) for i in range(3)] + [('Cancel', '')]
        _panel(draw, panel, title, value, preferred=2)
        selected = date_cursor
    elif current_mode in (MODE_EDIT_H, MODE_EDIT_M, MODE_EDIT_CANCEL):
        selected = (MODE_EDIT_H, MODE_EDIT_M, MODE_EDIT_CANCEL).index(current_mode)
        items = [('Hours', '< %02d >' % tmp_h if selected == 0 else '%02d' % tmp_h), ('Minutes', '< %02d >' % tmp_m if selected == 1 else '%02d' % tmp_m), ('Cancel', '')]
        _panel(draw, panel, title, value, preferred=3)
    else:
        _panel(draw, panel, title, value, preferred=2)
        items, selected = [('Save' if current_mode == MODE_EDIT_AUD else 'Continue', 'OK'), ('Cancel', '')], editor_action_cursor
    _rows(draw, rows, items, selected, accent)
    _footer(draw, 'U/D field L/R value', 'OK next  BACK cancel')


def draw_modals(vm, draw, w, h, accent, bg):
    error = current_mode in (MODE_ERR_DATE, MODE_ERR_TIME)
    _header(draw, 'CHECK INPUT' if error else 'CONFIRM', COLOR_ERROR if error else accent)
    panel, rows = _geometry(draw)
    if error:
        _panel(draw, panel, 'ERROR', 'INVALID DATE' if current_mode == MODE_ERR_DATE else 'INVALID TIME', 'Choose a valid future time.', 1)
        _rows(draw, rows, [('Return', 'OK')], 0, accent)
    else:
        deleting = current_mode == MODE_CONFIRM_DEL
        _panel(draw, panel, 'DELETE?' if deleting else 'CLEAR PAST?', settings['alarms'][cursor_idx][6] if deleting else 'Past alarms', preferred=1)
        selected = int(del_confirm_yes if deleting else clear_confirm_yes)
        _rows(draw, rows, [('No / Keep', ''), ('Yes / Delete', '')], selected, accent)
    _footer(draw, 'U/D select OK act', 'BACK cancel')


def draw_ring(vm, draw, w, h, accent, bg):
    _header(draw, 'ALARM!', accent)
    panel, rows = _geometry(draw)
    label = 'EGG READY!' if ringing_idx == -2 else ("TIME'S UP!" if ringing_idx == -3 else settings['alarms'][ringing_idx][6])
    _panel(draw, panel, 'ALARM', label, preferred=3, flash=ring_flash)
    items = [('Dismiss', 'OK')] if ringing_idx < 0 else [('Snooze' if snooze_count < 5 else 'Dismiss', 'S'), ('Dismiss', 'O')]
    _rows(draw, rows, items, 0 if ringing_idx < 0 else ring_cursor, accent)
    _footer(draw, 'U/D select OK act', 'BACK dismiss')


def draw_save_error(vm, draw, w, h, accent, bg):
    _header(draw, 'NOT SAVED', COLOR_ERROR)
    panel, rows = _geometry(draw)
    _panel(draw, panel, 'STORAGE UNAVAILABLE', 'SAVE FAILED', 'Changes remain in memory.', 1)
    _rows(draw, rows, [('Retry save / Exit', ''), ('Keep editing', ''), ('Discard / Exit', '')], exit_cursor, accent)
    _footer(draw, 'U/D select OK act', 'BACK keep editing')


def draw_options(draw, accent):
    _header(draw, 'OPTIONS', accent, '%d/4' % (options_cursor_idx + 1))
    _, box = _geometry(draw, False)
    rows = [('Accent', _THEMES[settings['theme_idx']][0]), ('Clock', '12 HOUR' if settings['use_12h'] else '24 HOUR'), ('Snooze', '%d MIN' % settings['snooze_min']), ('Back', '')]
    if options_cursor_idx < 3:
        label, value = rows[options_cursor_idx]
        rows[options_cursor_idx] = (label, '< ' + value + ' >')
    _rows(draw, box, rows, options_cursor_idx, accent)
    _footer(draw, 'U/D select L/R value', 'OK / BACK close')


def draw_help(draw, accent):
    global help_scroll
    _, box = _geometry(draw, False)
    lines = []
    for line in get_help_lines():
        lines.extend(_wrap(draw, line, box[2], 0))
    capacity = max(1, box[3] // 11)
    help_scroll = min(help_scroll, max(0, len(lines) - capacity))
    _header(draw, 'HELP', accent, '%d/%d' % (help_scroll + 1, len(lines)))
    for i, line in enumerate(lines[help_scroll:help_scroll + capacity]):
        _text(draw, box[0], box[1] + i * 11, line, COLOR_MUTED, 0, box[2])
    _footer(draw, 'U/D scroll OK close', 'BACK close')


VIEW_DISPATCH = {
    MODE_MAIN: draw_main,
    MODE_SAVE_ERROR: draw_save_error,
    MODE_EDIT_CANCEL: draw_editor,
    MODE_ALARM_ACTIONS: draw_alarm_actions,
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

def process_input(button, view_manager, t, c_sec):
    global show_help, show_options, help_scroll, current_mode, dirty_ui, options_cursor_idx, settings, editor_action_cursor, cursor_idx
    if show_help:
        if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_H, BUTTON_CENTER):
            show_help = False; help_scroll = 0; dirty_ui = True
        elif button == BUTTON_DOWN: help_scroll += 1; dirty_ui = True
        elif button == BUTTON_UP: help_scroll = max(0, help_scroll - 1); dirty_ui = True
        return
    elif show_options:
        if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER):
            show_options = False; dirty_ui = True; queue_save()
        elif button == BUTTON_DOWN: options_cursor_idx = (options_cursor_idx + 1) % 4; dirty_ui = True
        elif button == BUTTON_UP: options_cursor_idx = (options_cursor_idx - 1) % 4; dirty_ui = True
        elif button in (BUTTON_LEFT, BUTTON_RIGHT):
            delta = 1 if button == BUTTON_RIGHT else -1
            if options_cursor_idx == 0:
                settings["theme_idx"] = (settings["theme_idx"] + delta) % len(_THEMES)
            elif options_cursor_idx == 1:
                settings["use_12h"] = not settings["use_12h"]
            elif options_cursor_idx == 2:
                settings["snooze_min"] = (settings["snooze_min"] - 1 + delta) % 60 + 1
            dirty_ui = True
            queue_save()
        return

    handler = INPUT_DISPATCH.get(current_mode)
    previous_mode = current_mode
    if handler: handler(button, view_manager, t, c_sec)
    if current_mode != previous_mode and current_mode in (MODE_EDIT_TYPE, MODE_EDIT_AUD):
        editor_action_cursor = 0
    if current_mode == MODE_MAIN and previous_mode != MODE_MAIN:
        cursor_idx = 0

def draw_view(view_manager):
    global dirty_ui, _touch_context
    _touch_targets.clear()
    _touch_context = (current_mode, show_help, show_options)
    raw = view_manager.draw
    draw = _Canvas(raw)
    bg = COLOR_BG
    accent = _THEMES[settings['theme_idx']][1]
    raw.clear()
    raw.fill_rectangle(Vector(0, 0), raw.size, draw._color(bg))
    if show_help:
        draw_help(draw, accent)
    elif show_options:
        draw_options(draw, accent)
    else:
        VIEW_DISPATCH[current_mode](view_manager, draw, draw.size.x, draw.size.y, accent, bg)
    raw.swap()
    dirty_ui = False

# Define the start function that executes when the app is launched
def start(view_manager):
# Declare standard global variables needed for UI overlays and storage
    global storage, show_help, show_options, alarm_audio, alarm_note, alarm_audio_active
    global _touch_enabled, _touch_held, _touch_context
    from picoware.system.boards import BOARD_HAS_TOUCH, BOARD_ID, BOARD_CROWPANEL_WATCH_2_01
    _touch_enabled = bool(BOARD_HAS_TOUCH) or BOARD_ID == BOARD_CROWPANEL_WATCH_2_01
    _touch_held = False
    _touch_context = None
    _touch_targets.clear()
    # Declare global state variables needed to boot the main loop, including the new cursor
    global settings, current_mode, dirty_ui, last_s, cd_cursor, last_alarm_check, sw_cursor, ring_cursor
    
    global cd_run_cursor, alarm_action_cursor, label_cursor, label_char, editor_action_cursor, exit_cursor
    global _home_manager, _previous_home_handler, _exit_to_home
    if hasattr(view_manager, 'home_handler'):
        if view_manager.home_handler is not _before_home:
            _previous_home_handler = view_manager.home_handler
        _home_manager = view_manager
        view_manager.home_handler = _before_home
    _exit_to_home = False
    cd_run_cursor = alarm_action_cursor = label_char = 0
    label_cursor = 3
    editor_action_cursor = exit_cursor = 0

    # Re-initialize the lightweight settings dictionary fresh on boot
    settings = {
        "style_version": 1, "theme_idx": 0,
        "use_12h": False, "snooze_min": 5, "alarms": []
    }

    # Ensure the help overlay is hidden when the app opens
    show_help = False
    # Ensure the options menu is hidden when the app opens
    show_options = False
    # Bind the Picoware storage API reference to our global variable
    storage = view_manager.storage
    alarm_audio = alarm_note = None
    alarm_audio_active = False
    try:
        alarm_audio = view_manager.audio
        if alarm_audio is not None:
            from picoware.system.audio import AudioNote
            alarm_note = AudioNote(1000, 1000, 100)
    except Exception:
        # Audio is optional; the visual alarm must still work.
        alarm_audio = alarm_note = None
    
    # Read the JSON file from the SD card and populate the settings dictionary
    validate_and_load_settings()
    
    current_mode = MODE_MAIN

    # Flag the UI as dirty so the screen immediately renders on tick 1
    dirty_ui = True
    # Reset the last second tracker so the clock logic fires immediately
    last_s = -1
    last_alarm_check = None
    pending_alarms.clear()
    alarm_occurrences.clear()
    snoozes.clear()
    # Reset the countdown cursor to the first slot so it is fresh on boot
    cd_cursor = sw_cursor = ring_cursor = 0
    # Return True to signal to the OS that the app started successfully
    return True

def run(view_manager):
    global settings, dirty_ui, dirty_save, save_timer, sys_time
    
    draw = view_manager.draw; button = view_manager.button
    c_sec = time.time(); t = time.localtime(c_sec)
    
    check_time_and_alarms(t, c_sec)
    
    if _touch_enabled and _handle_touch(view_manager, t, c_sec): button = -1
    if settings is None: return
    if button == -1 and not dirty_ui and not dirty_save: return
    if button != -1: process_input(button, view_manager, t, c_sec)
    
    if settings is None: return
    
    if dirty_save and button == -1:
        if save_timer > 0: 
            save_timer -= 1
        else: 
            save_settings()

    if dirty_ui: draw_view(view_manager)

def stop(view_manager): # Function to halt the app and return memory to the Picoware OS
    # 1. System and Settings
    global settings, storage, _cached_help_lines, _last_saved_json # Add the new JSON cache string to globals
    # 2. Large Static Dispatchers and Hardware
    global alarm_audio, alarm_note
    # 3. Volatile Strings and Memory
    global tmp_label # Global strings
    # 4. Timers and Accumulators
    global sw_run, sw_start, sw_accum, last_sw_ms, egg_end, cd_end # Global timers
    global cd_h, cd_m, cd_s, egg_preset # Global presets
    # 5. UI Cursors and Trackers
    global show_help, show_options, help_scroll, current_mode, origin_mode, msg_origin # Global modes
    global dirty_ui, dirty_save, save_timer, cursor_idx, options_cursor_idx, date_cursor, cd_cursor, sw_cursor, ring_cursor # Global cursors
    global last_s, last_alarm_check, ringing_idx, ring_flash, snooze_count, edit_idx # Global trackers
    global tmp_daily, tmp_y, tmp_mo, tmp_d, tmp_h, tmp_m, tmp_audible, del_confirm_yes, clear_confirm_yes # Editor globals
    
    global _home_manager, _previous_home_handler
    saved = save_settings()
    handle_audio_silence() # Stop our alarm on the shared audio device
    
    # The framework may force-stop a view; never leave its Home hook attached.
    # User-initiated Home exits are guarded before stop is called.
    if _home_manager is not None and getattr(_home_manager, 'home_handler', None) is _before_home:
        _home_manager.home_handler = _previous_home_handler
    _home_manager = _previous_home_handler = None
    if not saved:
        return False

    if settings is not None: settings.clear() # Empty the settings dictionary
    settings = None # Destroy the settings reference
    storage = None # Destroy the storage reference
    
    _cached_help_lines = [] # Empty the help screen string cache
    _last_saved_json = "" # Empty the SD card delta-save cache to free the JSON string from RAM
    tmp_label = "" # Empty the temporary editor label
    
    sw_start = sw_accum = last_sw_ms = egg_end = cd_end = 0 # Zero out timer integer variables
    cd_h = cd_m = cd_s = save_timer = help_scroll = 0 # Zero out countdown and scroll integer variables
    cursor_idx = options_cursor_idx = date_cursor = cd_cursor = sw_cursor = ring_cursor = 0 # Zero out all navigation cursors
    current_mode = origin_mode = msg_origin = 0 # Return to the default main mode integer
    last_alarm_check = None
    pending_alarms.clear()
    alarm_occurrences.clear()
    snoozes.clear()
    last_s = ringing_idx = edit_idx = -1 # Reset special index trackers
    snooze_count = 0 # Reset snooze integer
    egg_preset = 1 # Reset the egg timer preset integer
    tmp_y = 2026; tmp_mo = 1; tmp_d = 1; tmp_h = 12; tmp_m = 0 # Reset the temporary editor date and time variables
    
    sw_run = dirty_ui = dirty_save = ring_flash = show_help = show_options = False # Reset UI and state booleans to False
    tmp_daily = del_confirm_yes = clear_confirm_yes = False # Reset modal and editor booleans to False
    tmp_audible = True # Reset audio toggle to its default True state
    
    # AppLoader can cache this module across exits. Keep immutable presets and
    # dispatch tables available for start(); unloading the module releases them.
    alarm_audio = None # Release our reference, not the shared device
    alarm_note = None
    
    gc.collect() # Force a deep garbage collection sweep using the global gc import
