"""BLE Advertise - Broadcast as a peripheral and accept connections"""

from micropython import const

_bluetooth = None
_advertising = False
_connections = []
_received_data = []
_last_update = 0
_pairing_status = ""
_passkey_action = None
_passkey = None
_passkey_input_active = False

STATE_IDLE = const(0)
STATE_ADVERTISING = const(1)
STATE_CONNECTED = const(2)
PASSKEY_ACTION_INPUT = const(2)

_state = STATE_IDLE


def bluetooth_callback(event, data):
    """Handle Bluetooth connection and disconnection events.

    Args:
        event (int): Bluetooth event code.
        data (tuple): Event payload with connection handle and address.
    """
    global _connections, _state, _pairing_status, _passkey_action, _passkey
    global _passkey_input_active

    if event == 1:  # _IRQ_CENTRAL_CONNECT
        conn_handle, addr_type, addr = data
        addr_str = ":".join("{:02X}".format(b) for b in addr)
        _connections.append((conn_handle, addr_str))
        _state = STATE_CONNECTED

    elif event == 2:  # _IRQ_CENTRAL_DISCONNECT
        conn_handle, addr_type, addr = data
        _connections = [(h, a) for h, a in _connections if h != conn_handle]
        if len(_connections) == 0:
            _state = STATE_ADVERTISING
            if _passkey_action is not None:
                _passkey_action = None
                _passkey = None
                _passkey_input_active = False
                if _pairing_status == "Pairing request":
                    _pairing_status = "Pairing cancelled"

    elif event == 28:  # _IRQ_ENCRYPTION_UPDATE
        conn_handle, encrypted, authenticated, bonded, key_size = data
        print(
            f"[Advertise] Encryption update handle={conn_handle}, "
            f"encrypted={encrypted}, authenticated={authenticated}, "
            f"bonded={bonded}, key_size={key_size}"
        )
        _passkey_action = None
        _passkey = None
        _passkey_input_active = False
        _pairing_status = "Bonded" if encrypted and bonded else "Pairing failed"

    elif event == 31:  # _IRQ_PASSKEY_ACTION
        conn_handle, _passkey_action, _passkey = data
        print(
            f"[Advertise] Passkey request handle={conn_handle}, "
            f"action={_passkey_action}, value={_passkey}"
        )
        _pairing_status = "Pairing request"


def on_data_received(data):
    """Store data received from the connected central.

    Args:
        data (bytes): Raw data received over BLE.
    """
    global _received_data
    try:
        text = data.decode("utf-8")
    except Exception:
        text = str(data)
    _received_data.append(text)
    # Keep only last 5 messages
    if len(_received_data) > 5:
        _received_data = _received_data[-5:]


def start(view_manager) -> bool:
    """Start the app and advertise this device for connections.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.

    Returns:
        bool: True if advertising started, False on failure.
    """
    from picoware.system.bluetooth import Bluetooth

    global _bluetooth, _advertising, _connections, _received_data, _state
    global _pairing_status, _passkey_action, _passkey, _passkey_input_active

    if _bluetooth is not None:
        del _bluetooth
        _bluetooth = None

    _advertising = False
    _connections = []
    _received_data = []
    _state = STATE_IDLE
    _pairing_status = ""
    _passkey_action = None
    _passkey = None
    _passkey_input_active = False

    _bluetooth = Bluetooth(storage=view_manager.storage)
    _bluetooth.callback = bluetooth_callback
    _bluetooth.on_write(on_data_received)

    try:
        if _bluetooth.start_peripheral(name="Picoware"):
            _advertising = True
            _state = STATE_ADVERTISING
        else:
            view_manager.alert("Failed to start advertising")
            return False
    except Exception as e:
        view_manager.alert(f"Error: {str(e)}")
        return False

    return True


