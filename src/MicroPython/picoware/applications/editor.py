from micropython import const

# 1. First menu: ask if creating new file or editing existing app
# 2. If creating new: enter filename via keyboard
# 3. Then show menu to select file type (Picoware App or Python Script)
# 4. If editing existing: show file browser starting in picoware/apps
# 5. Finally the pye editor is started

STATE_INITIAL_MENU = const(0)
STATE_KEYBOARD = const(1)
STATE_FILE_TYPE_MENU = const(2)
STATE_FILE_BROWSER = const(3)
STATE_EDITOR = const(4)

_filename = ""
_editor_state = STATE_INITIAL_MENU
_initial_menu = None
_file_type_menu = None
_file_browser = None
_keyboard_just_started = False


def __template(filename: str) -> str:
    """Return a basic Picoware app template"""
    return f'''
# {filename}

def start(view_manager) -> bool:
    """Start the app"""
    return True

    
def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK

    inp = view_manager.get_input_manager()
    button = inp.button

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()

        
def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    collect()

    '''


def __callback_filename_save(result: str) -> None:
    """Callback for when the filename is saved"""
    global _editor_state
    global _filename

    if _editor_state != STATE_KEYBOARD:
        return

    _filename = result.strip()
    _editor_state = STATE_FILE_TYPE_MENU


def _start_editor(view_manager, filename=None, create_template=False):
    """Start the pye editor with the specified filename"""
    from picoware.system.drivers.vt import vt

    global _editor_state

    # Create virtual terminal instance using view_manager
    terminal = vt(view_manager)

    # Dry the buffer before editing and clear any pending input
    terminal.dryBuffer()

    # Also reset input manager to clear any queued inputs
    view_manager.get_input_manager().reset()

    try:
        from picoware.system.drivers.pye import pye_edit

        # Enable input processing in the virtual terminal
        terminal.input_enabled = True
        storage = view_manager.get_storage()

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
                print(f"Template creation error: {e}")

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
        print(f"Editor error: {e}")
    except Exception as e:
        print(f"Unexpected editor error: {e}")
    finally:
        _editor_state = STATE_KEYBOARD
        view_manager.get_input_manager().reset()
        view_manager.back()


def _start_initial_menu(view_manager) -> None:
    """Start the initial menu to choose between new file or edit existing."""
    from picoware.gui.menu import Menu

    global _initial_menu

    if _initial_menu is None:
        _initial_menu = Menu(
            view_manager.draw,
            "Python Editor",
            0,
            view_manager.draw.size.y,
            view_manager.get_foreground_color(),
            view_manager.get_background_color(),
            view_manager.get_selected_color(),
            view_manager.get_foreground_color(),
            2,
        )

        _initial_menu.add_item("Create New File")
        _initial_menu.add_item("Edit Existing App")

    _initial_menu.draw()


def _start_file_type_menu(view_manager) -> None:
    """Start the file type menu."""
    from picoware.gui.menu import Menu

    global _file_type_menu

    if _file_type_menu is None:
        _file_type_menu = Menu(
            view_manager.draw,
            "What type of file?",
            0,
            view_manager.draw.size.y,
            view_manager.get_foreground_color(),
            view_manager.get_background_color(),
            view_manager.get_selected_color(),
            view_manager.get_foreground_color(),
            2,
        )

        _file_type_menu.add_item("Picoware App")
        _file_type_menu.add_item("Python Script")

    _file_type_menu.draw()


def _start_file_browser(view_manager) -> None:
    """Start the file browser for selecting an existing app."""
    from picoware.gui.file_browser import FileBrowser, FILE_BROWSER_SELECTOR

    global _file_browser

    if _file_browser is None:
        _file_browser = FileBrowser(
            view_manager,
            mode=FILE_BROWSER_SELECTOR,
            start_directory="/picoware/apps",
        )

        _file_browser.run()


def __alert(view_manager, message: str, back: bool = True) -> None:
    """Show an alert"""

    from picoware.gui.alert import Alert
    from picoware.system.buttons import BUTTON_BACK

    draw = view_manager.get_draw()
    draw.clear()
    _alert = Alert(
        draw,
        message,
        view_manager.get_foreground_color(),
        view_manager.get_background_color(),
    )
    _alert.draw("Alert")

    # Wait for user to acknowledge
    inp = view_manager.get_input_manager()
    while True:
        button = inp.button
        if button == BUTTON_BACK:
            inp.reset()
            break

    if back:
        view_manager.back()


def start(view_manager) -> bool:
    """Start the app."""
    if not view_manager.has_sd_card:
        __alert(view_manager, "Editor app requires an SD card")
        return False

    global _editor_state
    global _filename
    global _keyboard_just_started
    global _initial_menu
    global _file_type_menu
    global _file_browser

    _editor_state = STATE_INITIAL_MENU
    _filename = ""
    _keyboard_just_started = False
    _initial_menu = None
    _file_type_menu = None
    _file_browser = None

    # Show the initial menu
    draw = view_manager.get_draw()
    draw.clear(color=view_manager.get_background_color())
    _start_initial_menu(view_manager)

    return True


