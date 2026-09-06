"""vt - Virtual terminal driver."""

# modified from https://github.com/zenodante/PicoCalc-micropython-driver/blob/main/pico_files/modules/vt.py
# adapted for Picoware system

from collections import deque

try:
    import uio
    from utime import ticks_ms
except ImportError:
    import io as uio
    from supervisor import ticks_ms

from micropython import const
from picoware.system import buttons
from picoware.system import colors
import vt as vt_c

VT_PYTHON = const(0)
VT_C = const(1)
VT_JS = const(2)
VT_MMBASIC = const(3)

_PYTHON_SYNTAX_MAP = (
    ("def", colors.TFT_SKYBLUE),
    ("class", colors.TFT_SKYBLUE),
    ("import", colors.TFT_GREEN),
    ("from", colors.TFT_GREEN),
    ("if", colors.TFT_PINK),
    ("elif", colors.TFT_PINK),
    ("else", colors.TFT_PINK),
    ("for", colors.TFT_PINK),
    ("while", colors.TFT_PINK),
    ("return", colors.TFT_PINK),
    ("yield", colors.TFT_PINK),
    ("break", colors.TFT_PINK),
    ("continue", colors.TFT_PINK),
    ("pass", colors.TFT_PINK),
    ("try", colors.TFT_PINK),
    ("except", colors.TFT_PINK),
    ("finally", colors.TFT_PINK),
    ("raise", colors.TFT_PINK),
    ("with", colors.TFT_PINK),
    ("as", colors.TFT_PINK),
    ("in", colors.TFT_PINK),
    ("and", colors.TFT_PINK),
    ("or", colors.TFT_PINK),
    ("not", colors.TFT_PINK),
    ("is", colors.TFT_PINK),
    ("lambda", colors.TFT_PINK),
    ("True", colors.TFT_SKYBLUE),
    ("False", colors.TFT_SKYBLUE),
    ("None", colors.TFT_SKYBLUE),
    ("bool", colors.TFT_GREEN),
    ("int", colors.TFT_GREEN),
    ("float", colors.TFT_GREEN),
)

_C_SYNTAX_MAP = (
    ("auto", colors.TFT_GREEN),
    ("bool", colors.TFT_GREEN),
    ("char", colors.TFT_GREEN),
    ("const", colors.TFT_GREEN),
    ("double", colors.TFT_GREEN),
    ("enum", colors.TFT_GREEN),
    ("extern", colors.TFT_GREEN),
    ("float", colors.TFT_GREEN),
    ("int", colors.TFT_GREEN),
    ("long", colors.TFT_GREEN),
    ("short", colors.TFT_GREEN),
    ("signed", colors.TFT_GREEN),
    ("sizeof", colors.TFT_GREEN),
    ("static", colors.TFT_GREEN),
    ("struct", colors.TFT_GREEN),
    ("typedef", colors.TFT_GREEN),
    ("union", colors.TFT_GREEN),
    ("unsigned", colors.TFT_GREEN),
    ("void", colors.TFT_GREEN),
    ("volatile", colors.TFT_GREEN),
    ("break", colors.TFT_PINK),
    ("case", colors.TFT_PINK),
    ("continue", colors.TFT_PINK),
    ("default", colors.TFT_PINK),
    ("do", colors.TFT_PINK),
    ("else", colors.TFT_PINK),
    ("for", colors.TFT_PINK),
    ("goto", colors.TFT_PINK),
    ("if", colors.TFT_PINK),
    ("return", colors.TFT_PINK),
    ("switch", colors.TFT_PINK),
    ("while", colors.TFT_PINK),
    ("include", colors.TFT_VIOLET),
    ("define", colors.TFT_VIOLET),
    ("ifdef", colors.TFT_VIOLET),
    ("ifndef", colors.TFT_VIOLET),
    ("endif", colors.TFT_VIOLET),
    ("defined", colors.TFT_VIOLET),
    ("NULL", colors.TFT_SKYBLUE),
    ("true", colors.TFT_SKYBLUE),
    ("false", colors.TFT_SKYBLUE),
)

