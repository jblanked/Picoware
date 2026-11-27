import json
import gc
import os
from math import isfinite
from utime import ticks_ms, ticks_add, ticks_diff
from picoware.system.boards import BOARD_HAS_KEYBOARD, BOARD_HAS_TOUCH, BOARD_ID, BOARD_DESKTOP, BOARD_CROWPANEL_WATCH_2_01

from picoware.system.system import System
from picoware.system.vector import Vector
from picoware.system.font import FONT_XTRA_SMALL, FONT_SMALL, FONT_MEDIUM
from picoware.system.colors import TFT_WHITE, TFT_BLACK

from picoware.system.buttons import (
    BUTTON_BACK, BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_CENTER,
    BUTTON_0, BUTTON_1, BUTTON_2, BUTTON_3, BUTTON_4, 
    BUTTON_5, BUTTON_6, BUTTON_7, BUTTON_8, BUTTON_9,
    BUTTON_PERIOD, BUTTON_BACKSPACE,
    BUTTON_C, BUTTON_F, BUTTON_T, BUTTON_R, BUTTON_H, BUTTON_ESCAPE,
    BUTTON_M
)

_SETTINGS_FILE = "/picoware/settings/unit_converter_settings.json" 
_VERSION = "2.0"
_SETTINGS_TEMP = _SETTINGS_FILE + ".tmp"
_SETTINGS_BACKUP = _SETTINGS_FILE + ".bak"
SAVE_DELAY_MS = 1000
SAVE_RETRY_MS = 5000
_USE_NUMBER_PAD = not BOARD_HAS_KEYBOARD and BOARD_ID != BOARD_DESKTOP
_USE_TOUCH = bool(BOARD_HAS_TOUCH) or BOARD_ID == BOARD_CROWPANEL_WATCH_2_01

# Static tuple for conversions to save RAM over using dictionaries
_CONVERSIONS = (
    ("Length", (("um", 0.000001), ("thou", 0.0000254), ("mm", 0.001), ("cm", 0.01), ("m", 1.0), ("in", 0.0254), ("ft", 0.3048), ("yd", 0.9144))),
    ("Weight", (("mg", 0.000001), ("g", 0.001), ("kg", 1.0), ("oz", 0.0283495), ("lb", 0.453592))),
    ("Volume", (("ml", 0.001), ("L", 1.0), ("gal", 3.78541), ("fl oz", 0.0295735))),
    ("Kitchen", (("Drop", 0.05), ("ml", 1.0), ("US tsp", 4.92892), ("US tbsp", 14.7868), ("UK fl oz", 28.4131), ("US fl oz", 29.5735), ("Stick(US)", 118.294), ("US cup", 236.588), ("Met cup", 250.0), ("UK cup", 284.131), ("US pint", 473.176), ("UK pint", 568.261), ("US qt", 946.353), ("UK qt", 1136.52), ("L", 1000.0))),
    ("Speed", (("mm/s", 0.001), ("m/s", 1.0), ("km/h", 0.277778), ("mph", 0.44704))),
    ("Press", (("Pa", 1.0), ("kPa", 1000.0), ("bar", 100000.0), ("psi", 6894.76))),
    ("Torque", (("Nmm", 0.001), ("Nm", 1.0), ("in-lb", 0.1129848), ("ft-lb", 1.355818))),
    ("Area", (("cm2", 0.0001), ("m2", 1.0), ("sq in", 0.00064516), ("sq ft", 0.092903))),
    ("Power", (("W", 1.0), ("kW", 1000.0), ("hp", 745.7))),
    ("Angle", (("deg", 1.0), ("rad", 57.2957795))),
    ("Temp", (("C", 0), ("F", 0), ("K", 0))),
    ("Wood", (("cu in", 0.0069444), ("bd ft", 1.0), ("cu ft", 12.0), ("m3", 423.776), ("mbf", 1000.0)))
)

# View modes
MODE_MAIN = 0
MODE_HELP = 2
MODE_LIST = 3
MODE_NUMBER_PAD = 4
MODE_SAVE_ERROR = 5

state = {
    "category_idx": 0, "from_idx": 0, "to_idx": 1, "input_val": "1.0",
    "cursor_idx": 0
}

# Volatile state
current_mode = MODE_MAIN
conv_result = "0.0"
storage = None
help_scroll = 0
dirty_ui = True
entering_value = False
list_field = 0
list_cursor = 0
pending_save = False
save_due = 0
_last_saved_json = ""
save_error = False
exit_cursor = 0
pad_cursor = 0
closing = False
_cached_help_lines = []
_wrapped_help_lines = []
_help_width = None
_result_key = None
_surface = None
_surface_key = None
_touch_targets = []
_touch_held = False
board_name = "Unknown"

