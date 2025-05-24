from .draw import Draw
from .vector import Vector
from .list import List


class Menu:
    """A simple menu class for a GUI."""

    def __init__(
        self,
        draw: Draw,
        title: str,
        y: int,
        height: int,
        text_color: int,
        background_color: int,
        selected_color: int,
        border_color: int,
        border_width: int = 2,
    ):
        self.text_color = text_color
        self.background_color = background_color
        self.title = title
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

    def add_item(self, item: str) -> None:
        """Add an item to the menu."""
        self.list.add_item(item)

    def clear(self) -> None:
        """Clear the menu."""
        self.list.clear()

    def draw(self) -> None:
        """Draw the menu."""
        self.draw_title()
        self.list.draw()

    def draw_title(self) -> None:
        '''Draw the title of the menu."""'''
        self.list.scrollbar.display.text(Vector(2, 8), self.title, self.text_color, 1)

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
        """Set the selected item in the menu."""
        self.draw_title()
        self.list.set_selected(index)
