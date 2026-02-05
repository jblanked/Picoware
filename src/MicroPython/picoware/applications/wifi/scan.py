from picoware.system.buttons import (
    BUTTON_BACK,
    BUTTON_UP,
    BUTTON_DOWN,
    BUTTON_LEFT,
    BUTTON_RIGHT,
    BUTTON_CENTER,
)

_scan = None


def __save_ssid(view_manager) -> bool:
    """Save the selected SSID"""
    global _scan

    if _scan is None:
        return False

    selected_ssid: str = _scan.current_item
    ssid_name = selected_ssid.split(" (")[0]

    from picoware.applications.wifi.utils import save_wifi_ssid

    if not save_wifi_ssid(view_manager.storage, ssid_name):
        # try one last time
        return save_wifi_ssid(view_manager.storage, ssid_name)
    return True


def __should_save_choice(view_manager) -> bool:
    """Choose whether to save the selected SSID"""
    from picoware.gui.choice import Choice
    from picoware.system.vector import Vector

    choice = Choice(
        view_manager.draw,
        Vector(0, 0),
        view_manager.draw.size,
        f"Save SSID '{_scan.current_item.split(' (')[0]}'?",
        ["No", "Yes"],
        0,
        view_manager.foreground_color,
        view_manager.background_color,
    )
    choice.draw()
    choice.open()

    input_manager = view_manager.input_manager

    while True:
        _button = input_manager.button
        if _button in (BUTTON_LEFT, BUTTON_UP):
            input_manager.reset()
            choice.scroll_up()
        elif _button in (BUTTON_RIGHT, BUTTON_DOWN):
            input_manager.reset()
            choice.scroll_down()
        elif _button == BUTTON_CENTER:
            input_manager.reset()
            if choice.is_open():
                choice.close()

            _state = choice.state
            del choice
            choice = None
            if _state == 1:
                return True
            view_manager.draw.clear()
            _scan.draw()
            return False
        elif _button == BUTTON_BACK:
            input_manager.reset()
            del choice
            choice = None
            view_manager.draw.clear()
            _scan.draw()
            return False


def __switch_to_password_view(view_manager) -> None:
    """Switch to password view"""
    from picoware.applications.wifi import password
    from picoware.system.view import View

    view_manager.add(
        View(
            "wifi_password",
            password.run,
            password.start,
            password.stop,
        )
    )
    view_manager.switch_to("wifi_password")


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.gui.menu import Menu

    global _scan

    if _scan is None:
        wifi = view_manager.wifi

        if wifi is None:
            return False

        results = wifi.scan()

        _scan = Menu(
            view_manager.draw,
            "Scan",
            0,
            view_manager.draw.size.y,
            view_manager.foreground_color,
            view_manager.background_color,
            view_manager.selected_color,
            view_manager.foreground_color,
            2,
        )

        ssids: list[str] = []

        for ssid, bssid, channel, rssi, authmode, hidden in results:
            _ssid = ssid.decode("utf-8")
            if len(_ssid) == 0:
                _ssid = "<hidden>"
            if _ssid not in ssids:
                ssids.append(_ssid)
                _scan.add_item(f"{_ssid} ({rssi}dB)")

        _scan.set_selected(0)

        _scan.draw()
    return True


def run(view_manager) -> None:
    """Run the app"""
    if not _scan:
        return

    input_manager = view_manager.input_manager
    button: int = input_manager.button

    if button in (BUTTON_UP, BUTTON_LEFT):
        input_manager.reset()
        _scan.scroll_up()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        input_manager.reset()
        _scan.scroll_down()
    elif button == BUTTON_BACK:
        input_manager.reset()
        view_manager.back()
    elif button == BUTTON_CENTER:
        input_manager.reset()
        if __should_save_choice(view_manager):
            if not __save_ssid(view_manager):
                view_manager.alert("Failed to save SSID!", True)
                return
            __switch_to_password_view(view_manager)


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _scan
    if _scan:
        del _scan
        _scan = None
    collect()
