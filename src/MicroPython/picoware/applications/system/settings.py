import json
from micropython import const

# states
STATE_DARK_MODE = const(0)  # toggle (on/off)
STATE_ONSCREEN_KEYBOARD = const(1)  # toggle (show/hide)
STATE_LVGL_MODE = const(2)  # toggle (use LVGL or not)
STATE_THEME_COLOR = const(3)  # choice (select from predefined colors)
STATE_DEBUG = const(4)  # toggle (enable/disable)
STATE_TIME = const(5)  # menu with date (date picker), GMT offset (keyboard)
STATE_EXIT_BUTTON = const(6)  # selection to choose which button triggers app exits
STATE_SERVER_SETTINGS = const(7)  # menu with username and password

# modes
_MODE_MENU = const(0)
_MODE_TOGGLE = const(1)
_MODE_CHOICE = const(2)
_MODE_TIME_MENU = const(3)
_MODE_DATE_PICKER = const(4)
_MODE_GMT_KEYBOARD = const(5)
_MODE_SERVER_MENU = const(6)
_MODE_SERVER_KEYBOARD = const(7)

_menu = None
_toggle = None
_choice = None
_time_menu = None
_date_picker = None
_server_menu = None
_view_manager = None
_mode = _MODE_MENU
_current_setting = 0
_gmt_save_requested = False
_server_save_requested = False
_server_keyboard_field = 0  # 0 = username, 1 = password


def __color_values() -> list[int]:
    """Get the list of color values corresponding to the color names."""
    from picoware.system.colors import (
        TFT_BLUE,
        TFT_RED,
        TFT_GREEN,
        TFT_YELLOW,
        TFT_VIOLET,
        TFT_CYAN,
        TFT_ORANGE,
        TFT_PINK,
        TFT_SKYBLUE,
        TFT_LIGHTGREY,
        TFT_DARKGREY,
        TFT_DARKCYAN,
        TFT_DARKGREEN,
        TFT_BROWN,
    )

    return [
        TFT_RED,
        TFT_GREEN,
        TFT_BLUE,
        TFT_YELLOW,
        TFT_VIOLET,
        TFT_CYAN,
        TFT_ORANGE,
        TFT_PINK,
        TFT_SKYBLUE,
        TFT_LIGHTGREY,
        TFT_DARKGREY,
        TFT_DARKCYAN,
        TFT_DARKGREEN,
        TFT_BROWN,
    ]


def __config() -> tuple:
    """Get the configuration tuple for the current setting."""
    # (menu label, filename, json key, default value)
    return (
        ("Dark Mode", "picoware/settings/dark_mode.json", "dark_mode", True),
        (
            "Onscreen Keyboard",
            "picoware/settings/onscreen_keyboard.json",
            "onscreen_keyboard",
            True,
        ),
        ("Use LVGL", "picoware/settings/lvgl_mode.json", "lvgl_mode", False),
        ("Theme Color", None, None, None),
        ("Debug", "picoware/settings/debug.json", "debug", False),
        ("Time", None, None, None),
        ("Exit Button", None, None, None),
        ("Server Settings", None, None, None),
    )


def __exit_button_mapping() -> dict[int, str]:
    """Get the mapping of button values to their names for the exit button setting."""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_ESCAPE,
    )

    return {
        BUTTON_BACK: "<-Back",
        BUTTON_ESCAPE: "Esc",
    }


def __load_state(filename: str, key: str, default: bool = False) -> bool:
    """Load a boolean setting from storage."""
    data = _view_manager.storage.read(filename)
    if data is not None:
        try:
            obj = json.loads(data)
            if key in obj:
                return bool(obj[key])
        except Exception:
            pass
    return default


def __save_state(filename: str, key: str, state: bool) -> bool:
    """Save a boolean setting to storage."""
    return _view_manager.storage.write(filename, json.dumps({key: state}))


def __load_theme_color() -> int:
    """Load the saved theme color from storage."""
    data = _view_manager.storage.read("picoware/settings/theme_color.json")
    if data is not None:
        try:
            obj = json.loads(data)
            if "theme_color" in obj:
                return int(obj["theme_color"])
        except Exception:
            pass

    return 0x001F  # TFT_BLUE


