"""PicoIDE - Create, edit, and run source files."""

from micropython import const
from picoware.system.decorator import keyboard_required, storage_required

# 1. First menu: ask if creating new file or editing existing app
# 2. If creating new: enter filename via keyboard
# 3. Then show menu to select the new file type
# 4. If editing existing: show file browser starting in picoware/apps
# 5. Finally the pye editor is started

STATE_INITIAL_MENU = const(0)
STATE_KEYBOARD = const(1)
STATE_FILE_TYPE_MENU = const(2)
STATE_FILE_BROWSER = const(3)
STATE_EDITOR = const(4)
STATE_RUNNING = const(5)

_filename = ""
_editor_state = STATE_INITIAL_MENU
_initial_menu = None
_file_type_menu = None
_file_browser = None
_runner = None
_keyboard_just_started = False


def __template(filename: str) -> str:
    """Return a basic Picoware app template.

    Args:
        filename (str): The app filename.

    Returns:
        str: The template source.
    """
    return f'''# {filename}

def start(view_manager) -> bool:
    """Start the app"""
    return True

    
def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK

    button = view_manager.button

    if button == BUTTON_BACK:
        view_manager.back()

        
def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    collect()

    '''


def __callback_filename_save(result: str) -> None:
    """Callback for when the filename is saved.

    Args:
        result (str): The typed filename.
    """
    global _editor_state
    global _filename

    if _editor_state != STATE_KEYBOARD:
        return

    _filename = result.strip()
    _editor_state = STATE_FILE_TYPE_MENU


def _language_for_filename(filename):
    filename = filename.lower() if filename else ""
    if filename.endswith(".c"):
        return 1
    if filename.endswith(".js"):
        return 2
    if filename.endswith(".bas"):
        return 3
    return 0


def _ensure_extension(filename, extension):
    if not filename:
        return filename

    directory, separator, name = filename.rpartition("/")
    stem, dot, _ = name.rpartition(".")
    if dot and stem:
        name = stem + extension
    else:
        name += extension

    return directory + separator + name


def _run_file(view_manager, filename):
    global _runner

    extension = filename.lower().rsplit(".", 1)[-1]
    if extension == "py":
        view_manager.storage.execute_script(filename)
    elif extension == "js":
        from picoware.system.js import JS

        JS().exec(filename)
    elif extension == "c":
        from picoware.system.c import C

        C().exec(filename)
    elif extension == "bas":
        from picoware.system.mmbasic import MMBasic

        _runner = MMBasic(view_manager)
        return _runner.start(path=filename)
    return False


def _start_editor(view_manager, filename=None, create_template=False):
    """Start the pye editor with the specified filename.

    Args:
        view_manager (ViewManager): The view manager context.
        filename (str): The file to edit. Defaults to None.
        create_template (bool): Create a template if the file is empty. Defaults to False.
    """
    from picoware.system.drivers.pye import pye_edit
    from picoware.system.drivers.vt import vt

    global _editor_state

    # Create virtual terminal instance using view_manager
    terminal = vt(view_manager, _language_for_filename(filename))

    # Dry the buffer before editing and clear any pending input
    terminal.dryBuffer()

    # Also reset input manager to clear any queued inputs
    view_manager.input_manager.reset()

    try:
        # Enable input processing in the virtual terminal
        terminal.input_enabled = True
        storage = view_manager.storage

        # If we need to create a template, check if file exists or is empty
        if create_template and filename and len(filename) > 0:
            try:
                # Check if file exists and is empty or doesn't exist
                file_needs_template = False
                content = storage.read(filename)

                if not content or len(content.strip()) == 0:
                    file_needs_template = True

                # Create template if needed
                if file_needs_template:
                    storage.write(filename, __template(filename))
            except Exception as e:
                view_manager.log(f"[Editor]: Template creation error: {e}", 2)

        # Start the pye editor with our terminal
        if filename and len(filename) > 0:
            # Try to ensure filename is a proper string
            filename_str = str(filename)

            # IMPORTANT: pye_edit expects content as a LIST of filenames, not a string!
            # When passed as string, it iterates over each character!
            filename_list = [filename_str]

            pye_edit(
                filename_list, tab_size=4, undo=50, io_device=terminal, storage=storage
            )
        else:
            pye_edit("", tab_size=4, undo=50, io_device=terminal, storage=storage)

    except KeyboardInterrupt:
        # Handle Ctrl+C or quit command
        # nothing to do here
        pass
    except (OSError, MemoryError, RuntimeError) as e:
        view_manager.log(f"[Editor]: Editor error: {e}", 2)
    except Exception:
        view_manager.log("PicoIDE error", 2)

    if terminal.run_requested and filename and _run_file(view_manager, filename):
        _editor_state = STATE_RUNNING
    else:
        _editor_state = STATE_INITIAL_MENU if terminal.run_requested else STATE_KEYBOARD
        view_manager.back()


