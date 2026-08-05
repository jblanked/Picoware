"""SimpleRPN: a compact four-level RPN calculator for Picoware."""

import ujson as json
from math import sqrt
from utime import ticks_add, ticks_diff, ticks_ms

from picoware.system.vector import Vector
from picoware.system.font import FONT_XTRA_SMALL, FONT_SMALL, FONT_MEDIUM
from picoware.system.colors import TFT_WHITE
from picoware.system.buttons import (
    BUTTON_A,
    BUTTON_Z,
    BUTTON_BACK,
    BUTTON_UP,
    BUTTON_DOWN,
    BUTTON_LEFT,
    BUTTON_RIGHT,
    BUTTON_CENTER,
    BUTTON_0,
    BUTTON_9,
    BUTTON_PERIOD,
    BUTTON_SLASH,
    BUTTON_BACKSLASH,
    BUTTON_ASTERISK,
    BUTTON_MINUS,
    BUTTON_PLUS,
    BUTTON_EQUAL,
    BUTTON_PERCENT,
    BUTTON_BACKSPACE,
    BUTTON_DELETE,
    BUTTON_SPACE,
    BUTTON_TAB,
    BUTTON_ESCAPE,
    BUTTON_C,
    BUTTON_D,
    BUTTON_H,
    BUTTON_I,
    BUTTON_J,
    BUTTON_K,
    BUTTON_L,
    BUTTON_N,
    BUTTON_P,
    BUTTON_Q,
    BUTTON_R,
    BUTTON_S,
    BUTTON_T,
    BUTTON_U,
    BUTTON_V,
    BUTTON_X,
)


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

STATE_FILE = "picoware/settings/srpn.json"
STATE_VERSION = 1
SAVE_DELAY_MS = 1000


KEYS = (
    ("CLR", "clear", "function"),
    ("+/-", "negate", "function"),
    ("%", "percent", "function"),
    ("/", "divide", "operator"),
    ("x2", "square", "function"),
    ("SQRT", "sqrt", "function"),
    ("1/x", "reciprocal", "function"),
    ("*", "multiply", "operator"),
    ("7", "7", "number"),
    ("8", "8", "number"),
    ("9", "9", "number"),
    ("-", "subtract", "operator"),
    ("4", "4", "number"),
    ("5", "5", "number"),
    ("6", "6", "number"),
    ("+", "add", "operator"),
    ("1", "1", "number"),
    ("2", "2", "number"),
    ("3", "3", "number"),
    ("ENTER", "enter", "enter"),
    ("DROP", "drop", "function"),
    ("0", "0", "number"),
    (".", "decimal", "number"),
    ("SWAP", "swap", "function"),
    ("STO", "store", "memory"),
    ("RCL", "recall", "memory"),
    ("VARS", "variables", "memory"),
    ("HELP", "help", "function"),
)

ACTION_INDEX = {}
for _key_index in range(len(KEYS)):
    ACTION_INDEX[KEYS[_key_index][1]] = _key_index

ENTER_INDEX = ACTION_INDEX["enter"]


def format_number(value):
    """Return a compact value suitable for the calculator display."""
    if value != value:
        return "NAN"
    if abs(value) == float("inf"):
        return "OVERFLOW"
    if abs(value) < 1e-12:
        value = 0.0
    if abs(value) < 1000000000000.0 and value == int(value):
        return str(int(value))
    text = "%.10g" % value
    if len(text) > 15:
        text = "%.7e" % value
    return text.replace("e", "E")


