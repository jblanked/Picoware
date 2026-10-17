"""BLE RSSI Monitor - Monitor signal strength of nearby devices in real-time"""

from utime import ticks_ms, ticks_diff

_bluetooth = None
_menu = None
_devices = {}  # addr_str -> (name, rssi, last_seen)
_last_update = 0
_scan_count = 0


def bluetooth_callback(event, data):
    """Handle Bluetooth scan result events.

    Args:
        event (int): Bluetooth event code.
        data (tuple): Event payload with address and RSSI.
    """
    global _devices

    if event == 5:  # _IRQ_SCAN_RESULT
        _, addr, _, rssi, adv_data = data
        addr_str = ":".join("{:02X}".format(b) for b in addr)

        name = ""
        if _bluetooth is not None:
            name = _bluetooth.decode_name(adv_data)

        # Update or add device with timestamp
        _devices[addr_str] = (name, rssi, ticks_ms())

    elif event == 6:  # _IRQ_SCAN_DONE
        # Restart scan for continuous monitoring
        if _bluetooth is not None:
            _bluetooth.scan(duration_ms=2000)


def start(view_manager) -> bool:
    """Start the RSSI Monitor app and begin scanning.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.

    Returns:
        bool: True if the app started, False on failure.
    """
    from picoware.gui.menu import Menu
    from picoware.system.bluetooth import Bluetooth

    global _bluetooth, _menu, _devices, _scan_count

    if _bluetooth is not None:
        del _bluetooth
        _bluetooth = None
    if _menu is not None:
        del _menu
        _menu = None

    _devices = {}
    _scan_count = 0

    bg = view_manager.background_color
    fg = view_manager.foreground_color
    sel = view_manager.selected_color

    _menu = Menu(
        view_manager.draw,
        "RSSI Monitor",
        0,
        view_manager.draw.size.y,
        fg,
        bg,
        sel,
        fg,
        2,
    )

    _bluetooth = Bluetooth(view_manager.storage)
    _bluetooth.callback = bluetooth_callback

    # Start continuous scanning
    _bluetooth.scan(duration_ms=2000)

    return True


def run(view_manager) -> None:
    """Run the app and update the RSSI display.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
    from picoware.system.buttons import BUTTON_BACK, BUTTON_CENTER, BUTTON_UP, BUTTON_DOWN

    global _last_update, _devices, _scan_count

    button: int = view_manager.button

    if button == BUTTON_BACK:
        view_manager.back()
        return

    # Handle menu navigation
    if button == BUTTON_UP:
        _menu.scroll_up()
    elif button == BUTTON_DOWN:
        _menu.scroll_down()

    if button == BUTTON_CENTER:
        # Clear device list
        _devices = {}
        _scan_count = 0
        _menu.clear()

    # Update display periodically
    now = ticks_ms()
    if ticks_diff(now, _last_update) < 1000:
        return
    _last_update = now

    # Remove stale devices (not seen in last 10 seconds)
    stale_threshold = 10000
    _devices = {
        addr: (name, rssi, last_seen)
        for addr, (name, rssi, last_seen) in _devices.items()
        if ticks_diff(now, last_seen) < stale_threshold
    }

    _scan_count += 1

    # Rebuild menu items sorted by RSSI (strongest first)
    _menu.clear()

    if not _devices:
        _menu.add_item("Scanning...")
    else:
        # Sort devices by RSSI (strongest first)
        sorted_devices = sorted(
            _devices.items(), key=lambda x: x[1][1], reverse=True
        )

        for addr, (name, rssi, last_seen) in sorted_devices:
            display = name if name else addr[:11]
            display_str = f"{display[:10]}: {rssi}dB"
            _menu.add_item(display_str)

    # Redraw with updated items
    _menu.draw()


def stop(view_manager) -> None:
    """Stop the app and stop scanning.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
    from gc import collect

    global _bluetooth, _devices, _scan_count

    if _bluetooth is not None:
        if _bluetooth.is_scanning:
            _bluetooth.scan_stop()
        del _bluetooth
        _bluetooth = None

    _devices = {}
    _scan_count = 0

    collect()
