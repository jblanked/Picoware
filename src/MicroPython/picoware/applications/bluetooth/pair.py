"""BLE Pair - Scan, connect, and pair with BLE devices"""

from micropython import const

_bluetooth = None
_menu = None
_loading = None
_scanned_devices = []  # List of (addr_type, addr_bytes, name, rssi)
_addresses = []
_selected_device = None

# States
STATE_IDLE = const(0)
STATE_SCANNING = const(1)
STATE_CONNECTING = const(2)
STATE_DISCOVERING = const(3)
STATE_PAIRING = const(4)
STATE_CONNECTED = const(5)
STATE_PAIRED = const(6)
STATE_PAIR_FAILED = const(7)
STATE_PASSKEY_INPUT = const(8)
STATE_CHAT_READY = const(9)
PASSKEY_ACTION_INPUT = const(2)
PAIRING_TIMEOUT_MS = const(15000)
DISCOVERY_TIMEOUT_MS = const(15000)

_state = STATE_IDLE
_pairing_started = None
_pairing_error = ""
_passkey_action = None
_passkey = None
_paired_saved = None
_passkey_needs_draw = False
_discover_services_pending = False
_discovery_started = None
_connect_started = None


def __addr_to_str(addr) -> str:
    """Convert address bytes to a colon-separated string.

    Args:
        addr (bytes): The device address bytes.

    Returns:
        str: The formatted address string.
    """
    return ":".join("{:02X}".format(b) for b in addr)


def __is_device_paired(addr: str) -> bool:
    """Check if a device address is already in the paired devices list."""
    if _bluetooth is None:
        return False
    return _bluetooth.is_device_paired(addr)


def bluetooth_callback(event, data):
    """Handle Bluetooth scan and connection events.

    Args:
        event (int): Bluetooth event code.
        data (tuple): Event payload.
    """
    global _state, _selected_device, _pairing_started
    global _pairing_error, _passkey_action, _passkey
    global _discover_services_pending, _discovery_started, _connect_started

    if event == 5:  # _IRQ_SCAN_RESULT
        addr_type, addr, adv_type, rssi, adv_data = data
        addr_str = __addr_to_str(addr)
        name = _bluetooth.decode_name(adv_data)

        if addr_str in _addresses:
            index = _addresses.index(addr_str)
            _, _, old_name, _ = _scanned_devices[index]
            _scanned_devices[index] = (
                addr_type,
                bytes(addr),
                name or old_name,
                rssi,
            )
            return
        _addresses.append(addr_str)
        _scanned_devices.append((addr_type, bytes(addr), name, rssi))

        if _menu is not None:
            display = name if name else addr_str[:17]
            display = f"{display} ({rssi}dB)"
            _menu.add_item(display)

    elif event == 6:  # _IRQ_SCAN_DONE
        _addresses.clear()
        if _menu is not None:
            _menu.clear()
            for addr_type, addr, name, rssi in _scanned_devices:
                display = name if name else __addr_to_str(addr)[:17]
                _menu.add_item(f"{display} ({rssi}dB)")

    elif event == 7:  # _IRQ_PERIPHERAL_CONNECT
        _state = STATE_DISCOVERING
        _discover_services_pending = True
        _discovery_started = None
        _connect_started = None

    elif event == 8:  # _IRQ_PERIPHERAL_DISCONNECT
        _state = STATE_IDLE
        _selected_device = None
        _discover_services_pending = False
        _discovery_started = None
        _connect_started = None

    elif event == 10:  # _IRQ_GATTC_SERVICE_DONE
        _discover_services_pending = False
        _discovery_started = None
        _connect_started = None
        _state = STATE_CONNECTED

    elif event == 28:  # _IRQ_ENCRYPTION_UPDATE
        conn_handle, encrypted, authenticated, bonded, key_size = data
        print(
            f"[Pair] Encryption update handle={conn_handle}, "
            f"encrypted={encrypted}, authenticated={authenticated}, "
            f"bonded={bonded}, key_size={key_size}"
        )
        _pairing_started = None
        _passkey_action = None
        _passkey = None
        if encrypted and bonded:
            _state = STATE_PAIRED
            _pairing_error = ""
        else:
            _state = STATE_PAIR_FAILED
            _pairing_error = "Pairing was not bonded"

    elif event == 31:  # _IRQ_PASSKEY_ACTION
        conn_handle, _passkey_action, _passkey = data
        print(
            f"[Pair] Passkey request handle={conn_handle}, "
            f"action={_passkey_action}, value={_passkey}"
        )