class RPNStack:
    """Four-level T/Z/Y/X stack with an editable X register."""

    __slots__ = (
        "stack",
        "entry",
        "entering",
        "lift_on_entry",
        "error",
        "status",
        "variables",
        "variable_set",
    )

    def __init__(self):
        self.stack = [0.0, 0.0, 0.0, 0.0]  # X, Y, Z, T
        self.entry = ""
        self.entering = False
        self.lift_on_entry = False
        self.error = ""
        self.status = "READY"
        self.variables = [0.0] * 26
        self.variable_set = [False] * 26

    def clear(self):
        self.stack[0] = 0.0
        self.stack[1] = 0.0
        self.stack[2] = 0.0
        self.stack[3] = 0.0
        self.entry = ""
        self.entering = False
        self.lift_on_entry = False
        self.error = ""
        self.status = "STACK CLEARED"

    def clear_x(self):
        self.stack[0] = 0.0
        self.entry = ""
        self.entering = False
        self.lift_on_entry = False
        self.error = ""
        self.status = "X CLEARED - C/ESC AGAIN: ALL"

    def _dismiss_error(self):
        self.error = ""

    def _set_error(self, message):
        self.error = message
        self.status = message
        self.entry = ""
        self.entering = False

    def _lift(self):
        x, y, z = self.stack[0], self.stack[1], self.stack[2]
        self.stack[3] = z
        self.stack[2] = y
        self.stack[1] = x

    def _begin_entry(self):
        self._dismiss_error()
        if self.lift_on_entry:
            self._lift()
        self.entry = ""
        self.stack[0] = 0.0
        self.entering = True
        self.lift_on_entry = False

    def _sync_entry(self):
        if self.entry in ("", "-", ".", "-."):
            self.stack[0] = 0.0
        else:
            self.stack[0] = float(self.entry)

    def _commit_entry(self):
        if self.entering:
            self._sync_entry()
            self.entry = ""
            self.entering = False

    def digit(self, digit):
        if not self.entering:
            self._begin_entry()
        if len(self.entry) >= 15:
            self.status = "ENTRY LIMIT"
            return
        if self.entry in ("0", "-0") and "." not in self.entry:
            self.entry = "-" + digit if self.entry.startswith("-") else digit
        else:
            self.entry += digit
        self._sync_entry()
        self.status = "ENTER VALUE"

    def decimal(self):
        if not self.entering:
            self._begin_entry()
        if "." not in self.entry:
            self.entry = (self.entry if self.entry else "0") + "."
        self._sync_entry()
        self.status = "ENTER VALUE"

    def backspace(self):
        self._dismiss_error()
        if not self.entering:
            self.stack[0] = 0.0
            self.lift_on_entry = False
            self.status = "X CLEARED"
            return
        self.entry = self.entry[:-1]
        if self.entry in ("", "-"):
            self.entry = ""
            self.entering = False
        self._sync_entry()
        self.status = "EDIT X"

    def enter(self):
        self._dismiss_error()
        self._commit_entry()
        self._lift()
        self.entry = ""
        self.entering = False
        self.lift_on_entry = False
        self.status = "X ENTERED"

    def drop(self):
        self._dismiss_error()
        self._commit_entry()
        self.stack[0] = self.stack[1]
        self.stack[1] = self.stack[2]
        self.stack[2] = self.stack[3]
        self.lift_on_entry = True
        self.status = "STACK DROP"

    def swap(self):
        self._dismiss_error()
        self._commit_entry()
        self.stack[0], self.stack[1] = self.stack[1], self.stack[0]
        self.lift_on_entry = True
        self.status = "X / Y SWAPPED"

    def negate(self):
        self._dismiss_error()
        if self.entering:
            if self.entry.startswith("-"):
                self.entry = self.entry[1:]
            else:
                self.entry = "-" + (self.entry if self.entry else "0")
            self._sync_entry()
        else:
            self.stack[0] = -self.stack[0]
            self.lift_on_entry = True
        self.status = "SIGN CHANGED"

    def percent(self):
        """Replace X with X percent of Y and retain Y for + or -."""
        self._dismiss_error()
        self._commit_entry()
        try:
            result = self.stack[1] * self.stack[0] / 100.0
            if abs(result) == float("inf") or result != result:
                raise OverflowError
        except (OverflowError, ValueError):
            self._set_error("OVERFLOW")
            return
        self.stack[0] = result
        self.lift_on_entry = True
        self.status = "Y RETAINED: USE + OR -"

    def unary(self, action):
        self._dismiss_error()
        self._commit_entry()
        x = self.stack[0]
        try:
            if action == "square":
                result = x * x
                label = "X SQUARED"
            elif action == "sqrt":
                if x < 0:
                    self._set_error("SQRT DOMAIN")
                    return
                result = sqrt(x)
                label = "SQUARE ROOT"
            else:
                if x == 0:
                    self._set_error("DIVIDE BY ZERO")
                    return
                result = 1.0 / x
                label = "RECIPROCAL"
            if abs(result) == float("inf") or result != result:
                raise OverflowError
        except (OverflowError, ValueError):
            self._set_error("OVERFLOW")
            return
        self.stack[0] = result
        self.lift_on_entry = True
        self.status = label

    def binary(self, action):
        self._dismiss_error()
        self._commit_entry()
        x, y = self.stack[0], self.stack[1]
        try:
            if action == "add":
                result = y + x
                label = "ADD"
            elif action == "subtract":
                result = y - x
                label = "SUBTRACT"
            elif action == "multiply":
                result = y * x
                label = "MULTIPLY"
            else:
                if x == 0:
                    self._set_error("DIVIDE BY ZERO")
                    return
                result = y / x
                label = "DIVIDE"
            if abs(result) == float("inf") or result != result:
                raise OverflowError
        except (OverflowError, ValueError):
            self._set_error("OVERFLOW")
            return
        self.stack[0] = result
        self.stack[1] = self.stack[2]
        self.stack[2] = self.stack[3]
        self.lift_on_entry = True
        self.status = label

    def store(self, index):
        """Store X in the named variable without changing the stack."""
        self._dismiss_error()
        self._commit_entry()
        self.variables[index] = self.stack[0]
        self.variable_set[index] = True
        self.lift_on_entry = True
        self.status = "STO " + chr(ord("A") + index)

    def recall(self, index):
        """Lift the stack and recall the named variable into X."""
        self._dismiss_error()
        name = chr(ord("A") + index)
        if not self.variable_set[index]:
            self.status = "RCL " + name + ": EMPTY"
            return False
        self._commit_entry()
        self._lift()
        self.stack[0] = self.variables[index]
        self.entry = ""
        self.entering = False
        self.lift_on_entry = True
        self.status = "RCL " + name
        return True

    def clear_variable(self, index):
        """Clear one named variable without affecting the stack."""
        self.variables[index] = 0.0
        self.variable_set[index] = False
        self.status = "CLEARED " + chr(ord("A") + index)

    def display(self, level):
        if level == 0 and self.entering:
            return self.entry if self.entry not in ("", "-") else "0"
        return format_number(self.stack[level])


