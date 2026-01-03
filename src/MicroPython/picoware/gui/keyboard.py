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
    __slots__ = ("normal", "shifted", "width")

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
        from picoware.system.vector import Vector
        from picoware.system.auto_complete import AutoComplete

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

        self.max_chars_per_line = (self.draw.size.x - 10) // self.draw.font_size.x
        self.max_lines = (self.TEXTBOX_HEIGHT - 10) // self.draw.font_size.y

        self.keyboard_height = self.NUM_ROWS * (self.KEY_HEIGHT + self.KEY_SPACING) + 20
        self.key_vec = Vector(0, 0)
        self.size_vec = Vector(0, 0)
        self.text_vec = Vector(5, 8)
        self.cursor = Vector(0, 0)

        self.text_box_pos_vec = Vector(0, self.TEXTBOX_HEIGHT)
        self.text_box_pos_size = Vector(self.draw.size.x, self.keyboard_height + 10)

        self.textbox_pos = Vector(0, 0)
        self.textbox_size = Vector(self.draw.size.x, self.TEXTBOX_HEIGHT)

        self.text_border_pos = Vector(2, 2)
        self.text_border_size = Vector(self.draw.size.x - 4, self.TEXTBOX_HEIGHT - 4)

        self.title_vec = Vector(
            self.draw.size.x // 2 - len(self.current_title) * 3, self.TEXTBOX_HEIGHT + 5
        )

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

        self._show_keyboard = True
        self._auto_complete = AutoComplete()
        self._words_set = False

    def __del__(self):
        self.reset()
        self.current_title = ""
        self.key_vec = None
        self.size_vec = None
        self.text_vec = None
        self.cursor = None
        self.text_box_pos_vec = None
        self.text_box_pos_size = None
        self.textbox_pos = None
        self.textbox_size = None
        self.text_border_pos = None
        self.text_border_size = None
        self.title_vec = None
        self.manual_keys = {}
        self.key_mappings = {}
        del self._auto_complete
        self._auto_complete = None

    @property
    def callback(self) -> callable:
        """Returns the current save callback function"""
        return self.on_save_callback

    @callback.setter
    def callback(self, value: callable):
        """Sets the current save callback function"""
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
    def show_keyboard(self, value: bool):
        """Sets whether the on-screen keyboard is shown"""
        self._show_keyboard = value

    @property
    def title(self) -> str:
        """Returns the current title of the keyboard"""
        return self.current_title

    @title.setter
    def title(self, value: str):
        """Sets the current title of the keyboard"""
        from picoware.system.vector import Vector

        self.current_title = value
        self.title_vec = Vector(
            self.draw.size.x // 2 - len(value) * 3, self.TEXTBOX_HEIGHT + 5
        )

    @property
    def response(self) -> str:
        """Returns the response string"""
        return self._response

    @response.setter
    def response(self, value: str):
        """Sets the response string"""
        self._response = value
        self.text_cursor_position = len(value)

    def set_save_callback(self, callback: callable):
        """Sets the save callback function"""
        self.on_save_callback = callback

    def reset(self):
        """Resets the keyboard state"""
        self.cursor_row = 0
        self.cursor_col = 0
        self.is_shift_pressed = False
        self.is_caps_lock_on = False
        self._response = ""
        self.just_stopped = False
        self.on_save_callback = None
        self.is_save_pressed = False
        self.current_title = "Enter Text"
        self.is_in_textbox = False
        self.text_cursor_position = 0
        self.selected_suggestion_index = -1
        self._auto_complete.remove_suggestions()
        self._auto_complete.remove_words()
        self._words_set = False

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
        start_x = (self.draw.size.x - total_row_width) // 2

        # Calculate key position
        x_pos = start_x
        for i in range(col):
            x_pos += self.ROWS[row][i].width * self.KEY_WIDTH + self.KEY_SPACING
        y_pos = self.TEXTBOX_HEIGHT + 20 + row * (self.KEY_HEIGHT + self.KEY_SPACING)

        # Calculate key size
        width = key.width * self.KEY_WIDTH + (key.width - 1) * self.KEY_SPACING
        self.size_vec.x = width
        self.size_vec.y = self.KEY_HEIGHT

        # Draw key background
        bg_color = self.selected_color if is_selected else self.background_color
        self.key_vec.x = x_pos
        self.key_vec.y = y_pos
        self.draw.fill_rectangle(self.key_vec, self.size_vec, bg_color)

        # Draw key border
        self.draw.rect(self.key_vec, self.size_vec, self.text_color)

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
        self.key_vec.x = x_pos + width // 2 - len(key_label) * 3
        self.key_vec.y = y_pos + self.KEY_HEIGHT // 2 - 4
        self.draw.text(self.key_vec, key_label, self.text_color)

    def _draw_keyboard(self):
        """Draws the entire keyboard"""
        # Clear keyboard area
        self.draw.fill_rectangle(
            self.text_box_pos_vec,
            self.text_box_pos_size,
            self.background_color,
        )

        # Draw all keys
        for row in range(self.NUM_ROWS):
            for col in range(self.ROW_SIZES[row]):
                is_selected = row == self.cursor_row and col == self.cursor_col
                self._draw_key(row, col, is_selected)

    def _draw_textbox(self):
        """Draws the text box that displays the current saved response"""
        # Draw textbox border (highlight if in textbox mode)
        border_color = self.selected_color if self.is_in_textbox else self.text_color
        self.draw.rect(
            self.text_border_pos,
            self.text_border_size,
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

        if current_line or not lines:
            lines.append(current_line)
            line_positions.append(char_pos - len(current_line))

        # Show only the last few lines that fit
        start_line = max(0, len(lines) - self.max_lines)

        for i in range(start_line, len(lines)):
            self.text_vec.y = 8 + (i - start_line) * 10
            self.draw.text(self.text_vec, lines[i], self.text_color)

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
            self.cursor.x = 5 + cursor_col * 6
            self.cursor.y = 8 + display_line * 10
            self.draw.text(self.cursor, "_", self.text_color)

    def _draw_suggestions(self):
        """Draws auto-complete suggestions based on keyboard visibility"""
        from picoware.system.vector import Vector

        suggestions = self._auto_complete_suggestions()
        if not suggestions:
            return

        if self._show_keyboard:
            # Show only one suggestion below the keyboard area
            suggestion = suggestions[0]
            y_pos = self.TEXTBOX_HEIGHT + 20 + self.keyboard_height + 5
            text = f"Suggestion: {suggestion}"
            x_pos = (self.draw.size.x - len(text) * self.draw.font_size.x) // 2
            suggestion_vec = Vector(x_pos, y_pos)
            self.draw.text(suggestion_vec, text, self.text_color)
        else:
            # Show all suggestions in 2-column list below the title
            y_start = self.TEXTBOX_HEIGHT + 20
            x_col1 = 5
            x_col2 = self.draw.size.x // 2 + 5
            line_height = self.draw.font_size.y * 2

            for i, suggestion in enumerate(suggestions):
                row = i // 2
                col = i % 2
                x_pos = x_col1 if col == 0 else x_col2
                y_pos = y_start + row * line_height
                suggestion_vec = Vector(x_pos, y_pos)

                # Highlight selected suggestion
                if i == self.selected_suggestion_index:
                    # Draw background highlight
                    highlight_pos = Vector(x_pos - 2, y_pos - 2)
                    highlight_size = Vector(len(suggestion) * 6 + 4, line_height - 2)
                    self.draw.fill_rectangle(
                        highlight_pos, highlight_size, self.selected_color
                    )

                self.draw.text(suggestion_vec, suggestion, self.text_color)

    def _apply_suggestion(self, suggestion_text: str):
        """Applies an auto-complete suggestion to the current response"""
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

    def _handle_input(self):
        """Handles directional input and key selection"""
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

        # both modes can handle manual character entry for special characters
        if self.dpad_input in self.manual_keys:
            char = self.manual_keys[self.dpad_input]
            self._response = (
                self._response[: self.text_cursor_position]
                + char
                + self._response[self.text_cursor_position :]
            )
            self.text_cursor_position += 1
            return

        # Handle direct key presses
        if self.dpad_input in self.key_mappings:
            row, col = self.key_mappings[self.dpad_input]
            self._set_cursor_position(row, col)
            self._process_key_press()

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
            d_pad = {
                BUTTON_UP,
                BUTTON_DOWN,
                BUTTON_LEFT,
                BUTTON_RIGHT,
            }
            if self.is_shift_pressed and self.dpad_input not in d_pad:
                self.is_shift_pressed = False
                self.is_manual_shift = False

    def _set_cursor_position(self, row: int, col: int):
        """Sets the cursor position on the keyboard"""
        if row < self.NUM_ROWS and col < self.ROW_SIZES[row]:
            self.cursor_row = row
            self.cursor_col = col

    def _set_words(self):
        """Sets the words for auto-completion"""
        if not self._words_set and self._auto_complete is not None:
            self._auto_complete.add_words(
                [
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
            )
            self._words_set = True

    def run(self, swap: bool = True, force: bool = False):
        """Runs the input manager, handles input, and draws the keyboard"""
        if self.just_stopped:
            return False

        self.dpad_input = self.input_manager.button
        if self.dpad_input != -1 or force:
            if self.dpad_input == BUTTON_BACK:
                # Exit keyboard without saving
                self.just_stopped = True
                self.input_manager.reset()
                return False

            if not self.is_manual_shift:
                self.is_shift_pressed = self.input_manager.was_capitalized

            self.draw.erase()

            if not self._words_set:
                self._set_words()

            # only process input/redraw if there's input
            self._handle_input()
            self._draw_textbox()

            if self._show_keyboard:
                self._draw_keyboard()

            self.draw.text(
                self.title_vec,
                self.current_title,
                self.text_color,
            )

            # Draw auto-complete suggestions after keyboard/title
            self._draw_suggestions()

            self.input_manager.reset()

            if swap or force:
                self.draw.swap()

        return True
