"""BLE UART Chat - Send and receive messages over BLE UART service"""

from micropython import const

_bluetooth = None
_menu = None
_loading = None
_messages = []  # List of (is_sent, text)
_scanned_devices = []
_addresses = []
_selected_device = None

# States
STATE_MODE_SELECT = const(0)
STATE_SCANNING = const(1)
STATE_DEVICE_LIST = const(2)
STATE_CONNECTING = const(3)
STATE_CHAT = const(4)
STATE_TYPING = const(5)
STATE_PERIPHERAL_WAIT = const(6)

_state = STATE_MODE_SELECT
_mode = None  # "central" or "peripheral"
_last_update = 0


def __addr_to_str(addr) -> str:
    """Convert address bytes to string."""
    return ":".join("{:02X}".format(b) for b in addr)


def on_data_received(data):
    """Handle incoming data"""
    global _messages
    try:
        text = data.decode("utf-8").strip()
    except Exception:
        text = str(data)
    if text:
        _messages.append((False, text))
        # Keep last 20 messages
        if len(_messages) > 20:
            _messages = _messages[-20:]


def bluetooth_callback(event, data):
    """Bluetooth callback"""
    global _state, _addresses

    if event == 5:  # _IRQ_SCAN_RESULT
        addr_type, addr, adv_type, rssi, adv_data = data
        addr_str = __addr_to_str(addr)

        if addr_str in _addresses:
            return

        _addresses.append(addr_str)
        name = _bluetooth.decode_name(adv_data)
        _scanned_devices.append((addr_type, bytes(addr), name, rssi))

        if _menu is not None and _state == STATE_SCANNING:
            display = name if name else addr_str[:17]
            _menu.add_item(f"{display}")

    elif event == 6:  # _IRQ_SCAN_DONE
        _addresses.clear()
        if _state == STATE_SCANNING:
            _state = STATE_DEVICE_LIST

    elif event == 7:  # _IRQ_PERIPHERAL_CONNECT
        _state = STATE_CHAT

    elif event == 8:  # _IRQ_PERIPHERAL_DISCONNECT
        _state = STATE_MODE_SELECT

    elif event == 1:  # _IRQ_CENTRAL_CONNECT (peripheral mode)
        _state = STATE_CHAT

    elif event == 2:  # _IRQ_CENTRAL_DISCONNECT (peripheral mode)
        _state = STATE_PERIPHERAL_WAIT


