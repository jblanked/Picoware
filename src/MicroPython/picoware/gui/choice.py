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
        """Initialize the Choice switch with drawing context and styling.

        Args:
            draw (Draw): The drawing context to render the choice.
            position (Vector): Vector position of the choice.
            size (Vector): Vector size of the choice.
            title (str): The label title for the choices.
            options (list[str]): List of option strings.
            initial_state (int): Initial state of the choice. Defaults to 0.
            foreground_color (int): The color of the text. Defaults to 0xFFFF.
            background_color (int): The background color. Defaults to 0x0000.
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

        self.use_lvgl = draw.use_lvgl
        self._lvgl_choice = None

        # Initialize LVGL Choice if requested
        if self.use_lvgl:
            try:
                from picoware_lvgl import init, Choice as LVGLChoice

                init()

                class LVGLChoiceWrapper(LVGLChoice):
                    """Wrapper that forwards state assignment to LVGL."""

                    def __setattr__(self, name, value):
                        """Forward state assignment to the LVGL choice.

                        Args:
                            name (str): The attribute name.
                            value: The attribute value.
                        """
                        if name == "state":
                            self.set_state(value)
                        else:
                            super().__setattr__(name, value)

                # Create LVGL Choice instance
                self._lvgl_choice = LVGLChoiceWrapper(
                    draw,
                    (position.x, position.y),
                    (size.x, size.y),
                    title,
                    options,
                    initial_state,
                    foreground_color,
                    background_color,
                )
            except (ImportError, RuntimeError, ValueError):
                self.use_lvgl = False

        if not self.use_lvgl:
            self.clear()

    def __del__(self):
        """Clean up resources and deinitialize LVGL."""
        if self._lvgl_choice is not None:
            from picoware_lvgl import deinit

            del self._lvgl_choice
            self._lvgl_choice = None
            deinit()

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
        if self.use_lvgl and self._lvgl_choice is not None:
            return self._lvgl_choice.get_state()

        return self._state

    @state.setter
    def state(self, value: int) -> None:
        """Set the current state of the choice.

        Args:
            value (int): The new state index.
        """
        self._state = value

        if self.use_lvgl and self._lvgl_choice is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_choice.set_state(value)
            task_handler()

    def clear(self) -> None:
        """Clear the choice area with the background color."""
        if self.use_lvgl and self._lvgl_choice is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_choice.clear()
            task_handler()
            return

        self.display.clear(self.position, self.size, self.background_color)
        self.display.swap()

    def close(self) -> None:
        """Close the dropdown menu (LVGL only currently)."""
        if self.use_lvgl and self._lvgl_choice is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_choice.close()
            task_handler()

    def draw(self) -> None:
        """Render the choices on the display."""
        if self.use_lvgl and self._lvgl_choice is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_choice.draw()
            task_handler()
            self._state = self._lvgl_choice.get_state()
            return

        from picoware_boards import BOARD_ID, BOARD_FLIPPER_ZERO

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
            title_width = self.display.len(self.title)
            title_x = center_x - (title_width // 2)
            title_y = int(center_y - radius * 0.7)
            self.display._text(
               title_x, title_y, self.title, self.foreground_color
            )

            # arrange options vertically in center
            total_spacing = int(radius * 0.08)
            option_height = total_spacing * 2
            start_y = center_y - (
                (num_options * option_height + (num_options - 1) * total_spacing) // 2
            )
            _five_x, _five_y = self.display.scale(5, 5)
            for i, option in enumerate(self.options):
                opt_y = start_y + i * (option_height + total_spacing)
                text_width = self.display.len(option)

                if i == self._state:
                    # Highlighted option - draw filled rounded area
                    opt_center_x = center_x
                    opt_center_y = opt_y + option_height // 2
                    opt_radius = max(text_width // 2 + (_five_x * 2), option_height // 2 + _five_y)
                    self.display._fill_circle(
                        opt_center_x, opt_center_y,
                        opt_radius,
                        self.foreground_color,
                    )
                    text_color = self.background_color
                else:
                    # Non-selected option - draw circle outline
                    opt_center_x = center_x
                    opt_center_y = opt_y + option_height // 2
                    opt_radius = max(text_width // 2 + (_five_x * 2), option_height // 2 + _five_y)
                    self.display._circle(
                        opt_center_x, opt_center_y,
                        opt_radius,
                        self.foreground_color,
                    )
                    text_color = self.foreground_color

                # Draw option text centered
                text_x = center_x - (text_width // 2)
                text_y = opt_y + (option_height - font_size.y) // 2
                self.display._text(text_x, text_y, option, text_color)
        else:
            # Draw Title
            title_font_int = 1 if BOARD_ID == BOARD_FLIPPER_ZERO else 2
            _font = self.display.get_font(title_font_int)
            title_width = self.display.len(self.title, title_font_int)
            title_x = self.position.x + (self.size.x // 2) - (title_width // 2)
            title_y = self.position.y + self.display.scale_y(5)
            self.display._text(
                title_x, title_y, self.title, self.foreground_color, title_font_int
            )

            # Draw options in a 2-column list below the title
            y_start = title_y + (_font.height * 2) + self.display.scale_y(10)
            x_col1 = self.position.x + self.display.scale_x(5)
            x_col2 = self.position.x + self.size.x // 2 + self.display.scale_x(5)
            line_height = _font.height + 2

            for i, option in enumerate(self.options):
                row = i // 2
                col = i % 2
                x_pos = x_col1 if col == 0 else x_col2
                y_pos = y_start + row * line_height

                if i == self._state:
                    # Draw background highlight for selected option
                    self.display._fill_rectangle(
                        x_pos - self.display.scale_x(2), y_pos - self.display.scale_y(2), self.display.len(option) + self.display.scale_x(4), line_height - self.display.scale_y(2), self.foreground_color
                    )
                    text_color = self.background_color
                else:
                    text_color = self.foreground_color
                self.display._text(x_pos, y_pos, option, text_color)

        # Update display
        self.display.swap()

    def is_open(self) -> bool:
        """Check if the dropdown is open (LVGL only currently)."""
        if self.use_lvgl and self._lvgl_choice is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            is_open = self._lvgl_choice.is_open()
            task_handler()
            return is_open

        return False

    def open(self) -> None:
        """Open the dropdown menu (LVGL only currently)."""
        if self.use_lvgl and self._lvgl_choice is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_choice.open()
            task_handler()

    def reset(self) -> None:
        """Reset the choice to its initial state."""
        if self.use_lvgl and self._lvgl_choice is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_choice.reset()
            task_handler()
            self._state = 0
            return

        self._state = 0

    def scroll_down(self) -> None:
        """Scroll down the choice options."""
        if self.use_lvgl and self._lvgl_choice is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_choice.scroll_down()
            task_handler()
            self._state = self._lvgl_choice.get_state()
            return

        self._state += 1
        if self._state >= len(self.options):
            self._state = 0
        self.draw()

    def scroll_up(self) -> None:
        """Scroll up the choice options."""
        if self.use_lvgl and self._lvgl_choice is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_choice.scroll_up()
            task_handler()
            self._state = self._lvgl_choice.get_state()
            return

        self._state -= 1
        if self._state < 0:
            self._state = len(self.options) - 1
        self.draw()