def get_help_lines():
    global _cached_help_lines
    if _cached_help_lines:
        return _cached_help_lines

    if _USE_TOUCH:
        _cached_help_lines = [
            'UNIT CONVERTER v' + _VERSION, '',
            'Tap the value to edit.', 'Tap CAT, FROM or TO to choose.',
            'Tap a list row to select.', 'UP / DOWN browse list pages.',
            'BACK cancels a selection.', '',
            'KEYPAD:', 'First digit replaces the value.',
            'More digits append.', 'DEL removes the last digit.',
            'CLR resets the value to zero.',
            '+/- is available for Temp,', 'Angle and Torque.',
            'DONE or BACK finishes entry.', '',
            'EXIT closes the converter.',
            'Edits are saved automatically.',
            'If saving fails: retry, stay,', 'or explicitly exit unsaved.'
        ]
        return _cached_help_lines

    _cached_help_lines = [
        f"UNIT CONVERTER v{_VERSION}",
        "--------------------",
        "CATEGORIES:",
        "- Len, Area, Vol",
        "- Kitch, Wgt, Spd",
        "- Press, Torq, Pwr",
        "- Ang, Temp, Wood",
        "",
        "SHORTCUTS:",
        "[C] Cycle Cat",
        "[F] Edit From",
        "[T] Edit To",
        "[0-9 / .] Type value directly",
        "First digit starts a new value.",
        "More digits append.",
        "Navigation ends number entry.",
        "[BACKSPACE] Delete last digit",
        "[R] Reset value to 0",
        "NUMBER PAD (no keyboard):",
        "Arrows browse; ENTER uses key.",
        "DONE / BACK returns to main.",
        "[H] Open Help",
        "[M] Toggle +/-",
        "[ESC] Exit App",
        "",
        "CONTROLS:",
        "[UP/DN]: Cursor Nav",
        "[L/R]: Select / Edit",
        "[ENTER]: Open selection list",
        "LISTS:",
        "[UP/DN]: Browse (wraps)",
        "[ENTER]: Select highlighted",
        "[ESC/BACK]: Cancel list",
        "[BACK]: Exit App"
    ]
    return _cached_help_lines

def rgb_to_565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

def queue_save():
    global pending_save, save_due
    pending_save = storage is not None
    save_due = ticks_add(ticks_ms(), SAVE_RETRY_MS if save_error else SAVE_DELAY_MS)


def _write_verified(path, text):
    if not storage.write(path, text, "w") or storage.read(path, "r") != text:
        raise OSError("Save failed")


def save_settings():
    global _last_saved_json, pending_save, save_error, save_due, dirty_ui
    global current_mode
    if storage is None or not pending_save:
        return True
    try:
        serialized = json.dumps(state)
        if serialized != _last_saved_json:
            # Verify staging first; preserve the previous valid state before
            # overwriting the main file. Loading falls back to backup/staging.
            _write_verified(_SETTINGS_TEMP, serialized)
            if _last_saved_json:
                _write_verified(_SETTINGS_BACKUP, _last_saved_json)
            _write_verified(_SETTINGS_FILE, serialized)
            _last_saved_json = serialized
        pending_save = False
        if save_error: dirty_ui = True
        save_error = False
        if current_mode == MODE_SAVE_ERROR:
            current_mode = MODE_MAIN
            dirty_ui = True
        return True
    except Exception:
        pending_save = True
        save_error = True
        save_due = ticks_add(ticks_ms(), SAVE_RETRY_MS)
        dirty_ui = True
        return False


def _valid_input(value):
    if not isinstance(value, str): return False
    unsigned = value[1:] if value.startswith("-") else value
    if not unsigned or len(unsigned) > 32 or unsigned.count(".") > 1:
        return False
    digits = unsigned.replace(".", "")
    if not digits or any(c < "0" or c > "9" for c in digits):
        return False
    try:
        return isfinite(float(value))
    except (ValueError, OverflowError):
        return False


def validate_and_load_settings():
    global _last_saved_json, pending_save, save_due
    if storage is None: return
    for path in (_SETTINGS_FILE, _SETTINGS_BACKUP, _SETTINGS_TEMP):
        if not storage.exists(path): continue
        try:
            loaded = json.loads(storage.read(path, "r"))
            if not isinstance(loaded, dict): continue
            # Missing or invalid values invalidate the snapshot; try recovery files.
            if not _valid_input(loaded.get("input_val")):
                continue
            candidate = dict(state)
            limits = {"category_idx": len(_CONVERSIONS), "from_idx": 15,
                      "to_idx": 15, "cursor_idx": 5 if _USE_NUMBER_PAD else 4}
            for key in candidate:
                value = loaded.get(key)
                if key == "input_val":
                    candidate[key] = value
                elif isinstance(value, int) and not isinstance(value, bool):
                    if 0 <= value < limits[key]: candidate[key] = value
            state.update(candidate)
            clamp_unit_indices()
            _last_saved_json = json.dumps(state)
            if path != _SETTINGS_FILE:
                # Recommit recovered data, even if it is identical in memory.
                _last_saved_json = ""
                queue_save()
            return
        except Exception:
            continue