def start(view_manager) -> bool:
    """Start the UART Chat app"""
    from picoware.gui.menu import Menu

    global _bluetooth, _menu, _state, _messages, _scanned_devices, _addresses, _mode

    # Cleanup
    if _bluetooth is not None:
        del _bluetooth
        _bluetooth = None
    if _menu is not None:
        del _menu
        _menu = None

    _messages = []
    _scanned_devices = []
    _addresses = []
    _state = STATE_MODE_SELECT
    _mode = None

    # Create mode selection menu
    _menu = Menu(
        view_manager.draw,
        "UART Chat",
        0,
        view_manager.draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
        view_manager.foreground_color,
        2,
    )
    _menu.add_item("Central (Connect)")
    _menu.add_item("Peripheral (Wait)")
    _menu.draw()

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
    from utime import ticks_ms, ticks_diff

    global _state, _mode, _bluetooth, _menu, _loading
    global _selected_device, _scanned_devices, _addresses, _last_update

    input_manager = view_manager.input_manager
    button: int = input_manager.button

    # Handle back button
    if button == BUTTON_BACK:
        input_manager.reset()
        if _state == STATE_TYPING:
            _state = STATE_CHAT
            view_manager.keyboard.reset()
            return
        if _state == STATE_CHAT:
            if _bluetooth:
                _bluetooth.disconnect()
            _state = STATE_MODE_SELECT
            return
        if _state in (STATE_SCANNING, STATE_DEVICE_LIST, STATE_PERIPHERAL_WAIT):
            _state = STATE_MODE_SELECT
            if _bluetooth:
                if _bluetooth.is_scanning:
                    _bluetooth.scan_stop()
                _bluetooth.stop_peripheral()
            return
        view_manager.back()
        return

    # State: Mode Selection
    if _state == STATE_MODE_SELECT:
        if button in (BUTTON_UP, BUTTON_LEFT):
            input_manager.reset()
            _menu.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            input_manager.reset()
            _menu.scroll_down()
        elif button == BUTTON_CENTER:
            input_manager.reset()
            from picoware.system.bluetooth import Bluetooth

            _bluetooth = Bluetooth()
            _bluetooth.callback = bluetooth_callback

            if _menu.selected_index == 0:
                from picoware.gui.menu import Menu

                # Central mode - scan for devices
                _mode = "central"
                _bluetooth.on_notify(on_data_received)
                _scanned_devices = []
                _addresses = []

                # Create device list menu
                del _menu
                _menu = Menu(
                    view_manager.draw,
                    "Select Device",
                    0,
                    view_manager.draw.size.y,
                    view_manager.foreground_color,
                    view_manager.background_color,
                    view_manager.selected_color,
                    view_manager.foreground_color,
                    2,
                )

                if _loading is None:
                    from picoware.gui.loading import Loading

                    _loading = Loading(
                        view_manager.draw,
                        view_manager.foreground_color,
                        view_manager.background_color,
                    )
                else:
                    _loading.stop()
                _loading.text = "Scanning..."
                _state = STATE_SCANNING
                _bluetooth.scan()
            else:
                # Peripheral mode - wait for connection
                _mode = "peripheral"
                _bluetooth.on_write(on_data_received)
                _bluetooth.start_peripheral(name="Picoware-Chat")
                _state = STATE_PERIPHERAL_WAIT
        return

    # State: Scanning
    if _state == STATE_SCANNING:
        if _loading:
            _loading.animate()
        return

    # State: Device List
    if _state == STATE_DEVICE_LIST:
        if _loading:
            del _loading
            _loading = None

        if _menu.item_count == 0:
            view_manager.alert("No devices found.", True)
            return

        _menu.draw()

        if button in (BUTTON_UP, BUTTON_LEFT):
            input_manager.reset()
            _menu.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            input_manager.reset()
            _menu.scroll_down()
        elif button == BUTTON_CENTER:
            input_manager.reset()
            idx = _menu.selected_index
            if 0 <= idx < len(_scanned_devices):
                _selected_device = _scanned_devices[idx]
                addr_type, addr, name, rssi = _selected_device
                _state = STATE_CONNECTING
                _bluetooth.connect(addr_type, addr)
        return

    # State: Connecting
    if _state == STATE_CONNECTING:
        if _loading is None:
            from picoware.gui.loading import Loading

            _loading = Loading(
                view_manager.draw,
                view_manager.foreground_color,
                view_manager.background_color,
            )
        else:
            _loading.stop()
        _loading.text = "Connecting..."
        _loading.animate()
        return

    text_vec = Vector(5, 5)

    # State: Peripheral waiting
    if _state == STATE_PERIPHERAL_WAIT:
        now = ticks_ms()
        if ticks_diff(now, _last_update) < 500:
            return
        _last_update = now

        draw = view_manager.draw
        draw.clear()
        draw.text(text_vec, "UART Chat - Peripheral")
        text_vec.y = 30
        draw.text(text_vec, "Waiting for connection...")
        text_vec.y = 55
        draw.text(text_vec, "Name: Picoware-Chat")
        text_vec.y = 75
        draw.text(text_vec, f"MAC: {_bluetooth.mac_address}")
        text_vec.y = draw.size.y - 20
        draw.text(text_vec, "BACK: Cancel")
        draw.swap()
        return

    # State: Chat
    if _state == STATE_CHAT:
        if _loading:
            del _loading
            _loading = None

        now = ticks_ms()
        if ticks_diff(now, _last_update) < 100:
            return
        _last_update = now

        draw = view_manager.draw
        draw.clear()

        # Header
        mode_str = "Central" if _mode == "central" else "Peripheral"
        text_vec.x, text_vec.y = 5, 2
        draw.text(text_vec, f"Chat ({mode_str})")

        # Messages area
        y = 20
        max_y = draw.size.y - 35
        visible_messages = []

        for is_sent, text in _messages[-8:]:
            if y < max_y:
                prefix = "> " if is_sent else "< "
                visible_messages.append((y, prefix + text[:22]))
                y += 14

        for y_pos, msg in visible_messages:
            text_vec.x, text_vec.y = 5, y_pos
            draw.text(text_vec, msg)

        # Footer
        text_vec.x, text_vec.y = 5, draw.size.y - 30
        draw.text(text_vec, "CENTER: Type message")
        text_vec.y = draw.size.y - 15
        draw.text(text_vec, "BACK: Disconnect")
        draw.swap()

        if button == BUTTON_CENTER:
            input_manager.reset()
            _state = STATE_TYPING
            view_manager.keyboard.run()
        return

    # State: Typing
    if _state == STATE_TYPING:
        _keyboard = view_manager.keyboard
        if not _keyboard.run(input_manager):
            _state = STATE_CHAT
            return
        result = _keyboard.response
        if result is not None:
            # Message entered
            if result:
                _messages.append((True, result))
                if _mode == "central":
                    _bluetooth.write(result)
                else:
                    _bluetooth.send(result)

            _keyboard.reset()
            _state = STATE_CHAT


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _bluetooth, _menu, _loading, _messages
    global _scanned_devices, _addresses, _selected_device, _state, _mode

    if _bluetooth is not None:
        if _bluetooth.is_connected or _bluetooth.is_peripheral_connected:
            _bluetooth.disconnect()
        _bluetooth.stop_peripheral()
        del _bluetooth
        _bluetooth = None

    if _menu is not None:
        del _menu
        _menu = None

    if _loading is not None:
        del _loading
        _loading = None

    view_manager.keyboard.reset()

    _messages = []
    _scanned_devices = []
    _addresses = []
    _selected_device = None
    _state = STATE_MODE_SELECT
    _mode = None

    collect()
