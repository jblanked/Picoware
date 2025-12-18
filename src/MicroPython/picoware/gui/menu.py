class Menu:
    """A simple menu class for a GUI."""

    def __init__(
        self,
        draw,
        title: str,
        y: int,
        height: int,
        text_color: int = 0xFFFF,
        background_color: int = 0x0000,
        selected_color: int = 0x001F,
        border_color: int = 0xFFFF,
        border_width: int = 2,
    ):
        from picoware.system.vector import Vector
        from picoware.gui.list import List

        self.text_color = text_color
        self.background_color = background_color
        self._title = title
        self.display = draw
        self._height_offset = int(self.display.size.y // 8)  # Reserve space for title
        self.list = List(
            draw,
            y + self._height_offset,
            height - self._height_offset,
            text_color,
            background_color,
            selected_color,
            border_color,
            border_width,
        )
        self.position = Vector(0, y)
        self.size = Vector(draw.size.x, height)
        draw.clear(self.position, self.size, self.background_color)
        draw.swap()

    def __del__(self):
        if self.list:
            del self.list
            self.list = None
        if self.position:
            del self.position
            self.position = None
        if self.size:
            del self.size
            self.size = None
        self._title = ""

    @property
    def current_item(self) -> str:
        """Get the current item."""
        return self.list.current_item

    @property
    def item_count(self) -> int:
        """Get the number of items."""
        return self.list.item_count

    @property
    def list_height(self) -> int:
        """Get the height of the list."""
        return self.list.list_height

    @property
    def selected_index(self) -> int:
        """Get the selected index."""
        return self.list.selected_index

    @property
    def title(self) -> str:
        """Get the menu title."""
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        """Set the menu title."""
        self._title = value

    def add_item(self, item: str) -> None:
        """Add an item to the menu."""
        self.list.add_item(item)

    def clear(self) -> None:
        """Clear the menu."""
        from picoware.system.vector import Vector

        self.display.clear(
            Vector(0, 0),
            Vector(self.display.size.x, self._height_offset),
            self.background_color,
        )
        self.list.clear()

    def draw(self) -> None:
        """Draw the menu."""

        # Draw the title
        self.draw_title()

        # Draw the list with the underline position
        self.list.draw()

    def draw_title(self) -> None:
        """Draw the title (kept for API compatibility, now handled in draw)."""
        from picoware.system.vector import Vector

        # Draw title centered
        title_width = self.display.font_size.x * len(self._title)
        title_x = (self.display.size.x - title_width) // 2
        title_y = self.position.y + 15
        self.display.text(Vector(title_x, title_y), self._title, self.text_color)

        # Draw underline
        underline_y = title_y + 10
        self.display.line_custom(
            Vector(title_x, underline_y),
            Vector(title_x + title_width, underline_y),
            self.text_color,
        )

    def get_item(self, index: int) -> str:
        """Get the item at the specified index."""
        return self.list.get_item(index)

    def item_exists(self, item: str) -> bool:
        """Check if an item exists in the menu."""
        return self.list.item_exists(item)

    def refresh(self) -> None:
        """Refresh the menu display."""
        self.draw_title()
        self.list.set_selected(self.list.selected_index)

    def remove_item(self, index: int) -> None:
        """Remove an item from the menu."""
        self.list.remove_item(index)

    def scroll_down(self) -> None:
        """Scroll down the menu."""
        self.draw_title()
        self.list.scroll_down()

    def scroll_up(self) -> None:
        """Scroll up the menu."""
        self.draw_title()
        self.list.scroll_up()

    def set_selected(self, index: int) -> None:
        """Set the selected item."""
        self.draw_title()
        self.list.set_selected(index)
