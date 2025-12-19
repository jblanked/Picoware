from micropython import const

# browser modes
FILE_BROWSER_VIEWER = const(0)  # browse and view files only
FILE_BROWSER_MANAGER = const(1)  # browse, view, and manage files (delete)
FILE_BROWSER_SELECTOR = const(2)  # browse and select files (for other apps)


class FileBrowser:
    """A simple file browser implementation."""

    def __init__(
        self,
        view_manager,
        mode: int = FILE_BROWSER_SELECTOR,
        start_directory: str = "",
    ) -> None:
        """Initialize the file browser"""
        from picoware.gui.menu import Menu
        from picoware.gui.textbox import TextBox
        from picoware.gui.choice import Choice
        from picoware.system.vector import Vector

        self._mode = mode
        self._current_directory: str = start_directory
        self._current_path: str = ""
        self._current_file_viewed: str = ""
        self._is_viewing_file: bool = False
        self._directory_stack: list[str] = []
        self._directory_contents: list[str] = []
        self._storage = view_manager.storage
        self._input_manager = view_manager.input_manager

        draw = view_manager.draw

        self._file_browser_menu = Menu(
            draw,
            "File Browser",
            0,
            draw.size.y,
            view_manager.foreground_color,
            view_manager.background_color,
            view_manager.selected_color,
            view_manager.foreground_color,
        )

        self._file_browser_textbox = TextBox(
            draw,
            0,
            draw.size.y,
            view_manager.foreground_color,
            view_manager.background_color,
        )

        self._file_browser_choice = Choice(
            draw,
            Vector(0, 0),
            draw.size,
            "File Browser",
            ["View", "Delete"],
            0,
            view_manager.foreground_color,
            view_manager.background_color,
        )

        # Initialize state
        self._directory_stack.clear()
        self._directory_contents.clear()
        self._is_viewing_file = False
        self._current_file_viewed = ""

        self.__load_directory_contents()

    def __del__(self):
        if self._file_browser_menu:
            del self._file_browser_menu
            self._file_browser_menu = None
        if self._file_browser_textbox:
            del self._file_browser_textbox
            self._file_browser_textbox = None
        if self._file_browser_choice:
            del self._file_browser_choice
            self._file_browser_choice = None

        self._current_directory = None
        self._current_path = None
        self._current_file_viewed = None
        self._is_viewing_file = False
        self._directory_stack.clear()
        self._directory_contents.clear()

    @property
    def directory(self) -> str:
        """Get the current directory path."""
        _dir = self._current_directory
        if _dir.startswith("/sd/"):
            _dir = _dir[3:]
        return _dir

    @property
    def path(self) -> str:
        """Get the current path."""
        _path = self._current_path
        if _path.startswith("/sd/"):
            _path = _path[3:]
        return _path

    @property
    def stats(self) -> dict:
        """Get stastics about the current file"""
        return {
            "directory": self.directory,
            "path": self.path,
            "size": self._storage.size(self.path),
            "type": (
                self._current_path.split(".")[-1]
                if "." in self._current_path
                else "unknown"
            ),
        }

    def __load_directory_contents(self) -> None:
        """Load the contents of the current directory into the menu."""

        self._file_browser_menu.clear()
        self._directory_contents.clear()

        try:
            # Get directory listing
            entries = self._storage.listdir(self._current_directory)

            if not entries:
                # No files found, show empty message
                self._directory_contents.append("(Empty directory)")
                self._file_browser_menu.add_item(self._directory_contents[-1])
            else:
                # Add directories first, then files
                directories = []
                files = []
                entry: str
                for entry in entries:
                    if entry.startswith("."):
                        continue  # Skip hidden files and directories

                    check_path = self._current_directory
                    if check_path.startswith("/sd"):
                        check_path = check_path[3:]  # Remove "/sd"
                    if not check_path.endswith("/") and check_path != "":
                        check_path += "/"
                    check_path += entry

                    if self._storage.is_directory(check_path):
                        directories.append(entry + "/")
                    else:
                        files.append(entry)

                # Add directories first
                for directory in sorted(directories):
                    self._directory_contents.append(directory)
                    self._file_browser_menu.add_item(directory)

                # Add files
                for file in sorted(files):
                    self._directory_contents.append(file)
                    self._file_browser_menu.add_item(file)

        except Exception as e:
            print(f"Error loading directory {self._current_directory}: {e}")
            self._directory_contents.append("(Error reading directory)")
            self._file_browser_menu.add_item(self._directory_contents[-1])

        self._file_browser_menu.set_selected(0)
        self._file_browser_menu.draw()

    def __show_file_contents(self, file_path: str) -> None:
        """Display the contents of a file in the textbox."""

        self._file_browser_textbox.set_text(
            "Loading file... hit BACK if this takes too long"
        )

        try:
            if file_path.startswith("/sd/"):
                file_path = file_path[3:]
            file_content = self._storage.read(file_path)

            if not file_content:
                file_content = "Error: Could not read file or file is empty."
        except Exception as e:
            file_content = f"Error reading file: {e}"

        # Update text box with file contents and show file
        self._file_browser_textbox.set_text(file_content)
        lines = self._file_browser_textbox.lines_per_screen - 1
        total_lines = self._file_browser_textbox.total_lines
        index = lines if lines < total_lines else 0
        self._file_browser_textbox.set_current_line(index)

        self._is_viewing_file = True
        self._current_file_viewed = file_path

    def run(self) -> bool:
        """
        Run the app

        Returns:
            bool: True to continue running, False to exit the app.
        """
        from picoware.system.buttons import (
            BUTTON_UP,
            BUTTON_DOWN,
            BUTTON_LEFT,
            BUTTON_RIGHT,
            BUTTON_CENTER,
            BUTTON_BACK,
        )

        input_value: int = self._input_manager.button

        if self._is_viewing_file:
            # File viewing mode
            if input_value == BUTTON_UP:
                self._input_manager.reset()
                self._file_browser_textbox.scroll_up()
            elif input_value == BUTTON_DOWN:
                self._input_manager.reset()
                self._file_browser_textbox.scroll_down()
            elif input_value in [BUTTON_LEFT, BUTTON_BACK, BUTTON_CENTER, BUTTON_RIGHT]:
                # Clear the text box and show the menu again
                self._input_manager.reset()
                self._file_browser_textbox.clear()
                self._file_browser_menu.draw()
                self._is_viewing_file = False
                self._current_file_viewed = ""
        else:
            # Directory browsing mode
            if input_value in (BUTTON_UP, BUTTON_LEFT):
                self._input_manager.reset()
                self._file_browser_menu.scroll_up()
                self._file_browser_menu.draw()
                self._current_path = (
                    self._current_directory
                    + "/"
                    + self._file_browser_menu.current_item.rstrip("/")
                )
            elif input_value in (BUTTON_DOWN, BUTTON_RIGHT):
                self._input_manager.reset()
                self._file_browser_menu.scroll_down()
                self._file_browser_menu.draw()
                self._current_path = (
                    self._current_directory
                    + "/"
                    + self._file_browser_menu.current_item.rstrip("/")
                )
            elif input_value == BUTTON_BACK:
                self._input_manager.reset()
                if self._directory_stack:
                    # Pop the last directory from stack
                    self._current_directory = self._directory_stack.pop()

                    # Update menu title to show current path
                    self._file_browser_menu.title = (
                        f"File Browser: {self._current_directory}"
                    )

                    self._current_path = self._current_directory

                    # Reload directory contents
                    self.__load_directory_contents()
                else:
                    # No more directories in stack, exit the app
                    return False
            elif input_value == BUTTON_CENTER:
                self._input_manager.reset()
                current_item = self._file_browser_menu.current_item
                selected_index = self._file_browser_menu.selected_index

                # Skip if empty directory message
                if current_item in ("(Empty directory)", "(Error reading directory)"):
                    return

                # Get the selected item from our contents list
                if 0 <= selected_index < len(self._directory_contents):
                    selected_item = self._directory_contents[selected_index]

                    if selected_item.endswith("/"):
                        # It's a directory - navigate into it
                        self._directory_stack.append(
                            self._current_directory
                        )  # Save current directory to stack

                        # Build new directory path
                        new_path = self._current_directory
                        if not new_path.endswith("/"):
                            new_path += "/"
                        new_path += selected_item[:-1]  # Remove trailing slash
                        self._current_directory = new_path

                        # Update menu title to show current path
                        self._file_browser_menu.title = (
                            f"File Browser: {self._current_directory}"
                        )

                        self._current_path = self._current_directory

                        # Load new directory contents
                        self.__load_directory_contents()
                    else:
                        # It's a file - show choice menu
                        file_path = self._current_directory
                        if not file_path.endswith("/"):
                            file_path += "/"
                        file_path += selected_item
                        self._current_path = file_path
                        if self._mode == FILE_BROWSER_SELECTOR:
                            # In selector mode, just set the path and exit
                            return False
                        if self._mode == FILE_BROWSER_VIEWER:
                            # Directly show file contents
                            self.__show_file_contents(file_path)
                        if self._mode == FILE_BROWSER_MANAGER:
                            # Reset choice to default state and draw
                            self._file_browser_choice.state = 0
                            self._file_browser_choice.title = f"File: {selected_item}"
                            self._file_browser_choice.draw()

                            # Enter choice loop
                            while True:
                                _button = self._input_manager.button
                                if _button == BUTTON_LEFT:
                                    self._input_manager.reset()
                                    self._file_browser_choice.scroll_up()
                                elif _button == BUTTON_RIGHT:
                                    self._input_manager.reset()
                                    self._file_browser_choice.scroll_down()
                                elif _button == BUTTON_CENTER:
                                    self._input_manager.reset()
                                    if self._file_browser_choice.state == 0:
                                        # View option selected
                                        self.__show_file_contents(file_path)
                                        break
                                    if self._file_browser_choice.state == 1:
                                        # Delete option selected
                                        try:
                                            # Remove /sd/ prefix if present
                                            delete_path = file_path
                                            if delete_path.startswith("/sd/"):
                                                delete_path = delete_path[3:]
                                            self._storage.remove(delete_path)
                                        except Exception as e:
                                            print(f"Error deleting file: {e}")
                                        finally:
                                            # Reload directory contents
                                            self.__load_directory_contents()
                                        break
                                elif _button == BUTTON_BACK:
                                    self._input_manager.reset()
                                    self._file_browser_menu.draw()
                                    break

                self._input_manager.reset()
        return True
