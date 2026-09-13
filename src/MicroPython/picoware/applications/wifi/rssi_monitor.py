"""WiFi RSSI Monitor - Monitor signal strength of nearby WiFi networks in real-time"""

from utime import ticks_ms, ticks_diff
from picoware.system.colors import TFT_WHITE, TFT_RED, TFT_GREEN, TFT_YELLOW, TFT_ORANGE

_networks = {}  # ssid_str -> (bssid, channel, rssi, authmode, last_seen)
_last_update = 0
_scan_count = 0


def run(view_manager) -> None:
    """Run the app and update the RSSI display.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
    from picoware.system.buttons import BUTTON_BACK, BUTTON_CENTER
    from picoware.system.vector import Vector

    global _last_update, _networks, _scan_count

    button: int = view_manager.button

    if button == BUTTON_BACK:
        view_manager.back()
        return

    if button == BUTTON_CENTER:
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

    width = draw.size.x
    height = draw.size.y
    font_height = draw.font_size.y
    footer_y = max(0, height - font_height - 2)
    status_y = max(0, footer_y - font_height - 3)

    title = "WiFi RSSI Monitor"
    draw.text(Vector(max(0, (width - draw.len(title)) // 2), 2), title)

    # Sort networks by RSSI (strongest first)
    sorted_networks = sorted(_networks.items(), key=lambda x: x[1][2], reverse=True)

    y = 22
    max_networks = max(1, (status_y - y - 3) // 16)

    if not sorted_networks:
        message = "Scanning..."
        draw.text(Vector(max(0, (width - draw.len(message)) // 2), y), message)
    else:
        for i, (ssid, (bssid, channel, rssi, authmode, last_seen)) in enumerate(
            sorted_networks[:max_networks]
        ):
            if y > status_y - 3:
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

            if width < 180:
                color = TFT_WHITE

            rssi_text = f"{rssi}dB"
            suffix = f" {bar_sym} {rssi_text}"
            max_ssid_width = max(1, width - draw.len(suffix) - 2)
            max_ssid_chars = max(1, max_ssid_width // max(1, draw.font_size.x))
            row = f"{display_ssid[:max_ssid_chars]}{suffix}"
            draw.text(Vector(max(0, (width - draw.len(row)) // 2), y), row, color)
            y += 16

    # Status bar
    status = f"Networks: {len(_networks)}"
    draw.text(Vector(max(0, (width - draw.len(status)) // 2), status_y), status)

    footer = "CENTER: Clear | BACK: Exit"
    if width < 180:
        footer = "CTR: Clear | BACK: Exit"
    if draw.len(footer) > width:
        footer = "C:Clear | B:Exit"
    draw.text(Vector(max(0, (width - draw.len(footer)) // 2), footer_y), footer)

    draw.swap()


def start(view_manager) -> bool:
    """Start the WiFi RSSI Monitor app.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.

    Returns:
        bool: True if the app started, False if WiFi is unavailable.
    """
    global _networks, _scan_count, _last_update

    if view_manager.wifi is None:
        view_manager.alert("WiFi not available")
        return False

    _networks = {}
    _scan_count = 0
    _last_update = ticks_ms()

    return True


def stop(view_manager) -> None:
    """Stop the app and reset state.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
    from gc import collect

    global _networks, _scan_count, _last_update

    _networks = {}
    _scan_count = 0
    _last_update = 0

    collect()
