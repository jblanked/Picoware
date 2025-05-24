from time import monotonic
from math import cos, sin
from .draw import Draw
from .vector import Vector

PI = 3.14159265358979323846
RAD_FACTOR = PI / 180.0


class Loading:
    """A memory-optimized loading class for a GUI."""

    def __init__(self, draw: Draw, spinner_color: int, background_color: int):
        self.display = draw
        self.spinner_color = spinner_color
        self.background_color = background_color
        self.spinner_position = 0
        self.time_elapsed = 0
        self.time_start = 0
        self.animating = False
        self.current_text = "Loading..."
        self.center_x = self.display.board.width / 2
        self.center_y = self.display.board.height / 2
        self.radius = 20  # spinner radius
        self.span = 280  # degrees of arc
        self.step = 5  # degrees between segments

        # Pre-calculate sin/cos values for common angles to avoid repeated calculations
        self._cos_cache = {}
        self._sin_cache = {}
        for angle in range(0, 360, 5):
            self._cos_cache[angle] = cos(angle * RAD_FACTOR)
            self._sin_cache[angle] = sin(angle * RAD_FACTOR)

    def _get_cos(self, angle):
        """Get cosine value from cache or calculate it."""
        angle = angle % 360
        # Round to nearest 5 degrees for cache lookup
        cache_key = (angle // 5) * 5
        return self._cos_cache.get(cache_key, cos(angle * RAD_FACTOR))

    def _get_sin(self, angle):
        """Get sine value from cache or calculate it."""
        angle = angle % 360
        # Round to nearest 5 degrees for cache lookup
        cache_key = (angle // 5) * 5
        return self._sin_cache.get(cache_key, sin(angle * RAD_FACTOR))

    def animate(self) -> None:
        """Animate the loading spinner with proper buffer management."""
        if not self.animating:
            self.animating = True
            self.time_start = monotonic()

        self.clear()
        self.draw_spinner()
        self.display.text(Vector(130, 20), self.current_text, self.spinner_color)
        self.display.swap()
        self.time_elapsed = monotonic() - self.time_start
        self.spinner_position = (
            self.spinner_position + 10
        ) % 360  # Rotate by 10 degrees each frame

    def clear(self) -> None:
        """Clear the loading screen."""
        self.display.fill(self.background_color)

    def draw_spinner(self) -> None:
        """Draw the loading spinner with memory optimization."""
        # Use pre-calculated values
        center_x = self.center_x
        center_y = self.center_y
        radius = self.radius
        span = self.span
        step = self.step
        start_angle = self.spinner_position
        offset = 0

        # Calculate all points first to avoid tearing
        points = []
        colors = []

        while offset < span:
            angle = (start_angle + offset) % 360
            next_angle = (angle + step) % 360

            # Use cached or calculated values
            x1 = center_x + int(radius * self._get_cos(angle))
            y1 = center_y + int(radius * self._get_sin(angle))
            x2 = center_x + int(radius * self._get_cos(next_angle))
            y2 = center_y + int(radius * self._get_sin(next_angle))

            # Calculate fade color
            opacity = 255 - ((offset * 200) // span)
            color = self.fade_color(self.spinner_color, opacity)

            points.append((Vector(x1, y1), Vector(x2, y2)))
            colors.append(color)

            offset += step

        # Draw all segments at once
        for i, (point_pair, color) in enumerate(zip(points, colors)):
            self.display.line(point_pair[0], point_pair[1], color)

    def fade_color(self, color: int, opacity: int) -> int:
        """
        Optimized version of fade color function.
        `opacity` is 0–255.
        """
        # Skip calculation if no fade needed
        if opacity >= 255:
            return color

        # Quick bounds check using bitwise operations
        opacity = opacity & 0xFF  # clamp 0-255

        # Extract 5‑6‑5 channels
        r = (color >> 11) & 0x1F
        g = (color >> 5) & 0x3F
        b = color & 0x1F

        # Use integer division for better performance
        r = (r * opacity) // 255
        g = (g * opacity) // 255
        b = (b * opacity) // 255

        # Recombine to 16‑bit
        return (r << 11) | (g << 5) | b

    def stop(self) -> None:
        """Stop the loading animation."""
        self.clear()
        self.display.swap()
        self.animating = False
        self.time_elapsed = 0
        self.time_start = 0
