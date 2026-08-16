"""Settings - Configure device settings."""

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
STATE_OPENAI_API_KEY = const(8)  # keyboard input for OpenAI API key
STATE_DEEPSEEK_API_KEY = const(9)  # keyboard input for DeepSeek API key
STATE_USB_STREAM = const(10)  # toggle (enable/disable USB stream)
STATE_ANTHROPIC_API_KEY = const(11)  # keyboard input for Anthropic API key
STATE_GEMINI_API_KEY = const(12)  # keyboard input for Gemini API key
STATE_LOCAL_URL = const(13)  # keyboard input for Local URL
STATE_LOCAL_API_KEY = const(14)  # keyboard input for optional Local API key
STATE_XAI_API_KEY = const(15)  # keyboard input for xAI API key
STATE_SCREEN_BRIGHTNESS = const(16)  # choice (10 - 100)
STATE_MCP_INTEGRATIONS = const(17)  # keyboard input for integration IDs
STATE_MCP_GATEWAY_URL = const(18)  # keyboard input for integration gateway

# modes
_MODE_MENU = const(0)
_MODE_TOGGLE = const(1)
_MODE_CHOICE = const(2)
_MODE_TIME_MENU = const(3)
_MODE_DATE_PICKER = const(4)
_MODE_GMT_KEYBOARD = const(5)
_MODE_SERVER_MENU = const(6)
_MODE_SERVER_KEYBOARD = const(7)
_MODE_OPENAI_KEYBOARD = const(8)
_MODE_DEEPSEEK_KEYBOARD = const(9)
_MODE_ANTHROPIC_KEYBOARD = const(10)
_MODE_GEMINI_KEYBOARD = const(11)
_MODE_LOCAL_URL_KEYBOARD = const(12)
_MODE_LOCAL_API_KEYBOARD = const(13)
_MODE_XAI_KEYBOARD = const(14)
_MODE_MCP_INTEGRATIONS_KEYBOARD = const(15)
_MODE_MCP_GATEWAY_KEYBOARD = const(16)


_settings = None
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
_openai_save_requested = False
_deepseek_save_requested = False
_anthropic_save_requested = False
_gemini_save_requested = False
_local_url_save_requested = False
_local_api_save_requested = False
_xai_save_requested = False
_mcp_integrations_save_requested = False
_mcp_gateway_save_requested = False


def __color_values() -> list[int]:
    """Get the list of color values corresponding to the color names.

    Returns:
        list[int]: The color values matching the theme color names.
    """
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
    """Get the configuration tuple for the current setting.

    Returns:
        tuple: The (menu label, json key, default value) tuples.
    """
    # (menu label, json key, default value)
    return (
        ("Dark Mode", "dark_mode", True),
        (
            "Onscreen Keyboard",
            "onscreen_keyboard",
            True,
        ),
        ("Use LVGL", "lvgl_mode", False),
        ("Theme Color", "theme_color", None),
        ("Debug", "debug", False),
        ("Time", "time", None),
        ("Exit Button", "exit_button", None),
        ("Server Settings", "server_settings", None),
        ("OpenAI API Key", "openai_api_key", ""),
        ("DeepSeek API Key", "deepseek_api_key", ""),
        ("USB Stream", "usb_stream", False),
        ("Anthropic API Key", "anthropic_api_key", ""),
        ("Gemini API Key", "gemini_api_key", ""),
        ("Local URL", "local_url", "http://127.0.0.1:8080/v1/chat/completions"),
        ("Local API Key", "local_api_key", ""),
        ("xAI API Key", "xai_api_key", ""),
        ("Screen Brightness", "screen_brightness", 100),
        ("MCP Integrations / Servers", "mcp_integrations", ""),
        ("MCP Gateway URL", "mcp_gateway_url", ""),
    )


def __exit_button_mapping() -> dict[int, str]:
    """Get the mapping of button values to their names for the exit button setting.

    Returns:
        dict[int, str]: The button value to name mapping.
    """
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_ESCAPE,
    )

    return {
        BUTTON_BACK: "<-Back",
        BUTTON_ESCAPE: "Esc",
    }


def __save_server_username(value: str) -> bool:
    """Save the server username to storage.

    Args:
        value (str): The username to save.

    Returns:
        bool: True on success.
    """
    _current_settings = _settings.server_settings
    _current_settings["username"] = value
    _settings.server_settings = _current_settings
    return True


