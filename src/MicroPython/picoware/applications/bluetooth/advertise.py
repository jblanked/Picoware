_bluetooth = None
_advertising = False
_connections = []


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
    """Bluetooth callback function for connection events"""
    global _connections

    if event == 1:  # _IRQ_CENTRAL_CONNECT
        # A central device has connected
        conn_handle, addr_type, addr = data
        addr_str = ":".join("{:02X}".format(b) for b in addr)
        _connections.append((conn_handle, addr_str))

    elif event == 2:  # _IRQ_CENTRAL_DISCONNECT
        # A central device has disconnected
        conn_handle, addr_type, addr = data
        _connections = [(h, a) for h, a in _connections if h != conn_handle]


def start(view_manager) -> bool:
    """Start the app - advertise this device so others can find and connect to it"""
    from picoware.system.bluetooth import Bluetooth
    from picoware.system.vector import Vector

    global _bluetooth, _advertising, _connections

    if _bluetooth is not None:
        del _bluetooth
        _bluetooth = None

    _advertising = False
    _connections = []

    # Initialize Bluetooth
    _bluetooth = Bluetooth()
    _bluetooth.callback = bluetooth_callback

    # Start advertising with device name
    try:
        _bluetooth.advertise()
        _advertising = True

        # Draw initial status
        draw = view_manager.draw
        draw.clear()
        draw.text(Vector(5, 5), "Bluetooth Advertising")
        draw.text(Vector(5, 25), "Name: Picoware")
        draw.text(Vector(5, 45), f"MAC: {_bluetooth.mac_address}")
        draw.text(Vector(5, 70), "Status: Broadcasting...")
        draw.text(Vector(5, 95), "Connections: 0")
        draw.text(Vector(5, draw.size.y - 30), "Press BACK to stop")
        draw.swap()

    except Exception as e:
        __alert(view_manager, f"Failed to start advertising: {str(e)}")
        return False

    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK
    from picoware.system.vector import Vector

    input_manager = view_manager.input_manager
    button: int = input_manager.button

    if button == BUTTON_BACK:
        input_manager.reset()
        view_manager.back()
        return

    draw = view_manager.draw
    draw.clear()
    draw.text(Vector(5, 5), "Bluetooth Advertising")
    draw.text(Vector(5, 25), "Name: Picoware")
    draw.text(Vector(5, 45), f"MAC: {_bluetooth.mac_address}")

    if _advertising:
        draw.text(Vector(5, 70), "Status: Broadcasting...")
    else:
        draw.text(Vector(5, 70), "Status: Inactive")

    draw.text(Vector(5, 95), f"Connections: {len(_connections)}")

    # Display connected devices
    y_offset = 115
    if _connections:
        draw.text(Vector(5, y_offset), "Connected:")
        y_offset += 18
        for i, (handle, addr) in enumerate(
            _connections[:3]
        ):  # Show up to 3 connections
            if y_offset < draw.size.y - 40:
                draw.text(Vector(5, y_offset), f" {i+1}. {addr}")
                y_offset += 15

    # Draw exit instruction
    draw.text(Vector(5, draw.size.y - 30), "Press BACK to stop")
    draw.swap()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _bluetooth, _advertising, _connections

    # Stop advertising
    if _bluetooth is not None:
        _advertising = False
        try:
            _bluetooth.advertise(None)
        except Exception:
            pass

        # Disconnect all connections
        if _connections:
            for conn_handle, _ in _connections:
                try:
                    _bluetooth.disconnect(conn_handle)
                except Exception:
                    pass

        del _bluetooth
        _bluetooth = None

    _connections = []

    collect()