calculator = None
selected_index = ENTER_INDEX
help_visible = False
help_page = 0
variable_view_mode = None
selected_variable = 0
variable_confirm_action = None
variable_confirm_index = -1
escape_armed = False
back_exit_armed = False
flash_index = -1
flash_until = 0
storage = None
state_dirty = False
save_due = 0
last_saved_state = ""


def _state_json():
    """Serialize the complete calculator memory for the next app cycle."""
    return json.dumps(
        {
            "version": STATE_VERSION,
            "stack": calculator.stack,
            "entry": calculator.entry,
            "entering": calculator.entering,
            "lift_on_entry": calculator.lift_on_entry,
            "variables": calculator.variables,
            "variable_set": calculator.variable_set,
        }
    )


def _load_state():
    """Restore calculator memory, ignoring incomplete or incompatible files."""
    global last_saved_state
    if storage is None or not storage.exists(STATE_FILE):
        return False
    try:
        raw = storage.read(STATE_FILE, "r")
        saved = json.loads(raw)
        if saved.get("version") != STATE_VERSION:
            return False

        saved_stack = saved.get("stack")
        saved_variables = saved.get("variables")
        saved_variable_set = saved.get("variable_set")
        if (
            not isinstance(saved_stack, list)
            or len(saved_stack) != 4
            or not isinstance(saved_variables, list)
            or len(saved_variables) != 26
            or not isinstance(saved_variable_set, list)
            or len(saved_variable_set) != 26
        ):
            return False

        restored_stack = [float(value) for value in saved_stack]
        restored_variables = [float(value) for value in saved_variables]
        restored_variable_set = [bool(value) for value in saved_variable_set]
        entry = saved.get("entry", "")
        entering = bool(saved.get("entering", False))
        if not isinstance(entry, str) or len(entry) > 15:
            return False
        if entering and entry not in ("", "-", ".", "-."):
            float(entry)
        elif not entering:
            entry = ""

        calculator.stack = restored_stack
        calculator.variables = restored_variables
        calculator.variable_set = restored_variable_set
        calculator.entry = entry
        calculator.entering = entering
        calculator.lift_on_entry = bool(saved.get("lift_on_entry", False))
        calculator.error = ""
        calculator.status = "MEMORY RESTORED"
        last_saved_state = _state_json()
        return True
    except (AttributeError, KeyError, TypeError, ValueError, OSError):
        return False


def _queue_save():
    """Defer state writes briefly so rapid key entry does not wear the SD card."""
    global state_dirty, save_due
    state_dirty = True
    save_due = ticks_add(ticks_ms(), SAVE_DELAY_MS)


def _save_state(force=False):
    """Write changed calculator memory to Picoware's SD settings folder."""
    global state_dirty, last_saved_state
    if storage is None or calculator is None or (not force and not state_dirty):
        return False
    try:
        serialized = _state_json()
        if serialized == last_saved_state:
            state_dirty = False
            return True
        if not storage.write(STATE_FILE, serialized, "w"):
            return False
        if not storage.exists(STATE_FILE) or storage.size(STATE_FILE) != len(serialized):
            return False
        last_saved_state = serialized
        state_dirty = False
        return True
    except (OSError, TypeError, ValueError):
        # Keep the dirty flag set so a later idle cycle or stop can retry.
        return False


def _right_text(draw, right, y, text, color, font_size):
    x = right - draw.len(text, font_size)
    draw.text(Vector(x, y), text, color, font_size)


def _draw_stack(draw, width):
    panel_x = 5
    panel_y = 25
    panel_w = width - 10
    panel_h = 113
    draw.fill_rectangle(Vector(panel_x + 2, panel_y + 3), Vector(panel_w, panel_h), COLOR_SHADOW)
    draw.fill_rectangle(Vector(panel_x, panel_y), Vector(panel_w, panel_h), COLOR_EDGE)
    draw.fill_rectangle(Vector(panel_x + 2, panel_y + 2), Vector(panel_w - 4, panel_h - 4), COLOR_LCD)

    labels = ("T", "Z", "Y")
    for row in range(3):
        y = panel_y + 7 + row * 19
        draw.text(Vector(panel_x + 8, y), labels[row], COLOR_LCD_MID, FONT_XTRA_SMALL)
        _right_text(draw, width - 14, y, calculator.display(3 - row), COLOR_LCD_DARK, FONT_SMALL)
        draw.line_custom(
            Vector(panel_x + 27, y + 14),
            Vector(width - 14, y + 14),
            COLOR_LCD_MID,
        )

    x_y = panel_y + 67
    draw.text(Vector(panel_x + 8, x_y + 4), "X", COLOR_LCD_MID, FONT_SMALL)
    x_text = calculator.error if calculator.error else calculator.display(0)
    x_color = COLOR_ERROR if calculator.error else COLOR_LCD_DARK
    x_font = FONT_MEDIUM if len(x_text) <= 22 else FONT_SMALL
    _right_text(draw, width - 14, x_y, x_text, x_color, x_font)

    status = calculator.status
    if len(status) > 34:
        status = status[:34]
    draw.text(Vector(panel_x + 8, panel_y + 99), status, COLOR_LCD_MID, FONT_XTRA_SMALL)