def __save_server_password(value: str) -> bool:
    """Save the server password to storage.

    Args:
        value (str): The password to save.

    Returns:
        bool: True on success.
    """
    _current_settings = _settings.server_settings
    _current_settings["password"] = value
    _settings.server_settings = _current_settings
    return True

def __apply_toggle_setting(index: int, state: bool) -> None:
    """Apply a toggle setting change to the view manager.

    Args:
        index (int): The setting index to apply.
        state (bool): The new toggle state.
    """
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
    elif index == STATE_USB_STREAM:
        if state:
            _view_manager.usb_video_stream.start()
        else:
            _view_manager.usb_video_stream.stop()


def __open_toggle(setting_index: int) -> None:
    """Open a Toggle sub-view for the given setting index.

    Args:
        setting_index (int): The setting index to toggle.
    """
    global _toggle, _mode, _current_setting
    from picoware.gui.toggle import Toggle
    from picoware.system.vector import Vector

    _current_setting = setting_index
    cfg = __config()[setting_index]
    current_state = _settings._settings[cfg[1]]

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
    current_color = _settings.theme_color
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
    current_button = _settings.exit_button
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


def __open_choice_brightness() -> None:
    """Open a Choice sub-view for the screen brightness setting."""
    global _choice, _mode, _current_setting
    from picoware.gui.choice import Choice
    from picoware.system.vector import Vector

    _current_setting = STATE_SCREEN_BRIGHTNESS
    _brightness_options = [str(i) for i in range(10, 101, 10)]
    current_brightness = _settings.screen_brightness
    try:
        initial_index = _brightness_options.index(str(current_brightness))
    except ValueError:
        initial_index = len(_brightness_options) - 1

    draw = _view_manager.draw
    draw.erase()
    if _choice is not None:
        del _choice
        _choice = None

    _choice = Choice(
        draw,
        Vector(0, 0),
        draw.size,
        "Screen Brightness",
        _brightness_options,
        initial_index,
        _view_manager.foreground_color,
        _view_manager.background_color,
    )
    _choice.draw()
    _mode = _MODE_CHOICE


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
    keyboard.response = str(_settings.gmt_offset)
    keyboard.set_save_callback(__gmt_save_callback)
    keyboard.input_manager.reset()
    keyboard.run(force=True)
    _gmt_save_requested = False
    _mode = _MODE_GMT_KEYBOARD


def __gmt_save_callback(result: str) -> None:
    """Callback triggered when the GMT offset keyboard is saved.

    Args:
        result (str): The saved keyboard value.
    """
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
    """Open the keyboard for entering the server username or password.

    Args:
        field (int): 0 for username, 1 for password.
    """
    global _mode, _server_save_requested, _server_keyboard_field

    _server_keyboard_field = field
    keyboard = _view_manager.keyboard
    keyboard.reset()
    if field == 0:
        keyboard.title = "Username"
        keyboard.response = _settings.server_settings.get("username", "")
    else:
        keyboard.title = "Password"
        keyboard.response = _settings.server_settings.get("password", "")
    keyboard.set_save_callback(__server_save_callback)
    keyboard.input_manager.reset()
    keyboard.run(force=True)
    _server_save_requested = False
    _mode = _MODE_SERVER_KEYBOARD


def __server_save_callback(result: str) -> None:
    """Callback triggered when the server keyboard is saved.

    Args:
        result (str): The saved keyboard value.
    """
    global _server_save_requested
    _server_save_requested = True


def __open_openai_keyboard() -> None:
    """Open the keyboard for entering the OpenAI API key."""
    global _mode, _openai_save_requested

    keyboard = _view_manager.keyboard
    keyboard.reset()
    keyboard.title = "OpenAI API Key"
    keyboard.response = _settings.openai_api_key
    keyboard.set_save_callback(__openai_save_callback)
    keyboard.input_manager.reset()
    keyboard.run(force=True)
    _openai_save_requested = False
    _mode = _MODE_OPENAI_KEYBOARD


def __openai_save_callback(result: str) -> None:
    """Callback triggered when the OpenAI API key keyboard is saved.

    Args:
        result (str): The saved keyboard value.
    """
    global _openai_save_requested
    _openai_save_requested = True


