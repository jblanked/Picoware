from utime import ticks_ms
from math import cos, sin


class Loading:
    """A loading class with spinner animation."""

    def __init__(
        self,
        draw,
        spinner_color: int = 0xFFFF,
        background_color: int = 0x0000,
    ) -> None:
        """Initialize the Loading spinner with drawing context and styling.

        Args:
            draw (Draw): The drawing context to render the loading spinner.
            spinner_color (int): The color of the spinner. Defaults to 0xFFFF.
            background_color (int): The background color. Defaults to 0x0000.
        """
        from picoware.system.vector import Vector

        self.display = draw
        self.spinner_color = spinner_color
        self.background_color = background_color
        self.spinner_position = 0
        self.time_elapsed = 0
        self.time_start = 0
        self.animating = False
        self.current_text = "Loading..."
        self.radius = draw.scale_x(20)  # spinner radius
        self.span = 280  # degrees of arc
        self.step = 5  # degrees between segments (280/5 = 56 segments)
        self.text_vec = Vector(0, int(draw.size.y * 0.0625))
        self.text_vec_2 = Vector(0, draw.size.y - draw.scale_y(15))
        self.rad = (3.14159265358979323846) / 180.0
        self.twenty_y = draw.scale_y(20)

        # Calculate centered text position
        text_width = self.display.len(self.current_text)
        self.text_vec.x = (self.display.size.x - text_width) // 2

        self.use_lvgl = draw.use_lvgl
        self._lvgl_loading = None

        # Initialize LVGL Loading if requested
        if self.use_lvgl:
            try:
                from picoware_lvgl import init, Loading as LVGLLoading

                init()

                class LVGLLoadingWrapper(LVGLLoading):
                    """Wrapper that forwards text assignment to LVGL."""

                    def __setattr__(self, name, value):
                        """Forward text assignment to the LVGL loading spinner.

                        Args:
                            name (str): The attribute name.
                            value: The attribute value.
                        """
                        if name == "text":
                            self.set_text(value)
                        else:
                            super().__setattr__(name, value)

                # Create LVGL Loading instance
                self._lvgl_loading = LVGLLoadingWrapper(spinner_color, background_color)
                # Set initial text
                self._lvgl_loading.set_text(self.current_text)
            except (ImportError, RuntimeError, ValueError):
                self.use_lvgl = False

    def __del__(self) -> None:
        """Clean up resources and deinitialize LVGL."""
        if self._lvgl_loading is not None:
            from picoware_lvgl import deinit

            del self._lvgl_loading
            self._lvgl_loading = None
            deinit()
        self.current_text = ""
        self.animating = False
        self.time_elapsed = 0
        self.time_start = 0
        self.spinner_position = 0
        self.text_vec = None
        self.text_vec_2 = None
        self.rad = 0.0
    
    @property
    def text(self) -> str:
        """Get the current loading text."""
        if self.use_lvgl and self._lvgl_loading is not None:
            return self._lvgl_loading.text
        return self.current_text

    @text.setter
    def text(self, value: str) -> None:
        """Set the current loading text.

        Args:
            value (str): The new loading text.
        """
        self.current_text = value

        # Update LVGL Loading if using it
        if self.use_lvgl and self._lvgl_loading is not None:
            self._lvgl_loading.set_text(value)
            return

        # Calculate centered text position
        text_width = self.display.len(self.current_text)
        self.text_vec.x = (self.display.size.x - text_width) // 2

    def animate(self, swap: bool = True, http=None) -> None:
        """Animate the loading spinner.

        Args:
            swap (bool): Whether to swap the display buffer. Defaults to True.
            http: Optional HTTP client for download progress display. Defaults to None.
        """
        if self.use_lvgl and self._lvgl_loading is not None:
            from picoware_lvgl import tick, task_handler

            tick(10)
            self._lvgl_loading.animate(swap)
            task_handler()
            return

        if not self.animating:
            self.animating = True
            self.time_start = ticks_ms()

        # Clear the screen
        self.display.erase()

        # Get screen center
        screen_size = self.display.size
        center_x = screen_size.x // 2
        center_y = screen_size.y // 2

        # Draw spinner
        start_angle = self.spinner_position
        for offset in range(0, self.span, self.step):
            angle = (start_angle + offset) % 360
            next_angle = (angle + self.step) % 360

            # Convert to radians and calculate positions
            x1 = center_x + int(self.radius * cos(angle * self.rad))
            y1 = center_y + int(self.radius * sin(angle * self.rad))
            x2 = center_x + int(self.radius * cos(next_angle * self.rad))
            y2 = center_y + int(self.radius * sin(next_angle * self.rad))

            # Calculate fade color
            opacity = 255 - ((offset * 200) // self.span)
            color = self.fade_color(self.spinner_color, opacity)

            # Draw line segment
            self.display._line(x1, y1, x2, y2, color)

        # Draw text
        self.display._text(
            self.text_vec.x,
            self.text_vec.y,
            self.current_text,
            self.spinner_color,
        )

        if http is not None:
            # Draw download text below the main text
            _download_text = f"{http.downloaded_bytes / 1024:.1f} KB downloaded at {http.download_speed / 1024:.1f} KB/s"
            download_text_x = (screen_size.x - self.display.len(_download_text)) // 2
            self.display._text(
                download_text_x,
                self.text_vec.y + self.twenty_y,
                _download_text,
                self.spinner_color,
            )

        # draw time elapsed in seconds
        time_str = ""
        seconds = self.time_elapsed / 1000
        if seconds < 60:
            if seconds <= 1:
                time_str = f"{int(seconds)} second"
            else:
                time_str = f"{int(seconds)} seconds"
            self.text_vec_2.x = (screen_size.x - self.display.len(time_str)) // 2
            self.display._text(
                self.text_vec_2.x, self.text_vec_2.y, time_str, self.spinner_color
            )
        else:
            minutes = seconds / 60
            remaining_seconds = seconds % 60
            time_str = f"{int(minutes)}:{int(remaining_seconds):02} minutes"
            self.text_vec_2.x = (screen_size.x - self.display.len(time_str)) // 2
            self.display._text(
                self.text_vec_2.x, self.text_vec_2.y, time_str, self.spinner_color
            )

        self.time_elapsed = ticks_ms() - self.time_start
        self.spinner_position = (self.spinner_position + 10) % 360

        if swap:
            self.display.swap()

    def fade_color(self, color: int, opacity: int) -> int:
        """Fade a color by applying an opacity value.

        Args:
            color (int): The RGB565 color to fade.
            opacity (int): The opacity from 0 to 255.

        Returns:
            int: The faded RGB565 color.
        """
        if opacity >= 255:
            return color

        opacity = opacity & 0xFF
        r = ((color >> 11) * opacity) >> 8
        g = (((color >> 5) & 0x3F) * opacity) >> 8
        b = ((color & 0x1F) * opacity) >> 8

        return (r << 11) | (g << 5) | b

    def set_text(self, text: str) -> None:
        """Set the loading text.

        Args:
            text (str): The new loading text.
        """
        self.current_text = text

        # Update LVGL Loading if using it
        if self.use_lvgl and self._lvgl_loading is not None:
            self._lvgl_loading.set_text(text)
            return

        # Calculate centered text position
        text_width = self.display.len(self.current_text)
        self.text_vec.x = (self.display.size.x - text_width) // 2

    def stop(self) -> None:
        """Stop the loading animation."""
        if self.use_lvgl and self._lvgl_loading is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_loading.stop()
            task_handler()
            return

        # Clear the entire screen
        self.display.erase()
        self.display.swap()
        self.animating = False
        self.time_elapsed = 0
        self.time_start = 0
        self.spinner_position = 0
