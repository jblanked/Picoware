"""Infrared - Send and learn infrared remote signals."""
from micropython import const
from picoware.system.decorator import storage_required, infrared_tx_required, infrared_rx_required
from gc import collect


STATE_MAIN_MENU = const(0)
STATE_REMOTE_FILES = const(1)
STATE_REMOTE_KEYS = const(2)
STATE_LEARN_MENU = const(3)
STATE_BUTTON_MENU = const(4)
STATE_KEYBOARD = const(5)

FIELD_BUTTON = const(0)
FIELD_NAME = const(1)

_BUTTON_OPTIONS = (
    "Power",
    "Volume Up",
    "Volume Down",
    "Channel Up",
    "Channel Down",
    "Mute",
    "Play",
    "Pause",
    "Stop",
    "Input",
    "Menu",
    "Up",
    "Down",
    "Left",
    "Right",
    "OK",
    "Back",
    "Custom",
)

_state = STATE_MAIN_MENU
_menu = None
_remote_menu = None
_key_menu = None
_learn_menu = None
_button_menu = None
_infrared = None
_remote = None
_remote_paths = []
_key_names = []
_button_name = "Power"
_remote_name = "Remote"
_keyboard_field = -1
_keyboard_save_requested = False
_keyboard_result = ""


def _create_menu(view_manager, title):
    """Create a styled menu for the current view."""
    from picoware.gui.menu import Menu

    draw = view_manager.draw
    return Menu(
        draw,
        title,
        0,
        draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
        view_manager.foreground_color,
        2,
    )


def _display_value(value):
    """Limit a Learn field value to one menu line."""
    return value[:18]


def _relative_remote_path(path):
    """Convert a library path to a root-relative remote path."""
    path = path.lstrip("/")
    prefix = "infrared/"
    if path.startswith(prefix):
        return path[len(prefix) :]
    return path


def _remote_file_path():
    """Return the storage path for the current learned remote."""
    return "learned/" + _remote_name + ".ir"


def _clean_remote_name(value):
    """Normalize a user-provided remote filename."""
    value = value.strip()
    if value.lower().endswith(".ir"):
        value = value[:-3].strip()
    value = value.replace("/", "_").replace("\\", "_")
    if value in ("", ".", ".."):
        return ""
    return value


def _show_main_menu(view_manager):
    """Show the top-level infrared menu."""
    global _menu, _state, _remote, _key_names

    if _menu is None:
        _menu = _create_menu(view_manager, "Infrared")
        _menu.add_item("Remote")
        _menu.add_item("Learn")
        _menu.set_selected(0)

    _remote = None
    _key_names = []
    _state = STATE_MAIN_MENU
    view_manager.draw.erase()
    _menu.draw()


def _show_remote_menu(view_manager):
    """List available infrared remote files."""
    global _remote_menu, _key_menu, _remote_paths, _state, _remote

    if _key_menu is not None:
        del _key_menu
        _key_menu = None
    if _remote_menu is not None:
        del _remote_menu

    _remote = None
    _remote_paths = []
    try:
        for path in _infrared.list_files():
            relative_path = _relative_remote_path(path)
            if relative_path and relative_path.lower().endswith(".ir"):
                _remote_paths.append(relative_path)
    except Exception as error:
        view_manager.log("Infrared remote listing failed: {}".format(error), 2)

    _remote_paths.sort()
    _remote_menu = _create_menu(view_manager, "Remote")
    for path in _remote_paths:
        _remote_menu.add_item(path)
    if not _remote_paths:
        _remote_menu.add_item("No remotes found")

    _state = STATE_REMOTE_FILES
    view_manager.draw.erase()
    _remote_menu.draw()


def _show_key_menu(view_manager, path):
    """Load a remote and show its signal names."""
    global _key_menu, _key_names, _remote, _state

    try:
        remote = _infrared.load(path)
        key_names = list(remote.names)
        if not key_names:
            raise ValueError("remote contains no keys")
    except Exception as error:
        view_manager.alert("Could not read remote: {}".format(error))
        _show_remote_menu(view_manager)
        return

    if _key_menu is not None:
        del _key_menu
    _remote = remote
    _key_names = key_names
    _key_menu = _create_menu(view_manager, "Keys")
    for name in _key_names:
        _key_menu.add_item(name)
    _key_menu.set_selected(0)
    _state = STATE_REMOTE_KEYS
    view_manager.draw.erase()
    _key_menu.draw()


