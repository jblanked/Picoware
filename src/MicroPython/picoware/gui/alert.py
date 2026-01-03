class Alert:
    """A simple alert dialog class for displaying messages to the user."""

    def __init__(
        self, draw, text: str, text_color: int = 0xFFFF, background_color: int = 0x0000
    ):
        """
        Initialize the Alert with drawing context and styling.

        :param draw: The drawing context to render the alert.
        :param text: The message to display in the alert.
        :param text_color: The color of the text.
        :param background_color: The background color of the alert.
        """
        from picoware.system.system import System

        syst = System()
        self.is_circular = syst.is_circular

        self.display = draw
        self.text = text
        self.text_color = text_color
        self.background_color = background_color

    def __del__(self):
        self.text = ""
        self.text_color = 0
        self.background_color = 0

    def clear(self) -> None:
        """Clear the display with the background color."""
        from picoware.system.vector import Vector

        self.display.clear(Vector(0, 0), self.display.size, self.background_color)
        self.display.swap()

    def draw(self, title: str) -> None:
        """Render the alert message on the display."""
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
            title_width = len(title) * font_size.x
            title_x = center_x - (title_width // 2)
            title_y = int(center_y - radius * 0.85)
            self.display.text(Vector(title_x, title_y), title, self.text_color)

            # Draw circular border
            border_radius = int(radius * 0.9)
            self.display.circle(
                Vector(center_x, center_y), border_radius, self.text_color
            )

            # Calculate text area constraints for circular display
            text_start_y = int(center_y - radius * 0.6)
            max_radius_at_y = int(radius * 0.8)
            chars_per_line = (max_radius_at_y * 2) // (font_size.x + 1)

            # Wrap text manually based on character count
            line: int = 0
            if len(self.text) > 400:
                self.text = self.text[-400:]
            words = self.text.split()
            current_line = ""

            text_vector = Vector(0, text_start_y)
            for word in words:
                test_line = current_line + (" " if current_line else "") + word

                if len(test_line) <= chars_per_line:
                    current_line = test_line
                else:
                    if current_line:
                        line_width = len(current_line) * font_size.x
                        text_vector.x = center_x - (line_width // 2)
                        text_vector.y = text_start_y + line * 16
                        self.display.text(text_vector, current_line, self.text_color)
                        line += 1

                    if len(word) > chars_per_line:
                        for i in range(0, len(word), chars_per_line):
                            chunk = word[i : i + chars_per_line]
                            chunk_width = len(chunk) * font_size.x
                            text_vector.x = int(center_x - (chunk_width // 2))
                            text_vector.y = int(text_start_y + line * 16)
                            self.display.text(text_vector, chunk, self.text_color)
                            line += 1
                        current_line = ""
                    else:
                        current_line = word

            if current_line:
                line_width = len(current_line) * font_size.x
                text_vector.x = center_x - (line_width // 2)
                text_vector.y = text_start_y + line * 16
                self.display.text(text_vector, current_line, self.text_color)
        else:
            # Draw Title
            title_width = len(title) * font_size.x
            title_x = (size.x - title_width) // 2
            self.display.text(Vector(title_x, 0), title, self.text_color)

            # Draw Border
            border_left = int(size.x * 0.0625)
            border_top = int(size.y * 0.0625)
            border_width = int(size.x - (2 * border_left))
            border_height = int(size.y - (2 * border_top))
            self.display.rect(
                Vector(border_left, border_top),
                Vector(border_width, border_height),
                self.text_color,
            )

            # Calculate text area constraints
            text_start_x = int(size.x * 0.09375)
            text_start_y = int(size.y * 0.09375)
            text_max_width = size.x - (2 * text_start_x)  # Leave padding from border
            chars_per_line = int(text_max_width // (font_size.x + 1))

            # Wrap text manually based on character count
            line: int = 0
            # max/last/most-recent 400 characters only
            if len(self.text) > 400:
                self.text = self.text[-400:]
            words = self.text.split()
            current_line = ""

            text_vector = Vector(text_start_x, text_start_y)
            for word in words:
                # Check if adding this word would exceed the line width
                test_line = current_line + (" " if current_line else "") + word

                if len(test_line) <= chars_per_line:
                    current_line = test_line
                else:
                    # Draw the current line and start a new one
                    if current_line:
                        text_vector.x = text_start_x
                        text_vector.y = text_start_y + line * 18
                        self.display.text(
                            text_vector,
                            current_line,
                            self.text_color,
                        )
                        line += 1

                    # If the word itself is longer than a line, split it
                    if len(word) > chars_per_line:
                        for i in range(0, len(word), chars_per_line):
                            chunk = word[i : i + chars_per_line]
                            text_vector.x = text_start_x
                            text_vector.y = text_start_y + line * 18
                            self.display.text(
                                text_vector,
                                chunk,
                                self.text_color,
                            )
                            line += 1
                        current_line = ""
                    else:
                        current_line = word

            # Draw any remaining text
            if current_line:
                text_vector.x = text_start_x
                text_vector.y = text_start_y + line * 18
                self.display.text(
                    text_vector,
                    current_line,
                    self.text_color,
                )

        self.display.swap()
