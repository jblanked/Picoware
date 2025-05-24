from gc import collect as free
from .draw import Draw
from .vector import Vector
from .scrollbar import ScrollBar


class List:
    """A simple list class for a GUI."""

    def __init__(
        self,
        draw: Draw,
        y: int,
        height: int,
        text_color: int,
        background_color: int,
        selected_color: int,
        border_color: int,
        border_width: int = 2,
    ):
        self.position = Vector(0, y)
        self.size = Vector(draw.size.x, height)
        self.text_color = text_color
        self.background_color = background_color
        self.selected_color = selected_color
        self.border_color = border_color
        self.border_width = border_width
        draw.clear(self.position, self.size, background_color)
        self.scrollbar = ScrollBar(
            draw,
            Vector(0, 0),
            Vector(0, 0),
            border_color,
            background_color,
        )
        from picoware.system.boards import LIBRARY_TYPE_TFT

        self.lines_per_screen = (
            20 if draw.board.library_type == LIBRARY_TYPE_TFT else 26
        )
        self.item_height = 20
        self.selected_index = 0
        self.first_visible_index = 0
        self.visible_item_count = (self.size.y - 2 * border_width) / self.item_height
        self.items = []
        draw.swap()

    def add_item(self, item: str, update_view: bool = False) -> None:
        """Add an item to the list and update the display."""
        # Add an item to the list
        self.items.append(item)

        # Update visibility if necessary
        if update_view:
            self.update_visibility()

    def clear(self) -> None:
        """Clear the list."""
        # Clear the list of items
        self.items = []
        self.selected_index = 0
        self.first_visible_index = 0

        # Clear the display area
        self.scrollbar.display.clear(self.position, self.size, self.background_color)

        self.set_scrollbar_size()
        self.set_scrollbar_position()

        self.scrollbar.display.swap()

    def draw(self) -> None:
        """Draw the list."""
        # Clear previous text objects to prevent memory accumulation
        self.scrollbar.display.clear_text_objects(False)

        # Draw only visible items
        displayed = 0
        for i in range(self.first_visible_index, len(self.items)):
            if displayed >= int(self.visible_item_count):
                break
            self.draw_item(i, i == self.selected_index)
            displayed += 1

        # Draw the scrollbar
        self.set_scrollbar_size()
        self.set_scrollbar_position()
        self.scrollbar.draw()

        # swap the display buffer
        self.scrollbar.display.swap()
        free()

    def draw_item(self, index: int, selected: bool) -> None:
        """Draw an item in the list."""
        # Calculate the position within the visible area
        visible_index = index - self.first_visible_index
        y = self.position.y + self.border_width + visible_index * self.item_height

        # Check if the item is within visible bounds
        if visible_index >= self.visible_item_count:
            return

        # Draw item background
        if selected:
            self.scrollbar.display.rect_fill(
                Vector(self.position.x + self.border_width, y),
                Vector(self.size.x - 2 * self.border_width, self.item_height),
                self.selected_color,
            )
        else:
            self.scrollbar.display.rect_fill(
                Vector(self.position.x + self.border_width, y),
                Vector(self.size.x - 2 * self.border_width, self.item_height),
                self.background_color,
            )

        # Draw line separator
        if self.border_width > 0:
            self.scrollbar.display.line(
                Vector(self.position.x + self.border_width, y + self.item_height - 1),
                Vector(
                    self.position.x + self.size.x - self.border_width - 1,
                    y + self.item_height - 1,
                ),
                self.border_color,
            )

        # Draw the item text
        self.scrollbar.display.text(
            Vector(self.position.x + self.border_width + 5, y + 5),
            self.items[int(index)],
            self.text_color,
        )

    def get_current_item(self) -> str:
        """Get the currently selected item."""
        # Get the currently selected item
        if 0 <= self.selected_index < len(self.items):
            return self.items[self.selected_index]
        return ""

    def get_item(self, index: int) -> str:
        """Get an item from the list."""
        # Get the item from the list
        if 0 <= index < len(self.items):
            return self.items[index]
        return ""

    def get_item_count(self) -> int:
        """Get the number of items in the list."""
        return len(self.items)

    def get_list_height(self) -> int:
        """Get the height of the list."""
        return len(self.items) * self.item_height

    def remove_item(self, index: int) -> None:
        """Remove an item from the list and update the display."""
        # Remove the item from the list
        if 0 <= index < len(self.items):
            self.items.pop(index)

        if self.selected_index >= len(self.items):
            self.selected_index = len(self.items) - 1 if len(self.items) > 0 else 0

        # Update visibility if necessary
        self.update_visibility()

    def scroll_down(self) -> None:
        """Scroll the list down by one item."""
        if self.first_visible_index + self.visible_item_count < len(self.items):
            self.first_visible_index += 1
        if self.selected_index < len(self.items):
            self.selected_index += 1
        if self.selected_index >= len(self.items):
            self.selected_index = len(self.items) - 1
        self.update_visibility()
        self.draw()

    def scroll_up(self) -> None:
        """Scroll the list up by one item."""
        if self.first_visible_index > 0:
            self.first_visible_index -= 1
        if self.selected_index > 0:
            self.selected_index -= 1
        self.selected_index = max(self.selected_index, 0)
        self.update_visibility()
        self.draw()

    def set_selected(self, index: int) -> None:
        """Set the selected item in the list"""
        if 0 <= index < len(self.items):
            self.selected_index = index
            self.update_visibility()
            self.draw()

    def set_scrollbar_position(self) -> None:
        """Set the position of the scrollbar based on the list content and visible area."""
        # Calculate available scrollable area (view height minus scrollbar thumb height)
        view_height = self.size.y - 2 * self.border_width
        scrollable_area = 0

        # Position scrollbar on the right side of the list
        bar_x = self.position.x + self.size.x - self.scrollbar.size.x - 1
        bar_y = self.position.y + self.border_width  # Default to top

        # Only calculate scroll position if we need scrolling
        if len(self.items) > self.visible_item_count:
            scrollable_area = view_height - self.scrollbar.size.y

            # Calculate scroll position ratio based on first visible index and total scrollable items
            scroll_ratio = 0.0

            # Calculate the current scroll position as a ratio
            # Current position = firstVisibleIndex / (total items - visible items)
            max_first_visible = len(self.items) - self.visible_item_count
            if max_first_visible > 0:
                scroll_ratio = float(self.first_visible_index / max_first_visible)

                # Clamp between 0 and 1
                scroll_ratio = max(scroll_ratio, 0.0)
                scroll_ratio = min(scroll_ratio, 1.0)

                # Calculate Y position based on scroll ratio
                bar_y = (
                    self.position.y + self.border_width + scroll_ratio * scrollable_area
                )

        self.scrollbar.position = Vector(bar_x, bar_y)

    def set_scrollbar_size(self) -> None:
        '''Set the size of the scrollbar based on the list content and visible area."""'''
        # Get the total content height and visible view height
        content_height = self.get_list_height()
        view_height = self.size.y - 2 * self.border_width

        # Fixed width for scrollbar
        bar_width = 6.0

        # Calculate the scrollbar thumb height proportionally
        bar_height = 0.0

        # Always show the scrollbar with a minimum height
        if len(self.items) <= self.visible_item_count or content_height <= view_height:
            # Even if scrolling isn't needed, show a full-height scrollbar
            bar_height = view_height
        else:
            # Calculate proportional height of the scrollbar thumb
            # Thumb size = (visible portion / total content) * view height
            bar_height = float(self.visible_item_count) / len(self.items) * view_height

            # Enforce minimum scrollbar height for usability
            bar_height = max(bar_height, 12.0)

            # Make sure it doesn't exceed view height
            bar_height = min(bar_height, view_height)

        self.scrollbar.size = Vector(bar_width, bar_height)

    def update_visibility(self) -> None:
        """Update the visibility of the list."""
        # Make sure the selected item is visible
        if self.selected_index < self.first_visible_index:
            # Selected item is above visible area, scroll up
            self.first_visible_index = self.selected_index
        elif self.selected_index >= self.first_visible_index + self.visible_item_count:
            # Selected item is below visible area, scroll down
            self.first_visible_index = self.selected_index - self.visible_item_count + 1

        self.set_scrollbar_size()
        self.set_scrollbar_position()
