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
        from picoware.system.vector import Vector

        syst = System()
        self.is_circular = syst.is_circular

        self.display = draw
        self.y = y
        self.height = height
        self.text_color = text_color
        self.background_color = background_color
        self.selected_color = selected_color
        self.border_color = border_color
        self.border_width = border_width
        self.use_lvgl = draw.use_lvgl
        self._lvgl_list = None

        # Initialize LVGL List if requested
        if self.use_lvgl:
            try:
                from picoware_lvgl import init, List as LVGLList

                init()

                # Create LVGL List instance
                self._lvgl_list = LVGLList(
                    y,
                    height,
                    text_color,
                    background_color,
                    selected_color,
                    border_color,
                    border_width,
                )
            except (ImportError, RuntimeError, ValueError):
                self.use_lvgl = False

        # If not using LVGL, initialize standard rendering
        if not self.use_lvgl:
            self.position = Vector(0, y)
            self.size = Vector(draw.size.x, height)
            draw.clear(self.position, self.size, background_color)

            self.lines_per_screen = 14
            self.item_height = 20
            self._selected_index = 0
            self.visible_item_count = (
                self.size.y - 2 * border_width
            ) / self.item_height
            self.items = []
            draw.swap()

            self.size_x = self.display.size.x
            self._dec_v = Vector(0, 0)
            self._dec_v_b = Vector(0, 0)

            self.rec_vec_pos = Vector(5, 0)
            self.rec_vec_size = Vector(self.size_x - 10, 0)
            self.text_vec_pos = Vector(10, 0)

            self.menu_y = int(self.position.y + self.size.y // 4)
            self.box_width = int(self.size_x - int(self.size_x // 6.4))
            self.box_height = int(self.size.y // 8)
            self.box_x = int((self.size_x - self.box_width) // 2)
            self.box_pos = Vector(self.box_x, self.menu_y - 30)
            self.box_size = Vector(self.box_width, self.box_height)
            self.dot_size = Vector(10, 10)
            self.dot_pos = Vector(0, 0)
        else:
            # For LVGL mode, we still need to track items in Python
            self.items = []
            self._selected_index = 0
            self.position = Vector(0, y)
            self.size = Vector(draw.size.x, height)

    def __del__(self):
        """Destructor to clean up resources"""
        if self._lvgl_list is not None:
            self._lvgl_list.deinit()
            del self._lvgl_list
            self._lvgl_list = None
            self.items = []
            return

        self.items = []
        self.size = None
        self.position = None
        self._dec_v = None
        self._dec_v_b = None
        self.rec_vec_pos = None
        self.rec_vec_size = None
        self.text_vec_pos = None
        self.menu_y = None
        self.box_width = None
        self.box_height = None
        self.box_x = None
        self.box_pos = None
        self.box_size = None
        self.dot_size = None
        self.dot_pos = None

    @property
    def current_item(self) -> str:
        """Get the currently selected item."""
        if self.use_lvgl and self._lvgl_list is not None:
            item = self._lvgl_list.current_item()
            return item if item is not None else ""

        # Get the currently selected item
        if 0 <= self._selected_index < len(self.items):
            return self.items[self._selected_index]
        return ""

    @property
    def item_count(self) -> int:
        """Get the number of items in the list."""
        if self.use_lvgl and self._lvgl_list is not None:
            return self._lvgl_list.item_count()
        return len(self.items)

    @property
    def list_height(self) -> int:
        """Get the height of the list."""
        if self.use_lvgl and self._lvgl_list is not None:
            return self._lvgl_list.list_height()
        return len(self.items) * self.item_height

    @property
    def selected_index(self) -> int:
        """Get the selected index."""
        if self.use_lvgl and self._lvgl_list is not None:
            return self._lvgl_list.selected_index()
        return self._selected_index

    def add_item(self, item: str) -> None:
        """Add an item to the list."""
        if self.use_lvgl and self._lvgl_list is not None:
            self._lvgl_list.add_item(item)
        self.items.append(item)

    def clear(self) -> None:
        """Clear the list."""
        if self.use_lvgl and self._lvgl_list is not None:
            self._lvgl_list.clear()
            self.items = []
            self._selected_index = 0
            return

        # Clear the list of items
        self.items = []
        self._selected_index = 0

        # Clear the display area
        self.display.clear(self.position, self.size, self.background_color)
        self.display.swap()

    def draw(self) -> None:
        """Draw the list with new style."""
        if self.use_lvgl and self._lvgl_list is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_list.draw()
            task_handler()
            return

        self.display.clear(self.position, self.size, self.background_color)

        # Draw decorative pattern below underline
        self._dec_v.y = self.position.y + 5 + (self.display.size.y // 16)
        for i in range(0, self.size_x, 10):
            self._dec_v.x = i
            self.display.pixel(self._dec_v, self.border_color)

        # Get current selected item
        if 0 <= self._selected_index < len(self.items):
            current_item = self.items[self._selected_index]

            # Draw selection box
            self.display.fill_rectangle(
                self.box_pos,
                self.box_size,
                self.selected_color,
            )

            # Draw text centered
            item_width = len(current_item) * self.display.font_size.x
            item_x = (self.size_x - item_width) // 2
            self.text_vec_pos.x, self.text_vec_pos.y = item_x, self.menu_y - 10
            self.display.text(self.text_vec_pos, current_item, self.text_color)

            # Draw navigation arrows
            self.text_vec_pos.y = self.menu_y - 7
            if self._selected_index > 0:
                self.text_vec_pos.x = 5
                self.display.text(self.text_vec_pos, "<", self.border_color)
            if self._selected_index < len(self.items) - 1:
                self.text_vec_pos.x = self.size_x - 15
                self.display.text(self.text_vec_pos, ">", self.border_color)

            # Draw indicator dots
            indicator_y = self.menu_y + 20
            if len(self.items) <= 15:
                dots_spacing = 15
                dots_start_x = (self.size_x - (len(self.items) * dots_spacing)) // 2
                self.dot_pos.x, self.dot_pos.y = 0, indicator_y
                for i in range(len(self.items)):
                    dot_x = dots_start_x + (i * dots_spacing)
                    self.dot_pos.x = dot_x
                    if i == self._selected_index:
                        self.display.fill_rectangle(
                            self.dot_pos,
                            self.dot_size,
                            self.border_color,
                        )
                    else:
                        self.display.rect(
                            self.dot_pos,
                            self.dot_size,
                            self.border_color,
                        )
            else:
                # show the current selected item index and total count
                index_text = "{}/{}".format(self._selected_index + 1, len(self.items))
                index_text_width = len(index_text) * self.display.font_size.x
                index_text_x = (self.size_x - index_text_width) // 2
                self.text_vec_pos.x, self.text_vec_pos.y = index_text_x, indicator_y
                self.display.text(self.text_vec_pos, index_text, self.border_color)

            # Draw decorative bottom pattern
            self._dec_v_b.y = indicator_y + 25
            for i in range(0, self.size_x, 10):
                self._dec_v_b.x = i
                self.display.pixel(self._dec_v_b, self.border_color)

            # Draw scrollable list below decorative pattern
            list_start_y = indicator_y + 40
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
            for i in range(first_visible, last_visible):
                visible_idx = i - first_visible
                item_y = list_start_y + (visible_idx * item_height)

                # Draw background for selected item
                if i == self._selected_index:
                    self.rec_vec_pos.y = item_y
                    self.rec_vec_size.y = item_height
                    self.display.fill_rectangle(
                        self.rec_vec_pos,
                        self.rec_vec_size,
                        self.selected_color,
                    )

                # Draw item text
                text_y = item_y + 3
                item_text = self.items[i]

                # Truncate text if too long
                max_chars = (self.size_x - 20) // self.display.font_size.x
                if len(item_text) > max_chars:
                    item_text = item_text[: max_chars - 2] + ".."

                # Center text if circular display, otherwise left-align with padding
                if self.is_circular:
                    text_width = len(item_text) * self.display.font_size.x
                    text_x = (self.size_x - text_width) // 2
                else:
                    text_x = 10
                self.text_vec_pos.x, self.text_vec_pos.y = text_x, text_y
                self.display.text(self.text_vec_pos, item_text, self.text_color)

        # Swap buffers
        self.display.swap()

    def get_item(self, index: int) -> str:
        """Get an item from the list."""
        if self.use_lvgl and self._lvgl_list is not None:
            item = self._lvgl_list.get_item(index)
            return item if item is not None else ""

        # Get the item from the list
        if 0 <= index < len(self.items):
            return self.items[index]
        return ""

    def item_exists(self, item: str) -> bool:
        """Check if an item exists in the list."""
        if self.use_lvgl and self._lvgl_list is not None:
            return self._lvgl_list.item_exists(item)
        return item in self.items

    def remove_item(self, index: int) -> None:
        """Remove an item from the list and update the display."""
        if self.use_lvgl and self._lvgl_list is not None:
            self._lvgl_list.remove_item(index)
            if 0 <= index < len(self.items):
                self.items.pop(index)
            if self._selected_index >= len(self.items):
                self._selected_index = len(self.items) - 1 if len(self.items) > 0 else 0
            return

        # Remove the item from the list
        if 0 <= index < len(self.items):
            self.items.pop(index)

        if self._selected_index >= len(self.items):
            self._selected_index = len(self.items) - 1 if len(self.items) > 0 else 0

    def scroll_down(self) -> None:
        """Scroll the list down by one item."""
        if self.use_lvgl and self._lvgl_list is not None:
            self._lvgl_list.scroll_down()
            self._selected_index = self._lvgl_list.selected_index()
            self.draw()
            return

        self._selected_index += 1
        if self._selected_index >= len(self.items):
            self._selected_index = 0
        self.draw()

    def scroll_up(self) -> None:
        """Scroll the list up by one item."""
        if self.use_lvgl and self._lvgl_list is not None:
            self._lvgl_list.scroll_up()
            self._selected_index = self._lvgl_list.selected_index()
            self.draw()
            return

        self._selected_index -= 1
        if self._selected_index < 0:
            self._selected_index = len(self.items) - 1
        self.draw()

    def set_selected(self, index: int) -> None:
        """Set the selected item in the list"""
        if self.use_lvgl and self._lvgl_list is not None:
            self._lvgl_list.set_selected(index)
            self._selected_index = index
            self.draw()
            return

        if 0 <= index < len(self.items):
            self._selected_index = index
            self.draw()
