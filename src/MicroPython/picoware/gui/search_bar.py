from picoware.system.buttons import (
    BUTTON_UP,
    BUTTON_DOWN,
    BUTTON_LEFT,
    BUTTON_RIGHT,
    BUTTON_CENTER,
    BUTTON_BACK,
    BUTTON_SPACE,
    BUTTON_BACKSPACE,
)


class SearchBar:
    """A search bar class with text input and search functionality."""

    def __init__(
        self,
        view_manager,
        items: list,
        size=None,
        text_color: int = 0xFFFF,
        background_color: int = 0x0000,
        selected_color: int = 0x001F,
    ) -> None:
        """
        Initialize the SearchBar with a view manager, search items, and styling.

        Positions and sizes derive from the screen size when size is None.
        """
        from picoware.system.vector import Vector

        self._view_manager = view_manager
        self.draw = view_manager.draw
        self.input_manager = view_manager.input_manager

        self._size = self.draw.size if size is None else size
        self._text_color = text_color
        self._background_color = background_color
        self.selected_color = selected_color

        self.items = list(items)
        self._filtered_items = list(items)
        self._selected_index = 0

        # Search bar state
        self._current_text = ""
        self._cursor = 0
        self._dpad_input = -1
        self.just_stopped = False
        self.is_save_pressed = False

        self._touch_enabled = self.input_manager.has_touch_support

        # Layout from screen size
        self.max_chars_per_line = (self._size.x // self.draw.font_size.x) - 1
        self.max_lines = 2
        self._margin_x, self._margin_y = self.draw.scale(5, 5)
        self._row_height = self.draw.scale_y(20)
        self._text_box_height = self.max_lines * self.draw.font_size.y + self._margin_y * 2

        # Results area below text box
        self._results_top = self._text_box_height + self._margin_y
        self._results_height = self._size.y - self._results_top

        # Text box geometry
        self.text_box_pos_vec = Vector(0, 0)
        self.text_box_pos_size = Vector(self._size.x, self._text_box_height)

        # Hit-test rectangles for results
        self._item_rects = []
        self._compute_item_rects()

    def __del__(self) -> None:
        """Destructor to ensure cleanup on object deletion."""
        self.reset()
        self._current_text = ""
        self.items = []
        self._filtered_items = []
        self._item_rects = []
        self.text_box_pos_vec = None
        self.text_box_pos_size = None

    @property
    def text(self) -> str:
        """Get the current text in the search bar."""
        return self._current_text

    @property
    def is_finished(self) -> bool:
        """Returns whether the search bar is finished (an item was selected)."""
        return self.is_save_pressed

    @property
    def selected_item(self):
        """Get the currently highlighted (or clicked) matching item, or None."""
        if 0 <= self._selected_index < len(self._filtered_items):
            return self._filtered_items[self._selected_index]
        return None

    @property
    def results(self) -> list:
        """Get the current list of matching items."""
        return self._filtered_items

    def reset(self) -> None:
        """Resets the search bar state."""
        self._current_text = ""
        self._cursor = 0
        self._selected_index = 0
        self.just_stopped = False
        self.is_save_pressed = False
        self._filtered_items = list(self.items)
        self._compute_item_rects()

    def run(self, swap: bool = True, force: bool = False) -> bool:
        """
        Runs the input manager, handles input, and draws the search bar.

        Returns True while the search bar is running, or False when it is
        done (either an item was clicked/saved or back was pressed).
        """
        if self.just_stopped or self.is_save_pressed:
            return False

        self._dpad_input = self.input_manager.button
        has_touch_point = (
            self._touch_enabled
            and self.input_manager.point
            and self.input_manager.point != (0, 0)
        )

        if self._dpad_input != -1 or force or has_touch_point:
            if self._dpad_input == BUTTON_BACK:
                # Exit search without saving
                self.just_stopped = True
                self.input_manager.reset()
                return False

            self.draw.erase()

            # Process input and redraw
            self._handle_input()
            self._draw()

            self.input_manager.reset()

            if swap or force:
                self.draw.swap()

        # Done on save or back
        return not (self.is_save_pressed or self.just_stopped)

    def _handle_input(self) -> None:
        """Handles character entry, navigation, and item selection."""
        if self._touch_enabled and self._handle_touch_input():
            return

        button = self._dpad_input

        if button == BUTTON_CENTER:
            # Confirm the currently highlighted item
            self._select_item(self._selected_index)
        elif button == BUTTON_UP:
            self._move_selection(-1)
        elif button == BUTTON_DOWN:
            self._move_selection(1)
        elif button == BUTTON_LEFT:
            self._move_cursor(-1)
        elif button == BUTTON_RIGHT:
            self._move_cursor(1)
        elif button == BUTTON_BACKSPACE:
            self._delete_char()
        elif button == BUTTON_SPACE:
            self._type_char(" ")
        else:
            # Direct character entry
            char = self.input_manager.button_to_char(button)
            if char:
                self._type_char(char)

    def _handle_touch_input(self) -> bool:
        """Handle a touch tap. True if the touch was consumed."""
        point = self.input_manager.point
        if not point or point == (0, 0):
            return False

        index = self._item_at_point(point[0], point[1])
        if index is not None:
            self._select_item(index)
            return True

        # Tap moves the text cursor
        if (
            self.text_box_pos_vec.y <= point[1] < self._text_box_height
            and 0 <= point[0] < self._size.x
        ):
            self._cursor = max(
                0,
                min(
                    (point[0] - self._margin_x) // self.draw.font_size.x,
                    len(self._current_text),
                ),
            )
            return True

        return False

    def _item_at_point(self, x: int, y: int):
        """Return the index of the item under a touch point, or None."""
        for i, (rx, ry, rw, rh) in enumerate(self._item_rects):
            if rx <= x < rx + rw and ry <= y < ry + rh:
                return i
        return None

    def _type_char(self, char: str) -> None:
        """Insert a character at the cursor position and re-filter the items."""
        self._current_text = (
            self._current_text[: self._cursor]
            + char
            + self._current_text[self._cursor :]
        )
        self._cursor += 1
        self._update_filter()

    def _delete_char(self) -> None:
        """Delete the character before the cursor and re-filter the items."""
        if self._cursor > 0:
            self._current_text = (
                self._current_text[: self._cursor - 1]
                + self._current_text[self._cursor :]
            )
            self._cursor -= 1
            self._update_filter()

    def _move_cursor(self, delta: int) -> None:
        """Move the text cursor left or right."""
        self._cursor = max(0, min(self._cursor + delta, len(self._current_text)))

    def _move_selection(self, delta: int) -> None:
        """Move the item highlight up or down."""
        if not self._filtered_items:
            return
        index = self._selected_index + delta
        if 0 <= index < len(self._filtered_items):
            self._selected_index = index

    def _select_item(self, index: int) -> None:
        """Click an item: set the save flag and signal that we are done."""
        if not self._filtered_items:
            return
        if index < 0 or index >= len(self._filtered_items):
            return
        self._selected_index = index
        self.is_save_pressed = True
        self.just_stopped = True

    def _update_filter(self) -> None:
        """Filter the item list based on the current search text."""
        query = self._current_text.lower()
        if not query:
            self._filtered_items = list(self.items)
        else:
            self._filtered_items = [
                item for item in self.items if query in str(item).lower()
            ]
        if self._selected_index >= len(self._filtered_items):
            self._selected_index = max(0, len(self._filtered_items) - 1)
        self._compute_item_rects()

    def _compute_item_rects(self) -> None:
        """Precompute the hit-test rectangles for the filtered items."""
        self._item_rects = []
        if not self._filtered_items:
            self._num_columns = 1
            return
        longest = max(self.draw.len(str(item)) for item in self._filtered_items)
        column_width = longest + self._margin_x
        self._num_columns = max(
            1, (self._size.x - self._margin_x * 2) // column_width
        )
        column_width = (self._size.x - self._margin_x * 2) // self._num_columns
        for i in range(len(self._filtered_items)):
            row = i // self._num_columns
            col = i % self._num_columns
            x = self._margin_x + col * column_width
            y = self._results_top + self._margin_y + row * self._row_height
            self._item_rects.append(
                (
                    x - self._margin_x // 2,
                    y - self._margin_y // 2,
                    column_width,
                    self._row_height,
                )
            )

    def _draw(self) -> None:
        """Draw the search bar text box and the matching items."""
        self._draw_textbox()
        self._draw_results()

    def _draw_textbox(self) -> None:
        """Draw the text input box, the current text, and the cursor."""
        # Text box background
        self.draw._fill_rectangle(
            self.text_box_pos_vec.x,
            self.text_box_pos_vec.y,
            self.text_box_pos_size.x,
            self.text_box_pos_size.y,
            self._background_color,
        )

        # Text box border
        self.draw._rectangle(
            self.text_box_pos_vec.x,
            self.text_box_pos_vec.y,
            self.text_box_pos_size.x,
            self.text_box_pos_size.y,
            self._text_color,
        )

        # Wrap text into lines
        lines = []
        current_line = ""
        for char in self._current_text:
            if len(current_line) >= self.max_chars_per_line:
                lines.append(current_line)
                current_line = char
            else:
                current_line += char
        if current_line or not lines:
            lines.append(current_line)

        # Show last visible lines
        start_line = max(0, len(lines) - self.max_lines)
        _x = self._margin_x * 2
        _y = self.text_box_pos_vec.y + self._margin_y
        _distance = self.draw.font_size.y
        for i in range(start_line, len(lines)):
            self.draw._text(
                _x,
                _y + (i - start_line) * _distance,
                lines[i],
                self._text_color,
            )

        # Locate the text cursor
        cursor_line = 0
        cursor_col = self._cursor
        remaining = self._cursor
        for i, line in enumerate(lines):
            if remaining <= len(line):
                cursor_line = i
                cursor_col = remaining
                break
            remaining -= len(line) + 1

        # Draw visible cursor
        if cursor_line >= start_line:
            self.draw._text(
                _x + cursor_col * self.draw.font_size.x,
                _y + (cursor_line - start_line) * _distance,
                "_",
                self._text_color,
            )

    def _draw_results(self) -> None:
        """Draw the matching items in columns below the text box."""
        # Clear the results area
        self.draw._fill_rectangle(
            0,
            self._results_top,
            self._size.x,
            self._results_height,
            self._background_color,
        )

        if not self._filtered_items:
            message = "No matches"
            self.draw._text(
                (self._size.x - self.draw.len(message)) // 2,
                self._results_top + self._margin_y,
                message,
                self._text_color,
            )
            return

        for i, item in enumerate(self._filtered_items):
            if i >= len(self._item_rects):
                break

            x, y, width, height = self._item_rects[i]
            label = str(item)
            is_selected = i == self._selected_index

            # Highlight the selected item
            if is_selected:
                self.draw._fill_rectangle(x, y, width, height, self.selected_color)

            self.draw._text(
                x + self._margin_x // 2,
                y + self._margin_y // 2,
                label,
                self._text_color,
            )

    