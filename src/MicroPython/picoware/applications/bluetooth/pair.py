from micropython import const

_bluetooth = None
_menu = None
_loading = None
_scanned_devices = []  # List of (addr_type, addr_bytes, name, rssi)
_addresses = []
_selected_device = None

# states
STATE_IDLE = const(0)
STATE_SCANNING = const(1)
STATE_CONNECTING = const(2)
STATE_PAIRING = const(3)
STATE_CONNECTED = const(4)
STATE_PAIRED = const(5)

_state = STATE_IDLE


def __alert(view_manager, message: str, back: bool = False) -> None:
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


def __addr_to_str(addr) -> str:
    """Convert address bytes to string."""
    return ":".join("{:02X}".format(b) for b in addr)


def bluetooth_callback(event, data):
    """Bluetooth callback for scan and connection events"""
    global _state, _selected_device

    if event == 5:  # _IRQ_SCAN_RESULT
        addr_type, addr, adv_type, rssi, adv_data = data
        addr_str = __addr_to_str(addr)

        if addr_str in _addresses:
            return

        # New device
        _addresses.append(addr_str)
        name = _bluetooth.decode_name(adv_data)
        _scanned_devices.append((addr_type, bytes(addr), name, rssi))

        # Add to menu
        if _menu is not None:
            display = name if name else addr_str
            display = f"{display} ({rssi}dB)"
            _menu.add_item(display)
    elif event == 6:  # _IRQ_SCAN_DONE
        _addresses.clear()

    elif event == 7:  # _IRQ_PERIPHERAL_CONNECT
        _state = STATE_CONNECTED

    elif event == 8:  # _IRQ_PERIPHERAL_DISCONNECT
        _state = STATE_IDLE
        _selected_device = None

    elif event == 28:  # _IRQ_ENCRYPTION_UPDATE
        conn_handle, encrypted, authenticated, bonded, key_size = data
        if bonded:
            _state = STATE_PAIRED


def start(view_manager) -> bool:
    """Start the pairing app"""
    from picoware.gui.menu import Menu
    from picoware.gui.loading import Loading
    from picoware.system.bluetooth import Bluetooth

    global _bluetooth, _menu, _loading, _scanned_devices, _state

    # Clean up previous instances
    if _bluetooth is not None:
        del _bluetooth
        _bluetooth = None
    if _menu is not None:
        del _menu
        _menu = None
    if _loading is not None:
        del _loading
        _loading = None

    _scanned_devices = []
    _state = STATE_SCANNING

    # Create menu for device list
    _menu = Menu(
        view_manager.draw,
        "Pair Device",
        0,
        view_manager.draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
        view_manager.foreground_color,
        2,
    )

    # Create loading animation
    _loading = Loading(
        view_manager.draw,
        view_manager.foreground_color,
        view_manager.background_color,
    )
    _loading.text = "Scanning for devices..."

    # Initialize Bluetooth with storage for paired devices
    _bluetooth = Bluetooth(storage=view_manager.storage)
    _bluetooth.callback = bluetooth_callback

    # Start scanning
    _bluetooth.scan()

    return True


def run(view_manager) -> None:
    """Run the pairing app"""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_RIGHT,
        BUTTON_CENTER,
    )
    from picoware.system.vector import Vector

    global _state, _selected_device, _loading

    input_manager = view_manager.input_manager
    button: int = input_manager.button

    if button == BUTTON_BACK:
        input_manager.reset()
        if _state == STATE_CONNECTED or _state == STATE_PAIRED:
            # Disconnect first
            _bluetooth.disconnect()
            _state = STATE_IDLE
        view_manager.back()
        return

    # State: Scanning
    if _state == STATE_SCANNING:
        if _bluetooth.is_scanning:
            if _loading:
                _loading.animate()
            return

        # Scan complete
        _state = STATE_IDLE
        if _loading:
            _loading.stop()

        if _menu.item_count == 0:
            __alert(view_manager, "No Bluetooth devices found.", back=True)
            return
        else:
            _menu.draw()
        return

    # State: Connecting
    if _state == STATE_CONNECTING:
        if _loading:
            _loading.text = "Connecting..."
            _loading.animate()
        return

    # State: Connected - offer to pair
    if _state == STATE_CONNECTED:
        draw = view_manager.draw
        draw.clear()
        draw.text(Vector(5, 5), "Connected!")

        if _selected_device:
            addr_type, addr, name, rssi = _selected_device
            addr_str = __addr_to_str(addr)
            draw.text(Vector(5, 25), f"Device: {name or addr_str}")

        draw.text(Vector(5, 55), "Press CENTER to pair")
        draw.text(Vector(5, 75), "Press BACK to disconnect")
        draw.swap()

        if button == BUTTON_CENTER:
            input_manager.reset()
            # Initiate pairing
            _bluetooth.pair()
            _state = STATE_PAIRING
        return

    # State: Pairing
    if _state == STATE_PAIRING:
        if _loading:
            _loading.text = "Pairing..."
            _loading.animate()
        return

    # State: Paired
    if _state == STATE_PAIRED:
        # Save the paired device
        if _selected_device:
            addr_type, addr, name, rssi = _selected_device
            addr_str = __addr_to_str(addr)
            _bluetooth.save_paired_device(addr_str, name or "")

        draw = view_manager.draw
        draw.clear()
        draw.text(Vector(5, 5), "Paired Successfully!")

        if _selected_device:
            addr_type, addr, name, rssi = _selected_device
            addr_str = __addr_to_str(addr)
            draw.text(Vector(5, 25), f"Device: {name or addr_str}")

        draw.text(Vector(5, 55), "Device saved to paired list")
        draw.text(Vector(5, 85), "Press BACK to exit")
        draw.swap()
        return

    # State: Idle - show device list
    if _state == STATE_IDLE:
        if not _menu:
            return

        if button in (BUTTON_UP, BUTTON_LEFT):
            input_manager.reset()
            _menu.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            input_manager.reset()
            _menu.scroll_down()
        elif button == BUTTON_CENTER:
            input_manager.reset()
            # Connect to selected device
            idx = _menu.selected_index
            if 0 <= idx < len(_scanned_devices):
                _selected_device = _scanned_devices[idx]
                addr_type, addr, name, rssi = _selected_device
                _state = STATE_CONNECTING
                _bluetooth.connect(addr_type, addr)


def stop(view_manager) -> None:
    """Stop the pairing app"""
    from gc import collect

    global _bluetooth, _menu, _loading, _scanned_devices, _selected_device, _state, _addresses

    # Disconnect if connected
    if _bluetooth is not None:
        if _bluetooth.is_connected:
            _bluetooth.disconnect()
        del _bluetooth
        _bluetooth = None

    if _menu is not None:
        del _menu
        _menu = None

    if _loading is not None:
        del _loading
        _loading = None

    _scanned_devices = []
    _selected_device = None
    _addresses = []
    _state = STATE_IDLE

    collect()
