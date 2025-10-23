_scan = None


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.gui.menu import Menu

    global _scan
    if _scan is None:
        wifi = view_manager.get_wifi()

        if wifi is None:
            return False

        results = wifi.scan()

        _scan = Menu(
            view_manager.draw,
            "Scan",
            0,
            320,
            view_manager.get_foreground_color(),
            view_manager.get_background_color(),
            view_manager.get_selected_color(),
            view_manager.get_foreground_color(),
            2,
        )

        for ssid, bssid, channel, rssi, authmode, hidden in results:
            _ssid = ssid.decode("utf-8")
            if len(_ssid) == 0:
                _ssid = "<hidden>"
            _scan.add_item(f"{_ssid} ({rssi}dB)")

        _scan.set_selected(0)

        _scan.draw()
    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
    )

    global _scan
    if not _scan:
        return

    input_manager = view_manager.input_manager
    button: int = input_manager.get_last_button()

    if button == BUTTON_UP:
        input_manager.reset()
        _scan.scroll_up()
    elif button == BUTTON_DOWN:
        input_manager.reset()
        _scan.scroll_down()
    elif button in (BUTTON_BACK, BUTTON_LEFT):
        input_manager.reset()
        view_manager.back()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _scan
    if _scan:
        del _scan
        _scan = None
    collect()
