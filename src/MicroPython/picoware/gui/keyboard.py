"""Keyboard - On-screen keyboard widget."""

from picoware.system.buttons import (
    BUTTON_UP,
    BUTTON_DOWN,
    BUTTON_LEFT,
    BUTTON_RIGHT,
    BUTTON_CENTER,
    BUTTON_SPACE,
    BUTTON_A,
    BUTTON_B,
    BUTTON_C,
    BUTTON_D,
    BUTTON_E,
    BUTTON_F,
    BUTTON_G,
    BUTTON_H,
    BUTTON_I,
    BUTTON_J,
    BUTTON_K,
    BUTTON_L,
    BUTTON_M,
    BUTTON_N,
    BUTTON_O,
    BUTTON_P,
    BUTTON_Q,
    BUTTON_R,
    BUTTON_S,
    BUTTON_T,
    BUTTON_U,
    BUTTON_V,
    BUTTON_W,
    BUTTON_X,
    BUTTON_Y,
    BUTTON_Z,
    BUTTON_0,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    BUTTON_5,
    BUTTON_6,
    BUTTON_7,
    BUTTON_8,
    BUTTON_9,
    BUTTON_PERIOD,
    BUTTON_COMMA,
    BUTTON_SEMICOLON,
    BUTTON_MINUS,
    BUTTON_EQUAL,
    BUTTON_LEFT_BRACKET,
    BUTTON_RIGHT_BRACKET,
    BUTTON_SLASH,
    BUTTON_BACKSLASH,
    BUTTON_PIPE,
    BUTTON_UNDERSCORE,
    BUTTON_COLON,
    BUTTON_SINGLE_QUOTE,
    BUTTON_DOUBLE_QUOTE,
    BUTTON_AT,
    BUTTON_EXCLAMATION,
    BUTTON_HASH,
    BUTTON_DOLLAR,
    BUTTON_PERCENT,
    BUTTON_CARET,
    BUTTON_AMPERSAND,
    BUTTON_ASTERISK,
    BUTTON_LEFT_PARENTHESIS,
    BUTTON_RIGHT_PARENTHESIS,
    BUTTON_QUESTION,
    BUTTON_LESS_THAN,
    BUTTON_GREATER_THAN,
    BUTTON_BACKSPACE,
    BUTTON_LEFT_BRACE,
    BUTTON_RIGHT_BRACE,
    BUTTON_PLUS,
    BUTTON_BACK,
)


# Define the keyboard layout structure
class KeyLayout:
    """Structure to hold key layout information"""

    __slots__ = ("normal", "shifted", "width")

    def __init__(self, normal: str, shifted: str, width: int = 1) -> None:
        """Initialize a key layout entry.

        Args:
            normal (str): The character for the normal state.
            shifted (str): The character for the shifted state.
            width (int): The key width in units. Defaults to 1.
        """
        self.normal = normal
        self.shifted = shifted
        self.width = width  # Width in units (1 = normal key, 2 = double width, etc.)


