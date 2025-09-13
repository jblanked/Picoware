class Toggle:
    """A simple toggle switch for the GUI."""

    def __init__(
        self,
        draw,
        position,
        size,
        text: str,
        initial_state: bool = False,
        foreground_color: int = 0xFFFF,
        background_color: int = 0x0000,
        on_color: int = 0x001F,
        border_color: int = 0xFFFF,
        border_width: int = 1,
    ):
        """
        Initialize the Toggle switch with drawing context and styling.

        :param draw: The drawing context to render the toggle.
        :param position: Vector position of the toggle.
        :param size: Vector size of the toggle.
        :param text: The label text for the toggle.
        :param initial_state: Initial state of the toggle (True/False).
        :param foreground_color: The color of the text.
        :param background_color: The background color.
        :param on_color: The color when toggle is on.
        :param border_color: The color of the border.
        :param border_width: The width of the border.
        """
        self.display = draw
        self.position = position
        self.size = size
        self.text = text
        self.state = initial_state
        self.foreground_color = foreground_color
        self.background_color = background_color
        self.on_color = on_color
        self.border_color = border_color
        self.border_width = border_width

        self.clear()

    def clear(self) -> None:
        """Clear the toggle area with the background color."""
        self.display.clear(self.position, self.size, self.background_color)
        self.display.swap()

    def draw(self) -> None:
        """Render the toggle switch on the display."""
        from picoware.system.vector import Vector

        self.display.clear(self.position, self.size, self.background_color)
        self.display.line(
            Vector(self.position.x, self.position.y + self.size.y - self.border_width),
            Vector(
                self.position.x + self.size.x,
                self.position.y + self.size.y - self.border_width,
            ),
            self.border_color,
        )
        self.display.text(
            Vector(self.position.x + 5, self.position.y + self.size.y // 2 - 8),
            self.text,
            self.foreground_color,
        )

        toggle_width = 30
        toggle_height = 16
        toggle_x = self.position.x + self.size.x - toggle_width - 5
        toggle_y = self.position.y + (self.size.y - toggle_height) // 2
        knob_radius = 6

        if self.state:
            # Toggle is ON
            self.display.fill_rectangle(
                Vector(toggle_x, toggle_y),
                Vector(toggle_width, toggle_height),
                self.on_color,
            )
            self.display.fill_circle(
                Vector(
                    toggle_x + toggle_width - knob_radius - 2,
                    toggle_y + toggle_height // 2,
                ),
                knob_radius,
                self.background_color,
            )
        else:
            # Toggle is OFF
            self.display.fill_rectangle(
                Vector(toggle_x, toggle_y),
                Vector(toggle_width, toggle_height),
                self.border_color,
            )
            self.display.fill_circle(
                Vector(toggle_x + knob_radius + 2, toggle_y + toggle_height // 2),
                knob_radius,
                self.background_color,
            )

        self.display.swap()

    def set_state(self, new_state: bool) -> None:
        """Set the toggle state and redraw."""
        self.state = new_state
        self.draw()

    def toggle(self) -> None:
        """Toggle the current state."""
        self.set_state(not self.state)

    def get_state(self) -> bool:
        """Get the current state of the toggle."""
        return self.state
