_password_is_running = False
_password_save_requested = False
_back_hit = False
_keyboard_started = False


def __callback_save(result: str) -> None:
    """Callback for when the Password is saved"""

    global _password_is_running
    global _password_save_requested

    if not _password_is_running:
        return

    _password_save_requested = True


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.applications.wifi.utils import load_wifi_password

    global _password_is_running
    global _password_save_requested
    global _back_hit
    global _keyboard_started

    _password_is_running = True
    _password_save_requested = False
    _back_hit = False
    _keyboard_started = False

    keyboard = view_manager.keyboard

    if keyboard is None:
        print("No keyboard available")
        return False

    keyboard.set_save_callback(__callback_save)
    keyboard.response = load_wifi_password(view_manager)
    keyboard.run(force=True)

    return True


def run(view_manager) -> None:
    """Run the app."""
    keyboard = view_manager.keyboard
    if not keyboard:
        return

    from picoware.system.buttons import (
        BUTTON_BACK,
    )

    global _password_is_running
    global _password_save_requested
    global _back_hit
    global _keyboard_started

    if not _password_is_running:
        return

    input_manager = view_manager.input_manager
    button = input_manager.button

    if button == BUTTON_BACK:
        input_manager.reset()
        _back_hit = True
        _password_is_running = False
        keyboard.reset()
        view_manager.back()
        return

    if _password_save_requested:
        _password_save_requested = False
        password = keyboard.response
        from picoware.applications.wifi.utils import (
            save_wifi_password,
            save_wifi_settings,
            load_wifi_ssid,
        )

        if not save_wifi_password(view_manager.storage, password):
            print("Failed to save WiFi password")
        if not save_wifi_settings(
            view_manager.storage, load_wifi_ssid(view_manager), password
        ):
            print("Failed to save WiFi settings")
        keyboard.reset()
        _password_is_running = False
        view_manager.back()
        return

    if not _keyboard_started:
        keyboard.run(force=True)
        _keyboard_started = True
    else:
        if not keyboard.run():
            input_manager.reset()
            view_manager.back()


def stop(view_manager) -> None:
    """Stop the app."""
    from gc import collect

    global _password_is_running
    global _password_save_requested
    global _back_hit

    _password_is_running = False
    _password_save_requested = False
    _back_hit = False
    view_manager.keyboard.reset()

    collect()
