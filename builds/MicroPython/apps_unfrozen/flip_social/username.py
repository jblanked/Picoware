# picoware/apps/flip_social/username.py

_flip_social_user_is_running: bool = False
_flip_social_user_save_requested: bool = False
_flip_social_user_save_verified: bool = False
_flip_social_user_keyboard_ran: bool = False


def __flip_social_util_get_username(view_manager) -> str:
    """Get the username from storage, or return empty string"""
    storage = view_manager.get_storage()
    data: str = storage.read("picoware/flip_social/username.json")

    if data is not None:
        try:
            from ujson import loads

            obj: dict = loads(data)
            if "username" in obj:
                return obj["username"]
        except Exception:
            pass

    return ""


def __flip_social_user_callback(response: str) -> None:
    """Callback for when the user is done entering their username"""
    global _flip_social_user_save_requested

    _flip_social_user_save_requested = True


def __flip_social_user_start(view_manager) -> bool:
    """Start the user view"""
    keyboard = view_manager.get_keyboard()
    if not keyboard:
        return False

    global _flip_social_user_is_running, _flip_social_user_save_requested, _flip_social_user_save_verified, _flip_social_user_keyboard_ran

    # reset flags
    _flip_social_user_is_running = True
    _flip_social_user_save_requested = False
    _flip_social_user_save_verified = False
    _flip_social_user_keyboard_ran = False

    # Set up save callback that just sets a flag instead of immediately calling back()
    keyboard.on_save_callback = __flip_social_user_callback

    # load the ssid from flash
    keyboard.set_response(__flip_social_util_get_username(view_manager))

    keyboard.run(True, True)
    keyboard.run(True, True)

    return True


def __flip_social_user_run(view_manager) -> None:
    """Run the user view"""
    from picoware.system.buttons import BUTTON_BACK

    global _flip_social_user_is_running, _flip_social_user_save_requested, _flip_social_user_save_verified, _flip_social_user_keyboard_ran

    if not _flip_social_user_is_running:
        return

    keyboard = view_manager.get_keyboard()
    if not keyboard:
        _flip_social_user_is_running = False
        return

    input_manager = view_manager.get_input_manager()
    input_button = input_manager.button

    if input_button == BUTTON_BACK:
        input_manager.reset()
        _flip_social_user_is_running = False
        _flip_social_user_save_requested = False
        _flip_social_user_save_verified = False  # don't save
        view_manager.back()
        return

    if _flip_social_user_save_requested:
        input_manager.reset()
        _flip_social_user_save_requested = False
        _flip_social_user_is_running = False
        _flip_social_user_save_verified = True  # save
        view_manager.back()
        return

    if not _flip_social_user_keyboard_ran:
        keyboard.run(True, True)
        _flip_social_user_keyboard_ran = True
    else:
        keyboard.run(True, False)


def __flip_social_user_stop(view_manager) -> None:
    """Stop the user view"""
    from gc import collect

    global _flip_social_user_is_running, _flip_social_user_save_requested, _flip_social_user_save_verified, _flip_social_user_keyboard_ran

    keyboard = view_manager.get_keyboard()
    if keyboard:
        # if we need to save, do it now instead of in the callback
        if _flip_social_user_save_verified:
            storage = view_manager.get_storage()
            username = view_manager.get_keyboard().get_response()
            try:
                from ujson import dumps

                obj = {"username": username}
                storage.write("picoware/flip_social/username.json", dumps(obj))
            except Exception:
                pass

        keyboard.reset()

    # reset flags
    _flip_social_user_is_running = False
    _flip_social_user_save_requested = False
    _flip_social_user_save_verified = False
    _flip_social_user_keyboard_ran = False

    collect()