_JS_SYNTAX_MAP = (
    ("as", colors.TFT_GREEN),
    ("async", colors.TFT_GREEN),
    ("await", colors.TFT_GREEN),
    ("break", colors.TFT_PINK),
    ("case", colors.TFT_PINK),
    ("catch", colors.TFT_PINK),
    ("class", colors.TFT_SKYBLUE),
    ("const", colors.TFT_GREEN),
    ("continue", colors.TFT_PINK),
    ("debugger", colors.TFT_PINK),
    ("default", colors.TFT_PINK),
    ("delete", colors.TFT_PINK),
    ("do", colors.TFT_PINK),
    ("else", colors.TFT_PINK),
    ("export", colors.TFT_GREEN),
    ("extends", colors.TFT_GREEN),
    ("finally", colors.TFT_PINK),
    ("for", colors.TFT_PINK),
    ("from", colors.TFT_GREEN),
    ("function", colors.TFT_SKYBLUE),
    ("if", colors.TFT_PINK),
    ("import", colors.TFT_GREEN),
    ("in", colors.TFT_PINK),
    ("instanceof", colors.TFT_PINK),
    ("let", colors.TFT_GREEN),
    ("new", colors.TFT_PINK),
    ("of", colors.TFT_PINK),
    ("return", colors.TFT_PINK),
    ("static", colors.TFT_GREEN),
    ("super", colors.TFT_SKYBLUE),
    ("switch", colors.TFT_PINK),
    ("this", colors.TFT_SKYBLUE),
    ("throw", colors.TFT_PINK),
    ("try", colors.TFT_PINK),
    ("typeof", colors.TFT_PINK),
    ("var", colors.TFT_GREEN),
    ("void", colors.TFT_PINK),
    ("while", colors.TFT_PINK),
    ("with", colors.TFT_PINK),
    ("yield", colors.TFT_PINK),
    ("true", colors.TFT_SKYBLUE),
    ("false", colors.TFT_SKYBLUE),
    ("null", colors.TFT_SKYBLUE),
    ("undefined", colors.TFT_SKYBLUE),
    ("NaN", colors.TFT_SKYBLUE),
)

_MMBASIC_SYNTAX_MAP = (
    ("IF", colors.TFT_PINK),
    ("THEN", colors.TFT_PINK),
    ("ELSE", colors.TFT_PINK),
    ("ELSEIF", colors.TFT_PINK),
    ("ENDIF", colors.TFT_PINK),
    ("FOR", colors.TFT_PINK),
    ("TO", colors.TFT_PINK),
    ("STEP", colors.TFT_PINK),
    ("NEXT", colors.TFT_PINK),
    ("WHILE", colors.TFT_PINK),
    ("WEND", colors.TFT_PINK),
    ("DO", colors.TFT_PINK),
    ("LOOP", colors.TFT_PINK),
    ("EXIT", colors.TFT_PINK),
    ("GOTO", colors.TFT_PINK),
    ("GOSUB", colors.TFT_PINK),
    ("RETURN", colors.TFT_PINK),
    ("SELECT", colors.TFT_PINK),
    ("CASE", colors.TFT_PINK),
    ("END", colors.TFT_PINK),
    ("STOP", colors.TFT_PINK),
    ("RUN", colors.TFT_PINK),
    ("PRINT", colors.TFT_GREEN),
    ("INPUT", colors.TFT_GREEN),
    ("LET", colors.TFT_GREEN),
    ("DIM", colors.TFT_GREEN),
    ("DATA", colors.TFT_GREEN),
    ("READ", colors.TFT_GREEN),
    ("RESTORE", colors.TFT_GREEN),
    ("OPEN", colors.TFT_GREEN),
    ("CLOSE", colors.TFT_GREEN),
    ("CLS", colors.TFT_GREEN),
    ("LOCATE", colors.TFT_GREEN),
    ("PSET", colors.TFT_GREEN),
    ("LINE", colors.TFT_GREEN),
    ("CIRCLE", colors.TFT_GREEN),
    ("INTEGER", colors.TFT_GREEN),
    ("FLOAT", colors.TFT_GREEN),
    ("STRING", colors.TFT_GREEN),
    ("TRUE", colors.TFT_SKYBLUE),
    ("FALSE", colors.TFT_SKYBLUE),
    ("ABS", colors.TFT_GREEN),
    ("INT", colors.TFT_GREEN),
    ("RND", colors.TFT_GREEN),
    ("SIN", colors.TFT_GREEN),
    ("COS", colors.TFT_GREEN),
)


def _syntax_map_for_language(language):
    if language == VT_C:
        return _C_SYNTAX_MAP
    if language == VT_JS:
        return _JS_SYNTAX_MAP
    if language == VT_MMBASIC:
        return _MMBASIC_SYNTAX_MAP
    return _PYTHON_SYNTAX_MAP


