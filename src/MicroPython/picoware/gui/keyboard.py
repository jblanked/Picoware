from picoware.system.vector import Vector


# Define the keyboard layout structure
class KeyLayout:
    def __init__(self, normal: str, shifted: str, width: int = 1):
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

    # Key dimensions
    KEY_WIDTH = 22
    KEY_HEIGHT = 35
    KEY_SPACING = 1
    TEXTBOX_HEIGHT = 45

    def __init__(
        self,
        draw,
        input_manager,
        text_color: int = 0xFFFF,
        background_color: int = 0x0000,
        selected_color: int = 0x001F,
        on_save_callback: callable = None,
    ):
        """
        Initializes the keyboard with drawing context and input manager.

        Args:
            draw: Drawing context for rendering the keyboard.
            input_manager: Input manager to handle button presses.
            text_color: Color for the text on keys and textbox.
            background_color: Background color for keys and textbox.
            selected_color: Color for the selected key highlight.
            on_save_callback: Optional callback function to call when "Save" is pressed. (must accept one argument: the current response string)
        """
        self.draw = draw
        self.input_manager = input_manager
        self.text_color = text_color
        self.background_color = background_color
        self.selected_color = selected_color
        self.on_save_callback = on_save_callback

        # Initialize cursor position to top-left key
        self.cursor_row = 0
        self.cursor_col = 0
        self.last_input_time = 0
        self.input_delay = 10  # milliseconds

        # Keyboard state
        self.is_shift_pressed = False
        self.is_caps_lock_on = False
        self.current_key: int = -1
        self.dpad_input: int = -1
        self.response = ""
        self.is_save_pressed = False
        self.just_stopped = False
        self.current_title = "Enter Text"

    @property
    def is_finished(self) -> bool:
        """Returns whether the keyboard is finished"""
        return self.is_save_pressed

    @property
    def keyboard_width(self) -> int:
        """Returns the keyboard width/width of the display"""
        return self.draw.size.x

    @property
    def title(self) -> str:
        """Returns the current title of the keyboard"""
        return self.current_title

    @title.setter
    def title(self, value: str):
        """Sets the current title of the keyboard"""
        self.current_title = value

    def get_response(self) -> str:
        """Returns the response string"""
        return self.response

    def set_save_callback(self, callback: callable):
        """Sets the save callback function"""
        self.on_save_callback = callback

    def set_response(self, text: str):
        """Sets the response string"""
        self.response = text

    def reset(self):
        """Resets the keyboard state"""
        self.just_stopped = True
        self.cursor_row = 0
        self.cursor_col = 0
        self.is_shift_pressed = False
        self.is_caps_lock_on = False
        self.response = ""
        self.last_input_time = 0
        self.on_save_callback = None
        self.is_save_pressed = False
        self.current_title = "Enter Text"

    def _draw_key(self, row: int, col: int, is_selected: bool):
        """Draws a specific key on the keyboard"""
        if row >= self.NUM_ROWS or col >= self.ROW_SIZES[row]:
            return

        key = self.ROWS[row][col]

        # Calculate total row width for centering
        total_row_width = 0
        for i in range(self.ROW_SIZES[row]):
            total_row_width += self.ROWS[row][i].width * self.KEY_WIDTH + (
                self.KEY_SPACING if i > 0 else 0
            )

        # Calculate starting X position for centering
        start_x = (320 - total_row_width) // 2

        # Calculate key position
        x_pos = start_x
        for i in range(col):
            x_pos += self.ROWS[row][i].width * self.KEY_WIDTH + self.KEY_SPACING
        y_pos = self.TEXTBOX_HEIGHT + 20 + row * (self.KEY_HEIGHT + self.KEY_SPACING)

        # Calculate key size
        width = key.width * self.KEY_WIDTH + (key.width - 1) * self.KEY_SPACING
        height = self.KEY_HEIGHT

        # Draw key background
        bg_color = self.selected_color if is_selected else self.background_color
        self.draw.fill_rectangle(Vector(x_pos, y_pos), Vector(width, height), bg_color)

        # Draw key border
        self.draw.rect(Vector(x_pos, y_pos), Vector(width, height), self.text_color)

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

        # Center the text
        text_x = x_pos + width // 2 - len(key_label) * 3
        text_y = y_pos + height // 2 - 4

        self.draw.text(Vector(text_x, text_y), key_label, self.text_color)

    def _draw_keyboard(self):
        """Draws the entire keyboard"""
        # Clear keyboard area
        keyboard_height = self.NUM_ROWS * (self.KEY_HEIGHT + self.KEY_SPACING) + 20
        self.draw.fill_rectangle(
            Vector(0, self.TEXTBOX_HEIGHT),
            Vector(self.draw.size.x, keyboard_height + 10),
            self.background_color,
        )

        # Draw all keys
        for row in range(self.NUM_ROWS):
            for col in range(self.ROW_SIZES[row]):
                is_selected = row == self.cursor_row and col == self.cursor_col
                self._draw_key(row, col, is_selected)

        # Draw title
        title_x = self.draw.size.x // 2 - len(self.current_title) * 3
        self.draw.text(
            Vector(title_x, self.TEXTBOX_HEIGHT + 5),
            self.current_title,
            self.text_color,
        )

    def _draw_textbox(self):
        """Draws the text box that displays the current saved response"""
        # Clear textbox area
        self.draw.fill_rectangle(
            Vector(0, 0),
            Vector(self.draw.size.x, self.TEXTBOX_HEIGHT),
            self.background_color,
        )

        # Draw textbox border
        self.draw.rect(
            Vector(2, 2),
            Vector(self.draw.size.x - 4, self.TEXTBOX_HEIGHT - 4),
            self.text_color,
        )

        # Draw response text with word wrapping
        display_text = self.response
        max_chars_per_line = (self.draw.size.x - 10) // 6  # Approximate character width
        max_lines = (self.TEXTBOX_HEIGHT - 10) // 10  # Approximate line height

        # Split text into lines if needed
        lines = []
        current_line = ""

        for char in display_text:
            if char == "\n":
                lines.append(current_line)
                current_line = ""
            elif len(current_line) >= max_chars_per_line:
                lines.append(current_line)
                current_line = char
            else:
                current_line += char

        if current_line:
            lines.append(current_line)

        # Show only the last few lines that fit
        start_line = max(0, len(lines) - max_lines)

        for i in range(start_line, len(lines)):
            y_pos = 8 + (i - start_line) * 10
            self.draw.text(Vector(5, y_pos), lines[i], self.text_color)

        # Draw cursor
        last_line = lines[-1] if lines else ""
        cursor_x = 5 + len(last_line) * 6
        cursor_y = 8 + (min(len(lines), max_lines) - 1) * 10 if lines else 8

        self.draw.text(Vector(cursor_x, cursor_y), "_", self.text_color)

    def _handle_input(self):
        """Handles directional input and key selection"""
        from utime import ticks_ms
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
            BUTTON_BACKSPACE,
            BUTTON_SHIFT,
            BUTTON_CAPS_LOCK,
            BUTTON_PERIOD,
            BUTTON_COMMA,
            BUTTON_SEMICOLON,
            BUTTON_MINUS,
            BUTTON_EQUAL,
            BUTTON_LEFT_BRACKET,
            BUTTON_RIGHT_BRACKET,
            BUTTON_SLASH,
            BUTTON_BACKSLASH,
            BUTTON_UNDERSCORE,
            BUTTON_COLON,
            BUTTON_SINGLE_QUOTE,
            BUTTON_DOUBLE_QUOTE,
        )

        if ticks_ms() - self.last_input_time < self.input_delay:
            return

        # Handle directional navigation and direct key access
        if self.dpad_input == BUTTON_SPACE:
            self._set_cursor_position(4, 0)
            self._process_key_press()
            self.last_input_time = ticks_ms()
        elif self.dpad_input == BUTTON_UP:
            if self.cursor_row > 0:
                self.cursor_row -= 1
                if self.cursor_col >= self.ROW_SIZES[self.cursor_row]:
                    self.cursor_col = self.ROW_SIZES[self.cursor_row] - 1
            self.last_input_time = ticks_ms()
        elif self.dpad_input == BUTTON_DOWN:
            if self.cursor_row < self.NUM_ROWS - 1:
                self.cursor_row += 1
                if self.cursor_col >= self.ROW_SIZES[self.cursor_row]:
                    self.cursor_col = self.ROW_SIZES[self.cursor_row] - 1
            self.last_input_time = ticks_ms()
        elif self.dpad_input == BUTTON_LEFT:
            if self.cursor_col > 0:
                self.cursor_col -= 1
            elif self.cursor_row > 0:
                # Wrap to end of previous row
                self.cursor_row -= 1
                self.cursor_col = self.ROW_SIZES[self.cursor_row] - 1
            self.last_input_time = ticks_ms()
        elif self.dpad_input == BUTTON_RIGHT:
            if self.cursor_col < self.ROW_SIZES[self.cursor_row] - 1:
                self.cursor_col += 1
            elif self.cursor_row < self.NUM_ROWS - 1:
                # Wrap to start of next row
                self.cursor_row += 1
                self.cursor_col = 0
            self.last_input_time = ticks_ms()
        elif self.dpad_input == BUTTON_CENTER:
            self._process_key_press()
            self.last_input_time = ticks_ms()

        # Handle direct key presses
        key_mappings = {
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
            BUTTON_SHIFT: (3, 0),
            BUTTON_CAPS_LOCK: (2, 0),
            BUTTON_PERIOD: (3, 9),
            BUTTON_COMMA: (3, 8),
            BUTTON_SEMICOLON: (2, 10),
            BUTTON_MINUS: (0, 10),
            BUTTON_EQUAL: (0, 11),
            BUTTON_LEFT_BRACKET: (1, 10),
            BUTTON_RIGHT_BRACKET: (1, 11),
            BUTTON_SLASH: (3, 10),
            BUTTON_BACKSLASH: (3, 11),
            BUTTON_UNDERSCORE: (0, 10),
            BUTTON_COLON: (2, 10),
            BUTTON_SINGLE_QUOTE: (2, 11),
            BUTTON_DOUBLE_QUOTE: (2, 11),
        }

        if self.dpad_input in key_mappings:
            row, col = key_mappings[self.dpad_input]
            self._set_cursor_position(row, col)
            self._process_key_press()
            self.last_input_time = ticks_ms()

    def _process_key_press(self):
        """Processes the currently selected key press"""
        if (
            self.cursor_row >= self.NUM_ROWS
            or self.cursor_col >= self.ROW_SIZES[self.cursor_row]
        ):
            return

        key = self.ROWS[self.cursor_row][self.cursor_col]
        self.current_key = key.normal

        if self.current_key == "\b":  # Backspace
            if self.response:
                self.response = self.response[:-1]
        elif self.current_key == "\x01":  # Caps Lock
            self.is_caps_lock_on = not self.is_caps_lock_on
        elif self.current_key == "\x02":  # Shift
            self.is_shift_pressed = not self.is_shift_pressed
        elif self.current_key == "\r":  # Enter
            self.response += "\n"
        elif self.current_key == " ":  # Space
            self.response += " "
        elif self.current_key == "\x03":  # Save
            if self.on_save_callback:
                self.on_save_callback(self.response)
            self.is_save_pressed = True
        elif self.current_key == "?" and self.cursor_row == 1 and self.cursor_col == 12:
            # Clear function
            self.response = ""
        else:
            # Regular character
            if "a" <= self.current_key <= "z":
                # Handle letter case
                should_capitalize = (
                    self.is_shift_pressed and not self.is_caps_lock_on
                ) or (not self.is_shift_pressed and self.is_caps_lock_on)
                self.response += key.shifted if should_capitalize else key.normal
            elif self.is_shift_pressed and key.normal != key.shifted:
                # Handle shifted special characters
                self.response += key.shifted
            else:
                # Normal character
                self.response += key.normal

            # Reset shift after character entry
            if self.is_shift_pressed:
                self.is_shift_pressed = False

    def _set_cursor_position(self, row: int, col: int):
        """Sets the cursor position on the keyboard"""
        if row < self.NUM_ROWS and col < self.ROW_SIZES[row]:
            self.cursor_row = row
            self.cursor_col = col

    def run(self, swap: bool = True, force: bool = False):
        """Runs the input manager, handles input, and draws the keyboard"""
        if self.just_stopped:
            self.just_stopped = False
            return

        self.dpad_input = self.input_manager.button
        if self.dpad_input != -1 or force:
            self.is_shift_pressed = self.input_manager.was_capitalized
            # only process input/redraw if there's input
            self._handle_input()
            self._draw_textbox()
            self._draw_keyboard()

            self.input_manager.reset()

            if swap:
                self.draw.swap()
