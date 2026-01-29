from picoware.system.vector import Vector


class Toggle:
    """A simple toggle switch for the GUI."""

    def __init__(
        self,
        draw,
        position: Vector,
        size: Vector,
        text: str,
        initial_state: bool = False,
        foreground_color: int = 0xFFFF,
        background_color: int = 0x0000,
        on_color: int = 0x001F,
        border_color: int = 0xFFFF,
        border_width: int = 1,
        should_clear: bool = True,
        use_lvgl: bool = True,
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
        :param use_lvgl: If True, use LVGL rendering instead of standard rendering.
        """
        from picoware.system.system import System

        syst = System()
        self.is_circular = syst.is_circular

        self.display = draw
        self.position = position
        self.size = size
        self._text = text
        self._state = initial_state
        self.foreground_color = foreground_color
        self.background_color = background_color
        self.on_color = on_color
        self.border_color = border_color
        self.border_width = border_width

        self.use_lvgl = False if not use_lvgl else draw.use_lvgl
        self._lvgl_toggle = None

        # Initialize LVGL Toggle if requested
        if self.use_lvgl:
            try:
                from picoware_lvgl import init, Toggle as LVGLToggle

                init()

                # Create LVGL Toggle instance
                self._lvgl_toggle = LVGLToggle(
                    (position.x, position.y),
                    (size.x, size.y),
                    text,
                    initial_state,
                    foreground_color,
                    background_color,
                    on_color,
                    border_color,
                    border_width,
                    should_clear,
                )
            except (ImportError, RuntimeError, ValueError):
                self.use_lvgl = False

        if not self.use_lvgl and should_clear:
            self.clear()

    def __del__(self):
        if self._lvgl_toggle is not None:
            self._lvgl_toggle.deinit()
            del self._lvgl_toggle
            self._lvgl_toggle = None

        if self.position:
            del self.position
            self.position = None
        if self.size:
            del self.size
            self.size = None
        self._text = ""

    @property
    def state(self) -> bool:
        """Get the current state of the toggle."""
        return self._state

    @state.setter
    def state(self, new_state: bool) -> None:
        """Set the toggle state and redraw."""
        self._state = new_state

        if self.use_lvgl and self._lvgl_toggle is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_toggle.state = new_state
            task_handler()
            return

        self.draw()

    @property
    def text(self) -> str:
        """Get the current text of the toggle."""
        if self.use_lvgl and self._lvgl_toggle is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            current_text = self._lvgl_toggle.text()
            task_handler()
            return current_text
        return self._text

    @text.setter
    def text(self, new_text: str) -> None:
        """Set the toggle text and redraw."""
        self._text = new_text

        if self.use_lvgl and self._lvgl_toggle is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_toggle.set_text(new_text)
            task_handler()
            return

        self.draw()

    def clear(self) -> None:
        """Clear the toggle area with the background color."""
        if self.use_lvgl and self._lvgl_toggle is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_toggle.clear()
            task_handler()
            return

        self.display.clear(self.position, self.size, self.background_color)
        self.display.swap()

    def draw(
        self, swap: bool = True, clear: bool = True, selected: bool = False
    ) -> None:
        """Render the toggle switch on the display."""
        if self.use_lvgl and self._lvgl_toggle is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_toggle.draw(swap, clear, selected)
            task_handler()
            return

        if clear:
            self.display.clear(self.position, self.size, self.background_color)

        display_size: Vector = self.display.size

        if self.is_circular:
            center_x = display_size.x // 2

            # spacing based on screen size
            horizontal_offset = int(display_size.x * 0.02)
            vertical_offset = int(display_size.y * 0.05)

            # Center text and toggle with offsets
            text_y = (
                self.position.y
                + self.size.y // 2
                - self.display.font_size.y // 2
                + vertical_offset
            )

            # Draw text on left side
            text_width = len(self._text) * self.display.font_size.x
            toggle_spacing = int(display_size.x * 0.078)
            text_x = center_x - text_width - toggle_spacing + horizontal_offset
            self.display.text(Vector(text_x, text_y), self._text, self.foreground_color)

            # Draw circular toggle on right side
            toggle_offset = int(display_size.x * 0.0625)
            toggle_center_x = center_x + toggle_offset + horizontal_offset
            toggle_center_y = self.position.y + self.size.y // 2 + vertical_offset
            toggle_radius = int(display_size.x * 0.0375)
            knob_radius = toggle_radius // 2

            if self._state:
                # Toggle is ON - filled outer circle with knob on right
                self.display.fill_circle(
                    Vector(toggle_center_x, toggle_center_y),
                    toggle_radius,
                    self.on_color,
                )
                self.display.fill_circle(
                    Vector(
                        toggle_center_x + toggle_radius - knob_radius - 1,
                        toggle_center_y,
                    ),
                    knob_radius,
                    self.background_color,
                )
            else:
                # Toggle is OFF - circle outline with knob on left
                self.display.circle(
                    Vector(toggle_center_x, toggle_center_y),
                    toggle_radius,
                    self.border_color,
                )
                self.display.fill_circle(
                    Vector(
                        toggle_center_x - toggle_radius + knob_radius + 1,
                        toggle_center_y,
                    ),
                    knob_radius,
                    self.foreground_color,
                )
        else:
            self.display.line(
                Vector(
                    self.position.x, self.position.y + self.size.y - self.border_width
                ),
                Vector(
                    self.position.x + self.size.x,
                    self.position.y + self.size.y - self.border_width,
                ),
                self.border_color,
            )
            self.display.text(
                Vector(self.position.x + 5, self.position.y + self.size.y // 2 - 8),
                self._text,
                self.on_color if selected else self.foreground_color,
            )

            toggle_width = int(display_size.x * 0.09375)
            toggle_height = int(display_size.x * 0.05)
            toggle_x = self.position.x + self.size.x - toggle_width - 5
            toggle_y = self.position.y + (self.size.y - toggle_height) // 2
            knob_radius = 6

            if self._state:
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

        if swap:
            self.display.swap()

    def toggle(self) -> None:
        """Toggle the current state."""
        if self.use_lvgl and self._lvgl_toggle is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_toggle.toggle()
            task_handler()
            self._state = not self._state
            return

        self._state = not self._state
        self.draw()

    def update(self, text: str, state: bool) -> None:
        """Update both text and state of the toggle."""
        if self.use_lvgl and self._lvgl_toggle is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_toggle.update(text, state)
            task_handler()
            self._text = text
            self._state = state
            return

        self._text = text
        self._state = state
