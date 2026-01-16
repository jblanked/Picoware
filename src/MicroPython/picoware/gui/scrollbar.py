class ScrollBar:
    """A simple scrollbar class for a GUI."""

    def __init__(
        self,
        draw,
        position,  # Vector
        size,  # Vector
        outline_color: int = 0x0000,
        fill_color: int = 0xFFFFFF,
        is_horizontal: bool = False,
    ) -> None:
        from picoware.system.vector import Vector

        self.display = draw
        self.position = position
        self.size = size
        self.outline_color = outline_color
        self.fill_color = fill_color
        self.is_horizontal = is_horizontal

        self.fill_pos = Vector(self.position.x + 1, self.position.y + 1)
        self.fill_size = Vector(self.size.x - 2, self.size.y - 2)

    def __del__(self):
        if self.position:
            del self.position
            self.position = None
        if self.size:
            del self.size
            self.size = None

    def clear(self) -> None:
        """Clear the scrollbar."""
        self.display.clear(self.position, self.size, self.fill_color)

    def draw(self) -> None:
        """Draw the scrollbar."""
        if self.is_horizontal:
            # Draw horizontal scrollbar
            self.fill_pos.x, self.fill_pos.y = self.position.x + 1, self.position.y + 1
            self.fill_size.x, self.fill_size.y = self.size.x - 2, self.size.y - 2
            self.display.rect(self.position, self.size, self.outline_color)
            self.display.fill_rectangle(
                self.fill_pos,
                self.fill_size,
                self.fill_color,
            )
        else:
            # Draw vertical scrollbar
            self.fill_pos.x, self.fill_pos.y = self.position.x + 1, self.position.y + 1
            self.fill_size.x, self.fill_size.y = self.size.x - 2, self.size.y - 2
            self.display.rect(self.position, self.size, self.outline_color)
            self.display.fill_rectangle(
                self.fill_pos,
                self.fill_size,
                self.fill_color,
            )

    def set_all(
        self,
        position,  # Vector
        size,  # Vector
        outline_color: int,
        fill_color: int,
        is_horizontal: bool = False,
        should_draw: bool = True,
        should_clear: bool = True,
    ) -> None:
        """Set the properties of the scrollbar."""
        if should_clear:
            self.clear()
        self.position = position
        self.size = size
        self.outline_color = outline_color
        self.fill_color = fill_color
        self.is_horizontal = is_horizontal
        if should_draw:
            self.draw()
