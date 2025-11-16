from micropython import const

# 1. the user is entering filename via keyboard
# 2. then the menu is shown to select file type
#    - if Picoware App is selected and the file is empty or not created yet, we create a basic app template
#    - if Python Script is selected, we proceed directly
# 3. finally the pye editor is started

STATE_KEYBOARD = const(0)
STATE_MENU = const(1)
STATE_EDITOR = const(2)

_filename = ""
_editor_state = STATE_KEYBOARD
_editor_menu = None
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
    _editor_state = STATE_MENU


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


def _start_menu(view_manager) -> None:
    """Start the editor menu."""
    from picoware.gui.menu import Menu

    global _editor_menu

    if _editor_menu is None:
        _editor_menu = Menu(
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

        _editor_menu.add_item("Picoware App")
        _editor_menu.add_item("Python Script")

    _editor_menu.draw()


def start(view_manager) -> bool:
    """Start the app."""
    if not view_manager.has_sd_card:
        print("Screensavers app requires an SD card")
        return False

    global _editor_state
    global _filename
    global _keyboard_just_started
    global _editor_menu

    _editor_state = STATE_KEYBOARD
    _filename = ""
    _keyboard_just_started = False
    _editor_menu = None

    keyboard = view_manager.get_keyboard()
    if keyboard is None:
        print("No keyboard available")
        return False

    keyboard.set_save_callback(__callback_filename_save)
    keyboard.set_response("")  # Start with empty filename
    keyboard.title = "Enter filename"

    draw = view_manager.get_draw()
    draw.clear(color=view_manager.get_background_color())

    keyboard.run(force=True)

    return True


def run(view_manager) -> None:
    """
    Run the app.

    State 1 (KEYBOARD): Get filename input from user via keyboard
    State 2 (MENU): Show menu to select file type (Picoware App or Python Script)
    State 3 (EDITOR): Launch pye editor with the specified filename
    """
    from picoware.system.buttons import BUTTON_BACK, BUTTON_OK, BUTTON_UP, BUTTON_DOWN

    global _editor_state
    global _filename
    global _keyboard_just_started
    global _editor_menu

    input_manager = view_manager.get_input_manager()
    button = input_manager.get_last_button()

    # Handle back button - return to previous state or exit
    if button == BUTTON_BACK:
        input_manager.reset()

        if _editor_state == STATE_KEYBOARD:
            # Exit the app
            view_manager.back()
            return
        elif _editor_state == STATE_MENU:
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
        # If in EDITOR state, the editor handles back button itself

    # State 1: Keyboard input for filename
    if _editor_state == STATE_KEYBOARD:
        keyboard = view_manager.get_keyboard()
        if not keyboard:
            return

        # Continue running keyboard for filename input
        if not _keyboard_just_started:
            keyboard.run(force=True)
            _keyboard_just_started = True
        else:
            keyboard.run()

        # The callback will transition to STATE_MENU when filename is saved

    # State 2: Menu to select file type
    elif _editor_state == STATE_MENU:
        if _editor_menu is None:
            _start_menu(view_manager)
            return

        # Handle menu navigation
        if button == BUTTON_UP:
            _editor_menu.scroll_up()
            input_manager.reset()
        elif button == BUTTON_DOWN:
            _editor_menu.scroll_down()
            input_manager.reset()
        elif button == BUTTON_OK:
            selected_index = _editor_menu.get_selected_index()
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
        _editor_menu.draw()

    # State 3: Editor running
    # The editor handles its own state, and will call back() when done


def stop(view_manager) -> None:
    """Stop the app."""
    from gc import collect

    global _filename
    global _keyboard_just_started
    global _editor_menu
    global _editor_state

    _filename = ""
    _keyboard_just_started = False
    if _editor_menu:
        del _editor_menu
        _editor_menu = None
    _editor_state = STATE_KEYBOARD

    collect()