def identify_board():
    global board_name
    sys_inst = System()
    try:
        b_name = sys_inst.board_name
        if callable(b_name): b_name = b_name()
    except Exception:
        b_name = os.uname().machine if hasattr(os, "uname") else "Unknown Board"
    board_name = str(b_name)

def conversion_key():
    return (state["category_idx"], state["from_idx"], state["to_idx"],
            state["input_val"])

def calculate_conversion():
    try:
        val = float(state["input_val"])
        if not isfinite(val): return "Error"
        c_idx, f_idx, t_idx = state["category_idx"], state["from_idx"], state["to_idx"]
        cat_name = _CONVERSIONS[c_idx][0]

        # Temp conversions require additive logic instead of multipliers
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
            if not isfinite(final_val): return "Error"
            if 0 < abs(final_val) < 0.001: return f"{final_val:.2e}"
            return f"{final_val:.3f}"

        else:
            from_mult = _CONVERSIONS[c_idx][1][f_idx][1]
            to_mult = _CONVERSIONS[c_idx][1][t_idx][1]
            base_val = val * from_mult
            final_val = base_val / to_mult

            if not isfinite(final_val): return "Error"
            if 0 < abs(final_val) < 0.0001: return f"{final_val:.2e}"
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

def handle_value_input(button):
    """Edit the LCD value directly, without a separate view or focused field."""
    global dirty_ui, entering_value
    digits = (BUTTON_0, BUTTON_1, BUTTON_2, BUTTON_3, BUTTON_4,
              BUTTON_5, BUTTON_6, BUTTON_7, BUTTON_8, BUTTON_9)
    if button == BUTTON_R:
        state["input_val"] = "0"
        entering_value = False
    elif button in digits or button == BUTTON_PERIOD:
        value = state["input_val"] if entering_value else "0"
        if button == BUTTON_PERIOD:
            if "." not in value and len(value.lstrip("-")) < 32:
                value += "."
        else:
            digit = str(digits.index(button))
            if value == "0": value = digit
            elif value == "-0": value = "-" + digit
            elif len(value.lstrip("-")) < 32: value += digit
        state["input_val"] = value
        entering_value = True
    elif button == BUTTON_BACKSPACE:
        value = state["input_val"][:-1]
        state["input_val"] = "0" if value in ("", "-") else value
        entering_value = True
    else:
        return False
    dirty_ui = True
    return True

def handle_input_help(button, view_manager):
    global current_mode, help_scroll, dirty_ui
    if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_H): 
        current_mode = MODE_MAIN; help_scroll = 0; dirty_ui = True
    elif button == BUTTON_DOWN: help_scroll += 1; dirty_ui = True
    elif button == BUTTON_UP: help_scroll = max(0, help_scroll - 1); dirty_ui = True

def handle_input_main(button, view_manager):
    global current_mode, dirty_ui, entering_value

    if handle_value_input(button):
        return
    if button in (BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT,
                  BUTTON_C, BUTTON_F, BUTTON_T, BUTTON_H, BUTTON_CENTER):
        entering_value = False

    if button in (BUTTON_BACK, BUTTON_ESCAPE):
        request_exit(view_manager)
        return

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
    elif button == BUTTON_H: current_mode = MODE_HELP; state["cursor_idx"] = 3; dirty_ui = True

    elif button == BUTTON_M:
        if _CONVERSIONS[state["category_idx"]][0] in ("Temp", "Angle", "Torque"):
            if state["input_val"].startswith("-"): state["input_val"] = state["input_val"][1:]
            else: state["input_val"] = "-" + state["input_val"]
            entering_value = True
            dirty_ui = True

    elif button == BUTTON_DOWN: state["cursor_idx"] = (state["cursor_idx"] + 1) % (5 if _USE_NUMBER_PAD else 4); dirty_ui = True
    elif button == BUTTON_UP: state["cursor_idx"] = (state["cursor_idx"] - 1) % (5 if _USE_NUMBER_PAD else 4); dirty_ui = True

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
        if c_idx < 3: open_selection_list(c_idx)
        elif c_idx == 3: current_mode = MODE_HELP
        elif c_idx == 4: open_number_pad()
        dirty_ui = True

_LIST_FIELDS = ("category_idx", "from_idx", "to_idx")
_LIST_TITLES = ("CATEGORY", "FROM UNIT", "TO UNIT")


def selection_items():
    if list_field == 0:
        return _CONVERSIONS
    return _CONVERSIONS[state["category_idx"]][1]


def open_selection_list(field):
    global list_field, list_cursor, current_mode, entering_value, dirty_ui
    list_field = field
    list_cursor = state[_LIST_FIELDS[field]]
    current_mode = MODE_LIST
    entering_value = False
    dirty_ui = True