def __open_deepseek_keyboard() -> None:
    """Open the keyboard for entering the DeepSeek API key."""
    global _mode, _deepseek_save_requested

    keyboard = _view_manager.keyboard
    keyboard.reset()
    keyboard.title = "DeepSeek API Key"
    keyboard.response = _settings.deepseek_api_key
    keyboard.set_save_callback(__deepseek_save_callback)
    keyboard.input_manager.reset()
    keyboard.run(force=True)
    _deepseek_save_requested = False
    _mode = _MODE_DEEPSEEK_KEYBOARD


def __deepseek_save_callback(result: str) -> None:
    """Callback triggered when the DeepSeek API key keyboard is saved.

    Args:
        result (str): The saved keyboard value.
    """
    global _deepseek_save_requested
    _deepseek_save_requested = True

def __open_anthropic_keyboard() -> None:
    """Open the keyboard for entering the Anthropic API key."""
    global _mode, _anthropic_save_requested

    keyboard = _view_manager.keyboard
    keyboard.reset()
    keyboard.title = "Anthropic API Key"
    keyboard.response = _settings.anthropic_api_key
    keyboard.set_save_callback(__anthropic_save_callback)
    keyboard.input_manager.reset()
    keyboard.run(force=True)
    _anthropic_save_requested = False
    _mode = _MODE_ANTHROPIC_KEYBOARD

def __anthropic_save_callback(result: str) -> None:
    """Callback triggered when the Anthropic API key keyboard is saved.

    Args:
        result (str): The saved keyboard value.
    """
    global _anthropic_save_requested
    _anthropic_save_requested = True

def __open_gemini_keyboard() -> None:
    """Open the keyboard for entering the Gemini API key."""
    global _mode, _gemini_save_requested

    keyboard = _view_manager.keyboard
    keyboard.reset()
    keyboard.title = "Gemini API Key"
    keyboard.response = _settings.gemini_api_key
    keyboard.set_save_callback(__gemini_save_callback)
    keyboard.input_manager.reset()
    keyboard.run(force=True)
    _gemini_save_requested = False
    _mode = _MODE_GEMINI_KEYBOARD

def __gemini_save_callback(result: str) -> None:
    """Callback triggered when the Gemini API key keyboard is saved.

    Args:
        result (str): The saved keyboard value.
    """
    global _gemini_save_requested
    _gemini_save_requested = True

def __open_local_url_keyboard() -> None:
    """Open the keyboard for entering the Local URL."""
    global _mode, _local_url_save_requested

    keyboard = _view_manager.keyboard
    keyboard.reset()
    keyboard.title = "Local URL"
    keyboard.response = _settings.local_url
    keyboard.set_save_callback(__local_url_save_callback)
    keyboard.input_manager.reset()
    keyboard.run(force=True)
    _local_url_save_requested = False
    _mode = _MODE_LOCAL_URL_KEYBOARD

def __local_url_save_callback(result: str) -> None:
    """Callback triggered when the Local URL keyboard is saved.

    Args:
        result (str): The saved keyboard value.
    """
    global _local_url_save_requested
    _local_url_save_requested = True

def __open_local_api_keyboard() -> None:
    """Open the keyboard for entering the optional Local API key."""
    global _mode, _local_api_save_requested

    keyboard = _view_manager.keyboard
    keyboard.reset()
    keyboard.title = "Local API Key"
    keyboard.response = _settings.local_api_key
    keyboard.set_save_callback(__local_api_save_callback)
    keyboard.input_manager.reset()
    keyboard.run(force=True)
    _local_api_save_requested = False
    _mode = _MODE_LOCAL_API_KEYBOARD

def __local_api_save_callback(result: str) -> None:
    """Record that the optional Local API key should be saved."""
    global _local_api_save_requested
    _local_api_save_requested = True

def __open_mcp_integrations_keyboard() -> None:
    """Open the keyboard for configured MCP integration IDs."""
    global _mode, _mcp_integrations_save_requested

    keyboard = _view_manager.keyboard
    keyboard.reset()
    keyboard.title = "IDs or server:Label|URL"
    keyboard.response = _settings.mcp_integrations
    keyboard.set_save_callback(__mcp_integrations_save_callback)
    keyboard.input_manager.reset()
    keyboard.run(force=True)
    _mcp_integrations_save_requested = False
    _mode = _MODE_MCP_INTEGRATIONS_KEYBOARD

def __mcp_integrations_save_callback(result: str) -> None:
    """Record that MCP integration IDs should be saved."""
    global _mcp_integrations_save_requested
    _mcp_integrations_save_requested = True

