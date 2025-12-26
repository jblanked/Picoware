from picoware.system.vector import Vector


class List:
    """A simple list class for a GUI."""

    def __init__(
        self,
        draw,
        y: int,
        height: int,
        text_color: int = 0xFFFF,
        background_color: int = 0x0000,
        selected_color: int = 0x001F,
        border_color: int = 0xFFFF,
        border_width: int = 2,
    ):
        from picoware.system.system import System

        syst = System()
        self.is_circular = syst.is_circular

        self.display = draw
        self.position = Vector(0, y)
        self.size = Vector(draw.size.x, height)
        self.text_color = text_color
        self.background_color = background_color
        self.selected_color = selected_color
        self.border_color = border_color
        self.border_width = border_width
        draw.clear(self.position, self.size, background_color)

        self.lines_per_screen = 14
        self.item_height = 20
        self._selected_index = 0
        self.visible_item_count = (self.size.y - 2 * border_width) / self.item_height
        self.items = []
        draw.swap()

    def __del__(self):
        if self.size:
            del self.size
            self.size = None
        if self.position:
            del self.position
            self.position = None
        self.items = []

    @property
    def current_item(self) -> str:
        """Get the currently selected item."""
        # Get the currently selected item
        if 0 <= self._selected_index < len(self.items):
            return self.items[self._selected_index]
        return ""

    @property
    def item_count(self) -> int:
        """Get the number of items in the list."""
        return len(self.items)

    @property
    def list_height(self) -> int:
        """Get the height of the list."""
        return len(self.items) * self.item_height

    @property
    def selected_index(self) -> int:
        """Get the selected index."""
        return self._selected_index

    def add_item(self, item: str) -> None:
        """Add an item to the list."""
        self.items.append(item)

    def clear(self) -> None:
        """Clear the list."""
        # Clear the list of items
        self.items = []
        self._selected_index = 0

        # Clear the display area
        self.display.clear(self.position, self.size, self.background_color)
        self.display.swap()

    def draw(self) -> None:
        """Draw the list with new style."""
        self.display.clear(self.position, self.size, self.background_color)

        size_x = self.display.size.x

        # Draw decorative pattern below underline
        pattern_y = self.position.y + 5 + (self.display.size.y // 16)
        _dec_v = Vector(0, pattern_y)
        for i in range(0, size_x, 10):
            _dec_v.x = i
            self.display.pixel(_dec_v, self.border_color)

        # Get current selected item
        if 0 <= self._selected_index < len(self.items):
            current_item = self.items[self._selected_index]

            menu_y = self.position.y + self.size.y // 4
            box_width = size_x - int(size_x // 6.4)
            box_height = self.size.y // 8
            box_x = (size_x - box_width) // 2

            # Draw selection box
            self.display.fill_rectangle(
                Vector(box_x, menu_y - 30),
                Vector(box_width, box_height),
                self.selected_color,
            )

            # Draw text centered
            item_width = len(current_item) * self.display.font_size.x
            item_x = (size_x - item_width) // 2
            self.display.text(
                Vector(item_x, menu_y - 10), current_item, self.text_color
            )

            # Draw navigation arrows
            if self._selected_index > 0:
                self.display.text(Vector(5, menu_y - 7), "<", self.border_color)
            if self._selected_index < len(self.items) - 1:
                self.display.text(
                    Vector(size_x - 15, menu_y - 7), ">", self.border_color
                )

            # Draw indicator dots
            indicator_y = menu_y + 20
            if len(self.items) <= 15:
                dots_spacing = 15
                dots_start_x = (size_x - (len(self.items) * dots_spacing)) // 2
                _pos = Vector(0, indicator_y)
                _size = Vector(10, 10)
                for i in range(len(self.items)):
                    dot_x = dots_start_x + (i * dots_spacing)
                    _pos.x = dot_x
                    if i == self._selected_index:
                        self.display.fill_rectangle(
                            _pos,
                            _size,
                            self.border_color,
                        )
                    else:
                        self.display.rect(
                            _pos,
                            _size,
                            self.border_color,
                        )
            else:
                # show the current selected item index and total count
                index_text = "{}/{}".format(self._selected_index + 1, len(self.items))
                index_text_width = len(index_text) * self.display.font_size.x
                index_text_x = (size_x - index_text_width) // 2
                self.display.text(
                    Vector(index_text_x, indicator_y), index_text, self.border_color
                )

            # Draw decorative bottom pattern
            bottom_pattern_y = indicator_y + 25
            _dec_v_b = Vector(0, bottom_pattern_y)
            for i in range(0, size_x, 10):
                _dec_v_b.x = i
                self.display.pixel(_dec_v_b, self.border_color)

            # Draw scrollable list below decorative pattern
            list_start_y = bottom_pattern_y + 15
            available_height = (self.position.y + self.size.y) - list_start_y
            item_height = self.display.font_size.y + 6  # Font height + padding
            max_visible_items = max(1, int(available_height / item_height))

            # Calculate which items to show based on selected index
            if len(self.items) <= max_visible_items:
                # Show all items if they fit
                first_visible = 0
                last_visible = len(self.items)
            else:
                # Center the selected item when possible
                half_visible = max_visible_items // 2
                first_visible = max(0, self._selected_index - half_visible)
                last_visible = min(len(self.items), first_visible + max_visible_items)

                # Adjust if we're near the end
                if last_visible == len(self.items):
                    first_visible = max(0, len(self.items) - max_visible_items)

            # Draw each visible item
            rec_vec_pos = Vector(5, 0)
            rec_vec_size = Vector(size_x - 10, 0)
            text_vec_pos = Vector(10, 0)
            for i in range(first_visible, last_visible):
                visible_idx = i - first_visible
                item_y = list_start_y + (visible_idx * item_height)

                # Draw background for selected item
                if i == self._selected_index:
                    rec_vec_pos.y = item_y
                    rec_vec_size.y = item_height
                    self.display.fill_rectangle(
                        rec_vec_pos,
                        rec_vec_size,
                        self.selected_color,
                    )

                # Draw item text
                text_y = item_y + 3
                item_text = self.items[i]

                # Truncate text if too long
                max_chars = (size_x - 20) // self.display.font_size.x
                if len(item_text) > max_chars:
                    item_text = item_text[: max_chars - 2] + ".."

                # Center text if circular display, otherwise left-align with padding
                if self.is_circular:
                    text_width = len(item_text) * self.display.font_size.x
                    text_x = (size_x - text_width) // 2
                else:
                    text_x = 10
                text_vec_pos.x = text_x
                text_vec_pos.y = text_y
                self.display.text(text_vec_pos, item_text, self.text_color)

        # Swap buffers
        self.display.swap()

    def get_item(self, index: int) -> str:
        """Get an item from the list."""
        # Get the item from the list
        if 0 <= index < len(self.items):
            return self.items[index]
        return ""

    def item_exists(self, item: str) -> bool:
        """Check if an item exists in the list."""
        return item in self.items

    def remove_item(self, index: int) -> None:
        """Remove an item from the list and update the display."""
        # Remove the item from the list
        if 0 <= index < len(self.items):
            self.items.pop(index)

        if self._selected_index >= len(self.items):
            self._selected_index = len(self.items) - 1 if len(self.items) > 0 else 0

    def scroll_down(self) -> None:
        """Scroll the list down by one item."""
        self._selected_index += 1
        if self._selected_index >= len(self.items):
            self._selected_index = 0
        self.draw()

    def scroll_up(self) -> None:
        """Scroll the list up by one item."""
        self._selected_index -= 1
        if self._selected_index < 0:
            self._selected_index = len(self.items) - 1
        self.draw()

    def set_selected(self, index: int) -> None:
        """Set the selected item in the list"""
        if 0 <= index < len(self.items):
            self._selected_index = index
            self.draw()
