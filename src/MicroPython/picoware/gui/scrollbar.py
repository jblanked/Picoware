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
        """Initialize the scrollbar with position, size, and colors.

        Args:
            draw (Draw): The drawing context to render the scrollbar.
            position (Vector): The position of the scrollbar.
            size (Vector): The size of the scrollbar.
            outline_color (int): The outline color. Defaults to 0x0000.
            fill_color (int): The fill color. Defaults to 0xFFFFFF.
            is_horizontal (bool): Whether the scrollbar is horizontal. Defaults to False.
        """
        self.display = draw
        self.position = position
        self.size = size
        self.outline_color = outline_color
        self.fill_color = fill_color
        self.is_horizontal = is_horizontal

    def __del__(self):
        """Clean up resources."""
        if self.position:
            del self.position
            self.position = None
        if self.size:
            del self.size
            self.size = None

    def clear(self) -> None:
        """Clear the scrollbar."""
        self.display._fill_rectangle(
            self.position.x, self.position.y, self.size.x, self.size.y, self.fill_color
        )

    def draw(self) -> None:
        """Draw the scrollbar."""
        if self.is_horizontal:
            # Draw horizontal scrollbar
            self.display._rectangle(
                self.position.x,
                self.position.y,
                self.size.x,
                self.size.y,
                self.outline_color,
            )
            self.display._fill_rectangle(
                self.position.x + 1,
                self.position.y + 1,
                self.size.x - 2,
                self.size.y - 2,
                self.fill_color,
            )
        else:
            # Draw vertical scrollbar
            self.display._rectangle(
                self.position.x,
                self.position.y,
                self.size.x,
                self.size.y,
                self.outline_color,
            )
            self.display._fill_rectangle(
                self.position.x + 1,
                self.position.y + 1,
                self.size.x - 2,
                self.size.y - 2,
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
        """Set the properties of the scrollbar.

        Args:
            position (Vector): The new position of the scrollbar.
            size (Vector): The new size of the scrollbar.
            outline_color (int): The new outline color.
            fill_color (int): The new fill color.
            is_horizontal (bool): Whether the scrollbar is horizontal. Defaults to False.
            should_draw (bool): Whether to redraw after setting. Defaults to True.
            should_clear (bool): Whether to clear before setting. Defaults to True.
        """
        if should_clear:
            self.clear()
        self.position = position
        self.size = size
        self.outline_color = outline_color
        self.fill_color = fill_color
        self.is_horizontal = is_horizontal
        if should_draw:
            self.draw()
