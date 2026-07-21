"""SimpleRPN: a compact four-level RPN calculator for Picoware."""

from math import sqrt
from utime import ticks_diff, ticks_ms

from picoware.system.vector import Vector
from picoware.system.font import FONT_XTRA_SMALL, FONT_SMALL, FONT_MEDIUM
from picoware.system.colors import TFT_WHITE
from picoware.system.buttons import (
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
    BUTTON_SPACE,
    BUTTON_ESCAPE,
    BUTTON_C,
    BUTTON_D,
    BUTTON_H,
    BUTTON_N,
    BUTTON_P,
    BUTTON_Q,
    BUTTON_R,
    BUTTON_S,
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

    __slots__ = ("stack", "entry", "entering", "lift_on_entry", "error", "status")

    def __init__(self):
        self.stack = [0.0, 0.0, 0.0, 0.0]  # X, Y, Z, T
        self.entry = ""
        self.entering = False
        self.lift_on_entry = False
        self.error = ""
        self.status = "READY"

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
        self.status = "X CLEARED - ESC AGAIN: ALL"

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
        if self.entry == "-":
            self.entry = ""
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

    def display(self, level):
        if level == 0 and self.entering:
            return self.entry if self.entry not in ("", "-") else "0"
        return format_number(self.stack[level])


calculator = None
selected_index = ENTER_INDEX
help_visible = False
escape_armed = False
flash_index = -1
flash_until = 0


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
    key_width = (width - margin * 2 - gap * 3) // 4
    key_height = (height - keypad_y - 5 - gap * 5) // 6
    if key_height < 13:
        key_height = 13
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
    elif key_type == "function":
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


def _draw_help(view_manager):
    draw = view_manager.draw
    width = draw.size.x
    draw.clear(color=COLOR_BG)

    draw.fill_rectangle(Vector(0, 0), Vector(width, 23), COLOR_KEY_OP)
    draw.text(Vector(7, 5), "SimpleRPN HELP", TFT_WHITE, FONT_SMALL)
    draw.text(Vector(width - 58, 8), "H CLOSE", COLOR_AMBER, FONT_XTRA_SMALL)

    lines = (
        ("FAST INPUT", COLOR_AMBER),
        ("RETURN   enter / lift stack", TFT_WHITE),
        ("SPACE    use highlighted key", TFT_WHITE),
        ("0-9 . +-*/%  direct input", TFT_WHITE),
        ("ARROWS   move cursor only", TFT_WHITE),
        ("BS/DEL   edit current X", TFT_WHITE),
        ("ESC      clear X; again: all", TFT_WHITE),
        ("", TFT_WHITE),
        ("SHORTCUTS", COLOR_AMBER),
        ("D drop   S swap   N sign", TFT_WHITE),
        ("Q sqrt   X square R 1/x", TFT_WHITE),
        ("C clear all       H help", TFT_WHITE),
        ("", TFT_WHITE),
        ("PERCENT", COLOR_AMBER),
        ("Tax/tip: 200 RET 15 % +", TFT_WHITE),
        ("Discount: 200 RET 15 % -", TFT_WHITE),
        ("Y stays as the base after %", COLOR_MUTED),
    )
    y = 29
    for text, color in lines:
        draw.text(Vector(8, y), text, color, FONT_SMALL)
        y += 16
    draw.swap()


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


def _perform(action):
    if action and action[0] >= "0" and action[0] <= "9" and len(action) == 1:
        calculator.digit(action)
    elif action == "decimal":
        calculator.decimal()
    elif action == "enter":
        calculator.enter()
    elif action == "clear":
        calculator.clear()
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


def start(view_manager):
    global calculator, selected_index, help_visible, escape_armed, flash_index
    calculator = RPNStack()
    selected_index = ENTER_INDEX
    help_visible = False
    escape_armed = False
    flash_index = -1
    view_manager.input_manager.reset()
    _redraw(view_manager)
    return True


def run(view_manager):
    global selected_index, help_visible, escape_armed, flash_index
    inp = view_manager.input_manager
    button = inp.button
    if button == -1:
        if not help_visible:
            _finish_flash(view_manager)
        return

    if help_visible:
        if button in (BUTTON_H, BUTTON_ESCAPE, BUTTON_BACK):
            help_visible = False
            flash_index = -1
            inp.reset()
            _redraw(view_manager)
            return
        inp.reset()
        return

    if button == BUTTON_H:
        help_visible = True
        escape_armed = False
        flash_index = -1
        inp.reset()
        _draw_help(view_manager)
        return

    if button == BUTTON_BACK:
        if calculator.entering:
            calculator.backspace()
            escape_armed = False
            inp.reset()
            _refresh_stack(view_manager)
            return
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
        if inp.has_touch_support:
            action = KEYS[selected_index][1]
        else:
            action = "enter"
            direct_action = True
    elif button == BUTTON_SPACE:
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
    elif button == BUTTON_BACKSPACE:
        calculator.backspace()
        escape_armed = False
        _refresh_stack(view_manager)
    elif button == BUTTON_ESCAPE:
        if escape_armed:
            calculator.clear()
        else:
            calculator.clear_x()
            escape_armed = True
        _refresh_stack(view_manager, False)
        _flash_action(view_manager, "clear")
    elif button == BUTTON_C:
        action = "clear"
        direct_action = True
    elif button == BUTTON_D:
        action = "drop"
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
    elif button == BUTTON_X:
        action = "square"
        direct_action = True

    if action is not None:
        escape_armed = False
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
    global calculator, selected_index, help_visible, escape_armed, flash_index
    calculator = None
    selected_index = ENTER_INDEX
    help_visible = False
    escape_armed = False
    flash_index = -1
    from gc import collect

    collect()