def handle_input_list(button, view_manager):
    global list_cursor, current_mode, dirty_ui
    if button in (BUTTON_BACK, BUTTON_ESCAPE):
        current_mode = MODE_MAIN
    elif button in (BUTTON_UP, BUTTON_DOWN):
        step = -1 if button == BUTTON_UP else 1
        list_cursor = (list_cursor + step) % len(selection_items())
    elif button == BUTTON_CENTER:
        state[_LIST_FIELDS[list_field]] = list_cursor
        if list_field == 0:
            clamp_unit_indices()
        current_mode = MODE_MAIN
    else:
        return
    dirty_ui = True


_PAD_LABELS = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
               ".", "DELETE", "ZERO", "DONE")
_PAD_BUTTONS = (BUTTON_0, BUTTON_1, BUTTON_2, BUTTON_3, BUTTON_4,
                BUTTON_5, BUTTON_6, BUTTON_7, BUTTON_8, BUTTON_9,
                BUTTON_PERIOD, BUTTON_BACKSPACE, BUTTON_R)


def open_number_pad():
    global current_mode, pad_cursor, entering_value, dirty_ui
    current_mode = MODE_NUMBER_PAD
    pad_cursor = 0
    entering_value = False
    dirty_ui = True


def pad_labels():
    if _CONVERSIONS[state["category_idx"]][0] in ("Temp", "Angle", "Torque"):
        return _PAD_LABELS + ("+/-",)
    return _PAD_LABELS


def handle_input_pad(button, view_manager):
    global current_mode, pad_cursor, dirty_ui, entering_value
    if button in (BUTTON_BACK, BUTTON_ESCAPE):
        current_mode = MODE_MAIN
        entering_value = False
    elif button in (BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT):
        step = -1 if button in (BUTTON_UP, BUTTON_LEFT) else 1
        pad_cursor = (pad_cursor + step) % len(pad_labels())
    elif button == BUTTON_CENTER:
        if pad_cursor == 13:
            current_mode = MODE_MAIN
            entering_value = False
        elif pad_cursor == 14:
            handle_input_main(BUTTON_M, view_manager)
        else:
            handle_value_input(_PAD_BUTTONS[pad_cursor])
    elif button == BUTTON_M:
        handle_input_main(button, view_manager)
    elif not handle_value_input(button):
        return
    dirty_ui = True


def request_exit(view_manager):
    global current_mode, exit_cursor, closing, dirty_ui
    if save_settings():
        closing = True
        view_manager.back()
    else:
        current_mode = MODE_SAVE_ERROR
        exit_cursor = 0
        dirty_ui = True


def handle_input_save_error(button, view_manager):
    global current_mode, exit_cursor, pending_save, closing, dirty_ui
    if button in (BUTTON_BACK, BUTTON_ESCAPE):
        current_mode = MODE_MAIN
    elif button in (BUTTON_UP, BUTTON_DOWN):
        exit_cursor = (exit_cursor + (-1 if button == BUTTON_UP else 1)) % 3
    elif button == BUTTON_CENTER:
        if exit_cursor == 0:
            request_exit(view_manager)
        elif exit_cursor == 1:
            current_mode = MODE_MAIN
        else:
            pending_save = False
            closing = True
            view_manager.back()
    else:
        return
    if not closing: dirty_ui = True


INPUT_DISPATCH = {
    MODE_MAIN: handle_input_main,
    MODE_HELP: handle_input_help,
    MODE_LIST: handle_input_list,
    MODE_NUMBER_PAD: handle_input_pad,
    MODE_SAVE_ERROR: handle_input_save_error,
}

# Same powder-coated shell, LCD and focus palette as SimpleRPN.
COLOR_BG = rgb_to_565(15, 18, 19)
COLOR_EDGE = rgb_to_565(91, 101, 100)
COLOR_SHADOW = rgb_to_565(7, 9, 9)
COLOR_LCD = rgb_to_565(177, 193, 160)
COLOR_LCD_DARK = rgb_to_565(25, 38, 28)
COLOR_LCD_MID = rgb_to_565(72, 91, 72)
COLOR_KEY = rgb_to_565(54, 61, 62)
COLOR_KEY_TOP = rgb_to_565(77, 85, 85)
COLOR_AMBER = rgb_to_565(245, 166, 57)
COLOR_MUTED = rgb_to_565(161, 168, 164)