def __load_exit_button() -> int:
    """Load the saved exit button from storage."""
    from picoware.system.buttons import BUTTON_BACK

    data = _view_manager.storage.read("picoware/settings/exit_button.json")
    if data is not None:
        try:
            obj = json.loads(data)
            if "exit_button" in obj:
                return int(obj["exit_button"])
        except Exception:
            pass

    return BUTTON_BACK


def __save_theme_color(color: int) -> bool:
    """Save the theme color to storage."""
    return _view_manager.storage.write(
        "picoware/settings/theme_color.json",
        json.dumps({"theme_color": color}),
    )


def __save_exit_button(button: int) -> bool:
    """Save the exit button to storage."""
    return _view_manager.storage.write(
        "picoware/settings/exit_button.json",
        json.dumps({"exit_button": button}),
    )


def __load_server_username(view_manager) -> str:
    """Load the saved server username from storage."""
    data = view_manager.storage.read("picoware/settings/server_username.json")
    if data is not None:
        try:
            obj = json.loads(data)
            if "username" in obj:
                return str(obj["username"])
        except Exception:
            pass
    return ""


def __load_server_password(view_manager) -> str:
    """Load the saved server password from storage."""
    data = view_manager.storage.read("picoware/settings/server_password.json")
    if data is not None:
        try:
            obj = json.loads(data)
            if "password" in obj:
                return str(obj["password"])
        except Exception:
            pass
    return ""


def __save_server_username(value: str) -> bool:
    """Save the server username to storage."""
    return _view_manager.storage.write(
        "picoware/settings/server_username.json",
        json.dumps({"username": value}),
    )


def __save_server_password(value: str) -> bool:
    """Save the server password to storage."""
    return _view_manager.storage.write(
        "picoware/settings/server_password.json",
        json.dumps({"password": value}),
    )


def __apply_toggle_setting(index: int, state: bool) -> None:
    """Apply a toggle setting change to the view manager."""
    if index == STATE_DARK_MODE:
        if state:
            _view_manager.background_color = 0x0000
            _view_manager.foreground_color = 0xFFFF
        else:
            _view_manager.background_color = 0xFFFF
            _view_manager.foreground_color = 0x0000
    elif index == STATE_ONSCREEN_KEYBOARD:
        _view_manager.keyboard.show_keyboard = state
    elif index == STATE_LVGL_MODE:
        _view_manager.draw.use_lvgl = state


