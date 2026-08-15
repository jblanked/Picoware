"""WiFi Password - Enter a WiFi password."""

_password_is_running = False
_password_save_requested = False
_back_hit = False
_keyboard_started = False


def __callback_save(result: str) -> None:
    """Callback for when the Password is saved.

    Args:
        result (str): The saved password value.
    """

    global _password_is_running
    global _password_save_requested

    if not _password_is_running:
        return

    _password_save_requested = True


def start(view_manager) -> bool:
    """Start the app and open the password keyboard.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.

    Returns:
        bool: True if the keyboard started, False on failure.
    """
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

    keyboard.input_manager.reset()
    keyboard.set_save_callback(__callback_save)
    keyboard.response = load_wifi_password(view_manager)
    keyboard.title = "Enter WiFi Password"

    return keyboard.run(force=True)


def run(view_manager) -> None:
    """Run the app and handle keyboard input.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
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

    button = view_manager.button

    if button == BUTTON_BACK:
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
        )

        if not save_wifi_password(view_manager.storage, password):
            view_manager.alert("Failed to save WiFi password")
        keyboard.reset()
        _password_is_running = False
        view_manager.back()
        return

    if not _keyboard_started:
        keyboard.run(force=True)
        _keyboard_started = True
    else:
        if not keyboard.run():
            view_manager.back()


def stop(view_manager) -> None:
    """Stop the app and reset state.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
    from gc import collect

    global _password_is_running
    global _password_save_requested
    global _back_hit

    _password_is_running = False
    _password_save_requested = False
    _back_hit = False
    view_manager.keyboard.reset()

    collect()
