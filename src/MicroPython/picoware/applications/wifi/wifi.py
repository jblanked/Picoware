_wifi = None
_wifi_index = 0


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.gui.menu import Menu

    global _wifi
    global _wifi_index
    if _wifi is None:
        _wifi = Menu(
            view_manager.draw,
            "WiFi",
            0,
            320,
            view_manager.get_foreground_color(),
            view_manager.get_background_color(),
            view_manager.get_selected_color(),
            view_manager.get_foreground_color(),
            2,
        )
        _wifi.add_item("Connect")
        _wifi.add_item("Scan")
        _wifi.add_item("Settings")
        _wifi.set_selected(_wifi_index)

        _wifi.draw()
    return True


def run(view_manager) -> None:
    """Run the app."""
    from picoware.system.view import View
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_CENTER,
        BUTTON_RIGHT,
    )

    global _wifi
    if not _wifi:
        return
    global _wifi_index

    input_manager = view_manager.input_manager
    button: int = input_manager.get_last_button()

    if button == BUTTON_UP:
        input_manager.reset(True)
        _wifi.scroll_up()
    elif button == BUTTON_DOWN:
        input_manager.reset(True)
        _wifi.scroll_down()
    elif button in (BUTTON_BACK, BUTTON_LEFT):
        _wifi_index = 0
        input_manager.reset(True)
        view_manager.back()
    elif button in (BUTTON_CENTER, BUTTON_RIGHT):
        input_manager.reset(True)
        _wifi_index = _wifi.get_selected_index()

        if _wifi_index == 0:
            from picoware.applications.wifi import connect

            view_manager.add(
                View("wifi_connect", connect.run, connect.start, connect.stop)
            )
            view_manager.switch_to("wifi_connect")
        elif _wifi_index == 1:
            from picoware.applications.wifi import scan

            view_manager.add(View("wifi_scan", scan.run, scan.start, scan.stop))
            view_manager.switch_to("wifi_scan")
        elif _wifi_index == 2:
            from picoware.applications.wifi import settings

            view_manager.add(
                View("wifi_settings", settings.run, settings.start, settings.stop)
            )
            view_manager.switch_to("wifi_settings")


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _wifi
    if _wifi is not None:
        del _wifi
        _wifi = None
    collect()
