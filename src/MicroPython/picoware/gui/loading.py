from utime import ticks_ms
from math import cos, sin


class Loading:
    """A loading class with spinner animation."""

    def __init__(
        self, draw, spinner_color: int = 0xFFFF, background_color: int = 0x0000
    ) -> None:
        from picoware.system.vector import Vector

        self.display = draw
        self.spinner_color = spinner_color
        self.background_color = background_color
        self.spinner_position = 0
        self.time_elapsed = 0
        self.time_start = 0
        self.animating = False
        self.current_text = "Loading..."
        self.radius = 20  # spinner radius
        self.span = 280  # degrees of arc
        self.step = 5  # degrees between segments (280/5 = 56 segments)
        self.vec_line = Vector(0, 0)
        self.vec_line_end = Vector(0, 0)
        self.text_vec = Vector(0, int(draw.size.y * 0.0625))
        self.text_vec_2 = Vector(0, draw.size.y - 15)
        self.rad = (3.14159265358979323846) / 180.0

        self.font_size_x = self.display.font_size.x

        # Calculate centered text position
        text_width = len(self.current_text) * self.font_size_x
        self.text_vec.x = (self.display.size.x - text_width) // 2

    def __del__(self) -> None:
        self.current_text = ""
        self.animating = False
        self.time_elapsed = 0
        self.time_start = 0
        self.spinner_position = 0
        self.vec_line = None
        self.vec_line_end = None
        self.text_vec = None
        self.text_vec_2 = None
        self.rad = 0.0
        self.font_size_x = 0

    @property
    def text(self) -> str:
        """Get the current loading text."""
        return self.current_text

    @text.setter
    def text(self, value: str) -> None:
        """Set the current loading text."""
        self.current_text = value

        # Calculate centered text position
        text_width = len(self.current_text) * self.font_size_x
        self.text_vec.x = (self.display.size.x - text_width) // 2

    def animate(self, swap: bool = True) -> None:
        """Animate the loading spinner."""
        if not self.animating:
            self.animating = True
            self.time_start = ticks_ms()

        # Clear the screen
        self.display.fill_screen(self.background_color)

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
            self.vec_line.x, self.vec_line.y = x1, y1
            self.vec_line_end.x, self.vec_line_end.y = x2, y2
            self.display.line_custom(self.vec_line, self.vec_line_end, color)

        # Draw text
        self.display.text(
            self.text_vec,
            self.current_text,
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
            self.text_vec_2.x = (screen_size.x - len(time_str) * self.font_size_x) // 2
            self.display.text(self.text_vec_2, time_str, self.spinner_color)
        else:
            minutes = seconds / 60
            remaining_seconds = seconds % 60
            time_str = f"{int(minutes)}:{int(remaining_seconds):02} minutes"
            self.text_vec_2.x = (screen_size.x - len(time_str) * self.font_size_x) // 2
            self.display.text(self.text_vec_2, time_str, self.spinner_color)

        self.time_elapsed = ticks_ms() - self.time_start
        self.spinner_position = (self.spinner_position + 10) % 360

        if swap:
            self.display.swap()

    def fade_color(self, color: int, opacity: int) -> int:
        """Fast color fading."""
        if opacity >= 255:
            return color

        opacity = opacity & 0xFF
        r = ((color >> 11) * opacity) >> 8
        g = (((color >> 5) & 0x3F) * opacity) >> 8
        b = ((color & 0x1F) * opacity) >> 8

        return (r << 11) | (g << 5) | b

    def set_text(self, text: str) -> None:
        """Set the loading text."""
        self.current_text = text

        # Calculate centered text position
        text_width = len(self.current_text) * self.font_size_x
        self.text_vec.x = (self.display.size.x - text_width) // 2

    def stop(self) -> None:
        """Stop the loading animation."""
        # Clear the entire screen
        self.display.erase()
        self.display.swap()
        self.animating = False
        self.time_elapsed = 0
        self.time_start = 0
        self.spinner_position = 0