def start(view_manager) -> bool:
    """Start the pairing app and begin scanning for devices.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.

    Returns:
        bool: True if the app started, False on failure.
    """
    from picoware.gui.menu import Menu
    from picoware.gui.loading import Loading

    global _bluetooth, _menu, _loading, _scanned_devices, _state, _addresses
    global _pairing_started, _pairing_error, _passkey_action, _passkey
    global _paired_saved, _selected_device
    global _passkey_needs_draw
    global _discover_services_pending, _discovery_started, _connect_started

    _bluetooth = view_manager.bluetooth

    # Clean up previous instances
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
    _addresses = []
    _state = STATE_SCANNING
    _pairing_started = None
    _pairing_error = ""
    _passkey_action = None
    _passkey = None
    _paired_saved = None
    _passkey_needs_draw = False
    _discover_services_pending = False
    _discovery_started = None
    _connect_started = None

    if _bluetooth is not None:
        _bluetooth.callback = bluetooth_callback
        if _bluetooth.is_discovering_services:
            _state = STATE_DISCOVERING
        elif _bluetooth.services:
            _state = STATE_CONNECTED
        else:
            _state = STATE_DISCOVERING
            _discover_services_pending = True
        return True

    _selected_device = None

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

    _loading = Loading(
        view_manager.draw,
        view_manager.foreground_color,
        view_manager.background_color,
    )
    _loading.text = "Scanning..."

    _bluetooth = view_manager.bluetooth
    _bluetooth.callback = bluetooth_callback
    _bluetooth.scan()

    return True