def _text(draw, x, y, text, width, color, preferred=FONT_XTRA_SMALL,
          right=False, number=False, entry=False):
    font = preferred
    while font > FONT_XTRA_SMALL and draw.len(text, font) > width:
        font -= 1
    if number and not entry and draw.len(text, font) > width:
        try:
            value = float(text)
            for precision in range(7, -1, -1):
                candidate = ("%.*e" % (precision, value)).replace("e", "E")
                if draw.len(candidate, font) <= width:
                    text = candidate
                    break
        except ValueError:
            pass
    if draw.len(text, font) > width:
        if entry:
            while text and draw.len("<" + text, font) > width:
                text = text[1:]
            text = "<" + text
        else:
            while text and draw.len(text + ">", font) > width:
                text = text[:-1]
            text += ">"
    if right:
        x += width - draw.len(text, font)
    draw.text(Vector(x, y), text, color, font)


def _header(draw, width, title, accent):
    _text(draw, 4, 3, "SAVE FAILED" if save_error else title, width - 8, COLOR_AMBER if save_error else COLOR_MUTED)
    draw.fill_rectangle(Vector(4, 13), Vector(width - 8, 1), accent)


def _key(draw, x, y, w, h, text, selected, accent):
    draw.fill_rectangle(Vector(x + 1, y + 2), Vector(w, h), COLOR_SHADOW)
    draw.fill_rectangle(Vector(x, y), Vector(w, h), COLOR_KEY)
    draw.fill_rectangle(Vector(x + 1, y + 1), Vector(w - 2, 1), COLOR_KEY_TOP)
    if selected:
        draw.rect(Vector(x, y), Vector(w, h), accent)
    font = FONT_SMALL if h >= 20 else FONT_XTRA_SMALL
    _text(draw, x + 4, y + (h - (12 if font == FONT_SMALL else 8)) // 2,
          text, w - 8, accent if selected else TFT_WHITE, font)


