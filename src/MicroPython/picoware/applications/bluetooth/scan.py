"""BLE Scanner - Scan for nearby Bluetooth devices (Central mode)"""

_menu = None
_bluetooth = None
_loading = None
_addresses = []
_scanned_devices = []  # List of (addr_type, addr_bytes, name, rssi)


def bluetooth_callback(event, data):
    """Bluetooth callback function for scan results"""
    global _scanned_devices

    if event == 5:  # _IRQ_SCAN_RESULT
        addr_type, addr, adv_type, rssi, adv_data = data

        # Format the address
        addr_str = ":".join("{:02X}".format(b) for b in addr)

        # Skip if already seen
        if addr_str in _addresses:
            return

        _addresses.append(addr_str)

        # Try to decode the device name
        name = ""
        if _bluetooth is not None:
            name = _bluetooth.decode_name(adv_data)

        # Store device info
        _scanned_devices.append((addr_type, bytes(addr), name, rssi))

        # Create display string
        if name:
            display_str = f"{name} ({rssi}dB)"
        else:
            display_str = f"{addr_str[:17]} ({rssi}dB)"

        # Add to menu
        if _menu is not None:
            _menu.add_item(display_str)

    elif event == 6:  # _IRQ_SCAN_DONE
        _addresses.clear()


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.gui.loading import Loading
    from picoware.gui.menu import Menu
    from picoware.system.bluetooth import Bluetooth

    global _menu, _bluetooth, _loading, _scanned_devices

    # Cleanup
    if _menu is not None:
        del _menu
        _menu = None
    if _bluetooth is not None:
        del _bluetooth
        _bluetooth = None
    if _loading is not None:
        del _loading
        _loading = None

    _scanned_devices = []

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

    _loading = Loading(
        view_manager.draw,
        fg,
        bg,
    )
    _loading.text = "Scanning for Bluetooth devices..."

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
        BUTTON_CENTER,
    )
    from picoware.system.vector import Vector

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

        if _menu.item_count == 0:
            view_manager.alert("No Bluetooth devices found.", True)
        else:
            _menu.draw()
        return

    # Handle menu navigation
    if button in (BUTTON_UP, BUTTON_LEFT):
        input_manager.reset()
        _menu.scroll_up()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        input_manager.reset()
        _menu.scroll_down()
    elif button == BUTTON_CENTER:
        input_manager.reset()
        # Show device details
        idx = _menu.selected_index
        if 0 <= idx < len(_scanned_devices):
            addr_type, addr, name, rssi = _scanned_devices[idx]
            addr_str = ":".join("{:02X}".format(b) for b in addr)

            draw = view_manager.draw
            draw.clear()
            text_vec = Vector(5, 5)
            draw.text(text_vec, "Device Info")
            text_vec.y = 30
            draw.text(text_vec, f"Name: {name or 'Unknown'}")
            text_vec.y = 50
            draw.text(text_vec, f"Addr: {addr_str[:17]}")
            if len(addr_str) > 17:
                text_vec.y = 70
                draw.text(text_vec, f"      {addr_str[17:]}")
            text_vec.y = 90
            draw.text(text_vec, f"Type: {'Public' if addr_type == 0 else 'Random'}")
            text_vec.y = 110
            draw.text(text_vec, f"RSSI: {rssi} dB")
            text_vec.y = draw.size.y - 20
            draw.text(text_vec, "Press BACK to return")
            draw.swap()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _menu, _bluetooth, _loading, _addresses, _scanned_devices

    if _bluetooth is not None:
        if _bluetooth.is_scanning:
            _bluetooth.scan_stop()
        del _bluetooth
        _bluetooth = None
    if _menu is not None:
        del _menu
        _menu = None
    if _loading is not None:
        del _loading
        _loading = None

    _addresses.clear()
    _scanned_devices = []
    collect()