def __open_mcp_gateway_keyboard() -> None:
    """Open the keyboard for the optional MCP gateway URL."""
    global _mode, _mcp_gateway_save_requested

    keyboard = _view_manager.keyboard
    keyboard.reset()
    keyboard.title = "MCP Gateway URL"
    keyboard.response = _settings.mcp_gateway_url
    keyboard.set_save_callback(__mcp_gateway_save_callback)
    keyboard.input_manager.reset()
    keyboard.run(force=True)
    _mcp_gateway_save_requested = False
    _mode = _MODE_MCP_GATEWAY_KEYBOARD

def __mcp_gateway_save_callback(result: str) -> None:
    """Record that the MCP gateway URL should be saved."""
    global _mcp_gateway_save_requested
    _mcp_gateway_save_requested = True

def __open_xai_keyboard() -> None:
    """Open the keyboard for entering the xAI API key."""
    global _mode, _xai_save_requested

    keyboard = _view_manager.keyboard
    keyboard.reset()
    keyboard.title = "xAI API Key"
    keyboard.response = _settings.xai_api_key
    keyboard.set_save_callback(__xai_save_callback)
    keyboard.input_manager.reset()
    keyboard.run(force=True)
    _xai_save_requested = False
    _mode = _MODE_XAI_KEYBOARD

