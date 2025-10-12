_file_browser_menu = None
_file_browser_textbox = None
_current_directory: str = "/sd"
_is_viewing_file: bool = False
_current_file_path: str = ""
_directory_stack: list[str] = []
_directory_contents: list[str] = []


def __load_directory_contents(view_manager) -> None:
    """Load the contents of the current directory into the menu."""
    from picoware.system.storage import Storage

    storage: Storage = view_manager.get_storage()

    global _current_directory, _directory_contents, _file_browser_menu

    _file_browser_menu.clear()
    _directory_contents.clear()

    try:
        # Get directory listing
        entries = storage.listdir(_current_directory)

        if not entries:
            # No files found, show empty message
            _directory_contents.append("(Empty directory)")
            _file_browser_menu.add_item(_directory_contents[-1])
        else:
            # Add directories first, then files
            directories = []
            files = []
            entry: str
            for entry in entries:
                if entry.startswith("."):
                    continue  # Skip hidden files and directories
                # Remove the "/sd" prefix for the is_directory check since EasySD adds it
                check_path = _current_directory
                if check_path.startswith("/sd"):
                    check_path = check_path[3:]  # Remove "/sd"
                if not check_path.endswith("/") and check_path != "":
                    check_path += "/"
                check_path += entry

                if storage.is_directory(check_path):
                    directories.append(entry + "/")
                else:
                    files.append(entry)

            # Add directories first
            for directory in sorted(directories):
                _directory_contents.append(directory)
                _file_browser_menu.add_item(directory)

            # Add files
            for file in sorted(files):
                _directory_contents.append(file)
                _file_browser_menu.add_item(file)

    except Exception as e:
        print(f"Error loading directory {_current_directory}: {e}")
        _directory_contents.append("(Error reading directory)")
        _file_browser_menu.add_item(_directory_contents[-1])

    _file_browser_menu.set_selected(0)
    _file_browser_menu.draw()


def __show_file_contents(view_manager, file_path: str) -> None:
    """Display the contents of a file in the textbox."""
    from picoware.system.storage import Storage

    storage: Storage = view_manager.get_storage()

    global _file_browser_textbox, _is_viewing_file, _current_file_path

    _file_browser_textbox.set_text("Loading file... hit BACK if this takes too long")

    try:
        # remove /sd/ prefix if present since EasySD adds it
        if file_path.startswith("/sd/"):
            file_path = file_path[3:]
        file_content = storage.read(file_path)

        if not file_content:
            file_content = "Error: Could not read file or file is empty."
    except Exception as e:
        file_content = f"Error reading file: {e}"

    # Update text box with file contents and show file
    _file_browser_textbox.set_text(file_content)
    lines = _file_browser_textbox.lines_per_screen - 1
    total_lines = _file_browser_textbox.total_lines
    index = lines if lines < total_lines else 0
    _file_browser_textbox.set_current_line(index)

    _is_viewing_file = True
    _current_file_path = file_path


def __hide_file_contents() -> None:
    """Hide file contents and return to directory listing."""
    global _file_browser_textbox, _file_browser_menu, _is_viewing_file, _current_file_path

    # Clear the text box and show the menu again
    _file_browser_textbox.clear()
    _file_browser_menu.draw()
    _is_viewing_file = False
    _current_file_path = ""


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.gui.menu import Menu
    from picoware.gui.textbox import TextBox

    global _file_browser_menu, _file_browser_textbox, _current_directory
    global _directory_stack, _directory_contents, _is_viewing_file
    global _current_file_path

    if not _file_browser_menu:
        _file_browser_menu = Menu(
            view_manager.draw,
            "File Browser",
            0,
            320,
            view_manager.get_foreground_color(),
            view_manager.get_background_color(),
            view_manager.get_selected_color(),
            view_manager.get_foreground_color(),
        )

    if not _file_browser_textbox:
        _file_browser_textbox = TextBox(
            view_manager.draw,
            0,
            320,
            view_manager.get_foreground_color(),
            view_manager.get_background_color(),
        )

    # Initialize state
    _directory_stack.clear()
    _directory_contents.clear()
    _current_directory = "/sd"
    _is_viewing_file = False
    _current_file_path = ""

    __load_directory_contents(view_manager)

    return True