def _show_learn_menu(view_manager):
    """Show the fields and action for learning a remote."""
    global _learn_menu, _button_menu, _state

    if _button_menu is not None:
        del _button_menu
        _button_menu = None
    if _learn_menu is None:
        _learn_menu = _create_menu(view_manager, "Learn")
    else:
        _learn_menu.clear()

    _learn_menu.add_item("Button: " + _display_value(_button_name))
    _learn_menu.add_item("Name: " + _display_value(_remote_name))
    _learn_menu.add_item("Listen / Receive")
    _state = STATE_LEARN_MENU
    view_manager.draw.erase()
    _learn_menu.draw()


def _show_button_menu(view_manager):
    """Show standard and custom signal-name choices."""
    global _button_menu, _state

    if _button_menu is not None:
        del _button_menu
    _button_menu = _create_menu(view_manager, "Button")
    for option in _BUTTON_OPTIONS:
        _button_menu.add_item(option)

    try:
        selected = _BUTTON_OPTIONS.index(_button_name)
    except ValueError:
        selected = len(_BUTTON_OPTIONS) - 1
    _button_menu.set_selected(selected)
    _state = STATE_BUTTON_MENU
    view_manager.draw.erase()
    _button_menu.draw()


def _keyboard_save_callback(result):
    """Record that the Learn keyboard saved a value."""
    global _keyboard_save_requested, _keyboard_result

    _keyboard_save_requested = True
    _keyboard_result = result


def _open_keyboard(view_manager, field):
    """Open the keyboard for a Learn field."""
    global _state, _keyboard_field, _keyboard_save_requested, _keyboard_result

    keyboard = view_manager.keyboard
    if keyboard is None:
        view_manager.alert("Keyboard unavailable")
        _show_learn_menu(view_manager)
        return

    _keyboard_field = field
    _keyboard_save_requested = False
    _keyboard_result = ""
    keyboard.reset()
    keyboard.set_save_callback(_keyboard_save_callback)
    if field == FIELD_BUTTON:
        keyboard.title = "Button"
        keyboard.response = _button_name
    else:
        keyboard.title = "Remote Name"
        keyboard.response = _remote_name
    view_manager.input_manager.reset()
    view_manager.draw.clear(color=view_manager.background_color)
    keyboard.run(force=True)
    _state = STATE_KEYBOARD


def _close_keyboard(view_manager):
    """Close the Learn keyboard and return to its menu."""
    global _state, _keyboard_field, _keyboard_save_requested, _keyboard_result

    if view_manager.keyboard is not None:
        view_manager.keyboard.reset()
    view_manager.input_manager.reset()
    _keyboard_field = -1
    _keyboard_save_requested = False
    _keyboard_result = ""
    _show_learn_menu(view_manager)
    _state = STATE_LEARN_MENU


def _save_keyboard_value(view_manager):
    """Apply the value saved from the Learn keyboard."""
    global _button_name, _remote_name

    value = (_keyboard_result or view_manager.keyboard.response or "").strip()
    field = _keyboard_field
    if field == FIELD_BUTTON:
        if value:
            _button_name = value
    elif field == FIELD_NAME:
        value = _clean_remote_name(value)
        if value:
            _remote_name = value
        else:
            view_manager.alert("Remote name required")

    _close_keyboard(view_manager)


def _run_keyboard(view_manager):
    """Process one frame of Learn keyboard input."""
    global _keyboard_save_requested

    keyboard = view_manager.keyboard
    if keyboard is None:
        _close_keyboard(view_manager)
        return

    if _keyboard_save_requested:
        _keyboard_save_requested = False
        _save_keyboard_value(view_manager)
        return

    if not keyboard.run():
        _close_keyboard(view_manager)
        return

    if _keyboard_save_requested:
        _keyboard_save_requested = False
        _save_keyboard_value(view_manager)


