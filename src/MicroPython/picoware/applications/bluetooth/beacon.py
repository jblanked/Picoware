"""BLE Beacon - Simple beacon broadcaster"""

_bluetooth = None
_broadcasting = False
_last_update = 0
_beacon_count = 0


def start(view_manager) -> bool:
    """Start the Beacon app"""
    from picoware.system.bluetooth import Bluetooth

    global _bluetooth, _broadcasting, _beacon_count

    if _bluetooth is not None:
        del _bluetooth
        _bluetooth = None

    _broadcasting = False
    _beacon_count = 0

    _bluetooth = Bluetooth()

    try:
        if _bluetooth.start_peripheral(name="Picoware-Beacon", interval_us=100000):
            _broadcasting = True
        else:
            view_manager.alert("Failed to start BLE peripheral.")
            return False
    except Exception as e:
        view_manager.alert("Error starting BLE peripheral:\n{}".format(e))
        return False

    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK
    from picoware.system.vector import Vector
    from utime import ticks_ms, ticks_diff

    global _last_update, _beacon_count

    input_manager = view_manager.input_manager
    button: int = input_manager.button

    if button == BUTTON_BACK:
        input_manager.reset()
        view_manager.back()
        return

    # Update display periodically
    now = ticks_ms()
    if ticks_diff(now, _last_update) < 500:
        return
    _last_update = now

    if _broadcasting:
        _beacon_count += 1

    draw = view_manager.draw
    draw.erase()

    text_vec = Vector(5, 5)

    draw.text(text_vec, "BLE Beacon")
    text_vec.y = 30
    draw.text(text_vec, "Name: Picoware-Beacon")
    text_vec.y = 50
    draw.text(text_vec, f"MAC: {_bluetooth.mac_address}")

    if _broadcasting:
        text_vec.y = 80
        draw.text(text_vec, "Status: Broadcasting")
        text_vec.y = 100
        draw.text(text_vec, "Interval: 100ms")
        text_vec.y = 120
        draw.text(text_vec, f"Beacons: {_beacon_count}")
    else:
        text_vec.y = 80
        draw.text(text_vec, "Status: Stopped")

    # Show if anyone connected
    conn_count = len(_bluetooth.central_connections)
    if conn_count > 0:
        text_vec.y = 145
        draw.text(text_vec, f"Connections: {conn_count}")

    text_vec.y = draw.size.y - 20
    draw.text(text_vec, "BACK: Stop & Exit")
    draw.swap()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _bluetooth, _broadcasting, _beacon_count, _last_update

    if _bluetooth is not None:
        _bluetooth.stop_peripheral()
        del _bluetooth
        _bluetooth = None

    _broadcasting = False
    _beacon_count = 0
    _last_update = 0

    collect()
