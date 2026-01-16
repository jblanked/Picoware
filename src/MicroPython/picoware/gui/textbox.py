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
        from picoware.system.system import System
        from picoware.system.vector import Vector

        syst = System()
        self.is_circular = syst.is_circular

        self.foreground_color = foreground_color
        self.background_color = background_color
        self.characters_per_line = 0
        self.lines_per_screen = 0
        self.total_lines = 0
        self.current_line = -1
        self.show_scrollbar = show_scrollbar
        self.spacing = int(draw.size.x * 0.03125)
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
            is_horizontal=self.is_circular,
        )

        self.characters_per_line = int(
            draw.size.x // draw.font_size.x
        )  # width is 320, 5x8 font (width of 6)
        self.lines_per_screen = int(
            draw.size.y // draw.font_size.y
        )  # height is 320, 10 pixel line spacing

        self.line_vector = Vector(0, 0)

        draw.swap()

    def __del__(self):
        # Reset content
        self.current_text = ""
        self.current_line = -1
        self.line_buffer = []
        self.line_positions = []
        self.total_lines = 0
        # Reset scrollbar
        if self.scrollbar:
            del self.scrollbar
            self.scrollbar = None
        if self.position:
            del self.position
            self.position = None
        if self.size:
            del self.size
            self.size = None
        if self.line_vector:
            del self.line_vector
            self.line_vector = None

    @property
    def text(self) -> str:
        """Get the current text in the text box."""
        return self.current_text

    @property
    def text_height(self) -> int:
        """Get the height of the text box based on the number of lines and font size."""
        return (
            0
            if self.total_lines == 0
            else (self.total_lines - 1) * self.scrollbar.display.font_size.y + 2
        )

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

        if self.scrollbar.is_horizontal:
            # Horizontal scrollbar positioning (top for circular displays)
            max_offset = self.size.x - self.scrollbar.size.x - 2
            bar_offset_x = int(scroll_ratio * max_offset)
            bar_x = self.position.x + bar_offset_x + 1
            bar_y = self.position.y + self.spacing
        else:
            # Vertical scrollbar positioning
            max_offset = self.size.y - self.scrollbar.size.y - 2
            bar_offset_y = int(scroll_ratio * max_offset)
            bar_x = (
                self.position.x + self.size.x - self.scrollbar.size.x - 1
            )  # 1 pixel padding
            bar_y = self.position.y + bar_offset_y + 1  # 1 pixel padding

        self.scrollbar.position.x, self.scrollbar.position.y = int(bar_x), int(bar_y)

    def set_scrollbar_size(self):
        """Set the size of the scrollbar based on the number of lines."""
        content_height = self.text_height
        view_height = self.size.y

        if self.scrollbar.is_horizontal:
            # Horizontal scrollbar sizing
            view_width = self.size.x
            bar_width = 0

            if content_height <= view_height or content_height <= 0:
                bar_width = view_width - 2  # 1 pixel padding
            else:
                bar_width = int(view_width * (view_height / content_height))

            # enforce minimum scrollbar width
            min_bar_width = self.spacing
            bar_width = max(bar_width, min_bar_width)

            self.scrollbar.size.x, self.scrollbar.size.y = bar_width, 6
        else:
            # Vertical scrollbar sizing
            bar_height = 0

            if content_height <= view_height or content_height <= 0:
                bar_height = (
                    view_height - 2
                )  # 1 pixel padding (+1 pixel for the scrollbar)
            else:
                bar_height = int(view_height * (view_height / content_height))

            # enforce minimum scrollbar height
            min_bar_height = self.spacing
            bar_height = max(bar_height, min_bar_height)

            self.scrollbar.size.x, self.scrollbar.size.y = 6, bar_height

    def display_visible_lines(self):
        """Display only the lines that are currently visible."""
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

        if self.is_circular:
            # Circular display implementation
            center_x = self.scrollbar.display.size.x // 2
            center_y = self.scrollbar.display.size.y // 2

            # Display lines with center alignment for circular screen
            for i, line_idx in enumerate(visible_range):
                if line_idx < len(self.line_positions):
                    line_info = self.line_positions[line_idx]
                    start_idx, length = line_info

                    if start_idx + length <= len(self.current_text):
                        line_text = self.current_text[
                            start_idx : start_idx + length
                        ].rstrip()

                        # Calculate y position relative to center
                        y_offset = int(
                            (i * self.spacing)
                            - ((len(visible_range) * self.spacing) // 2)
                        )
                        y_pos = int(center_y + y_offset + (self.spacing // 2))

                        # Center align text horizontally
                        text_width = len(line_text) * self.scrollbar.display.font_size.x
                        self.line_vector.x = center_x - (text_width // 2)
                        self.line_vector.y = int(y_pos)

                        self.scrollbar.display.text(
                            self.line_vector,
                            line_text,
                            self.foreground_color,
                        )
        else:
            # Original rectangular implementation
            # Display only the lines in view
            for i, line_idx in enumerate(visible_range):
                if line_idx < len(self.line_positions):
                    line_info = self.line_positions[line_idx]
                    start_idx, length = line_info

                    if start_idx + length <= len(self.current_text):
                        line_text = self.current_text[
                            start_idx : start_idx + length
                        ].rstrip()
                        y_pos = int(
                            self.position.y + 5 + (i * self.spacing)
                        )  # Position based on line number within view
                        self.line_vector.x = int(self.position.x + 1)
                        self.line_vector.y = y_pos
                        self.scrollbar.display.text(
                            self.line_vector,
                            line_text,
                            self.foreground_color,
                        )

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
        if self.current_text == text:
            return
        self.current_text = text
        self.refresh()