def __open_toggle(setting_index: int) -> None:
    """Open a Toggle sub-view for the given setting index."""
    global _toggle, _mode, _current_setting
    from picoware.gui.toggle import Toggle
    from picoware.system.vector import Vector

    _current_setting = setting_index
    cfg = __config()[setting_index]
    current_state = __load_state(cfg[1], cfg[2], cfg[3])

    draw = _view_manager.draw
    draw.erase()
    if _toggle is not None:
        del _toggle
        _toggle = None

    _toggle = Toggle(
        draw,
        Vector(10, 10),
        Vector(draw.size.x - 20, int(draw.size.y // 10.67)),
        cfg[0],
        current_state,
        _view_manager.foreground_color,
        _view_manager.background_color,
        _view_manager.selected_color,
        _view_manager.foreground_color,
        2,
    )
    _toggle.draw()
    _mode = _MODE_TOGGLE


def __open_choice() -> None:
    """Open a Choice sub-view for the theme color setting."""
    global _choice, _mode, _current_setting
    from picoware.gui.choice import Choice
    from picoware.system.vector import Vector

    _current_setting = STATE_THEME_COLOR
    current_color = __load_theme_color()
    try:
        initial_index = __color_values().index(current_color)
    except ValueError:
        initial_index = 0

    draw = _view_manager.draw
    draw.erase()
    if _choice is not None:
        del _choice
        _choice = None

    _color_names = [
        "Red",
        "Green",
        "Blue",
        "Yellow",
        "Violet",
        "Cyan",
        "Orange",
        "Pink",
        "Sky Blue",
        "Light Grey",
        "Dark Grey",
        "Dark Cyan",
        "Dark Green",
        "Brown",
    ]

    _choice = Choice(
        draw,
        Vector(0, 0),
        draw.size,
        "Theme Color",
        _color_names,
        initial_index,
        _view_manager.foreground_color,
        _view_manager.background_color,
    )
    _choice.draw()
    _mode = _MODE_CHOICE


def __open_choice_button() -> None:
    """Open a Choice sub-view for the button to exit setting."""
    global _choice, _mode, _current_setting
    from picoware.gui.choice import Choice
    from picoware.system.vector import Vector

    _current_setting = STATE_EXIT_BUTTON
    current_button = __load_exit_button()
    str_buttons = list(__exit_button_mapping().values())
    initial_index = 0
    button_mapping = __exit_button_mapping()
    for i, button_value in enumerate(button_mapping.keys()):
        if button_value == current_button:
            initial_index = i
            break

    draw = _view_manager.draw
    draw.erase()
    if _choice is not None:
        del _choice
        _choice = None

    _choice = Choice(
        draw,
        Vector(0, 0),
        draw.size,
        "Button to Exit",
        str_buttons,
        initial_index,
        _view_manager.foreground_color,
        _view_manager.background_color,
    )
    _choice.draw()
    _mode = _MODE_CHOICE


def __load_gmt_offset() -> int:
    """Load the saved GMT offset from storage."""
    data = _view_manager.storage.read("picoware/settings/gmt_offset.json")
    if data is not None:
        try:
            obj = json.loads(data)
            if "gmt_offset" in obj:
                return int(obj["gmt_offset"])
        except Exception:
            pass
    return 0


def __save_gmt_offset(offset: int) -> bool:
    """Save the GMT offset to storage."""
    return _view_manager.storage.write(
        "picoware/settings/gmt_offset.json",
        json.dumps({"gmt_offset": offset}),
    )


def __open_time_menu() -> None:
    """Open the Time sub-menu (Date & Time / GMT Offset)."""
    global _time_menu, _mode
    from picoware.gui.menu import Menu

    draw = _view_manager.draw
    draw.erase()
    if _time_menu is not None:
        del _time_menu
        _time_menu = None

    _time_menu = Menu(
        draw,
        "Time",
        0,
        draw.size.y,
        _view_manager.foreground_color,
        _view_manager.background_color,
        _view_manager.selected_color,
        _view_manager.foreground_color,
        2,
    )
    _time_menu.add_item("Date & Time")
    _time_menu.add_item("GMT Offset")
    _time_menu.draw()
    _mode = _MODE_TIME_MENU


def __open_date_picker() -> None:
    """Open the DatePicker pre-loaded with the current RTC time."""
    global _date_picker, _mode
    from picoware.gui.date_picker import DatePicker
    from picoware.system.vector import Vector

    draw = _view_manager.draw
    draw.erase()
    if _date_picker is not None:
        del _date_picker
        _date_picker = None

    current_time = _view_manager.time.rtc.datetime()
    _date_picker = DatePicker(
        _view_manager,
        Vector(0, 0),
        draw.size,
        current_time,
    )
    _date_picker.run()
    _mode = _MODE_DATE_PICKER


def __open_gmt_keyboard() -> None:
    """Open the keyboard for entering the GMT offset."""
    global _mode, _gmt_save_requested

    keyboard = _view_manager.keyboard
    keyboard.reset()
    keyboard.title = "GMT Offset"
    keyboard.response = str(__load_gmt_offset())
    keyboard.set_save_callback(__gmt_save_callback)
    keyboard.input_manager.reset()
    keyboard.run(force=True)
    _gmt_save_requested = False
    _mode = _MODE_GMT_KEYBOARD


def __gmt_save_callback(result: str) -> None:
    """Callback triggered when the GMT offset keyboard is saved."""
    global _gmt_save_requested
    _gmt_save_requested = True


def __open_server_menu() -> None:
    """Open the Server Settings sub-menu (Username / Password)."""
    global _server_menu, _mode
    from picoware.gui.menu import Menu

    draw = _view_manager.draw
    draw.erase()
    if _server_menu is not None:
        del _server_menu
        _server_menu = None

    _server_menu = Menu(
        draw,
        "Server Settings",
        0,
        draw.size.y,
        _view_manager.foreground_color,
        _view_manager.background_color,
        _view_manager.selected_color,
        _view_manager.foreground_color,
        2,
    )
    _server_menu.add_item("Username")
    _server_menu.add_item("Password")
    _server_menu.draw()
    _mode = _MODE_SERVER_MENU


def __open_server_keyboard(field: int) -> None:
    """Open the keyboard for entering the server username (0) or password (1)."""
    global _mode, _server_save_requested, _server_keyboard_field

    _server_keyboard_field = field
    keyboard = _view_manager.keyboard
    keyboard.reset()
    if field == 0:
        keyboard.title = "Username"
        keyboard.response = __load_server_username(_view_manager)
    else:
        keyboard.title = "Password"
        keyboard.response = __load_server_password(_view_manager)
    keyboard.set_save_callback(__server_save_callback)
    keyboard.input_manager.reset()
    keyboard.run(force=True)
    _server_save_requested = False
    _mode = _MODE_SERVER_KEYBOARD


def __server_save_callback(result: str) -> None:
    """Callback triggered when the server keyboard is saved."""
    global _server_save_requested
    _server_save_requested = True


def __back_to_server_menu() -> None:
    """Return to the Server Settings sub-menu."""
    global _server_save_requested

    keyboard = _view_manager.keyboard
    keyboard.reset()
    _server_save_requested = False

    __open_server_menu()


def __back_to_menu() -> None:
    """Clean up any sub-view and return to the main menu."""
    global _toggle, _choice, _time_menu, _date_picker, _server_menu, _mode

    if _toggle is not None:
        del _toggle
        _toggle = None
    if _choice is not None:
        del _choice
        _choice = None
    if _time_menu is not None:
        del _time_menu
        _time_menu = None
    if _date_picker is not None:
        del _date_picker
        _date_picker = None
    if _server_menu is not None:
        del _server_menu
        _server_menu = None

    _mode = _MODE_MENU
    _menu.draw()


def __back_to_time_menu() -> None:
    """Return to the Time sub-menu from a date picker or keyboard."""
    global _date_picker, _gmt_save_requested

    if _date_picker is not None:
        del _date_picker
        _date_picker = None

    keyboard = _view_manager.keyboard
    keyboard.reset()
    _gmt_save_requested = False

    __open_time_menu()


def start(view_manager) -> bool:
    """Start the app"""
    if not view_manager.has_sd_card:
        print("Settings app requires an SD card")
        return False

    from picoware.gui.menu import Menu

    global _menu, _view_manager, _mode, _time_menu, _date_picker, _server_menu, _gmt_save_requested, _server_save_requested, _server_keyboard_field

    _view_manager = view_manager
    _mode = _MODE_MENU
    _gmt_save_requested = False
    _server_save_requested = False
    _server_keyboard_field = 0

    if _menu is not None:
        del _menu
        _menu = None
    if _time_menu is not None:
        del _time_menu
        _time_menu = None
    if _date_picker is not None:
        del _date_picker
        _date_picker = None
    if _server_menu is not None:
        del _server_menu
        _server_menu = None

    view_manager.storage.mkdir("picoware/settings")

    _menu = Menu(
        view_manager.draw,
        "Settings",
        0,
        view_manager.draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
        view_manager.foreground_color,
        2,
    )

    for cfg in __config():
        _menu.add_item(cfg[0])

    _menu.draw()
    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_RIGHT,
        BUTTON_CENTER,
    )

    button = view_manager.button

    if _mode == _MODE_MENU:
        if button == BUTTON_BACK:
            view_manager.back()
        elif button in (BUTTON_UP, BUTTON_LEFT):
            _menu.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            _menu.scroll_down()
        elif button == BUTTON_CENTER:
            selected = _menu.selected_index
            if selected == STATE_THEME_COLOR:
                __open_choice()
            elif selected == STATE_TIME:
                __open_time_menu()
            elif selected == STATE_EXIT_BUTTON:
                __open_choice_button()
            elif selected == STATE_SERVER_SETTINGS:
                __open_server_menu()
            else:
                __open_toggle(selected)

    elif _mode == _MODE_TIME_MENU:
        if button == BUTTON_BACK:
            __back_to_menu()
        elif button in (BUTTON_UP, BUTTON_LEFT):
            _time_menu.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            _time_menu.scroll_down()
        elif button == BUTTON_CENTER:
            selected = _time_menu.selected_index
            if selected == 0:  # Date & Time
                __open_date_picker()
            else:  # GMT Offset
                __open_gmt_keyboard()

    elif _mode == _MODE_DATE_PICKER:
        pending = view_manager.button
        if not _date_picker.run():
            if pending == BUTTON_CENTER:
                _saved_time = _date_picker.time
                view_manager.time.set(
                    _saved_time[0],  # year
                    _saved_time[1],  # month
                    _saved_time[2],  # day
                    _saved_time[4],  # hour
                    _saved_time[5],  # minute
                    _saved_time[6],  # second
                )
            __back_to_time_menu()

    elif _mode == _MODE_GMT_KEYBOARD:
        global _gmt_save_requested
        if _gmt_save_requested:
            _gmt_save_requested = False
            try:
                offset = int(view_manager.keyboard.response)
            except (ValueError, TypeError):
                offset = 0
            __save_gmt_offset(offset)
            view_manager.keyboard.reset()
            __back_to_time_menu()
        elif not view_manager.keyboard.run():
            # BACK pressed — discard without saving
            view_manager.keyboard.reset()
            __back_to_time_menu()

    elif _mode == _MODE_SERVER_MENU:
        if button == BUTTON_BACK:
            __back_to_menu()
        elif button in (BUTTON_UP, BUTTON_LEFT):
            _server_menu.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            _server_menu.scroll_down()
        elif button == BUTTON_CENTER:
            __open_server_keyboard(_server_menu.selected_index)

    elif _mode == _MODE_SERVER_KEYBOARD:
        global _server_save_requested
        if _server_save_requested:
            _server_save_requested = False
            value = view_manager.keyboard.response or ""
            if _server_keyboard_field == 0:
                __save_server_username(value)
            else:
                __save_server_password(value)
            view_manager.keyboard.reset()
            __back_to_server_menu()
        elif not view_manager.keyboard.run():
            view_manager.keyboard.reset()
            __back_to_server_menu()

    elif _mode == _MODE_TOGGLE:
        if button == BUTTON_BACK:
            __back_to_menu()
        elif button == BUTTON_CENTER:
            new_state = not _toggle.state
            _toggle.state = new_state
            cfg = __config()[_current_setting]
            __save_state(cfg[1], cfg[2], new_state)
            __apply_toggle_setting(_current_setting, new_state)

    elif _mode == _MODE_CHOICE:
        if button == BUTTON_BACK:
            __back_to_menu()
        elif button in (BUTTON_UP, BUTTON_LEFT):
            _choice.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            _choice.scroll_down()
        elif button == BUTTON_CENTER:
            if _current_setting == STATE_THEME_COLOR:
                selected_color = __color_values()[_choice.state]
                __save_theme_color(selected_color)
                _view_manager.selected_color = selected_color
            elif _current_setting == STATE_EXIT_BUTTON:
                button_mapping = __exit_button_mapping()
                selected_button_value = list(button_mapping.keys())[_choice.state]
                __save_exit_button(selected_button_value)
                from picoware.system.system import System

                s = System()
                s.hard_reset()
            __back_to_menu()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _menu, _toggle, _choice, _time_menu, _date_picker, _server_menu

    if _choice is not None:
        del _choice
        _choice = None
    if _toggle is not None:
        del _toggle
        _toggle = None
    if _date_picker is not None:
        del _date_picker
        _date_picker = None
    if _time_menu is not None:
        del _time_menu
        _time_menu = None
    if _server_menu is not None:
        del _server_menu
        _server_menu = None
    if _menu is not None:
        del _menu
        _menu = None

    if view_manager.draw.use_lvgl:
        # restart with wifi disconnected...
        if view_manager._wifi is not None:
            from picoware.system.system import System

            sys = System()
            sys.hard_reset()
    else:
        if view_manager._wifi is None:
            from picoware.system.system import System

            sys = System()
            if sys.has_wifi:
                # wifi was disabled before so just restart...
                # we probably could just deinit lvgl and continue
                # but maybe thats something we'll try later...
                sys.hard_reset()

    view_manager.keyboard.reset()
    collect()
