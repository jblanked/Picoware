from picoware.system.vector import Vector


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
        from picoware.gui.list import List

        self.text_color = text_color
        self.background_color = background_color
        self.title = title
        self.display = draw
        self.list = List(
            draw,
            y + 20,
            height - 20,
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
        self.title = ""

    def add_item(self, item: str) -> None:
        """Add an item to the menu."""
        self.list.add_item(item)

    def clear(self) -> None:
        """Clear the menu."""
        self.display.clear(Vector(0, 0), Vector(320, 20), self.background_color)
        self.list.clear()

    def draw(self) -> None:
        """Draw the menu."""
        self.draw_title()
        self.list.draw()

    def draw_title(self) -> None:
        """Draw the title."""
        self.display.text(Vector(2, 8), self.title, self.text_color)

    def get_current_item(self) -> str:
        """Get the current item in the menu."""
        return self.list.get_current_item()

    def get_item(self, index: int) -> str:
        """Get the item at the specified index."""
        return self.list.get_item(index)

    def get_item_count(self) -> int:
        """Get the number of items in the menu."""
        return self.list.get_item_count()

    def get_list_height(self) -> int:
        """Get the height of the list."""
        return self.list.get_list_height()

    def get_selected_index(self) -> int:
        """Get the index of the selected item."""
        return self.list.selected_index

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
