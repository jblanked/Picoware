_menu = None
_bluetooth = None
_loading = None
_addresses = []


def __alert(view_manager, message: str, back: bool = True) -> None:
    """Show an alert"""

    from picoware.gui.alert import Alert
    from picoware.system.buttons import BUTTON_BACK

    draw = view_manager.draw
    draw.clear()
    _alert = Alert(
        draw,
        message,
        view_manager.foreground_color,
        view_manager.background_color,
    )
    _alert.draw("Alert")

    # Wait for user to acknowledge
    inp = view_manager.input_manager
    while True:
        button = inp.button
        if button == BUTTON_BACK:
            inp.reset()
            break

    if back:
        view_manager.back()


def bluetooth_callback(event, data):
    """Bluetooth callback function for scan results"""
    if event == 5:  # _IRQ_SCAN_RESULT
        # Handle scan result
        addr_type, addr, adv_type, rssi, adv_data = data

        # Format the address
        addr_str = ":".join("{:02X}".format(b) for b in addr)

        # Skip if already seen
        if addr_str in _addresses:
            return

        _addresses.append(addr_str)

        # Try to decode the device name from advertising data
        name = ""
        if _bluetooth is not None:
            name = _bluetooth.decode_name(adv_data)

        # Create a display string with name if available
        if name:
            display_str = f"{name} ({rssi}dB)"
        else:
            # Show shortened address if no name
            display_str = f"{addr_str} ({rssi}dB)"

        # Add the device to the menu
        if _menu is not None:
            _menu.add_item(display_str)
    elif event == 6:  # _IRQ_SCAN_DONE
        # Scan complete
        _addresses.clear()


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.gui.loading import Loading
    from picoware.gui.menu import Menu

    global _menu
    global _bluetooth, _loading

    if _menu is not None:
        del _menu
        _menu = None
    if _bluetooth is not None:
        del _bluetooth
        _bluetooth = None
    if _loading is not None:
        del _loading
        _loading = None

    bg = view_manager.background_color
    fg = view_manager.foreground_color
    sel = view_manager.selected_color

    _menu = Menu(
        view_manager.draw,
        "BLE Scan",
        0,
        view_manager.draw.size.y,
        fg,
        bg,
        sel,
        fg,
        2,
    )

    # Create loading instance
    _loading = Loading(
        view_manager.draw,
        fg,
        bg,
    )
    _loading.text = "Scanning for Bluetooth devices..."

    from picoware.system.bluetooth import Bluetooth

    _bluetooth = Bluetooth()

    _bluetooth.callback = bluetooth_callback

    _bluetooth.scan()

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

    input_manager = view_manager.input_manager
    button: int = input_manager.button

    if button == BUTTON_BACK:
        input_manager.reset()
        view_manager.back()
        return

    global _loading

    # If scan is still active, show loading animation
    if _bluetooth.is_scanning:
        if _loading:
            _loading.animate()
        return

    # Scan just completed, transition to results
    if _loading is not None:
        _loading.stop()
        del _loading
        _loading = None

        # Check if we found any devices
        if _menu.item_count == 0:
            # Show alert for no results
            __alert(view_manager, "No Bluetooth devices found.", back=True)
        else:
            _menu.draw()
        return

    if button in (BUTTON_UP, BUTTON_LEFT):
        input_manager.reset()
        _menu.scroll_up()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        input_manager.reset()
        _menu.scroll_down()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _menu, _bluetooth, _loading, _addresses
    if _menu is not None:
        del _menu
        _menu = None
    if _bluetooth is not None:
        del _bluetooth
        _bluetooth = None
    if _loading is not None:
        del _loading
        _loading = None
    _addresses.clear()
    collect()