def run(view_manager) -> None:
    """Run the app"""

    from picoware.system.buttons import (
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_RIGHT,
        BUTTON_CENTER,
        BUTTON_BACK,
    )

    global _file_browser_menu, _file_browser_textbox, _current_directory
    global _is_viewing_file, _current_file_path, _directory_stack, _directory_contents

    input_manager = view_manager.get_input_manager()
    input_value: int = input_manager.get_last_button()

    if _is_viewing_file:
        # File viewing mode
        if input_value == BUTTON_UP:
            _file_browser_textbox.scroll_up()
            input_manager.reset()
        elif input_value == BUTTON_DOWN:
            _file_browser_textbox.scroll_down()
            input_manager.reset()
        elif input_value in [BUTTON_LEFT, BUTTON_BACK, BUTTON_CENTER, BUTTON_RIGHT]:
            __hide_file_contents()
            input_manager.reset()
    else:
        # Directory browsing mode
        if input_value == BUTTON_UP:
            _file_browser_menu.scroll_up()
            _file_browser_menu.draw()
            input_manager.reset()
        elif input_value == BUTTON_DOWN:
            _file_browser_menu.scroll_down()
            _file_browser_menu.draw()
            input_manager.reset()
        elif input_value in [BUTTON_LEFT, BUTTON_BACK]:
            if _directory_stack:
                # Pop the last directory from stack
                _current_directory = _directory_stack.pop()

                # Update menu title to show current path
                title = f"File Browser: {_current_directory}"
                _file_browser_menu.title = title

                # Reload directory contents
                __load_directory_contents(view_manager)
            else:
                # No more directories in stack, exit the app
                view_manager.back()
            input_manager.reset()
        elif input_value in [BUTTON_CENTER, BUTTON_RIGHT]:
            current_item = _file_browser_menu.get_current_item()
            selected_index = _file_browser_menu.get_selected_index()

            # Skip if empty directory message
            if (
                current_item == "(Empty directory)"
                or current_item == "(Error reading directory)"
            ):
                input_manager.reset()
                return

            # Get the selected item from our contents list
            if 0 <= selected_index < len(_directory_contents):
                selected_item = _directory_contents[selected_index]

                if selected_item.endswith("/"):
                    # It's a directory - navigate into it
                    _directory_stack.append(
                        _current_directory
                    )  # Save current directory to stack

                    # Build new directory path
                    new_path = _current_directory
                    if not new_path.endswith("/"):
                        new_path += "/"
                    new_path += selected_item[:-1]  # Remove trailing slash
                    _current_directory = new_path

                    # Update menu title to show current path
                    title = f"File Browser: {_current_directory}"
                    _file_browser_menu.title = title

                    # Load new directory contents
                    __load_directory_contents(view_manager)
                else:
                    # It's a file - show its contents
                    file_path = _current_directory
                    if not file_path.endswith("/"):
                        file_path += "/"
                    file_path += selected_item

                    __show_file_contents(view_manager, file_path)

            input_manager.reset()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _file_browser_menu, _file_browser_textbox, _current_directory
    global _is_viewing_file, _current_file_path
    global _directory_stack, _directory_contents

    if _file_browser_menu:
        del _file_browser_menu
        _file_browser_menu = None
    if _file_browser_textbox:
        del _file_browser_textbox
        _file_browser_textbox = None

    _current_directory = "/sd"
    _is_viewing_file = False
    _current_file_path = ""
    _directory_stack.clear()
    _directory_contents.clear()

    # Clean up memory
    collect()
