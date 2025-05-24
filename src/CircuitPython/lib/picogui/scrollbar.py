from .draw import Draw
from .vector import Vector


class ScrollBar:
    """A simple scrollbar class for a GUI."""

    def __init__(
        self,
        draw: Draw,
        position: Vector,
        size: Vector,
        outline_color: int,
        fill_color: int,
    ):
        self.display = draw
        self.position = position
        self.size = size
        self.outline_color = outline_color
        self.fill_color = fill_color

    def clear(self):
        """Clear the scrollbar."""
        self.display.clear(self.position, self.size, self.fill_color)

    def draw(self):
        """Draw the scrollbar."""
        self.display.rect(self.position, self.size, self.outline_color)
        self.display.rect_fill(
            Vector(self.position.x + 1, self.position.y + 1),
            Vector(self.size.x - 2, self.size.y - 2),
            self.fill_color,
        )

    def set_all(
        self,
        position: Vector,
        size: Vector,
        outline_color: int,
        fill_color: int,
        should_draw: bool = True,
        should_clear: bool = True,
    ):
        """Set the properties of the scrollbar."""
        if should_clear:
            self.clear()
        self.position = position
        self.size = size
        self.outline_color = outline_color
        self.fill_color = fill_color
        if should_draw:
            self.draw()