class Keyboard:
    """A simple on-screen keyboard class for a GUI."""

    # Define keyboard rows
    ROW1 = [
        KeyLayout("1", "!", 1),
        KeyLayout("2", "@", 1),
        KeyLayout("3", "#", 1),
        KeyLayout("4", "$", 1),
        KeyLayout("5", "%", 1),
        KeyLayout("6", "^", 1),
        KeyLayout("7", "&", 1),
        KeyLayout("8", "*", 1),
        KeyLayout("9", "(", 1),
        KeyLayout("0", ")", 1),
        KeyLayout("-", "_", 1),
        KeyLayout("=", "+", 1),
        KeyLayout("\b", "\b", 1),  # Backspace (special)
    ]

    ROW2 = [
        KeyLayout("q", "Q", 1),
        KeyLayout("w", "W", 1),
        KeyLayout("e", "E", 1),
        KeyLayout("r", "R", 1),
        KeyLayout("t", "T", 1),
        KeyLayout("y", "Y", 1),
        KeyLayout("u", "U", 1),
        KeyLayout("i", "I", 1),
        KeyLayout("o", "O", 1),
        KeyLayout("p", "P", 1),
        KeyLayout("[", "{", 1),
        KeyLayout("]", "}", 1),
        KeyLayout("?", "?", 1),  # ? is a special function key (CLR)
    ]

    ROW3 = [
        KeyLayout("\x01", "\x01", 1),  # Caps Lock (special)
        KeyLayout("a", "A", 1),
        KeyLayout("s", "S", 1),
        KeyLayout("d", "D", 1),
        KeyLayout("f", "F", 1),
        KeyLayout("g", "G", 1),
        KeyLayout("h", "H", 1),
        KeyLayout("j", "J", 1),
        KeyLayout("k", "K", 1),
        KeyLayout("l", "L", 1),
        KeyLayout(";", ":", 1),
        KeyLayout("'", '"', 1),
        KeyLayout("\r", "\r", 1),  # Enter (special)
    ]

    ROW4 = [
        KeyLayout("\x02", "\x02", 1),  # Shift (special)
        KeyLayout("z", "Z", 1),
        KeyLayout("x", "X", 1),
        KeyLayout("c", "C", 1),
        KeyLayout("v", "V", 1),
        KeyLayout("b", "B", 1),
        KeyLayout("n", "N", 1),
        KeyLayout("m", "M", 1),
        KeyLayout(",", "<", 1),
        KeyLayout(".", ">", 1),
        KeyLayout("/", "?", 1),
        KeyLayout("\\", "|", 1),
        KeyLayout("\x02", "\x02", 1),  # Right Shift (special)
    ]

    ROW5 = [
        KeyLayout(" ", " ", 6),  # Space bar
        KeyLayout("\x03", "\x03", 2),  # Save (special)
    ]

    ROWS = [ROW1, ROW2, ROW3, ROW4, ROW5]
    ROW_SIZES = [13, 13, 13, 13, 2]
    NUM_ROWS = 5

    def __init__(
        self,
        draw,
        input_manager,
        text_color: int = 0xFFFF,
        background_color: int = 0x0000,
        selected_color: int = 0x001F,
        on_save_callback: callable = None,
    ) -> None:
        """Initialize the keyboard with drawing context and input manager.

        Args:
            draw (Draw): Drawing context for rendering the keyboard.
            input_manager: Input manager to handle button presses.
            text_color (int): Color for the text on keys and textbox. Defaults to 0xFFFF.
            background_color (int): Background color for keys and textbox. Defaults to 0x0000.
            selected_color (int): Color for the selected key highlight. Defaults to 0x001F.
            on_save_callback (callable): Optional callback called when "Save" is pressed. Defaults to None.
        """
        from picoware.system.vector import Vector
        from picoware.system.auto_complete import AutoComplete
        from picoware.system.boards import (
            BOARD_ID,
            BOARD_FLIPPER_ZERO,
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        )

        self._is_flipper = BOARD_ID == BOARD_FLIPPER_ZERO

        self._rotated = BOARD_ID == BOARD_WAVESHARE_3_49_RP2350
        if self._rotated:
            from picoware.gui.keyboard_rotation import KeyboardRotation
            draw = KeyboardRotation(draw)
        self.draw = draw
        self.input_manager = input_manager
        self.text_color = text_color
        self.background_color = background_color
        self.selected_color = selected_color
        self.on_save_callback = on_save_callback

        # Initialize cursor position to top-left key
        self.cursor_row = 0
        self.cursor_col = 0
        self.text_cursor_x = 0
        self.text_cursor_y = 0

        # Keyboard state
        self.is_shift_pressed = False
        self.is_manual_shift = False
        self.is_caps_lock_on = False
        self.current_key: int = -1
        self.dpad_input: int = -1
        self._response = ""
        self.is_save_pressed = False
        self.just_stopped = False
        self.current_title = "Enter Text"
        self.is_in_textbox = False
        self.text_cursor_position = 0
        self.selected_suggestion_index = -1  # -1 means no suggestion selected

        # A square inscribed in the round panel keeps every control visible.
        self._layout_width = draw.size.x
        self._layout_height = draw.size.y
        if BOARD_ID in (BOARD_WAVESHARE_1_28_RP2350, BOARD_WAVESHARE_1_43_RP2350):
            side = int(min(draw.size.x, draw.size.y) * 0.707)
            self._layout_width = self._layout_height = side
        self._layout_x = (draw.size.x - self._layout_width) // 2
        self._layout_y = (draw.size.y - self._layout_height) // 2
        self.KEY_MARGIN = 0 if self._is_flipper else 2
        self.KEY_SPACING = 1
        self._touch_enabled = input_manager.has_touch_support

        font_height = draw.font_size.y
        padding = 1 if self._is_flipper else 3
        self.max_chars_per_line = max(
            1, (self._layout_width - 2 * (self.KEY_MARGIN + padding + 1))
            // draw.font_size.x - 1,
        )
        preferred_height = self._layout_height * 45 // 320
        self.max_lines = max(1, (preferred_height - 2 * (padding + 1)) // (font_height + 1))
        self.TEXTBOX_HEIGHT = 2 * (padding + 1) + self.max_lines * font_height + self.max_lines - 1
        self._text_y = self._layout_y + padding + 1
        self.size_vec = Vector(0, 0)
        self.text_vec = Vector(self._layout_x + self.KEY_MARGIN + padding + 1, self._text_y)
        self.cursor = Vector(0, 0)
        self.text_border_pos = Vector(self._layout_x + self.KEY_MARGIN, self._layout_y)
        self.text_border_size = Vector(
            self._layout_width - 2 * self.KEY_MARGIN, self.TEXTBOX_HEIGHT,
        )
        title_y = self._layout_y + self.TEXTBOX_HEIGHT + 1
        self.title_vec = Vector(0, title_y)
        self._keys_y = title_y + font_height + 1 if not self._is_flipper else title_y - 1
        self._suggestion_y = self._layout_y + self._layout_height - font_height
        self.KEY_HEIGHT = (self._suggestion_y - self._keys_y - (self.NUM_ROWS - 1)) // self.NUM_ROWS
        self.keyboard_height = self.NUM_ROWS * self.KEY_HEIGHT + self.NUM_ROWS - 1
        self.text_box_pos_vec = Vector(self._layout_x, self._keys_y)
        self.text_box_pos_size = Vector(self._layout_width, self.keyboard_height)
        self.KEY_WIDTH = max(1, self._layout_width * 22 // 320)
        self._key_font = draw.font
        self._key_rects = self._build_key_rects()
        self.title = self.current_title

        self.manual_keys = {
            BUTTON_PERIOD: ".",
            BUTTON_COMMA: ",",
            BUTTON_SEMICOLON: ";",
            BUTTON_MINUS: "-",
            BUTTON_EQUAL: "=",
            BUTTON_LEFT_BRACKET: "[",
            BUTTON_RIGHT_BRACKET: "]",
            BUTTON_SLASH: "/",
            BUTTON_BACKSLASH: "\\",
            BUTTON_PIPE: "|",
            BUTTON_UNDERSCORE: "_",
            BUTTON_COLON: ":",
            BUTTON_SINGLE_QUOTE: "'",
            BUTTON_DOUBLE_QUOTE: '"',
            BUTTON_AT: "@",
            BUTTON_EXCLAMATION: "!",
            BUTTON_HASH: "#",
            BUTTON_DOLLAR: "$",
            BUTTON_PERCENT: "%",
            BUTTON_CARET: "^",
            BUTTON_AMPERSAND: "&",
            BUTTON_ASTERISK: "*",
            BUTTON_LEFT_PARENTHESIS: "(",
            BUTTON_RIGHT_PARENTHESIS: ")",
            BUTTON_QUESTION: "?",
            BUTTON_LESS_THAN: "<",
            BUTTON_GREATER_THAN: ">",
            BUTTON_LEFT_BRACE: "{",
            BUTTON_RIGHT_BRACE: "}",
            BUTTON_PLUS: "+",
        }

        self.key_mappings = {
            BUTTON_1: (0, 0),
            BUTTON_2: (0, 1),
            BUTTON_3: (0, 2),
            BUTTON_4: (0, 3),
            BUTTON_5: (0, 4),
            BUTTON_6: (0, 5),
            BUTTON_7: (0, 6),
            BUTTON_8: (0, 7),
            BUTTON_9: (0, 8),
            BUTTON_0: (0, 9),
            BUTTON_A: (2, 1),
            BUTTON_B: (3, 5),
            BUTTON_C: (3, 3),
            BUTTON_D: (2, 3),
            BUTTON_E: (1, 2),
            BUTTON_F: (2, 4),
            BUTTON_G: (2, 5),
            BUTTON_H: (2, 6),
            BUTTON_I: (1, 7),
            BUTTON_J: (2, 7),
            BUTTON_K: (2, 8),
            BUTTON_L: (2, 9),
            BUTTON_M: (3, 7),
            BUTTON_N: (3, 6),
            BUTTON_O: (1, 8),
            BUTTON_P: (1, 9),
            BUTTON_Q: (1, 0),
            BUTTON_R: (1, 3),
            BUTTON_S: (2, 2),
            BUTTON_T: (1, 4),
            BUTTON_U: (1, 6),
            BUTTON_V: (3, 4),
            BUTTON_W: (1, 1),
            BUTTON_X: (3, 2),
            BUTTON_Y: (1, 5),
            BUTTON_Z: (3, 1),
            BUTTON_BACKSPACE: (0, 12),
        }

        self.d_pad = {
            BUTTON_UP,
            BUTTON_DOWN,
            BUTTON_LEFT,
            BUTTON_RIGHT,
        }

        self._show_keyboard = True
        self._auto_complete = AutoComplete()
        self._auto_complete_words_set = False
        self._auto_complete_words = []

    def __del__(self) -> None:
        """Clean up keyboard resources."""
        self.reset()
        self.current_title = ""
        self.size_vec = None
        self.text_vec = None
        self.cursor = None
        self.text_box_pos_vec = None
        self.text_box_pos_size = None
        self.text_border_pos = None
        self.text_border_size = None
        self.title_vec = None
        self._key_rects = None
        self.manual_keys = {}
        self.key_mappings = {}
        self.d_pad = {}
        del self._auto_complete
        self._auto_complete = None
        self._auto_complete_words.clear()

    @property
    def callback(self) -> callable:
        """Returns the current save callback function"""
        return self.on_save_callback

    @callback.setter
    def callback(self, value: callable) -> None:
        """Set the current save callback function.

        Args:
            value (callable): The new callback function.
        """
        self.on_save_callback = value

    @property
    def is_finished(self) -> bool:
        """Returns whether the keyboard is finished"""
        return self.is_save_pressed

    @property
    def keyboard_width(self) -> int:
        """Returns the keyboard width/width of the display"""
        return self.draw.size.x

    @property
    def show_keyboard(self) -> bool:
        """Returns whether the on-screen keyboard is shown"""
        return self._show_keyboard

    @show_keyboard.setter
    def show_keyboard(self, value: bool) -> None:
        """Set whether the on-screen keyboard is shown.

        Args:
            value (bool): True to show the keyboard.
        """
        self._show_keyboard = value

    @property
    def title(self) -> str:
        """Returns the current title of the keyboard"""
        return self.current_title

    @title.setter
    def title(self, value: str) -> None:
        """Set the current title of the keyboard.

        Args:
            value (str): The new title.
        """
        self.current_title = value
        self._display_title = self._fit_text(value, self._layout_width - 2 * self.KEY_MARGIN)
        self.title_vec.x = self._layout_x + (self._layout_width - self.draw.len(self._display_title)) // 2

    @property
    def response(self) -> str:
        """Returns the response string"""
        return self._response

    @response.setter
    def response(self, value: str) -> None:
        """Set the response string.

        Args:
            value (str): The new response string.
        """
        self._response = value
        self.text_cursor_position = len(value)

    @property
    def auto_complete_words(self) -> list[str]:
        """Returns the list of words for auto-completion"""
        return self._auto_complete_words

    @auto_complete_words.setter
    def auto_complete_words(self, value: list[str]) -> None:
        """Set the list of words for auto-completion.

        Args:
            value (list[str]): The new word list.
        """
        self._auto_complete_words = value
        self._auto_complete_words_set = False

    def set_save_callback(self, callback: callable) -> None:
        """Set the save callback function.

        Args:
            callback (callable): The callback to call on save.
        """
        self.on_save_callback = callback

    def reset(self) -> None:
        """Resets the keyboard state"""
        self.cursor_row = 0
        self.cursor_col = 0
        self.is_shift_pressed = False
        self.is_caps_lock_on = False
        self._response = ""
        self.just_stopped = False
        self.on_save_callback = None
        self.is_save_pressed = False
        self.title = "Enter Text"
        self.is_in_textbox = False
        self.text_cursor_position = 0
        self.selected_suggestion_index = -1
        self._auto_complete.remove_suggestions()
        self._auto_complete.remove_words()
        self._auto_complete_words_set = False
        self._auto_complete_words.clear()

    def run(self, swap: bool = True, force: bool = False, max_characters: int = 0) -> bool:
        """Run the input manager, handle input, and draw the keyboard.

        Args:
            swap (bool): Whether to swap the display buffer. Defaults to True.
            force (bool): Whether to force a redraw. Defaults to False.
            max_characters (int): The maximum number of characters allowed in the response. 0 means no limit. Defaults to 0.

        Returns:
            bool: True while running, False when stopped.
        """
        if self.just_stopped:
            return False

        self.dpad_input = self.input_manager.button
        if self._rotated:
            self.dpad_input = {
                BUTTON_UP: BUTTON_RIGHT, BUTTON_RIGHT: BUTTON_DOWN,
                BUTTON_DOWN: BUTTON_LEFT, BUTTON_LEFT: BUTTON_UP,
            }.get(self.dpad_input, self.dpad_input)
        has_touch_point = (
            self._touch_enabled
            and self.input_manager.point
            and self.input_manager.point != (0, 0)
        )
        if self.dpad_input != -1 or force or has_touch_point:
            if self.dpad_input == BUTTON_BACK:
                # Exit keyboard without saving
                self.just_stopped = True
                self.input_manager.reset()
                return False

            if not self.is_manual_shift:
                self.is_shift_pressed = self.input_manager.was_capitalized

            self.draw.erase()

            if not self._auto_complete_words_set:
                self._set_auto_complete_words()

            # only process input/redraw if there's input
            self._handle_input(max_characters)
            self._draw_textbox()

            if self._show_keyboard:
                self._draw_keyboard()

            if not self._is_flipper:
                self._draw_text(
                    self.title_vec.x, self.title_vec.y,
                    self._display_title,
                    self.text_color,
                )

            # Draw auto-complete suggestions after keyboard/title
            self._draw_suggestions()

            self.input_manager.reset()

            if swap or force:
                self.draw.swap()

        return True

    def _auto_complete_suggestion(self) -> str:
        """Gets the top auto-complete suggestion based on current response"""
        if self._auto_complete and self._response:
            words = self._response.strip().split()
            if words:
                last_word = words[-1]
                suggestions = self._auto_complete.search(last_word)
                if suggestions:
                    return suggestions[0]
        return ""

    def _auto_complete_suggestions(self) -> tuple:
        """Gets auto-complete suggestions based on current response"""
        if self._auto_complete and self._response:
            words = self._response.strip().split()
            if words:
                last_word = words[-1]
                return self._auto_complete.search(last_word)
        return ()

    def _default_words(self) -> list[str]:
        """Returns a default list of words for auto-completion"""
        return [
            "the",
            "that",
            "hi",
            "hey",
            "help",
            "hello",
            "how",
            "hack",
            "what",
            "JBlanked",
            "PicoCalc",
            "yooo",
            "everyone",
            "anyone",
            "good",
            "great",
            "morning",
            "night",
            "message",
            "awesome",
            "Picoware",
        ]

    def _draw_rectangle(self, x, y, width, height, color):
        """Keep all four borders inside the cell on every LCD driver."""
        right, bottom = x + width - 1, y + height - 1
        self.draw._line(x, y, right, y, color)
        self.draw._line(x, bottom, right, bottom, color)
        self.draw._line(x, y, x, bottom, color)
        self.draw._line(right, y, right, bottom, color)

    def _draw_text(self, x, y, text, color, font_size=None):
        """Use the measured font advance even on drivers that omit spacing."""
        size = self.draw.font if font_size is None else font_size
        if self._rotated:
            self.draw._text(x, y, text, color, size)
            return
        font = self.draw.get_font(size)
        for char in text:
            self.draw._char(x, y, char, color, size)
            x += font.width + font.spacing

    def _fit_text(self, text: str, width: int) -> str:
        """Keep a single line within the available pixel width."""
        text = text.replace("\n", " ").replace("\r", " ")
        count = max(0, width // self.draw.font_size.x)
        if len(text) <= count:
            return text
        return text[:max(0, count - 3)] + "." * min(3, count)

    def _key_widths(self, row: int, unit: int) -> list:
        font = self.draw.get_font(self._key_font)
        widths = []
        for col, key in enumerate(self.ROWS[row]):
            if key.normal in ("\x01", "\x02"):
                label_width = 5 * max(1, font.height // 8)
            else:
                label_width = self.draw.len(self._key_label(row, col), self._key_font) - font.spacing
            widths.append(max(key.width * unit, label_width + 2))
        return widths

    def _build_key_rects(self) -> list:
        """Fit labels and borders inside disjoint drawing and touch rectangles."""
        available = self._layout_width - 2 * self.KEY_MARGIN
        while self._key_font > 0:
            minimum = max(sum(self._key_widths(row, 1)) + self.ROW_SIZES[row] - 1 for row in range(self.NUM_ROWS))
            if minimum <= available and self.draw.get_font(self._key_font).height + 2 <= self.KEY_HEIGHT:
                break
            self._key_font -= 1
        while self.KEY_WIDTH > 1:
            widest = max(sum(self._key_widths(row, self.KEY_WIDTH)) + self.ROW_SIZES[row] - 1 for row in range(self.NUM_ROWS))
            if widest <= available:
                break
            self.KEY_WIDTH -= 1

        rects = []
        for row in range(self.NUM_ROWS):
            widths = self._key_widths(row, self.KEY_WIDTH)
            row_width = sum(widths) + (len(widths) - 1) * self.KEY_SPACING
            x = self._layout_x + (self._layout_width - row_width) // 2
            y = self._keys_y + row * (self.KEY_HEIGHT + self.KEY_SPACING)
            row_rects = []
            for width in widths:
                row_rects.append((x, y, width, self.KEY_HEIGHT))
                x += width + self.KEY_SPACING
            rects.append(row_rects)
        return rects

    def _key_at_point(self, x: int, y: int):
        """Return the (row, col) under a touch point, or None.

        Args:
            x (int): The touch X coordinate.
            y (int): The touch Y coordinate.

        Returns:
            tuple or None: The (row, col) of the key, or None if not on a key.
        """
        for row in range(self.NUM_ROWS):
            for col in range(self.ROW_SIZES[row]):
                rx, ry, rw, rh = self._key_rects[row][col]
                if rx <= x < rx + rw and ry <= y < ry + rh:
                    return row, col
        return None

    def _handle_touch_input(self) -> bool:
        """Press the key under the touch point. True if the touch was used."""
        point = self.input_manager.point
        if not point or point == (0, 0):
            return False

        if self._rotated:
            point = self.draw.touch_point(point[0], point[1])
        hit = self._key_at_point(point[0], point[1])
        if hit is None:
            return False

        self.cursor_row, self.cursor_col = hit
        self.is_in_textbox = False
        self.selected_suggestion_index = -1
        # a tap is a centre press: the zone it lands in would otherwise report
        # UP/DOWN/LEFT/RIGHT, which suppresses the shift reset
        self.dpad_input = BUTTON_CENTER
        self._process_key_press()

        if self.ROWS[self.cursor_row][self.cursor_col].normal == "":
            self.is_manual_shift = True
        return True

    def _draw_key(self, row: int, col: int, is_selected: bool) -> None:
        """Draw a specific key on the keyboard.

        Args:
            row (int): The key row index.
            col (int): The key column index.
            is_selected (bool): Whether the key is currently selected.
        """
        if row >= self.NUM_ROWS or col >= self.ROW_SIZES[row]:
            return

        key = self.ROWS[row][col]

        x_pos, y_pos, width, height = self._key_rects[row][col]
        self.size_vec.x = width
        self.size_vec.y = height

        if self._is_flipper:
            # draw key background
            self.draw._fill_rectangle(
                x_pos, y_pos, self.size_vec.x, self.size_vec.y, self.text_color if is_selected else self.background_color
            )
        else:
            # Draw key background
            bg_color = self.selected_color if is_selected else self.background_color
            self.draw._fill_rectangle(
                x_pos, y_pos, self.size_vec.x, self.size_vec.y, bg_color
            )

            # Draw key border
            self._draw_rectangle(
                x_pos,
                y_pos,
                self.size_vec.x,
                self.size_vec.y,
                self.text_color,
            )

        if key.normal in ("\x01", "\x02"):
            # Printable fonts have no Shift/Caps Lock glyphs.
            caps = key.normal == "\x01"
            rows = (4, 14, 31, 4, 4, 0, 31) if caps else (4, 14, 31, 4, 4, 4, 4)
            color = self.background_color if self._is_flipper and is_selected else self.text_color
            scale = max(1, self.draw.get_font(self._key_font).height // 8)
            x = x_pos + (width - 5 * scale) // 2
            y = y_pos + (height - 7 * scale) // 2
            for dy, bits in enumerate(rows):
                for dx in range(5):
                    if bits & (16 >> dx):
                        self.draw._fill_rectangle(x + dx * scale, y + dy * scale, scale, scale, color)
            active = self.is_caps_lock_on if caps else self.is_shift_pressed
            if active:
                inset = 0 if self._is_flipper else 1
                self.draw._line(
                    x_pos + inset, y_pos + height - 1 - inset,
                    x_pos + width - 1 - inset, y_pos + height - 1 - inset, color,
                )
            return

        key_label = self._key_label(row, col)
        font = self.draw.get_font(self._key_font)
        label_width = self.draw.len(key_label, self._key_font) - font.spacing
        key_x = x_pos + (width - label_width) // 2
        key_y = y_pos + (height - font.height) // 2
        color = self.background_color if self._is_flipper and is_selected else self.text_color
        self._draw_text(key_x, key_y, key_label, color, self._key_font)

    def _key_label(self, row: int, col: int) -> str:
        """Return the current key label, using compact modifier icons."""
        key = self.ROWS[row][col]
        if key.normal in ("\x01", "\x02"):
            return "^"  # Width placeholder for the 5-pixel modifier icon.

        # Determine what character to display
        display_char = key.normal
        should_capitalize = False

        if "a" <= key.normal <= "z":
            should_capitalize = (
                self.is_shift_pressed and not self.is_caps_lock_on
            ) or (not self.is_shift_pressed and self.is_caps_lock_on)
            display_char = key.shifted if should_capitalize else key.normal
        elif self.is_shift_pressed and key.normal != key.shifted:
            display_char = key.shifted

        # Draw key label
        key_label = ""
        if key.normal == "\b":
            key_label = "DEL"
        elif key.normal == "\x01":
            key_label = "CAPS*" if self.is_caps_lock_on else "CAPS"
        elif key.normal == "\x02":
            key_label = "SHFT*" if self.is_shift_pressed else "SHFT"
        elif key.normal == "\r":
            key_label = "ENT"
        elif key.normal == " ":
            key_label = "SPACE"
        elif key.normal == "\x03":
            key_label = "SAVE"
        elif key.normal == "?" and row == 1 and col == 12:
            key_label = "CLR"  # Clear function
        else:
            key_label = display_char

        return key_label

    def _draw_keyboard(self) -> None:
        """Draws the entire keyboard"""
        # Clear keyboard area
        self.draw._fill_rectangle(
            self.text_box_pos_vec.x,
            self.text_box_pos_vec.y,
            self.text_box_pos_size.x,
            self.text_box_pos_size.y,
            self.background_color,
        )

        # Draw all keys
        for row in range(self.NUM_ROWS):
            for col in range(self.ROW_SIZES[row]):
                is_selected = row == self.cursor_row and col == self.cursor_col
                self._draw_key(row, col, is_selected)

    def _draw_textbox(self) -> None:
        """Draws the text box that displays the current saved response"""
        # Draw textbox border (highlight if in textbox mode)
        border_color = self.selected_color if self.is_in_textbox else self.text_color
        self._draw_rectangle(
            self.text_border_pos.x,
            self.text_border_pos.y,
            self.text_border_size.x,
            self.text_border_size.y,
            border_color,
        )

        # Split text into lines if needed
        lines = []
        line_positions = []  # Track character positions for each line
        current_line = ""
        char_pos = 0

        for char in self._response:
            if char == "\n":
                lines.append(current_line)
                line_positions.append(char_pos - len(current_line))
                current_line = ""
            elif len(current_line) >= self.max_chars_per_line:
                lines.append(current_line)
                line_positions.append(char_pos - len(current_line))
                current_line = char
            else:
                current_line += char
            char_pos += 1

        if current_line or not lines or self._response.endswith("\n"):
            lines.append(current_line)
            line_positions.append(char_pos - len(current_line))

        # Show only the last few lines that fit
        start_line = max(0, len(lines) - self.max_lines)

        _start_y = self._text_y
        _distance = self.draw.font_size.y + 1
        for i in range(start_line, len(lines)):
            self.text_vec.y = _start_y + (i - start_line) * _distance
            self._draw_text(self.text_vec.x, self.text_vec.y, lines[i], self.text_color)

        # Draw cursor at the current position
        # Find which line and column the cursor is on
        cursor_line = 0
        cursor_col = self.text_cursor_position

        for i, line_start_pos in enumerate(line_positions):
            if self.text_cursor_position >= line_start_pos:
                cursor_line = i
                cursor_col = self.text_cursor_position - line_start_pos
            else:
                break

        # Only draw cursor if the line is visible
        if cursor_line >= start_line:
            display_line = cursor_line - start_line
            self.cursor.x = self.text_vec.x + cursor_col * self.draw.font_size.x
            self.cursor.y = _start_y + display_line * _distance
            self._draw_text(self.cursor.x, self.cursor.y, "_", self.text_color)

    def _draw_suggestions(self):
        """Draws auto-complete suggestions based on keyboard visibility"""
        suggestions = self._auto_complete_suggestions()
        if not suggestions:
            return
        if self._show_keyboard:
            # Show only one suggestion below the keyboard area
            suggestion = suggestions[0]
            text = self._fit_text("Suggestion: " + suggestion, self._layout_width - 2 * self.KEY_MARGIN)
            x_pos = self._layout_x + (self._layout_width - self.draw.len(text)) // 2
            self._draw_text(x_pos, self._suggestion_y, text, self.text_color)
        else:
            # Scroll the two-column list so the selected suggestion stays visible.
            line_height = self.draw.font_size.y + 4
            visible_rows = max(1, (self._layout_y + self._layout_height - self._keys_y) // line_height)
            first_row = max(0, self.selected_suggestion_index // 2 - visible_rows + 1)
            column_width = (self._layout_width - 2 * self.KEY_MARGIN) // 2
            for i in range(first_row * 2, min(len(suggestions), (first_row + visible_rows) * 2)):
                x_pos = self._layout_x + self.KEY_MARGIN + (i % 2) * column_width + 2
                y_pos = self._keys_y + (i // 2 - first_row) * line_height + 2
                text = self._fit_text(suggestions[i], column_width - 4)
                if i == self.selected_suggestion_index:
                    self.draw._fill_rectangle(
                        x_pos - 2, y_pos - 2, column_width, line_height, self.selected_color,
                    )
                self._draw_text(x_pos, y_pos, text, self.text_color)

    def _apply_suggestion(self, suggestion_text: str) -> None:
        """Apply an auto-complete suggestion to the current response.

        Args:
            suggestion_text (str): The suggestion to apply.
        """
        if not suggestion_text or not self._response:
            return

        # Find the last word to replace
        words = self._response[: self.text_cursor_position].strip().split()
        if not words:
            return

        # Calculate where the last word starts
        last_word = words[-1]
        word_start_pos = self._response[: self.text_cursor_position].rfind(last_word)

        if word_start_pos != -1:
            # Replace the last word with the suggestion
            self._response = (
                self._response[:word_start_pos]
                + suggestion_text
                + self._response[self.text_cursor_position :]
            )
            self.text_cursor_position = word_start_pos + len(suggestion_text)

    def _handle_input(self, max_characters: int = 0) -> None:
        """Handles directional input and key selection.

        Args:
            max_characters (int): The maximum number of characters allowed in the response. 0 means no limit.
        """
        if self._touch_enabled and self._handle_touch_input():
            return

        suggestions = self._auto_complete_suggestions()

        # Handle directional navigation and direct key access
        if self.is_in_textbox or not self._show_keyboard:
            # Check if we're in suggestion selection mode
            if self.selected_suggestion_index >= 0:
                # Navigation in suggestion list (non-keyboard mode only)
                if self.dpad_input == BUTTON_UP:
                    if self.selected_suggestion_index > 0:
                        self.selected_suggestion_index -= 1
                    else:
                        # Go back to textbox
                        self.selected_suggestion_index = -1
                        self.is_in_textbox = True
                elif self.dpad_input == BUTTON_DOWN:
                    if self.selected_suggestion_index < len(suggestions) - 1:
                        self.selected_suggestion_index += 1
                elif self.dpad_input == BUTTON_CENTER:
                    # Apply selected suggestion
                    if self.selected_suggestion_index < len(suggestions):
                        self._apply_suggestion(
                            suggestions[self.selected_suggestion_index]
                        )
                        self.selected_suggestion_index = -1
                        self.is_in_textbox = True
                return

            # Textbox mode navigation
            if self.dpad_input == BUTTON_LEFT:
                if self.text_cursor_position > 0:
                    self.text_cursor_position -= 1
            elif self.dpad_input == BUTTON_RIGHT:
                if self.text_cursor_position < len(self._response):
                    self.text_cursor_position += 1
            elif self.dpad_input == BUTTON_DOWN:
                if self._show_keyboard:
                    # Exit textbox mode and return to keyboard
                    self.is_in_textbox = False
                else:
                    # Enter suggestion selection mode
                    if suggestions:
                        self.selected_suggestion_index = 0
                        self.is_in_textbox = False
            elif self.dpad_input == BUTTON_SPACE:
                # Insert space at cursor position
                self._response = (
                    self._response[: self.text_cursor_position]
                    + " "
                    + self._response[self.text_cursor_position :]
                )
                self.text_cursor_position += 1
                return
            elif self.dpad_input == BUTTON_BACKSPACE:
                # Handle backspace in textbox mode
                if (
                    self.dpad_input == BUTTON_BACKSPACE
                    and self.text_cursor_position > 0
                ):
                    self._response = (
                        self._response[: self.text_cursor_position - 1]
                        + self._response[self.text_cursor_position :]
                    )
                    self.text_cursor_position -= 1
                    return
            elif self.dpad_input == BUTTON_CENTER:
                if self._show_keyboard and suggestions:
                    # Apply first suggestion in keyboard mode
                    self._apply_suggestion(suggestions[0])
                elif not self._show_keyboard:
                    # Save from textbox mode
                    if self.on_save_callback:
                        self.on_save_callback(self._response)
                    self.is_save_pressed = True

        else:
            # Keyboard mode navigation
            self.selected_suggestion_index = (
                -1
            )  # Reset suggestion selection in keyboard mode

            if self.dpad_input == BUTTON_SPACE:
                self._set_cursor_position(4, 0)
                self._process_key_press()
            elif self.dpad_input == BUTTON_UP:
                if self.cursor_row == 0:
                    # Enter textbox mode from top row
                    self.is_in_textbox = True
                    self.text_cursor_position = len(self._response)  # Start at end
                elif self.cursor_row > 0:
                    self.cursor_row -= 1
                    if self.cursor_col >= self.ROW_SIZES[self.cursor_row]:
                        self.cursor_col = self.ROW_SIZES[self.cursor_row] - 1
            elif self.dpad_input == BUTTON_DOWN:
                if self.cursor_row < self.NUM_ROWS - 1:
                    self.cursor_row += 1
                    if self.cursor_col >= self.ROW_SIZES[self.cursor_row]:
                        self.cursor_col = self.ROW_SIZES[self.cursor_row] - 1
            elif self.dpad_input == BUTTON_LEFT:
                if self.cursor_col > 0:
                    self.cursor_col -= 1
                elif self.cursor_row > 0:
                    # Wrap to end of previous row
                    self.cursor_row -= 1
                    self.cursor_col = self.ROW_SIZES[self.cursor_row] - 1
            elif self.dpad_input == BUTTON_RIGHT:
                if self.cursor_col < self.ROW_SIZES[self.cursor_row] - 1:
                    self.cursor_col += 1
                elif self.cursor_row < self.NUM_ROWS - 1:
                    # Wrap to start of next row
                    self.cursor_row += 1
                    self.cursor_col = 0
            elif self.dpad_input == BUTTON_CENTER:
                self._process_key_press()

                if self.ROWS[self.cursor_row][self.cursor_col].normal == "\x02":
                    self.is_manual_shift = True

        can_add = max_characters == 0 or len(self._response) < max_characters

        # both modes can handle manual character entry for special characters
        if self.dpad_input in self.manual_keys and can_add:
            char = self.manual_keys[self.dpad_input]
            self._response = (
                self._response[: self.text_cursor_position]
                + char
                + self._response[self.text_cursor_position :]
            )
            self.text_cursor_position += 1
            return

        # Handle direct key presses
        if self.dpad_input in self.key_mappings and can_add:
            row, col = self.key_mappings[self.dpad_input]
            self._set_cursor_position(row, col)
            self._process_key_press()

    def _process_key_press(self) -> None:
        """Processes the currently selected key press"""
        if (
            self.cursor_row >= self.NUM_ROWS
            or self.cursor_col >= self.ROW_SIZES[self.cursor_row]
        ):
            return

        key = self.ROWS[self.cursor_row][self.cursor_col]
        self.current_key = key.normal

        if self.current_key == "\b":  # Backspace
            if self.text_cursor_position > 0:
                self._response = (
                    self._response[: self.text_cursor_position - 1]
                    + self._response[self.text_cursor_position :]
                )
                self.text_cursor_position -= 1
        elif self.current_key == "\x01":  # Caps Lock
            self.is_caps_lock_on = not self.is_caps_lock_on
        elif self.current_key == "\x02":  # Shift
            self.is_shift_pressed = not self.is_shift_pressed
        elif self.current_key == "\r":  # Enter
            self._response = (
                self._response[: self.text_cursor_position]
                + "\n"
                + self._response[self.text_cursor_position :]
            )
            self.text_cursor_position += 1
        elif self.current_key == " ":  # Space
            self._response = (
                self._response[: self.text_cursor_position]
                + " "
                + self._response[self.text_cursor_position :]
            )
            self.text_cursor_position += 1
        elif self.current_key == "\x03":  # Save
            if self.on_save_callback:
                self.on_save_callback(self._response)
            self.is_save_pressed = True
        elif self.current_key == "?" and self.cursor_row == 1 and self.cursor_col == 12:
            # Clear function
            self._response = ""
            self.text_cursor_position = 0
        else:
            # Regular character
            char_to_insert = ""
            if "a" <= self.current_key <= "z":
                # Handle letter case
                should_capitalize = (
                    self.is_shift_pressed and not self.is_caps_lock_on
                ) or (not self.is_shift_pressed and self.is_caps_lock_on)
                char_to_insert = key.shifted if should_capitalize else key.normal
            elif self.is_shift_pressed and key.normal != key.shifted:
                # Handle shifted special characters
                char_to_insert = key.shifted
            else:
                # Normal character
                char_to_insert = key.normal

            # Insert character at cursor position
            self._response = (
                self._response[: self.text_cursor_position]
                + char_to_insert
                + self._response[self.text_cursor_position :]
            )
            self.text_cursor_position += 1

            # Reset shift after character entry (ignore left/right/up/down)
            if self.is_shift_pressed and self.dpad_input not in self.d_pad:
                self.is_shift_pressed = False
                self.is_manual_shift = False

    def _set_cursor_position(self, row: int, col: int) -> None:
        """Set the cursor position on the keyboard.

        Args:
            row (int): The row to move to.
            col (int): The column to move to.
        """
        if row < self.NUM_ROWS and col < self.ROW_SIZES[row]:
            self.cursor_row = row
            self.cursor_col = col

    def _set_auto_complete_words(self) -> None:
        """Sets the words for auto-completion"""
        if not self._auto_complete_words_set and self._auto_complete is not None:
            if not self._auto_complete.add_dictionary(
                "picoware/keyboard/dictionary.txt"
            ):
                if not self._auto_complete_words:
                    self._auto_complete_words = self._default_words()
                self._auto_complete.add_words(self._auto_complete_words)
            self._auto_complete_words_set = True