def _start_initial_menu(view_manager) -> None:
    """Start the initial menu to choose between new file or edit existing.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from picoware.gui.menu import Menu

    global _initial_menu

    if _initial_menu is None:
        _initial_menu = Menu(
            view_manager.draw,
            "PicoIDE",
            0,
            view_manager.draw.size.y,
            view_manager.foreground_color,
            view_manager.background_color,
            view_manager.selected_color,
            view_manager.foreground_color,
            2,
        )

        _initial_menu.add_item("Create New File")
        _initial_menu.add_item("Edit Existing File")

    _initial_menu.draw()


def _start_file_type_menu(view_manager) -> None:
    """Start the file type menu.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from picoware.gui.menu import Menu

    global _file_type_menu

    if _file_type_menu is None:
        _file_type_menu = Menu(
            view_manager.draw,
            "What type of file?",
            0,
            view_manager.draw.size.y,
            view_manager.foreground_color,
            view_manager.background_color,
            view_manager.selected_color,
            view_manager.foreground_color,
            2,
        )

        _file_type_menu.add_item("Python App")
        _file_type_menu.add_item("C Source File")
        _file_type_menu.add_item("JavaScript Script")
        _file_type_menu.add_item("MMBasic Program")
        _file_type_menu.add_item("Text File")

    _file_type_menu.draw()


