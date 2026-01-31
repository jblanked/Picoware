class ViewManager:
    """
    ViewManager class that manages multiple views and provides navigation capabilities.
    """

    MAX_VIEWS = 10
    MAX_STACK_SIZE = 10
    FREQ_DEFAULT = 200000000
    FREQ_RP2040 = 200000000  # was 210 but users had issues
    FREQ_RP2350 = 230000000

    def __init__(self):
        """Initialize the ViewManager with default settings."""
        from picoware.gui.draw import Draw
        from picoware.gui.keyboard import Keyboard
        from picoware.system.input import Input
        from picoware.system.storage import Storage
        from picoware.system.LED import LED
        from picoware.system.wifi import WiFi
        from picoware.system.system import System
        from picoware.system.time import Time

        # from picoware.system.thread import ThreadManager
        from picoware.system.colors import TFT_BLUE, TFT_BLACK, TFT_WHITE

        self._current_view = None
        self._view_count = 0
        self._selected_color = TFT_BLUE
        self._stack_depth = 0

        syst = System()
        self._current_board_id = syst.board_id

        self.freq()

        # Initialize ThreadManager
        self._thread_manager = None  # ThreadManager()

        # Initialize WiFi if available
        self._wifi = None
        if syst is not None and syst.has_wifi:
            # self._wifi = WiFi(thread_manager=self._thread_manager)
            self._wifi = WiFi()

        # Initialize storage
        self._storage = None
        if syst.has_sd_card:
            self._storage = Storage()
            self._storage.mkdir("picoware")
            self._storage.mkdir("picoware/settings")

        # Initialize LED
        self._led = LED()

        # Set up colors
        self._background_color = TFT_BLACK
        self._foreground_color = TFT_WHITE

        # Initialize drawing system
        self._draw = Draw(self._foreground_color, self._background_color)

        # Initialize input manager
        self._input_manager = Input()

        # Initialize keyboard
        self._keyboard = Keyboard(
            self._draw,
            self._input_manager,
            self._foreground_color,
            self._background_color,
            self._selected_color,
        )

        # Initialize time
        self._time = Time()

        # Initialize arrays
        self.views = [None] * self.MAX_VIEWS
        self.view_stack = [None] * self.MAX_STACK_SIZE

        if self._storage is not None:
            dark_mode_data: str = self._storage.read("picoware/settings/dark_mode.json")

            if len(dark_mode_data) > 1:
                state: bool = "true" in dark_mode_data.lower()
                if not state:
                    self._background_color = TFT_WHITE
                    self._foreground_color = TFT_BLACK
                    self._draw.background = self._background_color
                    self._draw.foreground = self._foreground_color
                    self._keyboard.background_color = self._background_color
                    self._keyboard.text_color = self._foreground_color

            on_screen_keyboard_data: str = self._storage.read(
                "picoware/settings/onscreen_keyboard.json"
            )

            if len(on_screen_keyboard_data) > 1:
                state: bool = "true" in on_screen_keyboard_data.lower()
                self._keyboard.show_keyboard = state

            lvgl_data: str = self._storage.read("picoware/settings/lvgl_mode.json")

            if len(lvgl_data) > 1:
                state: bool = "true" in lvgl_data.lower()
                self._draw.use_lvgl = state

        # Clear screen
        self.clear()

    def __del__(self):
        """Destructor to clean up resources."""
        from gc import collect

        # Clean up views
        for i in range(self.MAX_VIEWS):
            if self.views[i] is not None:
                del self.views[i]

        if self._current_view is not None:
            del self._current_view
            self._current_view = None

        # Clean up other resources
        if self._keyboard:
            del self._keyboard
            self._keyboard = None
        if self._draw:
            del self._draw
            self._draw = None
        if self._input_manager:
            del self._input_manager
            self._input_manager = None
        if self._storage is not None:
            del self._storage
            self._storage = None
        if self._led:
            del self._led
            self._led = None
        if self._wifi is not None:
            del self._wifi
            self._wifi = None
        if self._time:
            del self._time
            self._time = None
        if self._thread_manager:
            del self._thread_manager
            self._thread_manager = None

        collect()

    @property
    def background_color(self):
        """Return the current background color."""
        return self._background_color

    @background_color.setter
    def background_color(self, color):
        """Set the background color."""
        self._background_color = color
        self._draw.background = color
        self._keyboard.background_color = color

    @property
    def board_id(self):
        """Return the current board ID."""
        return self._current_board_id

    @property
    def board_name(self):
        """Return the current device name."""
        from picoware_boards import get_current_name

        return get_current_name()

    @property
    def current_view(self):
        """Return the current view."""
        return self._current_view

    @property
    def draw(self):
        """Return the Draw instance."""
        return self._draw

    @property
    def foreground_color(self):
        """Return the current foreground color."""
        return self._foreground_color

    @foreground_color.setter
    def foreground_color(self, color):
        """Set the foreground color."""
        self._foreground_color = color
        self._draw.foreground = color
        self._keyboard.text_color = color

    @property
    def has_psram(self):
        """Return whether the current board has PSRAM."""
        from picoware_boards import has_psram

        return has_psram(self._current_board_id)

    @property
    def has_sd_card(self):
        """Return whether the current board has an SD card."""
        return self._storage is not None

    @property
    def has_wifi(self):
        """Return whether the current board has WiFi capability."""
        return self._wifi is not None

    @property
    def input_manager(self):
        """Return the Input manager instance."""
        return self._input_manager

    @property
    def keyboard(self):
        """Return the Keyboard instance."""
        return self._keyboard

    @property
    def led(self):
        """Return the LED instance."""
        return self._led

    @property
    def selected_color(self):
        """Return the selected color."""
        return self._selected_color

    @selected_color.setter
    def selected_color(self, color):
        """Set the selected color."""
        self._selected_color = color
        self._keyboard.selected_color = color

    @property
    def screen_size(self):
        """Return the screen size as a Vector."""
        return self._draw.size

    @property
    def storage(self):
        """Return the Storage instance."""
        return self._storage

    @property
    def time(self):
        """Return the Time instance."""
        return self._time

    @property
    def thread_manager(self):
        """Return the ThreadManager instance."""
        return self._thread_manager

    @property
    def view_count(self):
        """Return the number of views managed."""
        return self._view_count

    @property
    def wifi(self):
        """Return the WiFi instance."""
        return self._wifi

    def add(self, view):
        """
        Add a view to the manager.

        Args:
            view: The View object to add

        Returns:
            bool: True if successfully added, False if max views reached
        """
        if self._view_count >= self.MAX_VIEWS:
            return False

        self.views[self._view_count] = view
        self._view_count += 1
        return True

    def alert(self, message: str, back: bool = False) -> None:
        """Show an alert"""

        from picoware.gui.alert import Alert
        from picoware.system.buttons import BUTTON_BACK

        self._draw.clear()
        _alert = Alert(
            self._draw,
            message,
            self._foreground_color,
            self._background_color,
        )
        _alert.draw("Alert")

        # Wait for user to acknowledge
        inp = self._input_manager
        while True:
            button = inp.button
            if button == BUTTON_BACK:
                inp.reset()
                break

        if back:
            self.back()

    def back(
        self,
        remove_current_view: bool = True,
        should_clear: bool = True,
        should_start: bool = True,
    ):
        """
        Navigate back to the previous view in the stack.

        Args:
            remove_current_view: Whether to remove the current view from the manager
        """
        if self._stack_depth > 0:
            view_to_remove = None

            # Mark current view for removal if requested
            if self._current_view is not None and remove_current_view:
                view_to_remove = self._current_view

            # Stop current view
            if self._current_view is not None:
                self._current_view.stop(self)
                if should_clear:
                    self.clear()

            # Pop from stack and set as current view
            self._stack_depth -= 1
            self._current_view = self.view_stack[self._stack_depth]
            self.view_stack[self._stack_depth] = None

            # Start the previous view
            if self._current_view is not None:
                if should_start:
                    if not self._current_view.start(self):
                        # If the previous view fails to start, try going back again
                        self.back(False, should_clear, should_start)
                        return

            # Remove the view if requested
            if view_to_remove is not None:
                # Find and remove the view from the views array
                for i in range(self._view_count):
                    if self.views[i] == view_to_remove:
                        # Remove any remaining instances from the stack
                        j = 0
                        while j < self._stack_depth:
                            if self.view_stack[j] == view_to_remove:
                                # Shift remaining stack elements down
                                for k in range(j, self._stack_depth - 1):
                                    self.view_stack[k] = self.view_stack[k + 1]
                                self._stack_depth -= 1
                                self.view_stack[self._stack_depth] = None
                                j -= 1  # Check this index again after shifting
                            j += 1

                        # Remove from views array
                        for j in range(i, self._view_count - 1):
                            self.views[j] = self.views[j + 1]
                        self.views[self._view_count - 1] = None
                        self._view_count -= 1
                        break

    def clear(self):
        """Clear the screen with the background color."""
        self._draw.fill_screen(self._background_color)
        self._draw.swap()

    def clear_stack(self):
        """Clear the navigation stack."""
        for i in range(self._stack_depth):
            self.view_stack[i] = None
        self._stack_depth = 0

    def freq(self, use_default: bool = False) -> int:
        """
        Set the CPU frequency.
        """
        import microcontroller
        from picoware.system.boards import (
            BOARD_PICOCALC_PICO,
            BOARD_PICOCALC_PICOW,
        )

        if use_default:
            microcontroller.cpu.frequency = self.FREQ_DEFAULT
            return microcontroller.cpu.frequency

        if self._current_board_id in (BOARD_PICOCALC_PICO, BOARD_PICOCALC_PICOW):
            microcontroller.cpu.frequency = self.FREQ_RP2040
        else:
            microcontroller.cpu.frequency = self.FREQ_RP2350
        return microcontroller.cpu.frequency

    def get_view(self, view_name: str):
        """
        Get a view by name.

        Args:
            view_name: The name of the view to find

        Returns:
            View object if found, None otherwise
        """
        for i in range(self._view_count):
            if self.views[i] is not None:
                if self.views[i].name == view_name:
                    return self.views[i]
            else:
                print(
                    f"ViewManager: View '{view_name}' found in views array but is None."
                )
        return None

    def remove(self, view_name: str):
        """
        Remove a view by name.

        Args:
            view_name: The name of the view to remove
        """
        for i in range(self._view_count):
            if self.views[i] and self.views[i].name == view_name:
                # Check if this view is in the stack and remove all instances
                j = 0
                while j < self._stack_depth:
                    if self.view_stack[j] == self.views[i]:
                        # Shift remaining stack elements down
                        for k in range(j, self._stack_depth - 1):
                            self.view_stack[k] = self.view_stack[k + 1]
                        self._stack_depth -= 1
                        self.view_stack[self._stack_depth] = None
                        j -= 1  # Check this index again after shifting
                    j += 1

                # If this is the current view, clear it
                if self._current_view == self.views[i]:
                    self._current_view.stop(self)
                    self._current_view = None
                    self.clear()

                # Delete the view and shift array
                del self.views[i]
                for j in range(i, self._view_count - 1):
                    self.views[j] = self.views[j + 1]
                self._view_count -= 1
                break

    def run(self):
        """Run the current view."""
        if self._input_manager.button == 80:  # BUTTON_HOME
            while self._stack_depth > 0:
                if self._stack_depth == 1:
                    self.back(should_clear=True, should_start=True)
                else:
                    self.back(should_clear=False, should_start=False)

        if self._thread_manager:
            self._thread_manager.run()

        if self._current_view is not None:
            self._current_view.run(self)

    def set(self, view_name: str):
        """
        Set the current view by name, clearing the stack.

        Args:
            view_name: The name of the view to set as current
        """
        if self._current_view is not None:
            self._current_view.stop(self)
            self.clear()

        self._current_view = self.get_view(view_name)
        if self._current_view is not None:
            if not self._current_view.start(self):
                self.back()

        # Clear the stack when explicitly setting a view
        self.clear_stack()

    def switch_to(self, view_name: str, clear_stack=False, push_view=True):
        """
        Switch to a view by name with options for stack management.

        Args:
            view_name: The name of the view to switch to
            clear_stack: Whether to clear the navigation stack
            push_view: Whether to push the current view to the stack
        """
        view = self.get_view(view_name)
        if view is None:
            print(f"ViewManager: View '{view_name}' not found or is None.")
            return

        # Push current view to stack before switching
        if self._current_view is not None:
            if clear_stack:
                self.clear_stack()
            if push_view:
                self._push_view(self._current_view)
            self._current_view.stop(self)
            self.clear()

        self._current_view = view
        if not self._current_view.start(self):
            self.back()

    def _push_view(self, view):
        """
        Internal method to push a view to the stack.

        Args:
            view: The view to push
        """
        if self._stack_depth < self.MAX_STACK_SIZE and view is not None:
            self.view_stack[self._stack_depth] = view
            self._stack_depth += 1

    def push_view(self, view_name: str):
        """
        Push a view to the stack by name.

        Args:
            view_name: The name of the view to push
        """
        view = self.get_view(view_name)
        if view is not None:
            self._push_view(view)
