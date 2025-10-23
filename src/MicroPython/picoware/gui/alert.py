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

        size: Vector = self.display.size

        # Draw Title
        title_width = len(title) * 6
        title_x = (size.x - title_width) // 2
        self.display.text(Vector(title_x, 0), title, self.text_color)

        # Draw Border
        border_left = 20
        border_top = 20
        border_width = size.x - 40
        border_height = size.y - 40
        self.display.rect(
            Vector(border_left, border_top),
            Vector(border_width, border_height),
            self.text_color,
        )

        # Calculate text area constraints
        text_start_x = 30
        text_start_y = 30
        text_max_width = size.x - 60  # Leave padding from border
        chars_per_line = text_max_width // 6  # 6 pixels per character

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
