_scan = None


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
        BUTTON_RIGHT,
    )

    global _scan
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


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _scan
    if _scan:
        del _scan
        _scan = None
    collect()
