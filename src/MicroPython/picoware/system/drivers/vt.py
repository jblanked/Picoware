# modified from https://github.com/zenodante/PicoCalc-micropython-driver/blob/main/pico_files/modules/vt.py
# adapted for Picoware system

from collections import deque

try:
    import uio
except ImportError:
    import io as uio
from micropython import const
import uos


from picoware.system.vector import Vector
from picoware.system import buttons
from utime import ticks_ms

sc_char_width = const(53)
sc_char_height = const(40)


def ensure_nested_dir(path):
    parts = path.split("/")
    current = ""
    for part in parts:
        if not part:
            continue
        current = current + "/" + part if current else part
        try:
            uos.stat(current)
        except OSError:
            uos.mkdir(current)


class vt(uio.IOBase):

    def __init__(self, view_manager):  # ctrl+U for screen capture
        self.view_manager = view_manager
        self.draw = view_manager.draw
        self.input_manager = view_manager.input_manager
        self.storage = view_manager.storage

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

        self.pos_vector = Vector(0, 0)
        self.char_vec = Vector(self.char_width, 2)
        self.cursor_pos = Vector(0, 0)

    def dryBuffer(self):
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
        """Print a character to the terminal"""
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
        """Handle ANSI/VT100 escape sequences"""
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
        """Write text, handling ANSI escape sequences"""
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
            current_time = int(ticks_ms())

            if current_time - self._last_render_time >= self._render_throttle_ms:
                self._render_terminal()
                self._needs_render = False
                self._last_render_time = current_time

        return len(text_input)

    def _render_terminal(self):
        """Render the terminal buffer to the display"""
        self.draw.clear(color=self.draw.background)

        # Render text lines
        self.pos_vector.x = 0
        self.pos_vector.y = 0
        for y in range(self.screen_height):
            line = "".join(self.terminal_buffer[y]).rstrip()
            if line:
                self.pos_vector.y = y * self.char_height
                self.draw.text(self.pos_vector, line, self.draw.foreground)

        # Draw cursor (simple block cursor) if visible
        if self.cursor_visible:
            self.cursor_pos.x = self.cursor_x * self.char_width
            self.cursor_pos.y = self.cursor_y * self.char_height

            self.draw.fill_rectangle(
                self.cursor_pos, self.char_vec, self.draw.foreground
            )

        # Force display update
        self.draw.swap()

    def start_batch(self):
        """Start batch mode - accumulate writes without rendering"""
        self._batch_mode = True

    def end_batch(self):
        """End batch mode and render if needed"""
        self._batch_mode = False
        if self._needs_render and self._render_enabled:
            self._render_terminal()
            self._needs_render = False
            self._last_render_time = int(ticks_ms())

    def update(self):
        """Update method to be called periodically to handle pending renders"""
        if self._needs_render and self._render_enabled:
            current_time = int(ticks_ms())
            if current_time - self._last_render_time >= self._render_throttle_ms:
                self._render_terminal()
                self._needs_render = False
                self._last_render_time = current_time

    def write(self, buf):
        return self.wr(buf.decode())

    def get_screen_size(self):
        return [sc_char_height, sc_char_width]

    def _convert_key_to_terminal(self, key):
        """Convert Picoware button codes to terminal escape sequences"""
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
            buttons.BUTTON_BACK: b"\x1b",  # ESC - will trigger KEY_QUIT in pye
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
        }

        return button_map.get(key, None)

    def _updateInternalBuffer(self):
        # Only process input if enabled
        if not self.input_enabled:
            return

        # Get input from the view_manager's input system
        button = self.input_manager.button

        if button != -1:

            # Convert button to terminal sequence
            terminal_seq = self._convert_key_to_terminal(button)
            self.input_manager.reset()
            if terminal_seq:
                self.outputBuffer.extend(terminal_seq)

    def rd(self):
        # Handle any pending renders before reading input
        self.update()

        while not self.outputBuffer:
            self._updateInternalBuffer()

        return chr(self.outputBuffer.popleft())

    def rd_raw(self):
        return self.rd()

    def readinto(self, buf):
        self._updateInternalBuffer()
        count = 0
        buf_len = len(buf)
        for i in range(buf_len):
            if self.outputBuffer:
                buf[i] = self.outputBuffer.popleft()
                count += 1
            else:
                break
        return count if count > 0 else None
