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
        from picoware.system.system import System

        syst = System()
        self.is_circular = syst.is_circular

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

        font_size = self.display.font_size

        # Clear the area first
        self.display.clear(self.position, self.size, self.background_color)

        num_options = len(self.options)
        if num_options == 0:
            return

        if self.is_circular:
            center_x = self.display.size.x // 2
            center_y = self.display.size.y // 2
            radius = min(self.display.size.x, self.display.size.y) // 2

            # Draw Title at top
            title_width = len(self.title) * font_size.x
            title_x = center_x - (title_width // 2)
            title_y = int(center_y - radius * 0.7)
            self.display.text(
                Vector(title_x, title_y), self.title, self.foreground_color
            )

            # arrange options vertically in center
            total_spacing = int(radius * 0.08)
            option_height = total_spacing * 2
            start_y = center_y - (
                (num_options * option_height + (num_options - 1) * total_spacing) // 2
            )
            text_pos = Vector(0, 0)
            circ_pos = Vector(0, 0)
            for i, option in enumerate(self.options):
                opt_y = start_y + i * (option_height + total_spacing)
                text_width = len(option) * font_size.x

                if i == self._state:
                    # Highlighted option - draw filled rounded area
                    opt_center_x = center_x
                    opt_center_y = opt_y + option_height // 2
                    opt_radius = max(text_width // 2 + 10, option_height // 2 + 5)
                    circ_pos.x, circ_pos.y = opt_center_x, opt_center_y
                    self.display.fill_circle(
                        circ_pos,
                        opt_radius,
                        self.foreground_color,
                    )
                    text_color = self.background_color
                else:
                    # Non-selected option - draw circle outline
                    opt_center_x = center_x
                    opt_center_y = opt_y + option_height // 2
                    opt_radius = max(text_width // 2 + 10, option_height // 2 + 5)
                    circ_pos.x, circ_pos.y = opt_center_x, opt_center_y
                    self.display.circle(
                        circ_pos,
                        opt_radius,
                        self.foreground_color,
                    )
                    text_color = self.foreground_color

                # Draw option text centered
                text_x = center_x - (text_width // 2)
                text_y = opt_y + (option_height - font_size.y) // 2
                text_pos.x, text_pos.y = text_x, text_y
                self.display.text(text_pos, option, text_color)
        else:
            # Draw Title
            title_width = len(self.title) * font_size.x
            title_x = self.position.x + (self.size.x - title_width) // 2
            title_y = self.position.y + 5
            self.display.text(
                Vector(title_x, title_y), self.title, self.foreground_color
            )

            # Calculate spacing and size for each option box
            total_spacing = int(self.display.size.x * 0.03125)  # Space between boxes
            options_y = title_y + total_spacing * 2  # Position below title
            available_width = self.size.x - (total_spacing * (num_options + 1))
            box_width = available_width // num_options
            box_height = total_spacing * 3

            # Draw each option horizontally
            box_pos = Vector(0, options_y)
            box_size = Vector(box_width, box_height)
            box_text = Vector(0, 0)
            for i, option in enumerate(self.options):
                # Calculate position for this option
                box_x = (
                    self.position.x + total_spacing + (i * (box_width + total_spacing))
                )
                box_pos.x = box_x

                # Draw rectangle for option
                if i == self._state:
                    # Highlighted (selected) option - filled rectangle
                    self.display.fill_rectangle(
                        box_pos, box_size, self.foreground_color
                    )
                    text_color = self.background_color
                else:
                    # Non-selected option - outline only
                    self.display.rect(box_pos, box_size, self.foreground_color)
                    text_color = self.foreground_color

                # Draw option text centered in the box
                text_width = len(option) * font_size.x
                box_text.x = box_x + (box_width - text_width) // 2
                box_text.y = options_y + (box_height - font_size.y) // 2
                self.display.text(box_text, option, text_color)

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