def run(view_manager) -> None:
    """Run the pairing app and handle input.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_RIGHT,
        BUTTON_CENTER,
    )
    from utime import ticks_ms, ticks_diff

    global _state, _selected_device, _loading
    global _pairing_started, _pairing_error, _passkey_action, _passkey
    global _paired_saved,_passkey_needs_draw
    global _discover_services_pending, _discovery_started, _connect_started

    button: int = view_manager.button
    _bluetooth.flush_secrets()

    if button == BUTTON_BACK:
        if _state in (
            STATE_CONNECTED,
            STATE_DISCOVERING,
            STATE_PAIRED,
            STATE_PAIR_FAILED,
            STATE_CHAT_READY,
        ):
            if _state == STATE_DISCOVERING and _discover_services_pending:
                _discover_services_pending = False
                _discovery_started = ticks_ms()
                if not _bluetooth.discover_services():
                    _discovery_started = None
            _connect_started = None
            if _state == STATE_PAIRED and _selected_device:
                _, addr, name, _ = _selected_device
                _paired_saved = _bluetooth.save_paired_device(
                    __addr_to_str(addr), name or ""
                )
            view_manager.back()
            return

        if _state in (STATE_PAIRING, STATE_PASSKEY_INPUT):
            if _state == STATE_PASSKEY_INPUT:
                view_manager.keyboard.reset()
                _passkey_needs_draw = False
            _pairing_started = None
            _passkey_action = None
            view_manager.back()
            return

        if _state == STATE_DISCOVERING:
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

        _state = STATE_IDLE
        if _loading:
            _loading.stop()

        if _menu.item_count == 0:
            view_manager.alert("No Bluetooth devices found.", back=True)
            return
        _menu.draw()
        return

    # State: Connecting
    if _state == STATE_CONNECTING:
        if (
            _connect_started is not None
            and ticks_diff(ticks_ms(), _connect_started) >= 10000
        ):
            _connect_started = None
            _state = STATE_PAIR_FAILED
            _pairing_error = "Connection timed out"
            return
        if _loading:
            _loading.text = "Connecting..."
            _loading.animate()
        return

    # State: Discovering services
    if _state == STATE_DISCOVERING:
        if _discover_services_pending:
            _discover_services_pending = False
            _discovery_started = ticks_ms()
            if not _bluetooth.discover_services():
                _discovery_started = None
                _state = STATE_PAIR_FAILED
                _pairing_error = "Could not start service discovery"
                return

        if _state != STATE_DISCOVERING:
            return
        if (
            _discovery_started is not None
            and ticks_diff(ticks_ms(), _discovery_started)
            >= DISCOVERY_TIMEOUT_MS
        ):
            _discovery_started = None
            _state = STATE_PAIR_FAILED
            _pairing_error = "Service discovery timed out"
            return

        if _loading:
            _loading.text = "Discovering services..."
            _loading.animate()
        return

    # State: Connected - check if already paired
    if _state == STATE_CONNECTED:
        draw = view_manager.draw
        draw.erase()
        fg = draw.foreground
        draw._text(5, 5, "Connected!", fg)
        _text_height = draw.font_size.y
        if _selected_device:
            addr_type, addr, name, rssi = _selected_device
            addr_str = __addr_to_str(addr)
            draw._text(5, 5 + _text_height, f"Name: {name or 'Unknown'}", fg)
            draw._text(5, 5 + 2 * _text_height, f"Addr: {addr_str[:17]}", fg)

        # Show discovered services count
        svc_count = len(_bluetooth.services)
        char_count = len(_bluetooth.characteristics)
        draw._text(5, 5 + 3 * _text_height, f"Services: {svc_count}", fg)
        draw._text(5, 5 + 4 * _text_height, f"Characteristics: {char_count}", fg)

        # Check if device is already paired/bonded
        addr_str = __addr_to_str(_selected_device[1]) if _selected_device else ""
        already_paired = (
            _selected_device is not None
            and _bluetooth.is_device_paired(addr_str)
        )

        if already_paired:
            if _paired_saved is None and _selected_device:
                _, addr, name, _ = _selected_device
                _paired_saved = _bluetooth.save_paired_device(
                    addr_str, name or ""
                )
            draw._text(5, 5 + 5 * _text_height, "DEVICE ALREADY PAIRED!", fg)
            draw._text(5, 5 + 6 * _text_height, "CENTER: Chat", fg)
            draw._text(5, 5 + 7 * _text_height, "BACK: Keep connection", fg)
            draw.swap()

            if button == BUTTON_CENTER:
                if _loading:
                    _loading.stop()
                _state = STATE_CHAT_READY
                return
        else:
            draw._text(5, 5 + 5 * _text_height, "Connected (not paired)", fg)
            draw._text(5, 5 + 6 * _text_height, "CENTER: Pair device", fg)
            draw._text(5, 5 + 7 * _text_height, "BACK: Keep connection", fg)
            draw.swap()

            if button == BUTTON_CENTER:
                if _loading:
                    _loading.stop()
                _pairing_error = ""
                _paired_saved = None
                _pairing_started = ticks_ms()
                _state = STATE_PAIRING
                if not _bluetooth.pair():
                    _pairing_started = None
                    _state = STATE_PAIR_FAILED
                    _pairing_error = "Could not start pairing"
        return

    # State: Chat Ready - BLE connected and paired, ready for data
    if _state == STATE_CHAT_READY:
        if _loading:
            _loading.stop()
            _loading = None
        if _selected_device:
            addr_type, addr, name, rssi = _selected_device
            addr_str = __addr_to_str(addr)
        draw = view_manager.draw
        draw.erase()
        fg = draw.foreground
        draw._text(5, 5, "Chat Ready", fg)

        if _selected_device:
            name_display = name or "Unknown"
            draw._text(5, 30, f"Name: {name_display}", fg)
            draw._text(5, 45, f"Addr: {addr_str[:17]}", fg)

        draw._text(5, 70, "BLE connected and paired!", fg)
        draw._text(5, 85, "Use UART to send/receive data", fg)
        draw._text(5, 110, "BACK: Keep connection", fg)
        draw.swap()
        return

    # State: Pairing
    if _state == STATE_PAIRING:
        if (
            _pairing_started is not None
            and ticks_diff(ticks_ms(), _pairing_started) >= PAIRING_TIMEOUT_MS
        ):
            _pairing_started = None
            _passkey_action = None
            _state = STATE_PAIR_FAILED
            _pairing_error = "No pairing response"
            if _loading:
                _loading.stop()
            return

        if _passkey_action is not None:
            draw = view_manager.draw
            draw.erase()
            fg = draw.foreground
            draw._text(5, 5, "Pairing confirmation", fg)
            _text_height = draw.font_size.y
            if _passkey_action == PASSKEY_ACTION_INPUT:
                draw._text(5, 5 + _text_height, "Passkey input required", fg)
                draw._text(5, draw.size.y - _text_height, "CENTER: Enter passkey", fg)
            else:
                draw._text(5, 5 + _text_height, "Confirm code:", fg)
                draw._text(5, 5 + 2 * _text_height, "{:06d}".format(_passkey or 0), fg)
                draw._text(5, draw.size.y - _text_height * 2, "CENTER: Accept", fg)
            draw._text(5, draw.size.y - _text_height, "BACK: Keep connection", fg)
            draw.swap()

            if button == BUTTON_CENTER:
                if _passkey_action == PASSKEY_ACTION_INPUT:
                    keyboard = view_manager.keyboard
                    keyboard.reset()
                    keyboard.title = "Enter Passkey"
                    _passkey_needs_draw = True
                    _state = STATE_PASSKEY_INPUT
                elif _bluetooth.passkey_reply(accept=True):
                    _passkey_action = None
                else:
                    _state = STATE_PAIR_FAILED
                    _pairing_error = "Could not answer passkey request"
            return

        if _loading:
            _loading.text = "Pairing..."
            _loading.animate()
        return

    if _state == STATE_PASSKEY_INPUT:
        keyboard = view_manager.keyboard
        if (
            _pairing_started is not None
            and ticks_diff(ticks_ms(), _pairing_started) >= PAIRING_TIMEOUT_MS
        ):
            _pairing_started = None
            _passkey_action = None
            _state = STATE_PAIR_FAILED
            _pairing_error = "No pairing response"
            keyboard.reset()
            return
        force_draw = _passkey_needs_draw
        _passkey_needs_draw = False
        if not keyboard.run(force=force_draw, max_characters=6):
            _pairing_started = None
            _state = STATE_PAIR_FAILED
            _pairing_error = "Passkey entry cancelled"
            _passkey_action = None
            keyboard.reset()
            return

        if keyboard.is_finished:
            result = keyboard.response
            if len(result) == 6 and result.isdigit():
                _state = STATE_PAIRING
                replied = _bluetooth.passkey_reply(
                    accept=True, passkey=int(result)
                )
                if replied:
                    _passkey_action = None
                else:
                    _state = STATE_PAIR_FAILED
                    _pairing_error = "Could not answer passkey request"
            else:
                _state = STATE_PASSKEY_INPUT
                _pairing_error = "Passkey must contain six digits"
            keyboard.reset()
            if _state == STATE_PASSKEY_INPUT:
                keyboard.title = "Enter Passkey"
                _passkey_needs_draw = True
        return

    # State: Paired
    if _state == STATE_PAIRED:
        if _loading:
            _loading.stop()
            _loading = None
        if _selected_device:
            addr_type, addr, name, rssi = _selected_device
            addr_str = __addr_to_str(addr)
            if _paired_saved is None:
                _paired_saved = _bluetooth.save_paired_device(addr_str, name or "")

        draw = view_manager.draw
        draw.erase()
        fg = draw.foreground
        draw._text(5, 5, "Paired Successfully!", fg)

        if _selected_device:
            addr_type, addr, name, rssi = _selected_device
            draw._text(5, 30, f"Name: {name or 'Unknown'}", fg)

        status = (
            "Device saved to paired list"
            if _paired_saved
            else "Bonded, but list save failed"
        )
        draw._text(5, 50, status, fg)
        draw._text(
            5,
            draw.size.y - draw.font_size.y - 1,
            "BACK: Keep connection",
            fg,
        )
        draw.swap()
        return

    if _state == STATE_PAIR_FAILED:
        if _loading:
            _loading.stop()
            _loading = None
        draw = view_manager.draw
        draw.erase()
        fg = draw.foreground
        draw._text(5, 5, "Pairing failed", fg)
        draw._text(5, 30, _pairing_error[:30], fg)
        if _bluetooth.is_connected:
            draw._text(5, draw.size.y - draw.font_size.y - 1, "CENTER: Retry", fg)
        else:
            draw._text(5, draw.size.y - draw.font_size.y - 1, "Connection ended", fg)
        back_text = (
            "BACK: Keep connection"
            if _bluetooth.is_connected
            else "BACK: Exit"
        )
        draw._text(5, 50, back_text, fg)
        draw.swap()
        if button == BUTTON_CENTER and _bluetooth.is_connected:
            _pairing_error = ""
            _paired_saved = None
            _pairing_started = ticks_ms()
            _state = STATE_PAIRING
            if not _bluetooth.pair():
                _pairing_started = None
                _state = STATE_PAIR_FAILED
                _pairing_error = "Could not start pairing"
        return

    # State: Idle - show device list
    if _state == STATE_IDLE:
        if not _menu:
            return

        if button in (BUTTON_UP, BUTTON_LEFT):

            _menu.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):

            _menu.scroll_down()
        elif button == BUTTON_CENTER:

            idx = _menu.selected_index
            if 0 <= idx < len(_scanned_devices):
                _selected_device = _scanned_devices[idx]
                addr_type, addr, name, rssi = _selected_device
                _state = STATE_CONNECTING
                _connect_started = ticks_ms()
                _discover_services_pending = False
                _discovery_started = None

                # Reinit loading for connection
                if _loading is None:
                    from picoware.gui.loading import Loading

                    _loading = Loading(
                        view_manager.draw,
                        view_manager.foreground_color,
                        view_manager.background_color,
                    )
                _loading.text = "Connecting..."

                if not _bluetooth.connect(addr_type, addr, auto_discover=False):
                    _connect_started = None
                    _state = STATE_PAIR_FAILED
                    _pairing_error = "Could not start connection"


def stop(view_manager) -> None:
    """Stop the pairing app and clean up.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
    from gc import collect

    global _bluetooth, _menu, _loading, _scanned_devices, _selected_device, _state, _addresses
    global _pairing_started, _pairing_error, _passkey_action, _passkey
    global _paired_saved
    global _passkey_needs_draw
    global _discover_services_pending, _discovery_started, _connect_started

    keep_connection = (
        _bluetooth is not None
        and _bluetooth.is_connected
        and (
            _state
            in (
                STATE_CONNECTED,
                STATE_DISCOVERING,
                STATE_PAIRED,
                STATE_PAIR_FAILED,
                STATE_CHAT_READY,
            )
        )
    )

    if _bluetooth is not None:
        _bluetooth.flush_secrets()
        if keep_connection:
            _bluetooth.callback = None
            _bluetooth.on_notify(None)
            _bluetooth.on_write(None)
        elif _bluetooth.is_connected:
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
    if not keep_connection:
        _selected_device = None
    _addresses = []
    _state = STATE_IDLE
    _pairing_started = None
    _pairing_error = ""
    _passkey_action = None
    _passkey = None
    _paired_saved = None
    _passkey_needs_draw = False
    _discover_services_pending = False
    _discovery_started = None
    _connect_started = None

    collect()
