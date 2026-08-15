"""Toggle - On/off toggle switch widget."""

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
        """Initialize the Toggle switch with drawing context and styling.

        Args:
            draw (Draw): The drawing context to render the toggle.
            position (Vector): Vector position of the toggle.
            size (Vector): Vector size of the toggle.
            text (str): The label text for the toggle.
            initial_state (bool): Initial state of the toggle. Defaults to False.
            foreground_color (int): The color of the text. Defaults to 0xFFFF.
            background_color (int): The background color. Defaults to 0x0000.
            on_color (int): The color when the toggle is on. Defaults to 0x001F.
            border_color (int): The color of the border. Defaults to 0xFFFF.
            border_width (int): The width of the border. Defaults to 1.
            should_clear (bool): Whether to clear on init. Defaults to True.
            use_lvgl (bool): Whether to use LVGL rendering. Defaults to True.
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

                class LVGLToggleWrapper(LVGLToggle):
                    """Wrapper for LVGL Toggle to integrate with our Toggle class."""

                    def __setattr__(self, name, value):
                        """Forward text and state assignments to LVGL.

                        Args:
                            name (str): The attribute name.
                            value: The attribute value.
                        """
                        if name == "text":
                            self.set_text(value)
                        elif name == "state":
                            self.set_state(value)
                        else:
                            super().__setattr__(name, value)

                # Create LVGL Toggle instance
                self._lvgl_toggle = LVGLToggleWrapper(
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
        """Clean up resources and deinitialize LVGL."""
        if self._lvgl_toggle is not None:
            from picoware_lvgl import deinit

            del self._lvgl_toggle
            self._lvgl_toggle = None
            deinit()

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
        """Set the toggle state and redraw.

        Args:
            new_state (bool): The new toggle state.
        """
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
        """Set the toggle text and redraw.

        Args:
            new_text (str): The new toggle text.
        """
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
        """Render the toggle switch on the display.

        Args:
            swap (bool): Whether to swap the display buffer. Defaults to True.
            clear (bool): Whether to clear the area first. Defaults to True.
            selected (bool): Whether the toggle is selected. Defaults to False.
        """
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
            text_width = self.display.len(self._text)
            toggle_spacing = int(display_size.x * 0.078)
            text_x = center_x - text_width - toggle_spacing + horizontal_offset
            self.display._text(text_x, text_y, self._text, self.foreground_color)

            # Draw circular toggle on right side
            toggle_offset = int(display_size.x * 0.0625)
            toggle_center_x = center_x + toggle_offset + horizontal_offset
            toggle_center_y = self.position.y + self.size.y // 2 + vertical_offset
            toggle_radius = int(display_size.x * 0.0375)
            knob_radius = toggle_radius // 2

            if self._state:
                # Toggle is ON - filled outer circle with knob on right
                self.display._fill_circle(
                    toggle_center_x, toggle_center_y,
                    toggle_radius,
                    self.on_color,
                )
                self.display.fill_circle(
                    toggle_center_x + toggle_radius - knob_radius - 1,
                    toggle_center_y,
                    knob_radius,
                    self.background_color,
                )
            else:
                # Toggle is OFF - circle outline with knob on left
                self.display._circle(
                    toggle_center_x, toggle_center_y,
                    toggle_radius,
                    self.border_color,
                )
                self.display._fill_circle(
                    toggle_center_x - toggle_radius + knob_radius + 1,
                    toggle_center_y,
                    knob_radius,
                    self.foreground_color,
                )
        else:
            self.display._line(
                self.position.x, self.position.y + self.size.y - self.border_width,
                self.position.x + self.size.x,
                self.position.y + self.size.y - self.border_width,
                self.border_color,
            )
            self.display._text(
                self.position.x + self.display.scale_x(5), 
                self.position.y + self.size.y // 2 - self.display.scale_y(8),
                self._text,
                self.on_color if selected else self.foreground_color,
            )

            toggle_width = int(display_size.x * 0.09375)
            toggle_height = int(display_size.x * 0.05)
            toggle_x = self.position.x + self.size.x - toggle_width - self.display.scale_x(5)
            toggle_y = self.position.y + (self.size.y - toggle_height) // 2
            knob_radius = self.display.scale_x(6)

            if self._state:
                # Toggle is ON
                self.display._fill_rectangle(
                    toggle_x, toggle_y,
                    toggle_width, toggle_height,
                    self.on_color,
                )
                self.display._fill_circle(
                    toggle_x + toggle_width - knob_radius - self.display.scale_x(2),
                    toggle_y + toggle_height // 2,
                    knob_radius,
                    self.background_color,
                )
            else:
                # Toggle is OFF
                self.display._fill_rectangle(
                    toggle_x, toggle_y,
                    toggle_width, toggle_height,
                    self.border_color,
                )
                self.display._fill_circle(
                    toggle_x + knob_radius + self.display.scale_x(2), toggle_y + toggle_height // 2,
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
        """Update both text and state of the toggle.

        Args:
            text (str): The new toggle text.
            state (bool): The new toggle state.
        """
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
