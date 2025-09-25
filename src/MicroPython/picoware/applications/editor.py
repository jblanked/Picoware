_editor_is_running = False
_filename_requested = False
_editor_mode = False
_filename = ""
_keyboard_just_started = False


def __callback_filename_save(result: str) -> None:
    """Callback for when the filename is saved"""
    global _editor_is_running
    global _filename_requested
    global _filename

    if not _editor_is_running:
        return

    _filename = result.strip()
    _filename_requested = True


def _start_editor(view_manager, filename=None):
    """Start the pye editor with the specified filename"""
    from picoware.system.drivers.vt import vt

    global _editor_is_running

    # Create virtual terminal instance using view_manager
    terminal = vt(view_manager)

    # Dry the buffer before editing and clear any pending input
    terminal.dryBuffer()

    # Also reset input manager to clear any queued inputs
    view_manager.get_input_manager().reset(True)

    try:
        from picoware.system.drivers.pye import pye_edit

        # Enable input processing in the virtual terminal
        terminal.input_enabled = True
        storage = view_manager.get_storage()

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
        _editor_is_running = False
        view_manager.get_input_manager().reset(True)
        view_manager.back()


def start(view_manager) -> bool:
    """Start the app."""
    global _editor_is_running
    global _filename_requested
    global _editor_mode
    global _filename
    global _keyboard_just_started

    _editor_is_running = True
    _filename_requested = False
    _editor_mode = False
    _filename = ""
    _keyboard_just_started = False

    keyboard = view_manager.get_keyboard()
    if keyboard is None:
        print("No keyboard available")
        return False

    keyboard.set_save_callback(__callback_filename_save)
    keyboard.set_response("")  # Start with empty filename

    draw = view_manager.get_draw()
    draw.clear(color=view_manager.get_background_color())

    from picoware.system.vector import Vector
    from time import sleep

    draw.text(
        Vector(10, 10),
        "Enter filename (blank for new file):",
        view_manager.get_foreground_color(),
    )
    draw.swap()

    sleep(2)  # Brief pause to let user read the header

    keyboard.run(force=True)

    return True


def run(view_manager) -> None:
    """
    Run the app.

    First phase: Get filename input from user via keyboard
    Second phase: Launch pye editor with the specified filename
    """
    from picoware.system.buttons import BUTTON_BACK

    global _editor_is_running
    global _filename_requested
    global _editor_mode
    global _filename
    global _keyboard_just_started

    # If editor is not running, don't do anything
    if not _editor_is_running:
        return

    input_manager = view_manager.get_input_manager()
    button = input_manager.get_last_button()

    if button == BUTTON_BACK:
        input_manager.reset(True)
        _editor_is_running = False
        _filename_requested = False
        _editor_mode = False
        _filename = ""
        view_manager.back()
        return

    if not _editor_mode:
        keyboard = view_manager.get_keyboard()
        if not keyboard:
            return

        # Check if filename was saved
        if _filename_requested:
            _filename_requested = False
            _editor_mode = True

            # Reset keyboard and clear display before starting editor
            keyboard.reset()
            draw = view_manager.get_draw()
            from picoware.system.vector import Vector

            draw.text(Vector(10, 10), "Starting editor...")
            draw.swap()

            # Start the editor with the entered filename
            _start_editor(view_manager, _filename if _filename else None)
            return

        # Continue running keyboard for filename input
        if not _keyboard_just_started:
            keyboard.run(force=True)
            _keyboard_just_started = True
        else:
            keyboard.run()

    if _editor_mode and not _editor_is_running:
        _filename_requested = False
        _editor_mode = False
        _filename = ""


def stop(view_manager) -> None:
    """Stop the app."""
    from gc import collect

    global _editor_is_running
    global _filename_requested
    global _editor_mode
    global _filename
    global _keyboard_just_started

    _editor_is_running = False
    _filename_requested = False
    _editor_mode = False
    _filename = ""
    _keyboard_just_started = False

    collect()
