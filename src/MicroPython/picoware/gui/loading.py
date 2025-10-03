from picoware.system.vector import Vector
from micropython import const

PI = const(3.14159265358979323846)


class Loading:
    """A loading class with spinner animation."""

    def __init__(
        self, draw, spinner_color: int = 0xFFFF, background_color: int = 0x0000
    ):
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

    def animate(self, swap: bool = True) -> None:
        """Animate the loading spinner."""
        from math import cos, sin

        if not self.animating:
            self.animating = True
            self.time_start = self._monotonic()

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
            rad = PI / 180.0
            x1 = center_x + int(self.radius * cos(angle * rad))
            y1 = center_y + int(self.radius * sin(angle * rad))
            x2 = center_x + int(self.radius * cos(next_angle * rad))
            y2 = center_y + int(self.radius * sin(next_angle * rad))

            # Calculate fade color
            opacity = 255 - ((offset * 200) // self.span)
            color = self.fade_color(self.spinner_color, opacity)

            # Draw line segment directly to framebuffer
            self.display.line_custom(Vector(x1, y1), Vector(x2, y2), color)

        # Draw text directly to framebuffer
        self.display.text(Vector(130, 20), self.current_text, self.spinner_color)

        # Single swap
        if swap:
            self.display.swap()

        self.time_elapsed = self._monotonic() - self.time_start
        self.spinner_position = (self.spinner_position + 10) % 360

    def fade_color(self, color: int, opacity: int) -> int:
        """Fast color fading."""
        if opacity >= 255:
            return color

        opacity = opacity & 0xFF
        r = ((color >> 11) * opacity) >> 8
        g = (((color >> 5) & 0x3F) * opacity) >> 8
        b = ((color & 0x1F) * opacity) >> 8

        return (r << 11) | (g << 5) | b

    def _monotonic(self) -> int:
        """Get the current time in milliseconds as integer."""
        from utime import ticks_ms

        return int(ticks_ms())

    def set_text(self, text: str) -> None:
        """Set the loading text."""
        self.current_text = text

    def stop(self) -> None:
        """Stop the loading animation."""
        # Clear the entire screen
        self.display.clear(Vector(0, 0), self.display.size, self.background_color)
        self.display.swap()
        self.animating = False
        self.time_elapsed = 0
        self.time_start = 0
