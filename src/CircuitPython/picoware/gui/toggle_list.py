from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_CENTER, BUTTON_BACK


class ToggleList:
    """A class to manage a list of Toggle objects."""

    def __init__(
        self,
        view_manager,
        foreground_color: int = 0xFFFF,
        background_color: int = 0x0000,
        on_color: int = 0x001F,
        border_color: int = 0xFFFF,
        border_width: int = 1,
        callback: callable = None,  # (index: int, state: bool)
    ):
        """
        Initialize the Toggle switch with drawing context and styling.

        :param view_manager: The view manager to render the toggle and handle input.
        :param position: Vector position of the toggle.
        :param size: Vector size of the toggle.
        :param foreground_color: The color of the text.
        :param background_color: The background color.
        :param on_color: The color when toggle is on.
        :param border_color: The color of the border.
        :param border_width: The width of the border.
        :param callback: Optional callback function when a toggle is changed.
        """
        from picoware.system.system import System
        from picoware.system.vector import Vector

        syst = System()
        self.is_circular = syst.is_circular

        self.view_manager = view_manager
        self.position = Vector(0, 0)
        self.size = view_manager.draw.size
        self.foreground_color = foreground_color
        self.background_color = background_color
        self.on_color = on_color
        self.border_color = border_color
        self.border_width = border_width

        self.toggle_list = []
        self.states = []
        self._selected_index = 0
        self.max_visible_items = 8
        self.toggle_size = Vector(self.size.x - 20, int(self.size.y // 10.67))
        self.toggle_position = Vector(10, 10)
        self.toggle_spacing = int(self.size.y // self.max_visible_items)

        self._callback = callback
        self._just_started = True

        self.clear()

    def __del__(self):
        if self.position:
            del self.position
            self.position = None
        if self.size:
            del self.size
            self.size = None
        self.toggle_list = []
        self.states = []

    @property
    def current_item(self):
        """Get the currently selected item (Toggle)."""
        if 0 <= self._selected_index < len(self.toggle_list):
            return self.toggle_list[self._selected_index]
        return ""

    @property
    def current_text(self) -> str:
        """Get the text of the currently selected toggle."""
        if 0 <= self._selected_index < len(self.toggle_list):
            return self.toggle_list[self._selected_index].text
        return ""

    @property
    def current_state(self) -> bool:
        """Get the state of the currently selected toggle."""
        if 0 <= self._selected_index < len(self.toggle_list):
            return self.toggle_list[self._selected_index].state
        return False

    @property
    def item_count(self) -> int:
        """Get the number of items in the list."""
        return len(self.toggle_list)

    @property
    def list_height(self) -> int:
        """Get the height of the list."""
        return len(self.toggle_list) * self.toggle_spacing

    @property
    def selected_index(self) -> int:
        """Get the selected index."""
        return self._selected_index

    def add_toggle(self, text: str, initial_state: bool = False) -> None:
        """Add a new toggle to the list.

        :param text: The label text for the toggle.
        :param initial_state: Initial state of the toggle (True/False).
        """
        from picoware.gui.toggle import Toggle
        from picoware.system.vector import Vector

        toggle_pos = Vector(self.toggle_position.x, self.toggle_position.y)

        self.toggle_list.append(
            Toggle(
                self.view_manager.draw,
                toggle_pos,
                self.toggle_size,
                text,
                initial_state,
                self.foreground_color,
                self.background_color,
                self.on_color,
                self.border_color,
                self.border_width,
                False,
                False,  # only because it clears objects
            )
        )

        self.toggle_position.y += self.toggle_spacing

    def clear(self) -> None:
        """Clear the toggle area with the background color."""
        # Clear the list of items
        self.toggle_list = []
        self._selected_index = 0
        # Reset toggle position for next time toggles are added
        self.toggle_position.x, self.toggle_position.y = 10, 0
        display = self.view_manager.draw
        display.clear(self.position, self.size, self.background_color)
        display.swap()

    def remove_toggle(self, index: int) -> bool:
        """Remove a toggle from the list by index."""
        if 0 <= index < len(self.toggle_list):
            for i in range(index, len(self.toggle_list) - 1):
                self.toggle_list[i] = self.toggle_list[i + 1]
            self.toggle_list.pop()
            if self._selected_index >= len(self.toggle_list):
                self._selected_index = len(self.toggle_list) - 1
            self.__draw()
            return True
        return False

    def run(self) -> bool:
        """Handle input to navigate and toggle items in the list. Returns False if the user wants to exit."""
        if self._just_started:
            self._just_started = False
            self.__draw()

        input_manager = self.view_manager.input_manager
        button = input_manager.button

        if button == BUTTON_BACK:
            input_manager.reset()
            return False
        if button == BUTTON_UP:
            input_manager.reset()
            self.__scroll_up()
        if button == BUTTON_DOWN:
            input_manager.reset()
            self.__scroll_down()
        if button == BUTTON_CENTER:
            input_manager.reset()
            self.__toggle()
        return True

    def update_toggle(self, index: int, text: str, state: bool) -> bool:
        """Update the text and state of a specific toggle in the list."""
        if 0 <= index < len(self.toggle_list):
            toggle = self.toggle_list[index]
            toggle.update(text, state)
            self.__draw()
            return True
        return False

    def __draw(self) -> None:
        """Render up to 8 toggles at a time with scrolling."""
        display = self.view_manager.draw
        display.clear(self.position, self.size, self.background_color)

        # Calculate which toggles to show based on selected index
        if len(self.toggle_list) <= self.max_visible_items:
            # Show all items if they fit
            first_visible = 0
            last_visible = len(self.toggle_list)
        else:
            # Center the selected item when possible
            half_visible = self.max_visible_items // 2
            first_visible = max(0, self._selected_index - half_visible)
            last_visible = min(
                len(self.toggle_list), first_visible + self.max_visible_items
            )

            # Adjust if we're near the end
            if last_visible == len(self.toggle_list):
                first_visible = max(0, len(self.toggle_list) - self.max_visible_items)

        # Draw each visible toggle with adjusted position
        for i in range(first_visible, last_visible):
            toggle = self.toggle_list[i]
            visible_idx = i - first_visible

            # Store original position
            original_y = toggle.position.y

            # Calculate new position for this visible slot
            new_y = int(10 + (visible_idx * self.toggle_spacing))
            toggle.position.y = new_y

            # Draw the toggle
            toggle.draw(swap=False, clear=False, selected=(i == self._selected_index))

            # Restore original position
            toggle.position.y = original_y

        display.swap()

    def __scroll_down(self) -> None:
        """Scroll down the toggle list."""
        self._selected_index += 1
        if self._selected_index >= len(self.toggle_list):
            self._selected_index = 0
        self.__draw()

    def __scroll_up(self) -> None:
        """Scroll the list up by one item."""
        self._selected_index -= 1
        if self._selected_index < 0:
            self._selected_index = len(self.toggle_list) - 1
        self.__draw()

    def __toggle(self) -> None:
        """Toggle the state of the currently selected item."""
        if 0 <= self._selected_index < len(self.toggle_list):
            self.toggle_list[self._selected_index].update(
                self.toggle_list[self._selected_index].text,
                not self.toggle_list[self._selected_index].state,
            )
            if self._callback:
                self._callback(
                    self._selected_index, self.toggle_list[self._selected_index].state
                )
            self.__draw()
