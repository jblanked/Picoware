_ssid_is_running = False
_ssid_save_requested = False
_back_hit = False
_keyboard_started = False


def __callback_save(result: str) -> None:
    """Callback for when the SSID is saved"""

    global _ssid_is_running
    global _ssid_save_requested

    if not _ssid_is_running:
        return

    _ssid_save_requested = True


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.applications.wifi.utils import load_wifi_ssid

    global _ssid_is_running
    global _ssid_save_requested
    global _back_hit
    global _keyboard_started

    _ssid_is_running = True
    _ssid_save_requested = False
    _back_hit = False
    _keyboard_started = False

    keyboard = view_manager.keyboard

    if keyboard is None:
        view_manager.alert("No keyboard available")
        return False

    keyboard.set_save_callback(__callback_save)
    keyboard.response = load_wifi_ssid(view_manager)
    keyboard.title = "Enter WiFi SSID"

    return keyboard.run(force=True)


def run(view_manager) -> None:
    """Run the app."""
    from picoware.system.buttons import (
        BUTTON_BACK,
    )

    global _ssid_is_running
    global _ssid_save_requested
    global _back_hit
    global _keyboard_started

    if not _ssid_is_running:
        return

    input_manager = view_manager.input_manager
    button = input_manager.button

    if button == BUTTON_BACK:
        input_manager.reset()
        _back_hit = True
        _ssid_is_running = False
        view_manager.back()
        return

    keyboard = view_manager.keyboard
    if not keyboard:
        return

    if _ssid_save_requested:
        _ssid_save_requested = False
        ssid = keyboard.response
        from picoware.applications.wifi.utils import (
            save_wifi_ssid,
            load_wifi_password,
            save_wifi_settings,
        )

        if not save_wifi_ssid(view_manager.storage, ssid):
            view_manager.alert("Failed to save WiFi SSID")
        if not save_wifi_settings(
            view_manager.storage, ssid, load_wifi_password(view_manager)
        ):
            view_manager.alert("Failed to save WiFi settings")
        keyboard.reset()
        _ssid_is_running = False
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

    global _ssid_is_running
    global _ssid_save_requested
    global _back_hit

    _ssid_is_running = False
    _ssid_save_requested = False
    _back_hit = False
    view_manager.keyboard.reset()

    collect()