def _key_geometry(draw):
    width = draw.size.x
    height = draw.size.y
    keypad_y = 145
    gap = 3
    margin = 5
    rows = (len(KEYS) + 3) // 4
    key_width = (width - margin * 2 - gap * 3) // 4
    key_height = (height - keypad_y - 5 - gap * (rows - 1)) // rows
    if key_height < 9:
        key_height = 9
    return keypad_y, gap, margin, key_width, key_height


def _draw_key(draw, index, selected, flashed=False):
    keypad_y, gap, margin, key_width, key_height = _key_geometry(draw)
    row = index // 4
    col = index % 4
    x = margin + col * (key_width + gap)
    y = keypad_y + row * (key_height + gap)
    text, _, key_type = KEYS[index]

    # Clear the outline and shadow footprint so individual keys can be refreshed.
    draw.fill_rectangle(
        Vector(x - 1, y - 1),
        Vector(key_width + 4, key_height + 4),
        COLOR_BG,
    )

    if flashed:
        color = COLOR_AMBER
    elif key_type in ("operator", "enter"):
        color = COLOR_KEY_OP
    elif key_type in ("function", "memory"):
        color = COLOR_KEY_FN
    else:
        color = COLOR_KEY

    draw.fill_rectangle(Vector(x + 2, y + 2), Vector(key_width, key_height), COLOR_SHADOW)
    draw.fill_rectangle(Vector(x, y), Vector(key_width, key_height), color)
    draw.line_custom(
        Vector(x + 1, y + 1),
        Vector(x + key_width - 2, y + 1),
        COLOR_KEY_TOP,
    )

    if selected:
        draw.rect(Vector(x - 1, y - 1), Vector(key_width + 2, key_height + 2), COLOR_AMBER)
        draw.rect(Vector(x, y), Vector(key_width, key_height), COLOR_AMBER)

    font_size = FONT_SMALL if key_height >= 20 else FONT_XTRA_SMALL
    font_height = 12 if font_size == FONT_SMALL else 8
    text_x = x + (key_width - draw.len(text, font_size)) // 2
    text_y = y + (key_height - font_height) // 2
    text_color = COLOR_LCD_DARK if flashed else TFT_WHITE
    draw.text(Vector(text_x, text_y), text, text_color, font_size)


def _redraw(view_manager):
    draw = view_manager.draw
    width = draw.size.x
    draw.clear(color=COLOR_BG)

    draw.text(Vector(7, 6), "SimpleRPN", TFT_WHITE, FONT_SMALL)
    draw.text(Vector(82, 9), "4-LEVEL", COLOR_MUTED, FONT_XTRA_SMALL)
    draw.fill_rectangle(Vector(width - 14, 8), Vector(6, 6), COLOR_AMBER)
    _draw_stack(draw, width)

    for index in range(len(KEYS)):
        _draw_key(draw, index, index == selected_index)
    draw.swap()