def _start_file_browser(view_manager) -> None:
    """Start the file browser for selecting an existing app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from picoware.gui.file_browser import FileBrowser, FILE_BROWSER_SELECTOR

    global _file_browser

    if _file_browser is None:
        _file_browser = FileBrowser(
            view_manager,
            mode=FILE_BROWSER_SELECTOR,
            start_directory="/picoware/apps",
        )

        _file_browser.run()


@keyboard_required
@storage_required
def start(view_manager) -> bool:
    """Start the app.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True on success.
    """

    global _editor_state
    global _filename
    global _keyboard_just_started
    global _initial_menu
    global _file_type_menu
    global _file_browser
    global _runner

    _editor_state = STATE_INITIAL_MENU
    _filename = ""
    _keyboard_just_started = False
    _initial_menu = None
    _file_type_menu = None
    _file_browser = None
    _runner = None

    # Show the initial menu
    draw = view_manager.draw
    draw.clear(color=view_manager.background_color)
    _start_initial_menu(view_manager)

    return True


def run(view_manager) -> None:
    """Run the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from picoware.system.buttons import BUTTON_BACK, BUTTON_OK, BUTTON_UP, BUTTON_DOWN

    global _editor_state
    global _filename
    global _keyboard_just_started
    global _runner

    button = view_manager.button

    # Handle back button - return to previous state or exit
    if button == BUTTON_BACK:

        if _editor_state == STATE_INITIAL_MENU:
            # Exit the app
            view_manager.back()
            return
        if _editor_state == STATE_KEYBOARD:
            # Go back to initial menu
            _editor_state = STATE_INITIAL_MENU
            draw = view_manager.draw
            draw.clear(color=view_manager.background_color)
            _start_initial_menu(view_manager)
            return
        if _editor_state == STATE_FILE_TYPE_MENU:
            # Go back to keyboard
            _editor_state = STATE_KEYBOARD
            keyboard = view_manager.keyboard
            if keyboard:
                keyboard.reset()
                view_manager.input_manager.reset()
                keyboard.response = _filename  # Restore previous filename
                draw = view_manager.draw
                draw.clear(color=view_manager.background_color)
                keyboard.run(force=True)
                _keyboard_just_started = True
            return
        if _editor_state == STATE_FILE_BROWSER:
            # Go back to initial menu
            _editor_state = STATE_INITIAL_MENU
            draw = view_manager.draw
            draw.clear(color=view_manager.background_color)
            _start_initial_menu(view_manager)
            return
        # If in EDITOR state, the editor handles back button itself

    # State 0: Initial menu - choose between new file or edit existing
    if _editor_state == STATE_INITIAL_MENU:
        if _initial_menu is None:
            _start_initial_menu(view_manager)
            return

        # Handle menu navigation
        if button == BUTTON_UP:
            _initial_menu.scroll_up()

        elif button == BUTTON_DOWN:
            _initial_menu.scroll_down()

        elif button == BUTTON_OK:
            selected_index = _initial_menu.selected_index

            if selected_index == 0:  # Create New File
                # Transition to keyboard state
                _editor_state = STATE_KEYBOARD
                keyboard = view_manager.keyboard
                if keyboard:
                    keyboard.set_save_callback(__callback_filename_save)
                    keyboard.response = ""  # Start with empty filename
                    keyboard.title = "Enter full file path"
                    view_manager.input_manager.reset()
                    draw = view_manager.draw
                    draw.clear(color=view_manager.background_color)
                    keyboard.run(force=True)
                    _keyboard_just_started = True
            else:  # Edit Existing File
                # Transition to file browser state
                _editor_state = STATE_FILE_BROWSER
                draw = view_manager.draw
                draw.clear(color=view_manager.background_color)
                _start_file_browser(view_manager)
            return

        # Redraw menu
        _initial_menu.draw()

    # State 1: Keyboard input for filename
    elif _editor_state == STATE_KEYBOARD:
        keyboard = view_manager.keyboard
        if not keyboard:
            return

        # Continue running keyboard for filename input
        if not _keyboard_just_started:
            keyboard.run(force=True)
            _keyboard_just_started = True
        else:
            if not keyboard.run():
                view_manager.back()
                return

        # The callback will transition to STATE_FILE_TYPE_MENU when filename is saved

    # State 2: Menu to select file type
    elif _editor_state == STATE_FILE_TYPE_MENU:
        if _file_type_menu is None:
            _start_file_type_menu(view_manager)
            return

        # Handle menu navigation
        if button == BUTTON_UP:
            _file_type_menu.scroll_up()

        elif button == BUTTON_DOWN:
            _file_type_menu.scroll_down()

        elif button == BUTTON_OK:
            selected_index = _file_type_menu.selected_index

            # Transition to editor state
            _editor_state = STATE_EDITOR

            draw = view_manager.draw
            draw.erase()
            draw._text(10, 10, "Starting editor...", draw.foreground)
            draw.swap()

            # Start editor with or without template
            if selected_index == 0:  # Python App
                _filename = _ensure_extension(_filename, ".py")
                true_path = f"picoware/apps/{_filename}" if _filename else None
                _start_editor(
                    view_manager,
                    true_path,
                    create_template=bool(true_path and true_path.lower().endswith(".py")),
                )
            else:
                extensions = (".c", ".js", ".bas", ".txt")
                _filename = _ensure_extension(_filename, extensions[selected_index - 1])
                _start_editor(
                    view_manager,
                    _filename or None,
                    create_template=False,
                )
            return

        # Redraw menu
        _file_type_menu.draw()

    # State 3: File browser for selecting existing app
    elif _editor_state == STATE_FILE_BROWSER:
        if _file_browser is None:
            _start_file_browser(view_manager)
            return

        # Run the file browser - it handles its own input
        continue_browsing = _file_browser.run()

        if not continue_browsing:
            # User selected a file or exited
            selected_path = _file_browser.path

            if selected_path and not selected_path.endswith("/"):
                # A file was selected, open it in the editor
                _editor_state = STATE_EDITOR
                _filename = selected_path

                draw = view_manager.draw
                draw.erase()
                draw._text(10, 10, "Starting editor...", draw.foreground)
                draw.swap()

                # Start editor with the selected file (no template needed for existing files)
                _start_editor(view_manager, _filename, create_template=False)
            else:
                # User backed out, return to initial menu
                _editor_state = STATE_INITIAL_MENU
                draw = view_manager.draw
                draw.erase()
                _start_initial_menu(view_manager)
            return

    elif _editor_state == STATE_RUNNING:
        if _runner is None or not _runner.run():
            _runner = None
            _editor_state = STATE_INITIAL_MENU
            view_manager.back()

    # State 4: Editor running
    # The editor handles its own state, and will call back() when done


def stop(view_manager) -> None:
    """Stop the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from gc import collect

    global _filename
    global _keyboard_just_started
    global _initial_menu
    global _file_type_menu
    global _file_browser
    global _editor_state
    global _runner

    _filename = ""
    _keyboard_just_started = False

    if _initial_menu:
        del _initial_menu
        _initial_menu = None

    if _file_type_menu:
        del _file_type_menu
        _file_type_menu = None

    if _file_browser:
        del _file_browser
        _file_browser = None
    _runner = None

    _editor_state = STATE_INITIAL_MENU
    view_manager.keyboard.reset()

    collect()
