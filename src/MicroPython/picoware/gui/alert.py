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
        self.display.text(Vector(size.x / 2 - 15, 0), title, self.text_color)

        # Draw Border
        self.display.rect(
            Vector(20, 20), Vector(size.x - 40, size.y - 40), self.text_color
        )

        # Draw Text (within the border - non-centered)
        line: int = 0
        lines = self.text.split("\n")

        for text_line in lines:
            # Draw each line of text
            self.display.text(Vector(30, 30 + line * 18), text_line, self.text_color)
            line += 1

        self.display.swap()