def _draw_variable_viewer(view_manager):
    draw = view_manager.draw
    width = draw.size.x
    height = draw.size.y
    draw.clear(color=COLOR_BG)

    if variable_view_mode == "store":
        title = "STO VARIABLE"
    elif variable_view_mode == "recall":
        title = "RCL VARIABLE"
    else:
        title = "VARIABLE VIEWER"

    footer_space = 53
    rows_per_column = (height - 29 - footer_space) // 18
    if rows_per_column < 3:
        rows_per_column = 3
    elif rows_per_column > 13:
        rows_per_column = 13
    page_size = rows_per_column * 2
    page_start = (selected_variable // page_size) * page_size
    page_end = page_start + page_size
    if page_end > 26:
        page_end = 26

    draw.fill_rectangle(Vector(0, 0), Vector(width, 23), COLOR_KEY_OP)
    draw.text(Vector(7, 5), title, TFT_WHITE, FONT_SMALL)
    range_text = chr(ord("A") + page_start) + "-" + chr(ord("A") + page_end - 1)
    draw.text(
        Vector(width - draw.len(range_text, FONT_XTRA_SMALL) - 7, 8),
        range_text,
        COLOR_AMBER,
        FONT_XTRA_SMALL,
    )

    cell_width = (width - 14) // 2
    for index in range(page_start, page_end):
        offset = index - page_start
        column = offset // rows_per_column
        row = offset % rows_per_column
        x = 5 + column * (cell_width + 4)
        y = 29 + row * 18
        selected = index == selected_variable
        text_color = COLOR_LCD_DARK if selected else TFT_WHITE
        value_color = COLOR_LCD_DARK if selected else COLOR_MUTED

        if selected:
            draw.fill_rectangle(Vector(x, y), Vector(cell_width, 16), COLOR_AMBER)
        else:
            draw.rect(Vector(x, y), Vector(cell_width, 16), COLOR_KEY)

        name = chr(ord("A") + index)
        value = format_number(calculator.variables[index])
        if not calculator.variable_set[index]:
            value = "--"
        draw.text(Vector(x + 4, y + 2), name, text_color, FONT_SMALL)
        _right_text(
            draw,
            x + cell_width - 4,
            y + 4,
            value,
            value_color,
            FONT_XTRA_SMALL,
        )

    status = calculator.status
    if len(status) > 38:
        status = status[:38]
    draw.text(Vector(7, height - 43), status, COLOR_AMBER, FONT_XTRA_SMALL)
    if variable_view_mode in ("store", "recall"):
        control_line = "A-Z SELECT  ENTER/=/SPACE ACT"
        close_line = "ARROWS SELECT  ESC/BACK/DEL CANCEL"
    else:
        control_line = "ENTER/= RCL  SPACE STORE?"
        close_line = "DEL CLEAR?  ESC/BACK CLOSE"
    draw.text(Vector(7, height - 27), control_line, COLOR_MUTED, FONT_XTRA_SMALL)
    draw.text(Vector(7, height - 14), close_line, COLOR_MUTED, FONT_XTRA_SMALL)
    draw.swap()


def _draw_help(view_manager):
    draw = view_manager.draw
    width = draw.size.x
    draw.clear(color=COLOR_BG)

    draw.fill_rectangle(Vector(0, 0), Vector(width, 23), COLOR_KEY_OP)
    draw.text(Vector(7, 5), "SimpleRPN HELP", TFT_WHITE, FONT_SMALL)
    draw.text(
        Vector(width - 94, 8),
        str(help_page + 1) + "/2",
        COLOR_MUTED,
        FONT_XTRA_SMALL,
    )
    draw.text(Vector(width - 58, 8), "H CLOSE", COLOR_AMBER, FONT_XTRA_SMALL)

    if help_page == 0:
        lines = (
            ("FAST INPUT", COLOR_AMBER),
            ("RETURN / SPACE / =  enter / lift", TFT_WHITE),
            ("TAB / TOUCH  use selected key", TFT_WHITE),
            ("ARROWS       move keypad cursor", TFT_WHITE),
            ("0-9 . + - * / \\  direct input", TFT_WHITE),
            ("% or P       percent of Y", TFT_WHITE),
            ("BS / DEL     edit entry / clear X", TFT_WHITE),
            ("C / ESC      clear X; again: all", TFT_WHITE),
            ("SYSTEM BACK x2  exit app", TFT_WHITE),
            ("OPERATOR SHORTCUTS", COLOR_AMBER),
            ("U divide          I multiply", TFT_WHITE),
            ("J subtract        K add", TFT_WHITE),
            ("OTHER SHORTCUTS", COLOR_AMBER),
            ("C clear X  D drop  S swap  N sign", TFT_WHITE),
            ("Q sqrt  X square  R reciprocal", TFT_WHITE),
            ("T store  L recall  V vars  H help", TFT_WHITE),
            ("H / ESC / BACK  close help", COLOR_MUTED),
            ("LEFT / RIGHT  change help page", COLOR_MUTED),
        )
    else:
        lines = (
            ("MEMORY", COLOR_AMBER),
            ("T / STO    choose variable A-Z", TFT_WHITE),
            ("L / RCL    choose variable A-Z", TFT_WHITE),
            ("V / VARS   open variable viewer", TFT_WHITE),
            ("STO copies X; RCL lifts into X", COLOR_MUTED),
            ("VARIABLE VIEWER", COLOR_AMBER),
            ("A-Z / ARROWS  select variable", TFT_WHITE),
            ("RET / TOUCH / =  recall selected", TFT_WHITE),
            ("SPACE       arm store X", TFT_WHITE),
            ("DEL         arm variable clear", TFT_WHITE),
            ("RET / =     confirm armed action", TFT_WHITE),
            ("ESC / BACK  cancel / close", TFT_WHITE),
            ("Pending STO/RCL: A-Z selects", COLOR_MUTED),
            ("RET / TOUCH / = / SPACE confirms", COLOR_MUTED),
            ("PERCENT", COLOR_AMBER),
            ("200 RET 15 % + = 230", TFT_WHITE),
            ("Y remains base after % for + / -", COLOR_MUTED),
            ("H/ESC/BACK close; LEFT/RIGHT page", COLOR_MUTED),
        )
    help_font = FONT_SMALL if draw.size.y >= 300 else FONT_XTRA_SMALL
    line_step = 15 if draw.size.y >= 300 else 11
    y = 29
    for text, color in lines:
        draw.text(Vector(8, y), text, color, help_font)
        y += line_step
    draw.swap()


def _reset_variable_confirmation():
    global variable_confirm_action, variable_confirm_index
    variable_confirm_action = None
    variable_confirm_index = -1


def _set_variable_selection_status():
    name = chr(ord("A") + selected_variable)
    if variable_view_mode == "store":
        calculator.status = "STO " + name + ": ENTER TO CONFIRM"
    elif variable_view_mode == "recall":
        calculator.status = "RCL " + name + ": ENTER TO CONFIRM"
    else:
        calculator.status = "SELECTED " + name


def _arm_variable_confirmation(action):
    global variable_confirm_action, variable_confirm_index
    variable_confirm_action = action
    variable_confirm_index = selected_variable
    name = chr(ord("A") + selected_variable)
    if action == "store":
        if calculator.variable_set[selected_variable]:
            calculator.status = "OVERWRITE " + name + "? ENTER YES"
        else:
            calculator.status = "STORE X TO " + name + "? ENTER YES"
    elif calculator.variable_set[selected_variable]:
        calculator.status = "DELETE " + name + "? ENTER/DEL YES"
    else:
        calculator.status = name + " IS ALREADY EMPTY"
        _reset_variable_confirmation()


def _confirm_variable_action(view_manager):
    action = variable_confirm_action
    index = variable_confirm_index
    _reset_variable_confirmation()
    if action == "store" and index >= 0:
        _complete_variable_action(view_manager, index, "store")
        return True
    if action == "delete" and index >= 0:
        calculator.clear_variable(index)
        _queue_save()
        _draw_variable_viewer(view_manager)
        return True
    return False


def _open_variable_viewer(view_manager, mode):
    global variable_view_mode, flash_index, escape_armed
    variable_view_mode = mode
    _reset_variable_confirmation()
    flash_index = -1
    escape_armed = False
    if mode == "store":
        calculator.status = "STO: CHOOSE A-Z"
    elif mode == "recall":
        calculator.status = "RCL: CHOOSE A-Z"
    else:
        calculator.status = "BROWSE A-Z"
    _draw_variable_viewer(view_manager)


def _close_variable_viewer(view_manager):
    global variable_view_mode, flash_index, escape_armed
    variable_view_mode = None
    _reset_variable_confirmation()
    flash_index = -1
    escape_armed = False
    _redraw(view_manager)


def _complete_variable_action(view_manager, index, action=None):
    """Apply a viewer action, returning True when the viewer closes."""
    global variable_view_mode, selected_variable
    selected_variable = index
    _reset_variable_confirmation()
    action = action or variable_view_mode

    if action == "store":
        calculator.store(index)
        _queue_save()
        if variable_view_mode == "view":
            _draw_variable_viewer(view_manager)
            return False
        variable_view_mode = None
        _redraw(view_manager)
        return True

    if action == "recall":
        if not calculator.recall(index):
            _draw_variable_viewer(view_manager)
            return False
        _queue_save()
        variable_view_mode = None
        _redraw(view_manager)
        return True

    return False


def _move_variable_selection(view_manager, button):
    global selected_variable
    rows_per_column = (view_manager.draw.size.y - 29 - 53) // 18
    if rows_per_column < 3:
        rows_per_column = 3
    elif rows_per_column > 13:
        rows_per_column = 13
    if button == BUTTON_UP:
        selected_variable = (selected_variable - 1) % 26
    elif button == BUTTON_DOWN:
        selected_variable = (selected_variable + 1) % 26
    elif button == BUTTON_LEFT:
        candidate = selected_variable - rows_per_column
        if candidate >= 0:
            selected_variable = candidate
    elif button == BUTTON_RIGHT:
        candidate = selected_variable + rows_per_column
        if candidate < 26:
            selected_variable = candidate


def _refresh_stack(view_manager, swap=True):
    draw = view_manager.draw
    _draw_stack(draw, draw.size.x)
    if swap:
        draw.swap()


def _flash_action(view_manager, action):
    global flash_index, flash_until
    index = ACTION_INDEX.get(action)
    if index is None:
        return
    draw = view_manager.draw
    if flash_index >= 0 and flash_index != index:
        _draw_key(draw, flash_index, flash_index == selected_index)
    flash_index = index
    flash_until = ticks_ms() + 90
    _draw_key(draw, index, index == selected_index, True)
    draw.swap()


def _finish_flash(view_manager):
    global flash_index
    if flash_index < 0 or ticks_diff(ticks_ms(), flash_until) < 0:
        return
    index = flash_index
    flash_index = -1
    draw = view_manager.draw
    _draw_key(draw, index, index == selected_index)
    draw.swap()


def _run_variable_viewer(view_manager, button):
    global selected_variable
    if button in (BUTTON_BACK, BUTTON_ESCAPE):
        if variable_confirm_action is not None:
            _reset_variable_confirmation()
            calculator.status = "ACTION CANCELLED"
            _draw_variable_viewer(view_manager)
            return
        _close_variable_viewer(view_manager)
        return

    if button in (BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT):
        _reset_variable_confirmation()
        _move_variable_selection(view_manager, button)
        _set_variable_selection_status()
        _draw_variable_viewer(view_manager)
        return

    if BUTTON_A <= button <= BUTTON_Z:
        _reset_variable_confirmation()
        index = button - BUTTON_A
        selected_variable = index
        _set_variable_selection_status()
        _draw_variable_viewer(view_manager)
        return

    if button in (BUTTON_BACKSPACE, BUTTON_DELETE):
        if variable_view_mode in ("store", "recall"):
            calculator.status = variable_view_mode.upper() + " CANCELLED"
            _close_variable_viewer(view_manager)
            return
        if (
            variable_confirm_action == "delete"
            and variable_confirm_index == selected_variable
        ):
            _confirm_variable_action(view_manager)
            return
        _arm_variable_confirmation("delete")
        _draw_variable_viewer(view_manager)
        return

    if button in (BUTTON_CENTER, BUTTON_EQUAL):
        if variable_confirm_action is not None:
            _confirm_variable_action(view_manager)
            return
        action = variable_view_mode if variable_view_mode != "view" else "recall"
        _complete_variable_action(view_manager, selected_variable, action)
        return

    if button == BUTTON_SPACE:
        if variable_view_mode != "view":
            _complete_variable_action(view_manager, selected_variable, variable_view_mode)
            return
        _arm_variable_confirmation("store")
        _draw_variable_viewer(view_manager)


def _perform_clear():
    global escape_armed
    if escape_armed:
        calculator.clear()
        escape_armed = False
    else:
        calculator.clear_x()
        escape_armed = True
    _queue_save()


def _perform(action):
    if action and action[0] >= "0" and action[0] <= "9" and len(action) == 1:
        calculator.digit(action)
    elif action == "decimal":
        calculator.decimal()
    elif action == "enter":
        calculator.enter()
    elif action == "clear":
        _perform_clear()
        return
    elif action == "drop":
        calculator.drop()
    elif action == "swap":
        calculator.swap()
    elif action == "negate":
        calculator.negate()
    elif action == "percent":
        calculator.percent()
    elif action in ("square", "sqrt", "reciprocal"):
        calculator.unary(action)
    elif action in ("add", "subtract", "multiply", "divide"):
        calculator.binary(action)
    else:
        return
    _queue_save()


def start(view_manager):
    global calculator, selected_index, help_visible, help_page, variable_view_mode
    global selected_variable, variable_confirm_action, variable_confirm_index
    global escape_armed, back_exit_armed, flash_index, storage, state_dirty
    global save_due, last_saved_state
    calculator = RPNStack()
    storage = view_manager.storage
    state_dirty = False
    save_due = 0
    last_saved_state = ""
    _load_state()
    selected_index = ENTER_INDEX
    help_visible = False
    help_page = 0
    variable_view_mode = None
    selected_variable = 0
    variable_confirm_action = None
    variable_confirm_index = -1
    escape_armed = False
    back_exit_armed = False
    flash_index = -1
    view_manager.input_manager.reset()
    _redraw(view_manager)
    return True


def run(view_manager):
    global selected_index, help_visible, help_page, escape_armed, back_exit_armed
    global flash_index
    inp = view_manager.input_manager
    button = inp.button
    if button == -1:
        if state_dirty and ticks_diff(ticks_ms(), save_due) >= 0:
            _save_state()
        if not help_visible and variable_view_mode is None:
            _finish_flash(view_manager)
        return

    if button != BUTTON_BACK:
        back_exit_armed = False

    if variable_view_mode is not None:
        _run_variable_viewer(view_manager, button)
        inp.reset()
        return

    if help_visible:
        if button in (BUTTON_H, BUTTON_ESCAPE, BUTTON_BACK):
            help_visible = False
            flash_index = -1
            inp.reset()
            _redraw(view_manager)
            return
        if button == BUTTON_LEFT:
            help_page = (help_page - 1) % 2
            inp.reset()
            _draw_help(view_manager)
            return
        if button == BUTTON_RIGHT:
            help_page = (help_page + 1) % 2
            inp.reset()
            _draw_help(view_manager)
            return
        inp.reset()
        return

    if button == BUTTON_H:
        help_visible = True
        help_page = 0
        escape_armed = False
        flash_index = -1
        inp.reset()
        _draw_help(view_manager)
        return

    if button == BUTTON_BACK:
        escape_armed = False
        if calculator.entering:
            calculator.backspace()
            _queue_save()
            back_exit_armed = False
            escape_armed = False
            inp.reset()
            _refresh_stack(view_manager)
            return
        if not back_exit_armed:
            back_exit_armed = True
            calculator.status = "BACK AGAIN: EXIT"
            inp.reset()
            _refresh_stack(view_manager)
            return
        back_exit_armed = False
        _save_state(force=True)
        inp.reset()
        view_manager.back()
        return

    action = None
    direct_action = False
    old_selected_index = selected_index
    if button == BUTTON_LEFT:
        selected_index = (selected_index - 1) % len(KEYS)
    elif button == BUTTON_RIGHT:
        selected_index = (selected_index + 1) % len(KEYS)
    elif button == BUTTON_UP:
        selected_index = (selected_index - 4) % len(KEYS)
    elif button == BUTTON_DOWN:
        selected_index = (selected_index + 4) % len(KEYS)
    elif button == BUTTON_CENTER:
        # PicoCalc Return arrives as CENTER; touch CENTER selects the UI key.
        if inp.has_touch_support:
            action = KEYS[selected_index][1]
        else:
            action = "enter"
            direct_action = True
    elif button == BUTTON_SPACE:
        action = "enter"
        direct_action = True
    elif button == BUTTON_TAB:
        action = KEYS[selected_index][1]
    elif BUTTON_0 <= button <= BUTTON_9:
        action = str(button - BUTTON_0)
        direct_action = True
    elif button == BUTTON_PERIOD:
        action = "decimal"
        direct_action = True
    elif button in (BUTTON_SLASH, BUTTON_BACKSLASH):
        action = "divide"
        direct_action = True
    elif button == BUTTON_ASTERISK:
        action = "multiply"
        direct_action = True
    elif button == BUTTON_MINUS:
        action = "subtract"
        direct_action = True
    elif button == BUTTON_PLUS:
        action = "add"
        direct_action = True
    elif button == BUTTON_EQUAL:
        action = "enter"
        direct_action = True
    elif button == BUTTON_PERCENT:
        action = "percent"
        direct_action = True
    elif button in (BUTTON_BACKSPACE, BUTTON_DELETE):
        calculator.backspace()
        _queue_save()
        escape_armed = False
        _refresh_stack(view_manager)
    elif button == BUTTON_ESCAPE:
        _perform_clear()
        _refresh_stack(view_manager, False)
        _flash_action(view_manager, "clear")
    elif button == BUTTON_C:
        action = "clear"
        direct_action = True
    elif button == BUTTON_D:
        action = "drop"
        direct_action = True
    elif button == BUTTON_I:
        action = "multiply"
        direct_action = True
    elif button == BUTTON_J:
        action = "subtract"
        direct_action = True
    elif button == BUTTON_K:
        action = "add"
        direct_action = True
    elif button == BUTTON_L:
        action = "recall"
        direct_action = True
    elif button == BUTTON_N:
        action = "negate"
        direct_action = True
    elif button == BUTTON_P:
        action = "percent"
        direct_action = True
    elif button == BUTTON_Q:
        action = "sqrt"
        direct_action = True
    elif button == BUTTON_R:
        action = "reciprocal"
        direct_action = True
    elif button == BUTTON_S:
        action = "swap"
        direct_action = True
    elif button == BUTTON_T:
        action = "store"
        direct_action = True
    elif button == BUTTON_U:
        action = "divide"
        direct_action = True
    elif button == BUTTON_V:
        action = "variables"
        direct_action = True
    elif button == BUTTON_X:
        action = "square"
        direct_action = True

    if action is not None:
        if action != "clear":
            escape_armed = False
        if action == "help":
            help_visible = True
            help_page = 0
            flash_index = -1
            inp.reset()
            _draw_help(view_manager)
            return
        if action in ("store", "recall", "variables"):
            mode = action if action != "variables" else "view"
            inp.reset()
            _open_variable_viewer(view_manager, mode)
            return
        _perform(action)
        if direct_action:
            _refresh_stack(view_manager, False)
            _flash_action(view_manager, action)
        else:
            _refresh_stack(view_manager)

    if old_selected_index != selected_index:
        escape_armed = False
        draw = view_manager.draw
        if flash_index >= 0:
            _draw_key(draw, flash_index, flash_index == old_selected_index)
            flash_index = -1
        _draw_key(draw, old_selected_index, False)
        _draw_key(draw, selected_index, True)
        draw.swap()

    inp.reset()


def stop(view_manager):
    global calculator, selected_index, help_visible, help_page, variable_view_mode
    global selected_variable, variable_confirm_action, variable_confirm_index
    global escape_armed, back_exit_armed, flash_index, storage, state_dirty
    global save_due, last_saved_state
    _save_state(force=True)
    calculator = None
    storage = None
    state_dirty = False
    save_due = 0
    last_saved_state = ""
    selected_index = ENTER_INDEX
    help_visible = False
    help_page = 0
    variable_view_mode = None
    selected_variable = 0
    variable_confirm_action = None
    variable_confirm_index = -1
    escape_armed = False
    back_exit_armed = False
    flash_index = -1
    from gc import collect

    collect()
