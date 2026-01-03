from micropython import const
from picoware.system.colors import TFT_BLACK, TFT_WHITE

STATE_DARK_MODE = const(0)
STATE_ONSCREEN_KEYBOARD = const(1)

_toggle_list = None
_view_manager = None


def __callback(index: int, state: bool) -> None:
    """Callback for when the toggle state changes."""

    if index == STATE_DARK_MODE:
        # Save the state to flash
        __save_state("picoware/settings/dark_mode.json", "dark_mode", state)

        if _toggle_list.current_state:
            _view_manager.background_color = TFT_BLACK
            _view_manager.foreground_color = TFT_WHITE
        else:
            _view_manager.background_color = TFT_WHITE
            _view_manager.foreground_color = TFT_BLACK
    elif index == STATE_ONSCREEN_KEYBOARD:
        # Save the state to flash
        __save_state(
            "picoware/settings/onscreen_keyboard.json", "onscreen_keyboard", state
        )
        _view_manager.keyboard.show_keyboard = state


def __load_state(filename: str, key: str, default: bool = False) -> bool:
    """Load the dark mode state from storage."""
    data = _view_manager.storage.read(filename)
    if data is not None:
        try:
            import ujson

            obj = ujson.loads(data)
            if key in obj:
                return bool(obj[key])
        except Exception:
            pass
    return default


def __save_state(filename: str, key: str, state: bool) -> None:
    """Save the dark mode state to storage."""
    import ujson

    obj = {key: state}
    data = ujson.dumps(obj)
    _view_manager.storage.write(filename, data)


def start(view_manager) -> bool:
    """Start the app"""
    if not view_manager.has_sd_card:
        print("Settings app requires an SD card")
        return False

    from picoware.gui.toggle_list import ToggleList

    global _toggle_list, _storage, _view_manager

    _view_manager = view_manager

    if _toggle_list is not None:
        del _toggle_list
        _toggle_list = None

    _toggle_list = ToggleList(
        view_manager,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
        view_manager.foreground_color,
        2,
        __callback,
    )

    _storage = view_manager.storage

    # create settings directory if it doesn't exist
    _storage.mkdir("picoware/settings")

    # get/add the saved dark mode state (set to True by default)
    _toggle_list.add_toggle(
        "Dark Mode?",
        __load_state("picoware/settings/dark_mode.json", "dark_mode", True),
    )

    # get/add the on-screen keyboard state (set to True by default)
    _toggle_list.add_toggle(
        "Show on-screen keyboard?",
        __load_state(
            "picoware/settings/onscreen_keyboard.json", "onscreen_keyboard", True
        ),
    )

    return True


def run(view_manager) -> None:
    """Run the app"""

    if not _toggle_list.run():
        # user wants to exit the app
        view_manager.back()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _toggle_list

    if _toggle_list:
        del _toggle_list
        _toggle_list = None

    collect()