def run(view_manager) -> None:
    """
    Run the app.

    State 0 (INITIAL_MENU): Choose between creating new file or editing existing app
    State 1 (KEYBOARD): Get filename input from user via keyboard (for new files)
    State 2 (FILE_TYPE_MENU): Show menu to select file type (Picoware App or Python Script)
    State 3 (FILE_BROWSER): Show file browser to select existing app to edit
    State 4 (EDITOR): Launch pye editor with the specified filename
    """
    from picoware.system.buttons import BUTTON_BACK, BUTTON_OK, BUTTON_UP, BUTTON_DOWN

    global _editor_state
    global _filename
    global _keyboard_just_started
    global _initial_menu
    global _file_type_menu
    global _file_browser

    input_manager = view_manager.get_input_manager()
    button = input_manager.get_last_button()

    # Handle back button - return to previous state or exit
    if button == BUTTON_BACK:
        input_manager.reset()

        if _editor_state == STATE_INITIAL_MENU:
            # Exit the app
            view_manager.back()
            return
        elif _editor_state == STATE_KEYBOARD:
            # Go back to initial menu
            _editor_state = STATE_INITIAL_MENU
            draw = view_manager.get_draw()
            draw.clear(color=view_manager.get_background_color())
            _start_initial_menu(view_manager)
            return
        elif _editor_state == STATE_FILE_TYPE_MENU:
            # Go back to keyboard
            _editor_state = STATE_KEYBOARD
            keyboard = view_manager.get_keyboard()
            if keyboard:
                keyboard.reset()
                keyboard.set_response(_filename)  # Restore previous filename
                draw = view_manager.get_draw()
                draw.clear(color=view_manager.get_background_color())
                keyboard.run(force=True)
                _keyboard_just_started = True
            return
        elif _editor_state == STATE_FILE_BROWSER:
            # Go back to initial menu
            _editor_state = STATE_INITIAL_MENU
            draw = view_manager.get_draw()
            draw.clear(color=view_manager.get_background_color())
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
            input_manager.reset()
        elif button == BUTTON_DOWN:
            _initial_menu.scroll_down()
            input_manager.reset()
        elif button == BUTTON_OK:
            selected_index = _initial_menu.get_selected_index()
            input_manager.reset()

            if selected_index == 0:  # Create New File
                # Transition to keyboard state
                _editor_state = STATE_KEYBOARD
                keyboard = view_manager.get_keyboard()
                if keyboard:
                    keyboard.set_save_callback(__callback_filename_save)
                    keyboard.set_response("")  # Start with empty filename
                    keyboard.title = "Enter filename"
                    draw = view_manager.get_draw()
                    draw.clear(color=view_manager.get_background_color())
                    keyboard.run(force=True)
                    _keyboard_just_started = True
            else:  # Edit Existing App
                # Transition to file browser state
                _editor_state = STATE_FILE_BROWSER
                draw = view_manager.get_draw()
                draw.clear(color=view_manager.get_background_color())
                _start_file_browser(view_manager)
            return

        # Redraw menu
        _initial_menu.draw()

    # State 1: Keyboard input for filename
    elif _editor_state == STATE_KEYBOARD:
        keyboard = view_manager.get_keyboard()
        if not keyboard:
            return

        # Continue running keyboard for filename input
        if not _keyboard_just_started:
            keyboard.run(force=True)
            _keyboard_just_started = True
        else:
            keyboard.run()

        # The callback will transition to STATE_FILE_TYPE_MENU when filename is saved

    # State 2: Menu to select file type
    elif _editor_state == STATE_FILE_TYPE_MENU:
        if _file_type_menu is None:
            _start_file_type_menu(view_manager)
            return

        # Handle menu navigation
        if button == BUTTON_UP:
            _file_type_menu.scroll_up()
            input_manager.reset()
        elif button == BUTTON_DOWN:
            _file_type_menu.scroll_down()
            input_manager.reset()
        elif button == BUTTON_OK:
            selected_index = _file_type_menu.get_selected_index()
            input_manager.reset()

            # Transition to editor state
            _editor_state = STATE_EDITOR

            draw = view_manager.get_draw()
            draw.clear(color=view_manager.get_background_color())
            from picoware.system.vector import Vector

            draw.text(Vector(10, 10), "Starting editor...")
            draw.swap()

            # Start editor with or without template
            if selected_index == 0:  # Picoware App
                _start_editor(
                    view_manager, _filename if _filename else None, create_template=True
                )
            else:  # Python Script
                _start_editor(
                    view_manager,
                    _filename if _filename else None,
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

                draw = view_manager.get_draw()
                draw.clear(color=view_manager.get_background_color())
                from picoware.system.vector import Vector

                draw.text(Vector(10, 10), "Starting editor...")
                draw.swap()

                # Start editor with the selected file (no template needed for existing files)
                _start_editor(view_manager, _filename, create_template=False)
            else:
                # User backed out, return to initial menu
                _editor_state = STATE_INITIAL_MENU
                draw = view_manager.get_draw()
                draw.clear(color=view_manager.get_background_color())
                _start_initial_menu(view_manager)
            return

    # State 4: Editor running
    # The editor handles its own state, and will call back() when done


def stop(view_manager) -> None:
    """Stop the app."""
    from gc import collect

    global _filename
    global _keyboard_just_started
    global _initial_menu
    global _file_type_menu
    global _file_browser
    global _editor_state

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

    _editor_state = STATE_INITIAL_MENU

    collect()
