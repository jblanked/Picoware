"""BLE RSSI Monitor - Monitor signal strength of nearby devices in real-time"""

from utime import ticks_ms, ticks_diff

_bluetooth = None
_devices = {}  # addr_str -> (name, rssi, last_seen)
_last_update = 0
_scan_count = 0


def bluetooth_callback(event, data):
    """Bluetooth callback for scan results"""
    global _devices

    if event == 5:  # _IRQ_SCAN_RESULT
        addr_type, addr, adv_type, rssi, adv_data = data
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
    """Start the RSSI Monitor app"""
    from picoware.system.bluetooth import Bluetooth

    global _bluetooth, _devices, _scan_count

    if _bluetooth is not None:
        del _bluetooth
        _bluetooth = None

    _devices = {}
    _scan_count = 0

    _bluetooth = Bluetooth()
    _bluetooth.callback = bluetooth_callback

    # Start continuous scanning
    _bluetooth.scan(duration_ms=2000)

    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK, BUTTON_CENTER
    from picoware.system.vector import Vector

    global _last_update, _devices, _scan_count

    input_manager = view_manager.input_manager
    button: int = input_manager.button

    if button == BUTTON_BACK:
        input_manager.reset()
        view_manager.back()
        return

    if button == BUTTON_CENTER:
        input_manager.reset()
        # Clear device list
        _devices = {}
        _scan_count = 0

    # Update display periodically
    now = ticks_ms()
    if ticks_diff(now, _last_update) < 300:
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

    draw = view_manager.draw
    draw.erase()

    text_vec = Vector(5, 2)
    height = draw.size.y

    draw.text(text_vec, "RSSI Monitor")

    # Sort devices by RSSI (strongest first)
    sorted_devices = sorted(_devices.items(), key=lambda x: x[1][1], reverse=True)

    y = 22
    max_devices = (height - 60) // 16

    if not sorted_devices:
        text_vec.x, text_vec.y = 5, y
        draw.text(text_vec, "Scanning...")
    else:
        for i, (addr, (name, rssi, last_seen)) in enumerate(
            sorted_devices[:max_devices]
        ):
            if y > height - 40:
                break

            # Display name or shortened address
            display = name if name else addr[:11]
            display = display[:12]

            # Create RSSI bar visualization
            # RSSI typically ranges from -30 (very close) to -100 (far)
            bar_length = max(0, min(8, (rssi + 100) // 10))
            bar_sym = "|" * bar_length + " " * (8 - bar_length)

            text_vec.x, text_vec.y = 5, y
            draw.text(text_vec, f"{display[:10]}")
            text_vec.x, text_vec.y = 70, y
            draw.text(text_vec, f"{bar_sym} ")
            text_vec.x, text_vec.y = 130, y
            draw.text(text_vec, f"{rssi}dB")
            y += 16

    # Status bar
    text_vec.x, text_vec.y = 5, height - 35
    draw.text(text_vec, f"Devices: {len(_devices)}")
    text_vec.x, text_vec.y = 5, height - 20
    draw.text(text_vec, "CENTER: Clear | BACK: Exit")

    draw.swap()


def stop(view_manager) -> None:
    """Stop the app"""
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
