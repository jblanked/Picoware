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
    ) -> None:
        from picoware.gui.list import List
        from picoware.system.vector import Vector

        self.text_color = text_color
        self.background_color = background_color
        self._title = title
        self.display = draw
        self.use_lvgl = draw.use_lvgl

        if self.use_lvgl:
            # LVGL mode: List handles title rendering internally
            self._height_offset = 0
            self.list = List(
                draw,
                y,
                height,
                text_color,
                background_color,
                selected_color,
                border_color,
                border_width,
            )
            # Set title on the LVGL list
            if hasattr(self.list, "_lvgl_list") and self.list._lvgl_list is not None:
                self.list._lvgl_list.set_title(title)
        else:
            # Standard mode: Reserve space for title at top
            self._height_offset = int(self.display.size.y // 8)
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

        # Initialize title rendering properties for standard mode
        if not self.use_lvgl:
            title_width = self.display.font_size.x * len(self._title)
            title_x = (self.display.size.x - title_width) // 2
            title_y = self.position.y + 15
            underline_y = title_y + 10

            self.title_pos = Vector(title_x, title_y)
            self.line_pos = Vector(self.title_pos.x, underline_y)
            self.line_size = Vector(self.title_pos.x + title_width, underline_y)

            self.clear_position = Vector(0, 0)
            self.clear_size = Vector(self.display.size.x, self._height_offset)

            draw.clear(self.position, self.size, self.background_color)
            draw.swap()
        else:
            # LVGL mode doesn't need these
            self.title_pos = None
            self.line_pos = None
            self.line_size = None
            self.clear_position = None
            self.clear_size = None

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
        if self.title_pos:
            del self.title_pos
            self.title_pos = None
        if self.line_pos:
            del self.line_pos
            self.line_pos = None
        if self.line_size:
            del self.line_size
            self.line_size = None
        if self.clear_position:
            del self.clear_position
            self.clear_position = None
        if self.clear_size:
            del self.clear_size
            self.clear_size = None
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

        # Update LVGL list title if using LVGL
        if (
            self.use_lvgl
            and hasattr(self.list, "_lvgl_list")
            and self.list._lvgl_list is not None
        ):
            self.list._lvgl_list.set_title(value)
            return

        # Update standard rendering title positions
        if not self.use_lvgl:
            title_width = self.display.font_size.x * len(self._title)
            title_x = (self.display.size.x - title_width) // 2
            title_y = self.position.y + 15
            underline_y = title_y + 10

            self.title_pos.x, self.title_pos.y = title_x, title_y
            self.line_pos.x, self.line_pos.y = self.title_pos.x, underline_y
            self.line_size.x, self.line_size.y = (
                self.title_pos.x + title_width,
                underline_y,
            )

    def add_item(self, item: str) -> None:
        """Add an item to the menu."""
        self.list.add_item(item)

    def clear(self) -> None:
        """Clear the menu."""
        if self.use_lvgl:
            self.list.clear()
        else:
            self.display.clear(
                self.clear_position,
                self.clear_size,
                self.background_color,
            )
            self.list.clear()

    def draw(self) -> None:
        """Draw the menu."""
        if self.use_lvgl:
            # LVGL mode: List handles everything including title
            self.list.draw()
        else:
            # Standard mode: Draw title then list
            self.draw_title()
            self.list.draw()

    def draw_title(self) -> None:
        """Draw the title (for standard rendering only)."""
        if self.use_lvgl:
            return  # Title is handled by LVGL list

        # clear title area
        self.display.clear(
            self.clear_position,
            self.clear_size,
            self.background_color,
        )

        # Draw title centered
        self.display.text(self.title_pos, self._title, self.text_color)

        # Draw underline
        self.display.line_custom(
            self.line_pos,
            self.line_size,
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
        if self.use_lvgl:
            self.list.set_selected(self.list.selected_index)
        else:
            self.draw_title()
            self.list.set_selected(self.list.selected_index)

    def remove_item(self, index: int) -> None:
        """Remove an item from the menu."""
        self.list.remove_item(index)

    def scroll_down(self) -> None:
        """Scroll down the menu."""
        if not self.use_lvgl:
            self.draw_title()
        self.list.scroll_down()

    def scroll_up(self) -> None:
        """Scroll up the menu."""
        if not self.use_lvgl:
            self.draw_title()
        self.list.scroll_up()

    def set_selected(self, index: int) -> None:
        """Set the selected item."""
        if not self.use_lvgl:
            self.draw_title()
        self.list.set_selected(index)
