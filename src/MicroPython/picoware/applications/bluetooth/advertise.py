"""BLE Advertise - Broadcast as a peripheral and accept connections"""

from micropython import const

_bluetooth = None
_advertising = False
_connections = []
_received_data = []
_last_update = 0

STATE_IDLE = const(0)
STATE_ADVERTISING = const(1)
STATE_CONNECTED = const(2)

_state = STATE_IDLE


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

    inp = view_manager.input_manager
    while True:
        button = inp.button
        if button == BUTTON_BACK:
            inp.reset()
            break

    if back:
        view_manager.back()


def bluetooth_callback(event, data):
    """Bluetooth callback function for connection events"""
    global _connections, _state

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


def on_data_received(data):
    """Handle data received from connected central"""
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
    """Start the app - advertise this device so others can find and connect to it"""
    from picoware.system.bluetooth import Bluetooth

    global _bluetooth, _advertising, _connections, _received_data, _state

    if _bluetooth is not None:
        del _bluetooth
        _bluetooth = None

    _advertising = False
    _connections = []
    _received_data = []
    _state = STATE_IDLE

    _bluetooth = Bluetooth()
    _bluetooth.callback = bluetooth_callback
    _bluetooth.on_write(on_data_received)

    try:
        if _bluetooth.start_peripheral(name="Picoware"):
            _advertising = True
            _state = STATE_ADVERTISING
        else:
            __alert(view_manager, "Failed to start advertising")
            return False
    except Exception as e:
        __alert(view_manager, f"Error: {str(e)}")
        return False

    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK, BUTTON_CENTER
    from picoware.system.vector import Vector
    from utime import ticks_ms, ticks_diff

    global _last_update

    input_manager = view_manager.input_manager
    button: int = input_manager.button

    if button == BUTTON_BACK:
        input_manager.reset()
        view_manager.back()
        return

    # Send test data when center pressed
    if button == BUTTON_CENTER and _state == STATE_CONNECTED:
        input_manager.reset()
        _bluetooth.send("Hello from Picoware!")

    # Update display periodically
    now = ticks_ms()
    if ticks_diff(now, _last_update) < 200:
        return
    _last_update = now

    draw = view_manager.draw
    draw.clear()

    draw.text(Vector(5, 5), "BLE Peripheral Mode")
    draw.text(Vector(5, 25), f"Name: Picoware")
    draw.text(Vector(5, 45), f"MAC: {_bluetooth.mac_address}")

    # Status
    if _state == STATE_ADVERTISING:
        draw.text(Vector(5, 70), "Status: Broadcasting...")
    elif _state == STATE_CONNECTED:
        draw.text(Vector(5, 70), "Status: Connected")
    else:
        draw.text(Vector(5, 70), "Status: Idle")

    draw.text(Vector(5, 90), f"Connections: {len(_connections)}")

    # Show connected devices
    y_offset = 110
    if _connections:
        for i, (handle, addr) in enumerate(_connections[:2]):
            if y_offset < draw.size.y - 60:
                draw.text(Vector(10, y_offset), f"{addr[:17]}")
                y_offset += 15

    # Show received data
    if _received_data:
        y_offset = max(y_offset, 140)
        draw.text(Vector(5, y_offset), "Last received:")
        y_offset += 15
        for msg in _received_data[-2:]:
            if y_offset < draw.size.y - 30:
                draw.text(Vector(10, y_offset), msg[:25])
                y_offset += 12

    # Instructions
    if _state == STATE_CONNECTED:
        draw.text(Vector(5, draw.size.y - 30), "CENTER: Send test msg")
    draw.text(Vector(5, draw.size.y - 15), "BACK: Exit")
    draw.swap()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _bluetooth, _advertising, _connections, _received_data, _state

    if _bluetooth is not None:
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
    collect()
