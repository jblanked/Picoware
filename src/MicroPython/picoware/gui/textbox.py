from picoware.system.vector import Vector


class TextBox:
    '''Class for a text box with scrolling functionality."""'''

    def __init__(
        self,
        draw,
        y: int,
        height: int,
        foreground_color: int = 0xFFFF,
        background_color: int = 0x0000,
        show_scrollbar: bool = True,
    ):
        from picoware.gui.scrollbar import ScrollBar

        self.foreground_color = foreground_color
        self.background_color = background_color
        self.characters_per_line = 0
        self.lines_per_screen = 0
        self.total_lines = 0
        self.current_line = -1
        self.show_scrollbar = show_scrollbar
        #
        self.current_text = ""
        self.position = Vector(0, y)
        self.size = Vector(draw.size.x, height)
        draw.clear(self.position, self.size, self.background_color)

        # Line state tracking for memory optimization
        self.line_buffer = []  # Stores line contents - only visible lines
        self.line_positions = []  # Stores positions of all lines for quick scrolling

        self.scrollbar = ScrollBar(
            draw,
            Vector(0, 0),
            Vector(0, 0),
            self.foreground_color,
            self.background_color,
        )

        self.characters_per_line = 53  # width is 320, 5x8 font (width of 6)
        self.lines_per_screen = 32  # height is 320, 10 pixel line spacing

        draw.swap()

    def __del__(self):
        # Reset content
        self.current_text = ""
        self.current_line = -1
        self.line_buffer = []
        self.line_positions = []
        self.total_lines = 0
        # Reset scrollbar
        del self.scrollbar
        self.scrollbar = None

    def get_text_height(self) -> int:
        """Get the height of the text box based on the number of lines and font size."""
        return (
            0 if self.total_lines == 0 else (self.total_lines - 1) * 10
        )  # 10 pixel spacing for 5x8 pixel font

    def set_scrollbar_position(self):
        """Set the position of the scrollbar based on the current line."""
        # Calculate the proper scroll position based on current line and total lines
        scroll_ratio = 0.0
        if self.total_lines > self.lines_per_screen and self.total_lines > 0:
            # Ensure we don't start scrolling until after self.lines_per_screen
            if self.current_line <= self.lines_per_screen:
                scroll_ratio = 0.0
            else:
                scroll_ratio = float(self.current_line - self.lines_per_screen) / float(
                    self.total_lines - self.lines_per_screen
                )

        # maximum vertical movement for scrollbar thumb
        max_offset = self.size.y - self.scrollbar.size.y - 2
        # Account for padding
        bar_offset_y = int(scroll_ratio * max_offset)

        bar_x = self.position.x + self.size.x - self.scrollbar.size.x - 1
        # 1 pixel padding
        bar_y = self.position.y + bar_offset_y + 1
        # 1 pixel padding

        self.scrollbar.position = Vector(int(bar_x), int(bar_y))

    def set_scrollbar_size(self):
        """Set the size of the scrollbar based on the number of lines."""
        content_height = self.get_text_height()
        view_height = self.size.y
        bar_height = 0

        if content_height <= view_height or content_height <= 0:
            bar_height = view_height - 2
            # 1 pixel padding (+1 pixel for the scrollbar)
        else:
            bar_height = int(view_height * (view_height / content_height))

        # enforce minimum scrollbar height
        min_bar_height = 10
        bar_height = max(bar_height, min_bar_height)

        self.scrollbar.size = Vector(6, bar_height)

    def display_visible_lines(self):
        """Display only the lines that are currently visible."""
        from gc import collect

        # Clear current display
        self.scrollbar.display.clear(self.position, self.size, self.background_color)

        # Calculate first visible line
        first_visible_line = 0
        if self.current_line > self.lines_per_screen:
            first_visible_line = self.current_line - self.lines_per_screen

        # Determine which lines to display
        visible_range = range(
            first_visible_line,
            min(first_visible_line + self.lines_per_screen, len(self.line_positions)),
        )

        # Display only the lines in view
        for i, line_idx in enumerate(visible_range):
            if line_idx < len(self.line_positions):
                line_info = self.line_positions[line_idx]
                start_idx, length = line_info

                if start_idx + length <= len(self.current_text):
                    line_text = self.current_text[
                        start_idx : start_idx + length
                    ].rstrip()
                    y_pos = (
                        self.position.y + 5 + (i * 10)
                    )  # Position based on line number within view
                    self.scrollbar.display.text(
                        Vector(int(self.position.x + 1), int(y_pos)),
                        line_text,
                        self.foreground_color,
                    )

        # Force garbage collection
        collect()

    def clear(self):
        """Clear the text box and reset the scrollbar."""
        # Clear display area
        self.scrollbar.display.clear(self.position, self.size, self.background_color)
        # Reset content
        self.current_text = ""
        self.current_line = -1
        self.line_buffer = []
        self.line_positions = []
        self.total_lines = 0
        # Reset scrollbar
        self.scrollbar.clear()
        self.set_scrollbar_size()
        self.set_scrollbar_position()
        self.scrollbar.display.swap()

    def refresh(self):
        """Refresh the display to show current text and scrollbar."""
        from gc import collect

        # Clear area for fresh draw
        self.scrollbar.display.clear(self.position, self.size, self.background_color)

        if self.show_scrollbar:
            self.scrollbar.clear()

        # Wrap text into lines (preserve words)
        self.line_positions = []
        str_len = len(self.current_text)
        line_start = 0
        line_length = 0
        total = 1
        i = 0
        while i < str_len:
            if self.current_text[i] == "\n":
                self.line_positions.append((line_start, line_length))
                total += 1
                i += 1
                line_start = i
                line_length = 0
                continue
            # skip leading spaces
            if line_length == 0:
                while i < str_len and self.current_text[i] == " ":
                    i += 1
                line_start = i
            # count word length
            word_start = i
            while i < str_len and self.current_text[i] not in (" ", "\n"):
                i += 1
            word_length = i - word_start
            if line_length + word_length > self.characters_per_line and line_length > 0:
                # new line
                self.line_positions.append((line_start, line_length))
                total += 1
                line_start = word_start
                line_length = 0
            # add word
            line_length += word_length
            # skip space
            if i < str_len and self.current_text[i] == " ":
                line_length += 1
                i += 1
        # append final line
        if line_length > 0 or total == 1:
            self.line_positions.append((line_start, line_length))

        self.total_lines = len(self.line_positions)

        # Initialize or clamp current line to last line
        if self.current_line == -1 or self.current_line >= self.total_lines:
            self.current_line = self.total_lines - 1

        # Update scrollbar and display
        self.display_visible_lines()

        if self.show_scrollbar:
            self.set_scrollbar_size()
            self.set_scrollbar_position()
            self.scrollbar.draw()

        self.scrollbar.display.swap()
        collect()

    def scroll_down(self):
        """Scroll down by one line."""
        if self.current_line < self.total_lines - 1:
            self.set_current_line(self.current_line + 1)

    def scroll_up(self):
        """Scroll up by one line."""
        if self.current_line > 0:
            self.set_current_line(self.current_line - 1)

    def set_current_line(self, line: int):
        """Scroll the text box to the specified line."""
        if self.total_lines == 0 or line < 0 or line > (self.total_lines - 1):
            return

        self.current_line = line
        # Update scrollbar and display
        self.display_visible_lines()
        if self.show_scrollbar:
            self.set_scrollbar_size()
            self.set_scrollbar_position()
            self.scrollbar.draw()
        self.scrollbar.display.swap()

    def set_text(self, text: str):
        """Set the text in the text box, wrap lines, and scroll to bottom."""
        self.current_text = text
        self.refresh()