def run(view_manager) -> None:
    """Run the app and update the display.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
    from picoware.system.buttons import BUTTON_BACK, BUTTON_CENTER
    from utime import ticks_ms, ticks_diff

    global _last_update, _pairing_status, _passkey_action, _passkey_input_active

    button: int = view_manager.button
    passkey_pending = _passkey_action is not None
    _bluetooth.flush_secrets()

    if button == BUTTON_BACK:
        if _passkey_action is not None:
            _bluetooth.passkey_reply(accept=False)
        if _passkey_input_active:
            view_manager.keyboard.reset()
        view_manager.back()
        return

    if _passkey_input_active:
        keyboard = view_manager.keyboard
        if not keyboard.run(max_characters=6):
            _bluetooth.passkey_reply(accept=False)
            _passkey_action = None
            _passkey_input_active = False
            keyboard.reset()
            _pairing_status = "Pairing rejected"
            return

        result = keyboard.response
        if result is not None:
            if len(result) == 6 and result.isdigit():
                if _bluetooth.passkey_reply(accept=True, passkey=int(result)):
                    if _pairing_status == "Pairing request":
                        _pairing_status = "Pairing confirmed"
                else:
                    _pairing_status = "Could not answer passkey"
            else:
                _bluetooth.passkey_reply(accept=False)
                _pairing_status = "Passkey must be six digits"
            _passkey_action = None
            _passkey_input_active = False
            keyboard.reset()
        return

    if button == BUTTON_CENTER and _passkey_action is not None:
        if _passkey_action == PASSKEY_ACTION_INPUT:
            keyboard = view_manager.keyboard
            keyboard.reset()
            keyboard.title = "Enter Passkey"
            keyboard.run(force=True, max_characters=6)
            _passkey_input_active = True
        else:
            if _bluetooth.passkey_reply(accept=True):
                if _pairing_status == "Pairing request":
                    _pairing_status = "Pairing confirmed"
                _passkey_action = None

    # Send test data when center pressed
    if (
        button == BUTTON_CENTER
        and _state == STATE_CONNECTED
        and not passkey_pending
    ):
        _bluetooth.send("Hello from Picoware!")

    # Update display periodically
    now = ticks_ms()
    if ticks_diff(now, _last_update) < 200:
        return
    _last_update = now

    draw = view_manager.draw
    draw.clear()
    fg = view_manager.foreground_color

    draw._text(5, 5, "BLE Peripheral Mode", fg)
    draw._text(5, 25, "Name: Picoware", fg)
    draw._text(5, 45, f"MAC: {_bluetooth.mac_address}", fg)

    # Status
    if _state == STATE_ADVERTISING:
        draw._text(5, 70, "Status: Broadcasting...", fg)
    elif _state == STATE_CONNECTED:
        draw._text(5, 70, "Status: Connected", fg)
    else:
        draw._text(5, 70, "Status: Idle", fg)

    draw._text(5, 90, f"Connections: {len(_connections)}", fg)
    if _pairing_status:
        draw._text(5, 105, "Pair: " + _pairing_status[:20], fg)
    if _passkey_action is not None and _passkey_action != PASSKEY_ACTION_INPUT:
        draw._text(5, 120, "Code: {:06d}".format(_passkey or 0), fg)
    elif _passkey_action == PASSKEY_ACTION_INPUT:
        draw._text(5, 120, "CENTER: Enter code", fg)

    # Show connected devices
    y_offset = 135 if _passkey_action is not None or _pairing_status else 110
    if _connections:
        for i, (handle, addr) in enumerate(_connections[:2]):
            if y_offset < draw.size.y - 60:
                draw._text(10, y_offset, f"{addr[:17]}", fg)
                y_offset += 15

    # Show received data
    if _received_data:
        y_offset = max(y_offset, 140)
        draw._text(5, y_offset, "Last received:", fg)
        y_offset += 15
        for msg in _received_data[-2:]:
            if y_offset < draw.size.y - 30:
                draw._text(10, y_offset, msg[:25], fg)
                y_offset += 12

    # Instructions
    if _state == STATE_CONNECTED:
        draw._text(5, draw.size.y - 30, "CENTER: Send test msg", fg)
    draw._text(5, draw.size.y - 10, "BACK: Exit", fg)
    draw.swap()


def stop(view_manager) -> None:
    """Stop the app and clean up the BLE connection.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
    from gc import collect

    global _bluetooth, _advertising, _connections, _received_data, _state
    global _pairing_status, _passkey_action, _passkey, _passkey_input_active
    global _pairing_status, _passkey_action, _passkey

    if _bluetooth is not None:
        _bluetooth.flush_secrets()
        _bluetooth.stop_peripheral()
        for conn_handle, _ in _connections:
            try:
                _bluetooth.disconnect(conn_handle)
            except Exception:
                pass
        del _bluetooth
        _bluetooth = None

    _advertising = False
    _connections = []
    _received_data = []
    _state = STATE_IDLE
    _pairing_status = ""
    _passkey_action = None
    _passkey = None
    _passkey_input_active = False
    collect()
