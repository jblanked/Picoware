"""WiFi RSSI Monitor - Monitor signal strength of nearby WiFi networks in real-time"""

from utime import ticks_ms, ticks_diff
from picoware.system.colors import TFT_WHITE, TFT_RED, TFT_GREEN, TFT_YELLOW, TFT_ORANGE

_networks = {}  # ssid_str -> (bssid, channel, rssi, authmode, last_seen)
_last_update = 0
_scan_count = 0


def start(view_manager) -> bool:
    """Start the WiFi RSSI Monitor app"""
    global _networks, _scan_count, _last_update

    if view_manager.wifi is None:
        view_manager.alert("WiFi not available")
        return False

    _networks = {}
    _scan_count = 0
    _last_update = ticks_ms()

    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK, BUTTON_CENTER
    from picoware.system.vector import Vector

    global _last_update, _networks, _scan_count

    input_manager = view_manager.input_manager
    button: int = input_manager.button

    if button == BUTTON_BACK:
        input_manager.reset()
        view_manager.back()
        return

    if button == BUTTON_CENTER:
        input_manager.reset()
        # Clear network list
        _networks = {}
        _scan_count = 0

    # Update display periodically
    now = ticks_ms()
    if ticks_diff(now, _last_update) < 500:
        return
    _last_update = now

    # Perform WiFi scan
    wifi = view_manager.wifi
    if wifi is not None:
        try:
            results = wifi.scan()
            for ssid, bssid, channel, rssi, authmode, hidden in results:
                ssid_str = ssid.decode("utf-8") if ssid else "<hidden>"
                if len(ssid_str) == 0:
                    ssid_str = "<hidden>"

                # Update or add network with timestamp
                _networks[ssid_str] = (bssid, channel, rssi, authmode, now)
        except Exception:
            pass  # Ignore scan errors

    # Remove stale networks (not seen in last 10 seconds)
    stale_threshold = 10000
    _networks = {
        ssid: (bssid, channel, rssi, authmode, last_seen)
        for ssid, (bssid, channel, rssi, authmode, last_seen) in _networks.items()
        if ticks_diff(now, last_seen) < stale_threshold
    }

    _scan_count += 1

    draw = view_manager.draw
    draw.erase()

    text_vec = Vector(5, 2)
    height = draw.size.y

    draw.text(text_vec, "WiFi RSSI Monitor")

    # Sort networks by RSSI (strongest first)
    sorted_networks = sorted(_networks.items(), key=lambda x: x[1][2], reverse=True)

    y = 22
    max_networks = (height - 60) // 16

    if not sorted_networks:
        text_vec.x, text_vec.y = 5, y
        draw.text(text_vec, "Scanning...")
    else:
        for i, (ssid, (bssid, channel, rssi, authmode, last_seen)) in enumerate(
            sorted_networks[:max_networks]
        ):
            if y > height - 40:
                break

            # Display SSID (truncate if needed)
            display_ssid = ssid[:12]

            # Create RSSI bar visualization
            # WiFi RSSI typically ranges from -30 (very close) to -90 (far)
            bar_length = max(0, min(8, (rssi + 90) // 8))
            bar_sym = "|" * bar_length + " " * (8 - bar_length)

            # Color based on RSSI strength
            if rssi >= -50:
                color = TFT_GREEN
            elif rssi >= -60:
                color = TFT_WHITE
            elif rssi >= -70:
                color = TFT_YELLOW
            elif rssi >= -80:
                color = TFT_ORANGE
            else:
                color = TFT_RED

            text_vec.x, text_vec.y = 5, y
            draw.text(text_vec, f"{display_ssid[:10]}", color)
            text_vec.x, text_vec.y = 70, y
            draw.text(text_vec, f"{bar_sym} ", color)
            text_vec.x, text_vec.y = 130, y
            draw.text(text_vec, f"{rssi}dB", color)
            y += 16

    # Status bar
    text_vec.x, text_vec.y = 5, height - 35
    draw.text(text_vec, f"Networks: {len(_networks)}")
    text_vec.x, text_vec.y = 5, height - 20
    draw.text(text_vec, "CENTER: Clear | BACK: Exit")

    draw.swap()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _networks, _scan_count, _last_update

    _networks = {}
    _scan_count = 0
    _last_update = 0

    collect()
