_bluetooth = None
_bluetooth_index = 0


def start(view_manager) -> bool:
    """Start the app"""
    if not view_manager.has_wifi:
        view_manager.alert("Bluetooth not available....")
        return False

    from picoware.gui.menu import Menu

    # create bluetooth folder
    view_manager.storage.mkdir("picoware/bluetooth")

    global _bluetooth

    if _bluetooth is None:
        _bluetooth = Menu(
            view_manager.draw,
            "Bluetooth",
            0,
            view_manager.draw.size.y,
            view_manager.foreground_color,
            view_manager.background_color,
            view_manager.selected_color,
            view_manager.foreground_color,
            2,
        )
        _bluetooth.add_item("Advertise")
        _bluetooth.add_item("Pair")
        _bluetooth.add_item("Scan")
        _bluetooth.set_selected(_bluetooth_index)

        _bluetooth.draw()
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

    if not _bluetooth:
        return

    global _bluetooth_index

    input_manager = view_manager.input_manager
    button: int = input_manager.button

    if button in (BUTTON_UP, BUTTON_LEFT):
        input_manager.reset()
        _bluetooth.scroll_up()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        input_manager.reset()
        _bluetooth.scroll_down()
    elif button == BUTTON_BACK:
        _bluetooth_index = 0
        input_manager.reset()
        view_manager.back()
    elif button == BUTTON_CENTER:
        input_manager.reset()
        _bluetooth_index = _bluetooth.selected_index
        if _bluetooth_index == 0:
            from picoware.applications.bluetooth import advertise

            view_manager.add(
                View(
                    "bluetooth_advertise",
                    advertise.run,
                    advertise.start,
                    advertise.stop,
                )
            )
            view_manager.switch_to("bluetooth_advertise")
        elif _bluetooth_index == 1:
            from picoware.applications.bluetooth import pair

            view_manager.add(
                View(
                    "bluetooth_pair",
                    pair.run,
                    pair.start,
                    pair.stop,
                )
            )
            view_manager.switch_to("bluetooth_pair")
        elif _bluetooth_index == 2:
            from picoware.applications.bluetooth import scan

            view_manager.add(
                View(
                    "bluetooth_scan",
                    scan.run,
                    scan.start,
                    scan.stop,
                )
            )
            view_manager.switch_to("bluetooth_scan")


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _bluetooth
    if _bluetooth is not None:
        del _bluetooth
        _bluetooth = None
    collect()
