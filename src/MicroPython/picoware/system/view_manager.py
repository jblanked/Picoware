class ViewManager:
    """
    ViewManager class that manages multiple views and provides navigation capabilities.
    """

    MAX_VIEWS = 10
    MAX_STACK_SIZE = 10

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
        from picoware.system.colors import TFT_BLUE, TFT_BLACK, TFT_WHITE

        self.current_view = None
        self.view_count = 0
        self.selected_color = TFT_BLUE
        self.stack_depth = 0
        self.delay_ticks = 0
        self.delay_elapsed = 0

        # Initialize storage
        self.storage = Storage(True)
        self.storage.mkdir("picoware")

        # Initialize LED
        self.led = LED()

        # Set up colors
        dark_mode_data: str = self.storage.read("picoware/settings/dark_mode.json")
        self.background_color = TFT_BLACK
        self.foreground_color = TFT_WHITE

        if dark_mode_data is not None:
            state: bool = "true" in dark_mode_data.lower()
            if not state:
                self.background_color = TFT_WHITE
                self.foreground_color = TFT_BLACK

        # Initialize drawing system
        self.draw = Draw(self.foreground_color, self.background_color)

        # Initialize input manager
        self.input_manager = Input()

        # Initialize keyboard
        self.keyboard = Keyboard(
            self.draw,
            self.input_manager,
            self.foreground_color,
            self.background_color,
            self.selected_color,
        )

        # Initialize WiFi
        self.wifi = None
        syst = System()
        if syst is not None and syst.has_wifi:
            self.wifi = WiFi()

        # Initialize time
        self.time = Time()

        # Initialize arrays
        self.views = [None] * self.MAX_VIEWS
        self.view_stack = [None] * self.MAX_STACK_SIZE

        # Clear screen
        self.clear()

    def __del__(self):
        """Destructor to clean up resources."""
        from gc import collect

        # Clean up views
        for i in range(self.MAX_VIEWS):
            if self.views[i] is not None:
                del self.views[i]

        if self.current_view:
            del self.current_view
            self.current_view = None

        # Clean up other resources
        if self.keyboard:
            del self.keyboard
            self.keyboard = None
        if self.draw:
            del self.draw
            self.draw = None
        if self.input_manager:
            del self.input_manager
            self.input_manager = None
        if self.storage:
            del self.storage
            self.storage = None
        if self.led:
            del self.led
            self.led = None
        if self.wifi:
            del self.wifi
            self.wifi = None
        if self.time:
            del self.time
            self.time = None

        collect()

    def add(self, view):
        """
        Add a view to the manager.

        Args:
            view: The View object to add

        Returns:
            bool: True if successfully added, False if max views reached
        """
        if self.view_count >= self.MAX_VIEWS:
            return False

        self.views[self.view_count] = view
        self.view_count += 1
        return True

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
        if self.stack_depth > 0:
            view_to_remove = None

            # Mark current view for removal if requested
            if self.current_view is not None and remove_current_view:
                view_to_remove = self.current_view

            # Stop current view
            if self.current_view is not None:
                self.current_view.stop(self)
                if should_clear:
                    self.clear()

            # Pop from stack and set as current view
            self.stack_depth -= 1
            self.current_view = self.view_stack[self.stack_depth]
            self.view_stack[self.stack_depth] = None

            # Start the previous view
            if self.current_view is not None:
                if should_start:
                    if not self.current_view.start(self):
                        # If the previous view fails to start, try going back again
                        self.back(False, should_clear, should_start)
                        return

            # Remove the view if requested
            if view_to_remove is not None:
                # Find and remove the view from the views array
                for i in range(self.view_count):
                    if self.views[i] == view_to_remove:
                        # Remove any remaining instances from the stack
                        j = 0
                        while j < self.stack_depth:
                            if self.view_stack[j] == view_to_remove:
                                # Shift remaining stack elements down
                                for k in range(j, self.stack_depth - 1):
                                    self.view_stack[k] = self.view_stack[k + 1]
                                self.stack_depth -= 1
                                self.view_stack[self.stack_depth] = None
                                j -= 1  # Check this index again after shifting
                            j += 1

                        # Remove from views array
                        for j in range(i, self.view_count - 1):
                            self.views[j] = self.views[j + 1]
                        self.views[self.view_count - 1] = None
                        self.view_count -= 1
                        break

    def clear(self):
        """Clear the screen with the background color."""
        self.draw.fill_screen(self.background_color)
        self.draw.swap()

    def get_view(self, view_name):
        """
        Get a view by name.

        Args:
            view_name: The name of the view to find

        Returns:
            View object if found, None otherwise
        """
        for i in range(self.view_count):
            if self.views[i] is not None:
                if self.views[i].name == view_name:
                    return self.views[i]
            else:
                print(
                    f"ViewManager: View '{view_name}' found in views array but is None."
                )
        return None

    def remove(self, view_name):
        """
        Remove a view by name.

        Args:
            view_name: The name of the view to remove
        """
        for i in range(self.view_count):
            if self.views[i] and self.views[i].name == view_name:
                # Check if this view is in the stack and remove all instances
                j = 0
                while j < self.stack_depth:
                    if self.view_stack[j] == self.views[i]:
                        # Shift remaining stack elements down
                        for k in range(j, self.stack_depth - 1):
                            self.view_stack[k] = self.view_stack[k + 1]
                        self.stack_depth -= 1
                        self.view_stack[self.stack_depth] = None
                        j -= 1  # Check this index again after shifting
                    j += 1

                # If this is the current view, clear it
                if self.current_view == self.views[i]:
                    self.current_view.stop(self)
                    self.current_view = None
                    self.clear()

                # Delete the view and shift array
                del self.views[i]
                for j in range(i, self.view_count - 1):
                    self.views[j] = self.views[j + 1]
                self.view_count -= 1
                break

    def run(self):
        """Run the current view."""
        if self.input_manager.button == 80:  # BUTTON_HOME
            while self.stack_depth > 0:
                if self.stack_depth == 1:
                    self.back(should_clear=True, should_start=True)
                else:
                    self.back(should_clear=False, should_start=False)

        if self.current_view is not None:
            self.current_view.run(self)

    def set(self, view_name):
        """
        Set the current view by name, clearing the stack.

        Args:
            view_name: The name of the view to set as current
        """
        if self.current_view is not None:
            self.current_view.stop(self)
            self.clear()

        self.current_view = self.get_view(view_name)
        if self.current_view is not None:
            if not self.current_view.start(self):
                self.back()

        # Clear the stack when explicitly setting a view
        self.clear_stack()

    def switch_to(self, view_name, clear_stack=False, push_view=True):
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
        if self.current_view is not None:
            if clear_stack:
                self.clear_stack()
            if push_view:
                self._push_view(self.current_view)
            self.current_view.stop(self)
            self.clear()

        self.current_view = view
        if not self.current_view.start(self):
            self.back()

    def _push_view(self, view):
        """
        Internal method to push a view to the stack.

        Args:
            view: The view to push
        """
        if self.stack_depth < self.MAX_STACK_SIZE and view is not None:
            self.view_stack[self.stack_depth] = view
            self.stack_depth += 1

    def push_view(self, view_name):
        """
        Push a view to the stack by name.

        Args:
            view_name: The name of the view to push
        """
        view = self.get_view(view_name)
        if view is not None:
            self._push_view(view)

    def clear_stack(self):
        """Clear the navigation stack."""
        for i in range(self.stack_depth):
            self.view_stack[i] = None
        self.stack_depth = 0

    def get_background_color(self):
        """Get the background color."""
        return self.background_color

    def get_current_view(self):
        """Get the current view."""
        return self.current_view

    def get_draw(self):
        """Get the Draw object."""
        return self.draw

    def get_foreground_color(self):
        """Get the foreground color."""
        return self.foreground_color

    def get_input_manager(self):
        """Get the Input manager."""
        return self.input_manager

    def get_keyboard(self):
        """Get the Keyboard object."""
        return self.keyboard

    def get_led(self):
        """Get the LED object."""
        return self.led

    def get_selected_color(self):
        """Get the selected color."""
        return self.selected_color

    def get_size(self):
        """Get the display size as a Vector."""
        return self.draw.size

    def get_stack_depth(self):
        """Get the current stack depth."""
        return self.stack_depth

    def get_storage(self):
        """Get the Storage object."""
        return self.storage

    def get_time(self):
        """Get the Time object."""
        return self.time

    def get_wifi(self):
        """Get the WiFi object."""
        return self.wifi

    def set_background_color(self, color):
        """Set the background color."""
        self.background_color = color

    def set_foreground_color(self, color):
        """Set the foreground color."""
        self.foreground_color = color

    def set_selected_color(self, color):
        """Set the selected color."""
        self.selected_color = color