def _rows(draw, labels, selected, x, y, w, h, accent):
    # Scroll a complete row at a time; selection is always visible.
    count = min(len(labels), max(1, h // 19))
    row_h = min(36, h // count)
    first = min(max(0, selected - count + 1), len(labels) - count)
    for row in range(count):
        index = first + row
        _key(draw, x, y + row * row_h, w - 2, row_h - 3,
             labels[index], index == selected, accent)


def draw_selection_list(view_manager, draw, screen_w, screen_h, accent):
    items = selection_items()
    title = "%s %d/%d" % (_LIST_TITLES[list_field], list_cursor + 1, len(items))
    _header(draw, screen_w, title, accent)
    # Reserve two footer lines even on 128x64, scrolling whole items.
    _rows(draw, tuple(item[0] for item in items), list_cursor,
          4, 17, screen_w - 8, screen_h - 40, accent)
    hints = ("UP/DN WRAP ENT PICK", "ESC/BACK CANCEL")
    for row, hint in enumerate(hints):
        _text(draw, 4, screen_h - 20 + row * 10, hint, screen_w - 8, COLOR_MUTED)


def draw_number_pad(view_manager, draw, screen_w, screen_h, accent):
    _header(draw, screen_w, "NUMBER PAD", accent)
    _text(draw, 4, 17, state["input_val"], screen_w - 8, TFT_WHITE, entry=True)
    _rows(draw, pad_labels(), pad_cursor, 4, 29, screen_w - 8,
          screen_h - 49, accent)
    _text(draw, 4, screen_h - 18, "ARROWS PICK ENT USE", screen_w - 8, COLOR_MUTED)
    _text(draw, 4, screen_h - 8, "BACK DONE", screen_w - 8, COLOR_MUTED)


def draw_save_error(view_manager, draw, screen_w, screen_h, accent):
    _header(draw, screen_w, "SAVE FAILED", accent)
    _rows(draw, ("RETRY SAVE / EXIT", "STAY IN APP", "EXIT UNSAVED"),
          exit_cursor, 4, 17, screen_w - 8, screen_h - 30, accent)
    _text(draw, 4, screen_h - 10, "UP/DN ENT BACK STAY", screen_w - 8, COLOR_MUTED)


def wrapped_help_lines(draw, width):
    global _wrapped_help_lines, _help_width
    if _help_width != width:
        # Draw.len uses a fixed character width for each font.
        columns = max(1, width // draw.len("M", FONT_XTRA_SMALL))
        lines = []
        for source in get_help_lines():
            if not source:
                lines.append("")
            else:
                for offset in range(0, len(source), columns):
                    lines.append(source[offset:offset + columns])
        _wrapped_help_lines = lines
        _help_width = width
    return _wrapped_help_lines


def draw_help(view_manager, draw, screen_w, screen_h, accent):
    global help_scroll
    _header(draw, screen_w, "HELP / MANUAL", accent)
    lines = wrapped_help_lines(draw, screen_w - 8)
    count = max(1, (screen_h - 30) // 10)
    help_scroll = min(help_scroll, max(0, len(lines) - count))
    for i, line in enumerate(lines[help_scroll:help_scroll + count]):
        _text(draw, 4, 17 + i * 10, line, screen_w - 8, TFT_WHITE)
    _text(draw, 4, screen_h - 10, "UP/DN SCROLL H CLOSE", screen_w - 8, COLOR_MUTED)


def draw_main(view_manager, draw, screen_w, screen_h, accent):
    cat = _CONVERSIONS[state["category_idx"]]
    f_name = cat[1][state["from_idx"]][0]
    t_name = cat[1][state["to_idx"]][0]
    compact = screen_h < 100
    side = screen_w > screen_h and not compact
    _header(draw, screen_w, "UNIT CONVERTER", accent)
    if side:
        x, y, w, h = 4, 17, max(90, (screen_w - 16) * 2 // 5), screen_h - 41
        kx, ky, kw, kh = x + w + 6, y, screen_w - w - 14, h
    else:
        x, y, w = 4, 17, screen_w - 10
        h = 24 if compact else min(100, max(52, (screen_h - 55) // 3))
        gap = 2 if compact else 5
        kx, ky, kw, kh = 4, y + h + gap, screen_w - 8, screen_h - (y + h + gap) - 24
    draw.fill_rectangle(Vector(x + 1, y + 2), Vector(w, h), COLOR_SHADOW)
    draw.fill_rectangle(Vector(x, y), Vector(w, h), COLOR_EDGE)
    draw.fill_rectangle(Vector(x + 1, y + 1), Vector(w - 2, h - 2), COLOR_LCD)
    if compact:
        _text(draw, x + 3, y + 3, state["input_val"] + " " + f_name,
              w - 6, COLOR_LCD_DARK, right=True, entry=True)
        unit_width = draw.len(t_name, FONT_XTRA_SMALL)
        _text(draw, x + 3, y + 13, conv_result, w - unit_width - 12,
              COLOR_LCD_DARK, number=True, right=True)
        _text(draw, x + w - unit_width - 3, y + 13, t_name, unit_width, COLOR_LCD_MID)
    else:
        _text(draw, x + 5, y + 5, "RESULT / " + t_name, w - 10, COLOR_LCD_MID)
        _text(draw, x + 5, y + 17, conv_result, w - 10, COLOR_LCD_DARK,
              FONT_MEDIUM if h >= 52 else FONT_SMALL, right=True, number=True)
        if h >= 52:
            _text(draw, x + 5, y + h - 14, state["input_val"] + " " + f_name,
                  w - 10, COLOR_LCD_MID, right=True, entry=True)
    sign_hint = " M:+/-" if cat[0] in ("Temp", "Angle", "Torque") else ""
    labels = ("CAT: " + cat[0], "FROM: " + f_name, "TO: " + t_name,
              "HELP / MANUAL")
    if _USE_NUMBER_PAD: labels += ("NUMBER PAD",)
    if compact:
        # One selected control on 128x64; arrows reach every control.
        _key(draw, kx, ky, kw - 2, 10, labels[state["cursor_idx"]], True, accent)
        hint = "0-9 . R:0" + sign_hint + " ENT" if sign_hint else "0-9 . R:0 ENT:LIST"
        if _USE_NUMBER_PAD: hint = "ARROWS NAV ENT OPEN"
        _text(draw, 4, screen_h - 8, hint, screen_w - 8, COLOR_MUTED)
    else:
        _rows(draw, labels, state["cursor_idx"], kx, ky, kw, kh, accent)
        if screen_w < 200:
            hints = (("0-9 . R:0 BS" + sign_hint) if sign_hint else "0-9 . TYPE R:0 BS:DEL", "ENT:LIST ARROWS:NAV H:HELP")
        else:
            hints = ("0-9 . TYPE R:0 BS:DEL" + sign_hint, "ENT:LIST C:CAT F:FROM T:TO H:HELP")
        if _USE_NUMBER_PAD:
            hints = ("ARROWS NAV ENT OPEN", "NUMBER PAD: TYPE VALUE")
        for row, hint in enumerate(hints):
            _text(draw, 4, screen_h - 20 + row * 10, hint, screen_w - 8, COLOR_MUTED)


class _Surface:
    """Keep all content inside the inscribed square on round displays."""
    def __init__(self, draw):
        self.draw = draw
        self.mono = "flipper" in board_name.lower()
        w, h = int(draw.size.x), int(draw.size.y)
        self.inset = w * 15 // 100 if w == h and w in (240, 466) else 0
        self.size = Vector(w - self.inset * 2, h - self.inset * 2)

    def len(self, text, font):
        return self.draw.len(text, font)

    def _color(self, color):
        if not self.mono: return color
        return TFT_BLACK if color in (COLOR_BG, COLOR_SHADOW, COLOR_KEY, COLOR_LCD_DARK, COLOR_LCD_MID) else TFT_WHITE

    def _position(self, position):
        if not self.inset: return position
        return Vector(position.x + self.inset, position.y + self.inset)

    def text(self, position, text, color, font):
        self.draw.text(self._position(position), text, self._color(color), font)

    def fill_rectangle(self, position, size, color):
        self.draw.fill_rectangle(self._position(position), size, self._color(color))

    def rect(self, position, size, color):
        self.draw.rect(self._position(position), size, self._color(color))

def _touch_key(draw, x, y, w, h, label, action, selected=False):
    _key(draw, x, y, w - 2, h - 3, label, selected, COLOR_AMBER)
    _touch_targets.append((x, y, w, h, action))


def _touch_footer(draw, width, height, controls):
    cell = (width - 8) // len(controls)
    for index, (label, action) in enumerate(controls):
        _touch_key(draw, 4 + index * cell, height - 28, cell, 24,
                   label, action)


def draw_touch(view_manager, draw, screen_w, screen_h, accent):
    global _touch_targets, help_scroll
    _touch_targets = []
    titles = {MODE_MAIN: 'UNIT CONVERTER', MODE_HELP: 'HELP',
              MODE_LIST: _LIST_TITLES[list_field], MODE_NUMBER_PAD: 'ENTER VALUE',
              MODE_SAVE_ERROR: 'SAVE FAILED'}
    _header(draw, screen_w, titles[current_mode], accent)
    if current_mode == MODE_MAIN:
        cat = _CONVERSIONS[state['category_idx']]
        source = cat[1][state['from_idx']][0]
        target = cat[1][state['to_idx']][0]
        draw.fill_rectangle(Vector(4, 17), Vector(screen_w - 8, 40), COLOR_LCD)
        unit_width = draw.len(target, FONT_XTRA_SMALL)
        _text(draw, 8, 20, conv_result, screen_w - unit_width - 20,
              COLOR_LCD_DARK, right=True, number=True)
        _text(draw, screen_w - unit_width - 8, 20, target, unit_width, COLOR_LCD_MID)
        _text(draw, 8, 33, state['input_val'] + ' ' + source, screen_w - 16,
              COLOR_LCD_DARK, right=True, entry=True)
        _text(draw, 8, 45, 'TAP TO EDIT', screen_w - 16, COLOR_LCD_MID)
        _touch_targets.append((4, 17, screen_w - 8, 40, ('value', 0)))
        labels = ('CAT: ' + cat[0], 'FROM: ' + source, 'TO: ' + target)
        row_h = min(48, (screen_h - 93) // 3)
        for i, label in enumerate(labels):
            _touch_key(draw, 4, 61 + i * row_h, screen_w - 8, row_h,
                       label, ('field', i), state['cursor_idx'] == i)
        _touch_footer(draw, screen_w, screen_h,
                      (('EXIT', ('button', BUTTON_ESCAPE)), ('HELP', ('button', BUTTON_H))))
    elif current_mode == MODE_NUMBER_PAD:
        _text(draw, 4, 18, state['input_val'], screen_w - 8, TFT_WHITE, entry=True)
        labels = pad_labels()
        cell_w = (screen_w - 8) // 4
        cell_h = min(52, (screen_h - 62) // 4)
        for i, label in enumerate(labels):
            if label == 'DELETE': label = 'DEL'
            elif label == 'ZERO': label = 'CLR'
            _touch_key(draw, 4 + (i % 4) * cell_w, 30 + (i // 4) * cell_h,
                       cell_w, cell_h, label, ('pad', i), i == pad_cursor)
        _touch_footer(draw, screen_w, screen_h, (('BACK', ('button', BUTTON_BACK)),))
    elif current_mode == MODE_HELP:
        lines = wrapped_help_lines(draw, screen_w - 8)
        count = max(1, (screen_h - 49) // 10)
        help_scroll = min(help_scroll, max(0, len(lines) - count))
        for i, line in enumerate(lines[help_scroll:help_scroll + count]):
            _text(draw, 4, 17 + i * 10, line, screen_w - 8, TFT_WHITE)
        _touch_footer(draw, screen_w, screen_h,
                      (('BACK', ('button', BUTTON_BACK)), ('UP', ('help', -count)),
                       ('DOWN', ('help', count))))
    else:
        if current_mode == MODE_LIST:
            labels = tuple(item[0] for item in selection_items())
            selected = list_cursor
            kind = 'item'
        else:
            labels = ('RETRY SAVE / EXIT', 'STAY IN APP', 'EXIT UNSAVED')
            selected = exit_cursor
            kind = 'exit'
        count = min(len(labels), max(1, (screen_h - 49) // 28))
        row_h = min(48, (screen_h - 49) // count)
        first = min(max(0, selected - count + 1), len(labels) - count)
        for row in range(count):
            index = first + row
            _touch_key(draw, 4, 17 + row * row_h, screen_w - 8, row_h,
                       labels[index], (kind, index), index == selected)
        controls = (('BACK', ('button', BUTTON_BACK)),)
        if current_mode == MODE_LIST:
            controls += (('UP', ('page', -count)), ('DOWN', ('page', count)))
        _touch_footer(draw, screen_w, screen_h, controls)


def handle_touch(view_manager):
    """Consume screen taps before their generic directional-button mapping."""
    global _touch_held, list_cursor, pad_cursor, exit_cursor, help_scroll, dirty_ui
    input_manager = getattr(view_manager, 'input_manager', None)
    if input_manager is None: return False
    point = input_manager.point
    gesture = input_manager.gesture
    down = getattr(input_manager, 'touch_down', False)
    if point == (0, 0):
        if not down: _touch_held = False
        return down
    if gesture:
        from waveshare_touch import TOUCH_GESTURE_CLICK
        if gesture != TOUCH_GESTURE_CLICK:
            input_manager.reset()
            return True
    if _touch_held:
        input_manager.reset()
        return True
    _touch_held = True
    input_manager.reset()
    if _surface is None: return True
    x, y = point[0] - _surface.inset, point[1] - _surface.inset
    for left, top, width, height, action in _touch_targets:
        if left <= x < left + width and top <= y < top + height:
            kind, value = action
            if kind == 'value': open_number_pad()
            elif kind == 'field':
                state['cursor_idx'] = value
                open_selection_list(value)
            elif kind == 'button': INPUT_DISPATCH[current_mode](value, view_manager)
            elif kind == 'item':
                list_cursor = value
                handle_input_list(BUTTON_CENTER, view_manager)
            elif kind == 'page':
                list_cursor = max(0, min(len(selection_items()) - 1, list_cursor + value))
            elif kind == 'pad':
                pad_cursor = value
                handle_input_pad(BUTTON_CENTER, view_manager)
            elif kind == 'exit':
                exit_cursor = value
                handle_input_save_error(BUTTON_CENTER, view_manager)
            elif kind == 'help': help_scroll = max(0, help_scroll + value)
            dirty_ui = True
            break
    return True


VIEW_DISPATCH = {
    MODE_MAIN: draw_main,
    MODE_HELP: draw_help,
    MODE_LIST: draw_selection_list,
    MODE_NUMBER_PAD: draw_number_pad,
    MODE_SAVE_ERROR: draw_save_error,
}

def start(view_manager):
    global conv_result, storage, dirty_ui, current_mode, entering_value, closing
    global _result_key, _touch_held
    _touch_held = False
    current_mode = MODE_MAIN
    entering_value = False
    closing = False
    storage = view_manager.storage if System().has_storage and BOARD_ID != BOARD_CROWPANEL_WATCH_2_01 else None
    identify_board()
    if not pending_save:
        validate_and_load_settings()
    clamp_unit_indices()
    conv_result = calculate_conversion()
    _result_key = conversion_key()
    dirty_ui = True
    return True

def run(view_manager):
    global conv_result, dirty_ui, _result_key, _surface, _surface_key

    draw = view_manager.draw; button = view_manager.button
    screen_w = draw.size.x; screen_h = draw.size.y

    before_touch = conversion_key() if _USE_TOUCH else None
    if _USE_TOUCH and handle_touch(view_manager):
        button = -1  # A touch must not also dispatch its mapped keyboard event.
        if closing: return
        if conversion_key() != before_touch: queue_save()

    if button == -1 and not dirty_ui and not pending_save: return

    if button != -1:
        before = conversion_key()
        handler = INPUT_DISPATCH.get(current_mode)
        if handler: handler(button, view_manager)

        if closing: return
        # Focus is saved opportunistically with edits, never on its own.
        if conversion_key() != before: queue_save()

    # Process pending SD saves when idle
    if pending_save and button == -1:
        if ticks_diff(ticks_ms(), save_due) >= 0:
            save_settings()

    if dirty_ui and current_mode == MODE_MAIN:
        key = conversion_key()
        if key != _result_key:
            conv_result = calculate_conversion()
            _result_key = key

    if dirty_ui:
        draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), COLOR_BG)
        surface_key = (screen_w, screen_h, board_name)
        if (_surface is None or _surface.draw is not draw
                or _surface_key != surface_key):
            _surface = _Surface(draw)
            _surface_key = surface_key
        surface = _surface

        if _USE_TOUCH:
            handler = draw_touch
        else:
            handler = VIEW_DISPATCH.get(current_mode)
        if handler: handler(view_manager, surface, int(surface.size.x), int(surface.size.y), COLOR_AMBER)

        draw.swap(); dirty_ui = False

def stop(view_manager):
    # Normal exit is handled before leaving the app. If the OS stops this view
    # directly, make a best-effort save and retain state for a resumed view.
    global closing, _surface, _surface_key, _touch_targets, _touch_held
    if not closing:
        save_settings()
    closing = True
    _surface = None
    _surface_key = None
    _touch_targets = []
    _touch_held = False
    gc.collect()
