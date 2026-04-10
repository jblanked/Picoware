# picoware/apps/games/free_roam/password.py

_free_roam_password_is_running: bool = False
_free_roam_password_save_requested: bool = False
_free_roam_password_save_verified: bool = False
_free_roam_password_keyboard_ran: bool = False


def __free_roam_util_get_password(view_manager) -> str:
    """Get the password from storage, or return empty string"""
    storage = view_manager.storage
    data: str = storage.read("picoware/flip_social/password.json")

    if data is not None:
        try:
            from ujson import loads

            obj: dict = loads(data)
            if "password" in obj:
                return obj["password"]
        except Exception:
            pass

    return ""


def __free_roam_password_callback(response: str) -> None:
    """Callback for when the user is done entering their password"""
    global _free_roam_password_save_requested

    _free_roam_password_save_requested = True


def __free_roam_password_start(view_manager) -> bool:
    """Start the password view"""
    keyboard = view_manager.keyboard
    if not keyboard:
        return False

    global _free_roam_password_is_running, _free_roam_password_save_requested, _free_roam_password_save_verified, _free_roam_password_keyboard_ran

    # reset flags
    _free_roam_password_is_running = True
    _free_roam_password_save_requested = False
    _free_roam_password_save_verified = False
    _free_roam_password_keyboard_ran = False

    keyboard.input_manager.reset()

    # Set up save callback that just sets a flag instead of immediately calling back()
    keyboard.on_save_callback = __free_roam_password_callback

    # load the password from flash
    keyboard.response = __free_roam_util_get_password(view_manager)

    keyboard.run(True, True)
    keyboard.run(True, True)

    return True


def __free_roam_password_run(view_manager) -> None:
    """Run the password view"""
    from picoware.system.buttons import BUTTON_BACK

    global _free_roam_password_is_running, _free_roam_password_save_requested, _free_roam_password_save_verified, _free_roam_password_keyboard_ran

    if not _free_roam_password_is_running:
        return

    keyboard = view_manager.keyboard
    if not keyboard:
        _free_roam_password_is_running = False
        return

    input_manager = view_manager.input_manager
    input_button = input_manager.button

    if input_button == BUTTON_BACK:
        input_manager.reset()
        _free_roam_password_is_running = False
        _free_roam_password_save_requested = False
        _free_roam_password_save_verified = False  # don't save
        view_manager.back()
        return

    if _free_roam_password_save_requested:
        input_manager.reset()
        _free_roam_password_save_requested = False
        _free_roam_password_is_running = False
        _free_roam_password_save_verified = True  # save
        view_manager.back()
        return

    if not _free_roam_password_keyboard_ran:
        keyboard.run(True, True)
        _free_roam_password_keyboard_ran = True
    else:
        keyboard.run(True, False)


def __free_roam_password_stop(view_manager) -> None:
    """Stop the password view"""
    from gc import collect

    global _free_roam_password_is_running, _free_roam_password_save_requested, _free_roam_password_save_verified, _free_roam_password_keyboard_ran

    keyboard = view_manager.keyboard
    if keyboard:
        # if we need to save, do it now instead of in the callback
        if _free_roam_password_save_verified:
            storage = view_manager.storage
            password = view_manager.keyboard.response
            try:
                from ujson import dumps

                obj = {"password": password}
                storage.write("picoware/flip_social/password.json", dumps(obj))
            except Exception:
                pass

        keyboard.reset()

    # reset flags
    _free_roam_password_is_running = False
    _free_roam_password_save_requested = False
    _free_roam_password_save_verified = False
    _free_roam_password_keyboard_ran = False

    collect()
