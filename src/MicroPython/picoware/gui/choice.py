class Choice:
    """A simple choice switch for the GUI."""

    def __init__(
        self,
        draw,
        position,
        size,
        title: str,
        options: list[str],
        initial_state: int = 0,
        foreground_color: int = 0xFFFF,
        background_color: int = 0x0000,
    ):
        """
        Initialize the Choice switch with drawing context and styling.

        :param draw: The drawing context to render the choice.
        :param position: Vector position of the choice.
        :param size: Vector size of the choice.
        :param title: The label title for the choices.
        :param options: List of option strings.
        :param initial_state: Initial state of the choice.
        :param foreground_color: The color of the text.
        :param background_color: The background color.
        """
        self.display = draw
        self.position = position
        self.size = size
        self.title = title
        self._state = initial_state
        self.options = options
        self.foreground_color = foreground_color
        self.background_color = background_color

        self.clear()

    def __del__(self):
        if self.position:
            del self.position
            self.position = None
        if self.size:
            del self.size
            self.size = None
        self.title = None
        self.options = None

    @property
    def state(self) -> int:
        """Get the current state of the choice."""
        return self._state

    @state.setter
    def state(self, value: int) -> None:
        """Set the current state of the choice."""
        self._state = value

    def clear(self) -> None:
        """Clear the choice area with the background color."""
        self.display.clear(self.position, self.size, self.background_color)
        self.display.swap()

    def draw(self) -> None:
        """Render the choices on the display."""
        from picoware.system.vector import Vector

        # Clear the area first
        self.display.clear(self.position, self.size, self.background_color)

        # Draw Title
        title_width = len(self.title) * 6
        title_x = self.position.x + (self.size.x - title_width) // 2
        title_y = self.position.y + 5
        self.display.text(Vector(title_x, title_y), self.title, self.foreground_color)

        # Calculate dimensions for options
        num_options = len(self.options)
        if num_options == 0:
            return

        # Calculate spacing and size for each option box
        total_spacing = 10  # Space between boxes
        options_y = title_y + 20  # Position below title
        available_width = self.size.x - (total_spacing * (num_options + 1))
        box_width = available_width // num_options
        box_height = 30

        # Draw each option horizontally
        for i, option in enumerate(self.options):
            # Calculate position for this option
            box_x = self.position.x + total_spacing + (i * (box_width + total_spacing))
            box_pos = Vector(box_x, options_y)
            box_size = Vector(box_width, box_height)

            # Draw rectangle for option
            if i == self._state:
                # Highlighted (selected) option - filled rectangle
                self.display.fill_rectangle(box_pos, box_size, self.foreground_color)
                text_color = self.background_color
            else:
                # Non-selected option - outline only
                self.display.rect(box_pos, box_size, self.foreground_color)
                text_color = self.foreground_color

            # Draw option text centered in the box
            text_width = len(option) * 6
            text_x = box_x + (box_width - text_width) // 2
            text_y = options_y + (box_height - 8) // 2  # 8 is approximate text height
            self.display.text(Vector(text_x, text_y), option, text_color)

        # Update display
        self.display.swap()

    def reset(self) -> None:
        """Reset the choice to its initial state."""
        self._state = 0

    def scroll_down(self) -> None:
        """Scroll down the choice options."""
        self._state += 1
        if self._state >= len(self.options):
            self._state = 0
        self.draw()

    def scroll_up(self) -> None:
        """Scroll up the choice options."""
        self._state -= 1
        if self._state < 0:
            self._state = len(self.options) - 1
        self.draw()
