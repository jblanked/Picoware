"""Alert - Simple alert dialog."""

class Alert:
    """A simple alert dialog class for displaying messages to the user."""

    def __init__(
        self, draw, text: str, text_color: int = 0xFFFF, background_color: int = 0x0000
    ):
        """Initialize the Alert with drawing context and styling.

        Args:
            draw (Draw): The drawing context to render the alert.
            text (str): The message to display in the alert.
            text_color (int): The color of the text. Defaults to 0xFFFF.
            background_color (int): The background color of the alert. Defaults to 0x0000.
        """
        from picoware.system.system import System

        syst = System()
        self.is_circular = syst.is_circular

        self.display = draw
        self._text = text
        self.text_color = text_color
        self.background_color = background_color
        self.use_lvgl = draw.use_lvgl
        self._lvgl_alert = None

        # Initialize LVGL Alert if requested
        if self.use_lvgl:
            try:
                from picoware_lvgl import init, Alert as LVGLAlert

                init()

                class LVGLAlertWrapper(LVGLAlert):
                    """Wrapper that forwards text assignment to LVGL."""

                    def __setattr__(self, name, value):
                        """Forward text assignment to the LVGL alert.

                        Args:
                            name (str): The attribute name.
                            value: The attribute value.
                        """
                        if name == "text":
                            self.set_text(value)
                        else:
                            super().__setattr__(name, value)

                # Create LVGL Alert instance
                self._lvgl_alert = LVGLAlertWrapper(text, text_color, background_color)
            except (ImportError, RuntimeError, ValueError):
                self.use_lvgl = False

    def __del__(self):
        """Clean up resources and deinitialize LVGL."""
        if self._lvgl_alert is not None:
            from picoware_lvgl import deinit

            del self._lvgl_alert
            self._lvgl_alert = None
            deinit()
        self._text = ""
        self.text_color = 0
        self.background_color = 0

    @property
    def text(self) -> str:
        """Get the current alert text."""
        if self._lvgl_alert is not None:
            return self._lvgl_alert.text
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        """Set the alert text.

        Args:
            value (str): The new alert text.
        """
        self._text = value
        if self._lvgl_alert is not None:
            self._lvgl_alert.text = value

    def clear(self) -> None:
        """Clear the display with the background color."""
        if self.use_lvgl and self._lvgl_alert is not None:
            self._lvgl_alert.clear()
            return

        from picoware.system.vector import Vector

        self.display.clear(Vector(0, 0), self.display.size, self.background_color)
        self.display.swap()

    def draw(self, title: str) -> None:
        """Render the alert message on the display.

        Args:
            title (str): The title text to display at the top.
        """
        if self.use_lvgl and self._lvgl_alert is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_alert.draw(title)
            task_handler()
            return

        from picoware.system.vector import Vector

        self.clear()

        size: Vector = self.display.size
        font_size: Vector = self.display.font_size

        if self.is_circular:
            # Circular display implementation
            center_x = size.x // 2
            center_y = size.y // 2
            radius = min(size.x, size.y) // 2

            # Draw Title at top center
            title_width = self.display.len(title)
            title_x = center_x - (title_width // 2)
            title_y = int(center_y - radius * 0.85)
            self.display._text(title_x, title_y, title, self.text_color)

            # Draw circular border
            border_radius = int(radius * 0.9)
            self.display._circle(
                center_x, center_y, border_radius, self.text_color
            )

            # Calculate text area constraints for circular display
            text_start_y = int(center_y - radius * 0.6)
            max_radius_at_y = int(radius * 0.8)
            chars_per_line = ((max_radius_at_y * 2) // (font_size.x)) - 1

            # Wrap text manually based on character count
            line: int = 0
            if len(self._text) > 400:
                self._text = self._text[-400:]
            words = self._text.split()
            current_line = ""

            distance = font_size.y + 1
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                current_y = text_start_y + line * distance

                if current_y + distance > size.y:
                    break

                if len(test_line) <= chars_per_line:
                    current_line = test_line
                else:
                    if current_line:
                        line_width = self.display.len(current_line)
                        self.display._text(center_x - (line_width // 2), current_y, current_line, self.text_color)
                        line += 1

                    if len(word) > chars_per_line:
                        for i in range(0, len(word), chars_per_line):
                            chunk = word[i : i + chars_per_line]
                            chunk_width = self.display.len(chunk)
                            self.display._text(center_x - (chunk_width // 2), current_y, chunk, self.text_color)
                            line += 1
                        current_line = ""
                    else:
                        current_line = word

            if current_line:
                line_width = self.display.len(current_line)
                self.display._text(center_x - (line_width // 2), current_y, current_line, self.text_color)
        else:
            # Draw Title
            title_width = self.display.len(title)
            title_x = (size.x - title_width) // 2
            self.display._text(title_x, 0, title, self.text_color)

            # Draw Border
            border_left = int(size.x * 0.0625)
            border_top = self.display.font_size.y + 1
            border_width = int(size.x - (2 * border_left))
            border_height = (size.y - self.display.scale_y(5)) - border_top
            self.display._rectangle(
                border_left, border_top,
                border_width, border_height,
                self.text_color,
            )

            # Calculate text area constraints
            text_start_x = int(size.x * 0.09375)
            text_start_y = border_top + 2
            text_max_width = size.x - (2 * text_start_x)  # Leave padding from border
            chars_per_line = (text_max_width // font_size.x) - 1

            # Wrap text manually based on character count
            line: int = 0
            # max/last/most-recent 400 characters only
            if len(self._text) > 400:
                self._text = self._text[-400:]
            words = self._text.split()
            current_line = ""

            distance = self.display.font_size.y + 1
            for word in words:
                # Check if adding this word would exceed the line width
                test_line = current_line + (" " if current_line else "") + word
                current_y = text_start_y + line * distance

                if current_y + distance > border_height:
                    break

                if len(test_line) <= chars_per_line:
                    current_line = test_line
                else:
                    # Draw the current line and start a new one
                    if current_line:
                        self.display._text(
                            text_start_x,
                            current_y,
                            current_line,
                            self.text_color,
                        )
                        line += 1

                    # If the word itself is longer than a line, split it
                    if len(word) > chars_per_line:
                        for i in range(0, len(word), chars_per_line):
                            chunk = word[i : i + chars_per_line]
                            self.display._text(
                                text_start_x,
                                current_y,
                                chunk,
                                self.text_color,
                            )
                            line += 1
                        current_line = ""
                    else:
                        current_line = word

            # Draw any remaining text
            if current_line:
                self.display._text(
                    text_start_x,
                    text_start_y + line * distance,
                    current_line,
                    self.text_color,
                )

        self.display.swap()
