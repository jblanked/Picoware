from micropython import const

STATE_MENU = const(0)
STATE_BROWSE = const(1)
STATE_KEYBOARD = const(2)
STATE_EDIT = const(3)

_state = STATE_MENU
_filename = ""
_menu = None
_file_browser = None
_textbox = None
_keyboard_just_started = False
_file_selected = False


def __is_editable_file(path: str) -> bool:
    """Return whether the text editor app should open this path."""
    from picoware.gui.file_browser import FileBrowser

    ext = path.split(".")[-1].lower() if "." in path else ""
    return ext in FileBrowser.TEXT_EDITABLE_EXTENSIONS


def __start_menu(view_manager) -> None:
    """Build and draw the main menu."""
    from picoware.gui.menu import Menu

    global _menu

    if _menu is None:
        draw = view_manager.draw
        _menu = Menu(
            draw,
            "Text Editor",
            0,
            draw.size.y,
            view_manager.foreground_color,
            view_manager.background_color,
            view_manager.selected_color,
            view_manager.foreground_color,
            2,
        )
        _menu.add_item("Create New File")
        _menu.add_item("Select File")
        _menu.set_selected(0)

    _menu.draw()


def __start_browse(view_manager) -> None:
    """Start the file browser in selector mode."""
    from picoware.gui.file_browser import FileBrowser, FILE_BROWSER_SELECTOR

    global _file_browser

    if _file_browser is None:
        _file_browser = FileBrowser(
            view_manager,
            mode=FILE_BROWSER_SELECTOR,
            start_directory="/",
            allowed_extensions=list(FileBrowser.TEXT_EDITABLE_EXTENSIONS),
        )


def __callback_keyboard_save(result: str) -> None:
    """Called by the keyboard when the user presses Save."""
    global _state, _filename

    if _state != STATE_KEYBOARD:
        return

    _filename = result.strip()
    if _filename:
        _state = STATE_EDIT


def __start_keyboard(view_manager) -> None:
    """Activate the on-screen keyboard for filename entry."""
    global _keyboard_just_started

    kb = view_manager.keyboard
    kb.set_save_callback(__callback_keyboard_save)
    kb.title = "Enter filename:"
    kb.response = ""
    view_manager.input_manager.reset()
    view_manager.draw.clear(color=view_manager.background_color)
    kb.run(force=True)
    _keyboard_just_started = True


def __start_edit(view_manager) -> None:
    """Open the TextEditor for the current filename."""
    from picoware.gui.text_editor import TextEditor

    global _state, _textbox

    if _textbox is None:
        if _filename and not __is_editable_file(_filename):
            view_manager.alert("Unsupported file format.")
            _state = STATE_MENU
            view_manager.draw.clear(color=view_manager.background_color)
            __start_menu(view_manager)
            return
        _textbox = TextEditor(view_manager)
        if _filename:
            _textbox.load_file(_filename)
        _textbox.refresh()
        view_manager.input_manager.reset()


def __save_and_return_to_menu(view_manager) -> None:
    """Save the current file and transition back to the menu state."""
    global _state, _textbox, _filename

    if _textbox is not None and _filename:
        storage = view_manager.storage
        if storage is not None:
            storage.write(_filename, _textbox.text)
        del _textbox
        _textbox = None

    _filename = ""
    _state = STATE_MENU
    view_manager.draw.clear(color=view_manager.background_color)
    __start_menu(view_manager)


def start(view_manager) -> bool:
    """Start the app."""
    global _state, _filename, _menu, _file_browser, _textbox, _keyboard_just_started, _file_selected

    _state = STATE_MENU
    _filename = ""
    _menu = None
    _file_browser = None
    _textbox = None
    _keyboard_just_started = False
    _file_selected = False

    __start_menu(view_manager)
    return True


def run(view_manager) -> None:
    """Run the app."""
    from picoware.system.buttons import BUTTON_BACK, BUTTON_UP, BUTTON_DOWN, BUTTON_OK

    global _state, _filename, _file_browser, _keyboard_just_started

    button = view_manager.button

    if _state == STATE_MENU:
        if _menu is None:
            __start_menu(view_manager)
            return

        if button == BUTTON_BACK:
            view_manager.back()
            return

        if button == BUTTON_UP:
            _menu.scroll_up()
        elif button == BUTTON_DOWN:
            _menu.scroll_down()
        elif button == BUTTON_OK:
            selected = _menu.selected_index
            view_manager.input_manager.reset()
            if selected == 0:
                # Create new file -> keyboard
                _state = STATE_KEYBOARD
                __start_keyboard(view_manager)
            else:
                # Select existing file -> browse
                _state = STATE_BROWSE
                view_manager.draw.clear(color=view_manager.background_color)
                __start_browse(view_manager)
            return

        _menu.draw()

    elif _state == STATE_BROWSE:
        if _file_browser is None:
            view_manager.input_manager.reset()
            __start_browse(view_manager)
            return

        continue_browsing = _file_browser.run()

        if not continue_browsing:
            view_manager.input_manager.reset()
            selected_path = _file_browser.path
            is_exit = _file_browser.mode == _file_browser.MODE_EXIT

            del _file_browser
            _file_browser = None

            if selected_path and not is_exit:
                if not __is_editable_file(selected_path):
                    view_manager.alert("Unsupported file format.")
                    _state = STATE_MENU
                    view_manager.draw.clear(color=view_manager.background_color)
                    __start_menu(view_manager)
                    return
                _filename = selected_path
                _state = STATE_EDIT
                view_manager.draw.clear(color=view_manager.background_color)
                __start_edit(view_manager)
            else:
                # Backed out -> return to menu
                _state = STATE_MENU
                view_manager.draw.clear(color=view_manager.background_color)
                __start_menu(view_manager)

    elif _state == STATE_KEYBOARD:
        kb = view_manager.keyboard
        if kb is None:
            return

        # If callback already fired, transition to edit
        if _state == STATE_EDIT:
            view_manager.draw.clear(color=view_manager.background_color)
            __start_edit(view_manager)
            return

        if not _keyboard_just_started:
            kb.run(force=True)
            _keyboard_just_started = True
        else:
            result = kb.run()
            if not result:
                kb.reset()
                view_manager.input_manager.reset()
                _state = STATE_MENU
                view_manager.draw.clear(color=view_manager.background_color)
                __start_menu(view_manager)
                return

        # Check if callback has fired
        if _state == STATE_EDIT:
            kb.reset()
            _keyboard_just_started = False
            view_manager.draw.clear(color=view_manager.background_color)
            __start_edit(view_manager)

    elif _state == STATE_EDIT:
        if _textbox is None:
            __start_edit(view_manager)
            return

        still_editing = _textbox.run()
        if not still_editing:
            __save_and_return_to_menu(view_manager)


def stop(view_manager) -> None:
    """Stop the app."""
    from gc import collect

    global _state, _filename, _menu, _file_browser, _textbox, _keyboard_just_started

    if _textbox is not None:
        del _textbox
        _textbox = None

    if _file_browser is not None:
        del _file_browser
        _file_browser = None

    if _menu is not None:
        del _menu
        _menu = None

    kb = view_manager.keyboard
    if kb:
        kb.reset()

    _state = STATE_MENU
    _filename = ""
    _keyboard_just_started = False

    collect()
