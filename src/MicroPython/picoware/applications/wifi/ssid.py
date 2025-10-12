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

    keyboard = view_manager.get_keyboard()

    if keyboard is None:
        print("No keyboard available")
        return False

    keyboard.set_save_callback(__callback_save)
    keyboard.set_response(load_wifi_ssid(view_manager))
    keyboard.run(force=True)

    return True


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
    button = input_manager.get_last_button()

    if button == BUTTON_BACK:
        input_manager.reset()
        _back_hit = True
        _ssid_is_running = False
        view_manager.back()
        return

    keyboard = view_manager.get_keyboard()
    if not keyboard:
        return

    if _ssid_save_requested:
        _ssid_save_requested = False
        ssid = keyboard.get_response()
        from picoware.applications.wifi.utils import save_wifi_ssid

        if not save_wifi_ssid(view_manager.get_storage(), ssid):
            print("Failed to save SSID")
        keyboard.reset()
        _ssid_is_running = False
        view_manager.back()
        return

    if not _keyboard_started:
        keyboard.run(force=True)
        _keyboard_started = True
    else:
        keyboard.run()


def stop(view_manager) -> None:
    """Stop the app."""
    from gc import collect

    global _ssid_is_running
    global _ssid_save_requested
    global _back_hit

    _ssid_is_running = False
    _ssid_save_requested = False
    _back_hit = False

    collect()