class vt(uio.IOBase):
    """A virtual terminal that renders text output to the display."""

    def __init__(self, view_manager, language=VT_PYTHON):  # ctrl+U for screen capture
        """Initialize the virtual terminal for a view manager.

        Args:
            view_manager (ViewManager): The view manager for draw and input access.
        """
        self.view_manager = view_manager
        self.draw = view_manager.draw
        self.input_manager = view_manager.input_manager
        self.storage = view_manager.storage
        self.language = language if language in (VT_PYTHON, VT_C, VT_JS, VT_MMBASIC) else VT_PYTHON

        self.outputBuffer = deque((), 30)

        # Virtual terminal state
        self.cursor_x = 0
        self.cursor_y = 0
        self.char_width = self.draw.font_size.x  # Font character width
        self.char_height = self.draw.font_size.y  # Font character height
        self.screen_width = self.draw.size.x // self.char_width
        self.screen_height = self.draw.size.y // self.char_height

        self._needs_render = False
        self._render_enabled = True
        self._last_render_time = 0
        self._render_throttle_ms = 50
        self._batch_mode = False
        self.run_requested = False

        # Terminal buffer for text display
        self.terminal_buffer = []
        for _ in range(self.screen_height):
            self.terminal_buffer.append([" "] * self.screen_width)

        # Clear the screen initially
        self.draw.clear(color=self.draw.background)
        self.draw.swap()

        # Initialize terminal to known state
        self.cursor_visible = True
        self.scroll_top = 0
        self.scroll_bottom = self.screen_height - 1
        self.input_enabled = False  # Start with input disabled

        # Direct keyword → TFT color map for C module syntax highlighting
        # (skips ANSI escape code intermediate step entirely)
        self._syntax_map = _syntax_map_for_language(self.language)
        self._string_color = colors.TFT_ORANGE
        self._comment_color = colors.TFT_YELLOW

    def dryBuffer(self):
        """Clear the output buffer and enable input."""
        self.outputBuffer = deque((), 30)
        # Enable input when buffer is dried (editor is starting)
        self.input_enabled = True

    def _scroll_up(self):
        """Scroll terminal content up by one line"""
        self._needs_render = True
        for y in range(self.screen_height - 1):
            for x in range(self.screen_width):
                self.terminal_buffer[y][x] = self.terminal_buffer[y + 1][x]
        # Clear the last line
        for x in range(self.screen_width):
            self.terminal_buffer[self.screen_height - 1][x] = " "

    def _print_char(self, char_code):
        """Print a character to the terminal buffer.

        Args:
            char_code (int): The character code to print.
        """
        self._needs_render = True

        if char_code == 10:  # newline
            self.cursor_x = 0
            self.cursor_y += 1
            if self.cursor_y >= self.screen_height:
                self._scroll_up()
                self.cursor_y = self.screen_height - 1
        elif char_code == 13:  # carriage return
            self.cursor_x = 0
        elif char_code == 8:  # backspace
            if self.cursor_x > 0:
                self.cursor_x -= 1
                self.terminal_buffer[self.cursor_y][self.cursor_x] = " "
        elif char_code == 27:  # ESC - start of escape sequence, ignore for now
            pass  # We'll handle escape sequences in wr() method
        elif char_code >= 32:  # printable characters
            if self.cursor_x < self.screen_width:
                self.terminal_buffer[self.cursor_y][self.cursor_x] = chr(char_code)
                self.cursor_x += 1
                if self.cursor_x >= self.screen_width:
                    self.cursor_x = 0
                    self.cursor_y += 1
                    if self.cursor_y >= self.screen_height:
                        self._scroll_up()
                        self.cursor_y = self.screen_height - 1

    def _handle_escape_sequence(self, sequence):
        """Handle an ANSI/VT100 escape sequence.

        Args:
            sequence (str): The escape sequence to handle.
        """
        self._needs_render = True

        if sequence.startswith("\x1b["):
            # CSI (Control Sequence Introducer) sequences
            params = sequence[2:]

            if params.endswith("H"):
                # Cursor position
                try:
                    if ";" in params[:-1]:
                        row, col = params[:-1].split(";")
                        self.cursor_y = max(
                            0, min(int(row) - 1, self.screen_height - 1)
                        )
                        self.cursor_x = max(0, min(int(col) - 1, self.screen_width - 1))
                    else:
                        # Move to home position
                        self.cursor_x = 0
                        self.cursor_y = 0
                except (ValueError, IndexError):
                    pass
            elif params.endswith("K"):
                # Clear line
                if params == "K" or params == "0K":
                    # Clear from cursor to end of line
                    for x in range(self.cursor_x, self.screen_width):
                        self.terminal_buffer[self.cursor_y][x] = " "
                elif params == "1K":
                    # Clear from start of line to cursor
                    for x in range(0, self.cursor_x + 1):
                        self.terminal_buffer[self.cursor_y][x] = " "
                elif params == "2K":
                    # Clear entire line
                    for x in range(self.screen_width):
                        self.terminal_buffer[self.cursor_y][x] = " "
            elif params.endswith("J"):
                # Clear screen
                if params == "J" or params == "0J":
                    # Clear from cursor to end of screen
                    for y in range(self.cursor_y, self.screen_height):
                        start_x = self.cursor_x if y == self.cursor_y else 0
                        for x in range(start_x, self.screen_width):
                            self.terminal_buffer[y][x] = " "
                elif params == "1J":
                    # Clear from start of screen to cursor
                    for y in range(0, self.cursor_y + 1):
                        end_x = (
                            self.cursor_x
                            if y == self.cursor_y
                            else self.screen_width - 1
                        )
                        for x in range(0, end_x + 1):
                            self.terminal_buffer[y][x] = " "
                elif params == "2J":
                    # Clear entire screen
                    for y in range(self.screen_height):
                        for x in range(self.screen_width):
                            self.terminal_buffer[y][x] = " "
            elif params.endswith("r"):
                # Set scroll region - we'll ignore this for simplicity
                pass
            elif params.endswith("h") or params.endswith("l"):
                # Set/reset mode
                if "?25" in params:
                    # Cursor visibility
                    self.cursor_visible = params.endswith("h")
                # Ignore other modes for now
            elif params.endswith("m"):
                # SGR (color/style) - ignore for now
                pass

    def wr(self, text_input):
        """Write text to the terminal, handling ANSI escape sequences.

        Args:
            text_input (str): The text to write.

        Returns:
            int: The number of characters written.
        """
        i = 0
        while i < len(text_input):
            if text_input[i] == "\x1b":  # ESC character
                # Find the end of the escape sequence
                seq_start = i
                i += 1
                if i < len(text_input) and text_input[i] == "[":
                    # CSI sequence
                    i += 1
                    while i < len(text_input):
                        c = text_input[i]
                        if c.isalpha() or c in "~":
                            # End of sequence
                            sequence = text_input[seq_start : i + 1]
                            self._handle_escape_sequence(sequence)
                            i += 1
                            break
                        i += 1
                    else:
                        # Malformed sequence, treat as regular character
                        self._print_char(ord(text_input[seq_start]))
                        i = seq_start + 1
                elif i < len(text_input) and text_input[i] in "OHFM":
                    # Simple escape sequences
                    sequence = text_input[seq_start : i + 1]
                    self._handle_escape_sequence(sequence)
                    i += 1
                else:
                    # Just ESC by itself or unknown sequence
                    self._print_char(ord(text_input[seq_start]))
                    i = seq_start + 1
            else:
                # Regular character
                if ord(text_input[i]) == 0x07:  # bell character - ignore
                    pass
                else:
                    self._print_char(ord(text_input[i]))
                i += 1

        # Only render if changes were made and rendering is enabled and not in batch mode
        if self._needs_render and self._render_enabled and not self._batch_mode:
            current_time = ticks_ms()

            if current_time - self._last_render_time >= self._render_throttle_ms:
                self._render_terminal()
                self._needs_render = False
                self._last_render_time = current_time

        return len(text_input)

    def _render_terminal(self):
        """Render the terminal buffer to the display using C module"""
        vt_c.render(
            self.terminal_buffer,
            self.screen_height,
            self.screen_width,
            self.char_height,
            self.char_width,
            self.draw.background,
            self.draw.foreground,
            self.cursor_visible,
            self.cursor_x * self.char_width,
            self.cursor_y * self.char_height,
            self.char_width,
            2,
            self.draw.foreground,
            self._syntax_map,
            self._string_color,
            self._comment_color,
            self.draw.font,
            self.language,
        )

    def start_batch(self):
        """Start batch mode - accumulate writes without rendering"""
        self._batch_mode = True

    def end_batch(self):
        """End batch mode and render if needed"""
        self._batch_mode = False
        if self._needs_render and self._render_enabled:
            self._render_terminal()
            self._needs_render = False
            self._last_render_time = ticks_ms()

    def update(self):
        """Update method to be called periodically to handle pending renders"""
        if self._needs_render and self._render_enabled:
            current_time = ticks_ms()
            if current_time - self._last_render_time >= self._render_throttle_ms:
                self._render_terminal()
                self._needs_render = False
                self._last_render_time = current_time

    def get_screen_size(self):
        """Return the terminal dimensions.

        Returns:
            list: The screen height and width.
        """
        return [self.screen_height, self.screen_width]

    def _convert_key_to_terminal(self, key):
        """Convert a Picoware button code to a terminal escape sequence.

        Args:
            key (int): The button code.

        Returns:
            bytes or None: The terminal sequence, or None if unmapped.
        """
        # Handle regular character keys
        if buttons.BUTTON_A <= key <= buttons.BUTTON_Z:
            char_code = ord("a") + (key - buttons.BUTTON_A)
            if self.input_manager.was_capitalized:
                char_code = ord("A") + (key - buttons.BUTTON_A)
            return bytes([char_code])

        # Handle number keys
        if buttons.BUTTON_0 <= key <= buttons.BUTTON_9:
            char_code = ord("0") + (key - buttons.BUTTON_0)
            return bytes([char_code])

        button_map = {
            buttons.BUTTON_BACK: b"\x11",  # Ctrl+Q - directly triggers KEY_QUIT in pye without escape sequence parsing
            buttons.BUTTON_UP: b"\x1b[A",
            buttons.BUTTON_DOWN: b"\x1b[B",
            buttons.BUTTON_RIGHT: b"\x1b[C",
            buttons.BUTTON_LEFT: b"\x1b[D",
            buttons.BUTTON_HOME: b"\x1b[H",
            buttons.BUTTON_ENTER: b"\r",
            buttons.BUTTON_CENTER: b"\r",  # Map CENTER to Enter as well
            buttons.BUTTON_BACKSPACE: b"\x7f",  # Use BACKSPACE for backspace in pye
            buttons.BUTTON_DELETE: b"\x1b[3~",
            buttons.BUTTON_TAB: b"\t",
            buttons.BUTTON_ESCAPE: b"\x1b",
            buttons.BUTTON_SPACE: b" ",
            buttons.BUTTON_PERIOD: b".",
            buttons.BUTTON_COMMA: b",",
            buttons.BUTTON_MINUS: b"-",
            buttons.BUTTON_UNDERSCORE: b"_",
            buttons.BUTTON_PLUS: b"+",
            buttons.BUTTON_EQUAL: b"=",
            buttons.BUTTON_SEMICOLON: b";",
            buttons.BUTTON_COLON: b":",
            buttons.BUTTON_SINGLE_QUOTE: b"'",
            buttons.BUTTON_DOUBLE_QUOTE: b'"',
            buttons.BUTTON_SLASH: b"/",
            buttons.BUTTON_BACKSLASH: b"\\",
            buttons.BUTTON_LEFT_BRACKET: b"[",
            buttons.BUTTON_RIGHT_BRACKET: b"]",
            buttons.BUTTON_LEFT_PARENTHESIS: b"(",
            buttons.BUTTON_RIGHT_PARENTHESIS: b")",
            buttons.BUTTON_LEFT_BRACE: b"{",
            buttons.BUTTON_RIGHT_BRACE: b"}",
            buttons.BUTTON_LESS_THAN: b"<",
            buttons.BUTTON_GREATER_THAN: b">",
            buttons.BUTTON_QUESTION: b"?",
            buttons.BUTTON_EXCLAMATION: b"!",
            buttons.BUTTON_AT: b"@",
            buttons.BUTTON_HASH: b"#",
            buttons.BUTTON_DOLLAR: b"$",
            buttons.BUTTON_PERCENT: b"%",
            buttons.BUTTON_CARET: b"^",
            buttons.BUTTON_AMPERSAND: b"&",
            buttons.BUTTON_ASTERISK: b"*",
            buttons.BUTTON_BACK_TICK: b"`",
            buttons.BUTTON_TILDE: b"~",
            buttons.BUTTON_PIPE: b"|",
            buttons.BUTTON_F5: b"\x13\r\x11",
        }

        return button_map.get(key, None)

    def _updateInternalBuffer(self):
        """Poll input and fill the output buffer with terminal sequences."""
        # Only process input if enabled
        if not self.input_enabled:
            return

        # Get input from the view_manager's input system
        button = self.input_manager.button

        if button != -1:

            # Convert button to terminal sequence
            terminal_seq = self._convert_key_to_terminal(button)
            if button == buttons.BUTTON_F5:
                self.run_requested = True
            self.input_manager.reset()
            if terminal_seq:
                self.outputBuffer.extend(terminal_seq)

    def rd(self):
        """Read one character from the terminal input buffer.

        Returns:
            str: The next buffered character.
        """
        # Handle any pending renders before reading input
        self.update()

        while not self.outputBuffer:
            self._updateInternalBuffer()

        return chr(self.outputBuffer.popleft())

    def rd_raw(self):
        """Read one raw character from the terminal input buffer.

        Returns:
            str: The next buffered character.
        """
        return self.rd()