def __xai_save_callback(result: str) -> None:
    """Callback triggered when the xAI API key keyboard is saved.

    Args:
        result (str): The saved keyboard value.
    """
    global _xai_save_requested
    _xai_save_requested = True

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
    """Start the app and build the settings menu.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.

    Returns:
        bool: True if the app started, False if no SD card is present.
    """
    if not view_manager.has_sd_card:
        print("Settings app requires an SD card")
        return False

    from picoware.gui.menu import Menu
    from picoware.system.settings import Settings

    global _settings, _menu, _view_manager, _mode, _time_menu, _date_picker, _server_menu, _gmt_save_requested, _server_save_requested, _server_keyboard_field, _openai_save_requested, _deepseek_save_requested, _anthropic_save_requested, _gemini_save_requested, _local_url_save_requested, _local_api_save_requested, _xai_save_requested, _mcp_integrations_save_requested, _mcp_gateway_save_requested

    _view_manager = view_manager
    _mode = _MODE_MENU
    _gmt_save_requested = False
    _server_save_requested = False
    _server_keyboard_field = 0
    _openai_save_requested = False
    _deepseek_save_requested = False
    _anthropic_save_requested = False
    _gemini_save_requested = False
    _local_url_save_requested = False
    _local_api_save_requested = False
    _xai_save_requested = False
    _mcp_integrations_save_requested = False
    _mcp_gateway_save_requested = False

    if _settings is not None:
        del _settings
        _settings = None
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

    _settings = Settings(view_manager.storage)

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
    """Run the app and handle setting input.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
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
            elif selected == STATE_OPENAI_API_KEY:
                __open_openai_keyboard()
            elif selected == STATE_DEEPSEEK_API_KEY:
                __open_deepseek_keyboard()
            elif selected == STATE_ANTHROPIC_API_KEY:
                __open_anthropic_keyboard()
            elif selected == STATE_GEMINI_API_KEY:
                __open_gemini_keyboard()
            elif selected == STATE_LOCAL_URL:
                __open_local_url_keyboard()
            elif selected == STATE_LOCAL_API_KEY:
                __open_local_api_keyboard()
            elif selected == STATE_MCP_INTEGRATIONS:
                __open_mcp_integrations_keyboard()
            elif selected == STATE_MCP_GATEWAY_URL:
                __open_mcp_gateway_keyboard()
            elif selected == STATE_XAI_API_KEY:
                __open_xai_keyboard()
            elif selected == STATE_SCREEN_BRIGHTNESS:
                __open_choice_brightness()
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
            _settings.gmt_offset = offset
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

    elif _mode == _MODE_OPENAI_KEYBOARD:
        global _openai_save_requested
        if _openai_save_requested:
            _openai_save_requested = False
            _settings.openai_api_key = view_manager.keyboard.response or ""
            view_manager.keyboard.reset()
            __back_to_menu()
        elif not view_manager.keyboard.run():
            view_manager.keyboard.reset()
            __back_to_menu()

    elif _mode == _MODE_DEEPSEEK_KEYBOARD:
        global _deepseek_save_requested
        if _deepseek_save_requested:
            _deepseek_save_requested = False
            _settings.deepseek_api_key = view_manager.keyboard.response or ""
            view_manager.keyboard.reset()
            __back_to_menu()
        elif not view_manager.keyboard.run():
            view_manager.keyboard.reset()
            __back_to_menu()
    
    elif _mode == _MODE_ANTHROPIC_KEYBOARD:
        global _anthropic_save_requested
        if _anthropic_save_requested:
            _anthropic_save_requested = False
            _settings.anthropic_api_key = view_manager.keyboard.response or ""
            view_manager.keyboard.reset()
            __back_to_menu()
        elif not view_manager.keyboard.run():
            view_manager.keyboard.reset()
            __back_to_menu()
    
    elif _mode == _MODE_GEMINI_KEYBOARD:
        global _gemini_save_requested
        if _gemini_save_requested:
            _gemini_save_requested = False
            _settings.gemini_api_key = view_manager.keyboard.response or ""
            view_manager.keyboard.reset()
            __back_to_menu()
        elif not view_manager.keyboard.run():
            view_manager.keyboard.reset()
            __back_to_menu()

    elif _mode == _MODE_LOCAL_URL_KEYBOARD:
        global _local_url_save_requested
        if _local_url_save_requested:
            _local_url_save_requested = False
            _settings.local_url = view_manager.keyboard.response or ""
            view_manager.keyboard.reset()
            __back_to_menu()
        elif not view_manager.keyboard.run():
            view_manager.keyboard.reset()
            __back_to_menu()

    elif _mode == _MODE_LOCAL_API_KEYBOARD:
        global _local_api_save_requested
        if _local_api_save_requested:
            _local_api_save_requested = False
            _settings.local_api_key = view_manager.keyboard.response or ""
            view_manager.keyboard.reset()
            __back_to_menu()
        elif not view_manager.keyboard.run():
            view_manager.keyboard.reset()
            __back_to_menu()

    elif _mode == _MODE_XAI_KEYBOARD:
        global _xai_save_requested
        if _xai_save_requested:
            _xai_save_requested = False
            _settings.xai_api_key = view_manager.keyboard.response or ""
            view_manager.keyboard.reset()
            __back_to_menu()
        elif not view_manager.keyboard.run():
            view_manager.keyboard.reset()
            __back_to_menu()

    elif _mode == _MODE_MCP_INTEGRATIONS_KEYBOARD:
        global _mcp_integrations_save_requested
        if _mcp_integrations_save_requested:
            _mcp_integrations_save_requested = False
            _settings.mcp_integrations = view_manager.keyboard.response or ""
            view_manager.keyboard.reset()
            __back_to_menu()
        elif not view_manager.keyboard.run():
            view_manager.keyboard.reset()
            __back_to_menu()

    elif _mode == _MODE_MCP_GATEWAY_KEYBOARD:
        global _mcp_gateway_save_requested
        if _mcp_gateway_save_requested:
            _mcp_gateway_save_requested = False
            _settings.mcp_gateway_url = view_manager.keyboard.response or ""
            view_manager.keyboard.reset()
            __back_to_menu()
        elif not view_manager.keyboard.run():
            view_manager.keyboard.reset()
            __back_to_menu()

    elif _mode == _MODE_TOGGLE:
        if button == BUTTON_BACK:
            __back_to_menu()
        elif button == BUTTON_CENTER:
            new_state = not _toggle.state
            _toggle.state = new_state
            cfg = __config()[_current_setting]
            _settings._settings[cfg[1]] = new_state
            _settings.__save_settings()
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
                _settings.theme_color = selected_color
                _view_manager.selected_color = selected_color
            elif _current_setting == STATE_EXIT_BUTTON:
                button_mapping = __exit_button_mapping()
                selected_button_value = list(button_mapping.keys())[_choice.state]
                _settings.exit_button = selected_button_value
                from picoware.system.system import System

                s = System()
                s.hard_reset()
            elif _current_setting == STATE_SCREEN_BRIGHTNESS:
                selected_value = int(_choice.options[_choice.state])
                _settings.screen_brightness = selected_value
                _view_manager.draw.set_brightness(selected_value)
            __back_to_menu()


def stop(view_manager) -> None:
    """Stop the app and clean up.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
    from gc import collect

    global _settings, _menu, _toggle, _choice, _time_menu, _date_picker, _server_menu

    if _settings is not None:
        del _settings
        _settings = None
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