def _show_listening(view_manager):
    """Show the receive status screen."""
    draw = view_manager.draw
    draw.erase()
    draw._text(5, draw.size.y // 2, "Listening...", view_manager.foreground_color)
    draw.swap()

@infrared_rx_required
def _receive_signal(view_manager):
    """Capture and save the selected infrared signal."""
    if not _button_name or not _remote_name:
        view_manager.alert("Set Button and Name first")
        _show_learn_menu(view_manager)
        return

    _show_listening(view_manager)
    path = _remote_file_path()
    try:
        _infrared.capture(path=path, name=_button_name, display=True)
        view_manager.alert(f"Saved {path}")
    except Exception as error:
        view_manager.alert(f"Receive failed: {error}")
    _show_learn_menu(view_manager)

@infrared_tx_required
def _send_signal(view_manager):
    """Transmit the selected signal from the loaded remote."""
    if _remote is None or not _key_names:
        return

    selected = _key_menu.selected_index
    if selected < 0 or selected >= len(_key_names):
        return

    try:
        _infrared.send(_remote, selected)
    except Exception as error:
        view_manager.alert("Send failed: {}".format(error))
        _key_menu.draw()

@storage_required
def start(view_manager) -> bool:
    """Start the infrared app."""
    from picoware.system.infrared import Infrared

    view_manager.storage.mkdir("infrared")

    global _state, _menu, _remote_menu, _key_menu, _learn_menu, _button_menu
    global _infrared, _remote, _remote_paths, _key_names
    global _button_name, _remote_name, _keyboard_field
    global _keyboard_save_requested, _keyboard_result

    _state = STATE_MAIN_MENU
    _menu = None
    _remote_menu = None
    _key_menu = None
    _learn_menu = None
    _button_menu = None
    _infrared = Infrared(view_manager.storage, "infrared")
    _remote = None
    _remote_paths = []
    _key_names = []
    _button_name = "Power"
    _remote_name = "Remote"
    _keyboard_field = -1
    _keyboard_save_requested = False
    _keyboard_result = ""
    _show_main_menu(view_manager)
    collect()
    return True


def run(view_manager) -> None:
    """Run the infrared app."""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_RIGHT,
        BUTTON_CENTER,
    )

    global _button_name

    if _state == STATE_KEYBOARD:
        _run_keyboard(view_manager)
        return

    button = view_manager.button

    if _state == STATE_MAIN_MENU:
        if button == BUTTON_BACK:
            view_manager.back()
        elif button in (BUTTON_UP, BUTTON_LEFT):
            _menu.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            _menu.scroll_down()
        elif button == BUTTON_CENTER:
            if _menu.selected_index == 0:
                _show_remote_menu(view_manager)
            else:
                _show_learn_menu(view_manager)
        return

    if _state == STATE_REMOTE_FILES:
        if button == BUTTON_BACK:
            _show_main_menu(view_manager)
        elif button in (BUTTON_UP, BUTTON_LEFT):
            _remote_menu.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            _remote_menu.scroll_down()
        elif button == BUTTON_CENTER:
            selected = _remote_menu.selected_index
            if selected < len(_remote_paths):
                _show_key_menu(view_manager, _remote_paths[selected])
        return

    if _state == STATE_REMOTE_KEYS:
        if button == BUTTON_BACK:
            _show_remote_menu(view_manager)
        elif button in (BUTTON_UP, BUTTON_LEFT):
            _key_menu.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            _key_menu.scroll_down()
        elif button == BUTTON_CENTER:
            _send_signal(view_manager)
        return

    if _state == STATE_LEARN_MENU:
        if button == BUTTON_BACK:
            _show_main_menu(view_manager)
        elif button in (BUTTON_UP, BUTTON_LEFT):
            _learn_menu.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            _learn_menu.scroll_down()
        elif button == BUTTON_CENTER:
            selected = _learn_menu.selected_index
            if selected == 0:
                _show_button_menu(view_manager)
            elif selected == 1:
                _open_keyboard(view_manager, FIELD_NAME)
            elif selected == 2:
                _receive_signal(view_manager)
        return

    if _state == STATE_BUTTON_MENU:
        if button == BUTTON_BACK:
            _show_learn_menu(view_manager)
        elif button in (BUTTON_UP, BUTTON_LEFT):
            _button_menu.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            _button_menu.scroll_down()
        elif button == BUTTON_CENTER:
            selected = _button_menu.selected_index
            if selected == len(_BUTTON_OPTIONS) - 1:
                _open_keyboard(view_manager, FIELD_BUTTON)
            else:
                _button_name = _BUTTON_OPTIONS[selected]
                _show_learn_menu(view_manager)


def stop(view_manager) -> None:
    """Stop the infrared app and clean up resources."""
    global _state, _menu, _remote_menu, _key_menu, _learn_menu, _button_menu
    global _infrared, _remote, _remote_paths, _key_names, _keyboard_field
    global _keyboard_save_requested, _keyboard_result

    if view_manager.keyboard is not None:
        view_manager.keyboard.reset()
    for menu in (_menu, _remote_menu, _key_menu, _learn_menu, _button_menu):
        if menu is not None:
            del menu

    _state = STATE_MAIN_MENU
    _menu = None
    _remote_menu = None
    _key_menu = None
    _learn_menu = None
    _button_menu = None
    _infrared = None
    _remote = None
    _remote_paths = []
    _key_names = []
    _keyboard_field = -1
    _keyboard_save_requested = False
    _keyboard_result = ""
    collect()