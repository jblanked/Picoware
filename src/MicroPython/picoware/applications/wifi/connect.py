from utime import ticks_ms

_connect = None
_status_message: str = ""
_connection_start_time = 0
_ssid = ""
_password = ""


def __connect_callback(state: int, error: str) -> None:
    """Callback for Wi-Fi connection status updates."""
    from picoware.system.wifi import (
        WIFI_STATE_CONNECTED,
        WIFI_STATE_TIMEOUT,
        WIFI_STATE_ISSUE,
    )

    global _status_message
    if state == WIFI_STATE_CONNECTED:
        _status_message = "Connected successfully!"
    elif state == WIFI_STATE_ISSUE:
        _status_message = error or "Connection issue"
    elif state == WIFI_STATE_TIMEOUT:
        _status_message = "Connection timeout"


def _get_status_text(view_manager) -> str:
    global _status_message

    wifi = view_manager.wifi
    text = "WiFi Setup\n\n"
    text += "Network: " + _ssid + "\n"
    text += "Status: " + _status_message + "\n\n"

    if wifi.is_connected():
        text += "IP Address: " + wifi.device_ip + "\n"
        text += "Connected!\n\n"
        _status_message = "Connected successfully!"
    else:
        from picoware.system.wifi import (
            WIFI_STATE_IDLE,
            WIFI_STATE_CONNECTING,
            WIFI_STATE_CONNECTED,
            WIFI_STATE_TIMEOUT,
        )

        state = wifi.status()

        if state == WIFI_STATE_IDLE:
            text += "Ready to connect\n\n"
        elif state == WIFI_STATE_CONNECTING:
            elapsed = (ticks_ms() - wifi.connection_start_time) // 1000
            text += f"Connecting... ({elapsed}s)\n\n"
        elif state == WIFI_STATE_CONNECTED:
            text += "Connected!\n\n"
        elif state == WIFI_STATE_TIMEOUT:
            text += "Connection timeout\n\n"

    text += "Press RIGHT to connect\n"
    text += "Press LEFT/BACK to go back\n"
    text += "Press UP to disconnect"

    return text


def start(view_manager) -> bool:
    """Start the app."""
    from picoware.applications.wifi.utils import load_wifi_password, load_wifi_ssid

    global _connect, _ssid, _password

    _ssid = load_wifi_ssid(view_manager)
    _password = load_wifi_password(view_manager)

    if not _ssid or not _password:
        view_manager.alert(
            "No saved WiFi credentials found.\nPlease set up WiFi in the Settings app.",
        )
        return False

    if _connect is None:
        from picoware.gui.textbox import TextBox

        global _connection_start_time
        global _status_message

        _connect = TextBox(
            view_manager.draw,
            0,
            view_manager.draw.size.y,
            view_manager.foreground_color,
            view_manager.background_color,
        )

        if _connect is None:
            return False

        # Reset state
        _connection_start_time = 0
        _status_message = (
            "Connected" if view_manager.wifi.is_connected() else "Disconnected"
        )
        _connect.set_text(_get_status_text(view_manager))

    return True


def run(view_manager) -> None:
    """Run the app."""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_LEFT,
        BUTTON_UP,
        BUTTON_RIGHT,
    )

    global _connect
    if _connect is None:
        return

    global _status_message
    global _connection_start_time

    input_manager = view_manager.input_manager
    button: int = input_manager.button
    wifi = view_manager.wifi

    if button in (BUTTON_BACK, BUTTON_LEFT):
        input_manager.reset()
        view_manager.back()
        return

    if button == BUTTON_UP:
        wifi.disconnect()
        _status_message = "Disconnected"
        input_manager.reset()
    elif button == BUTTON_RIGHT:
        input_manager.reset()
        wifi.reset()
        _status_message = "Starting connection..."
        wifi.callback_connect = __connect_callback
        if wifi.connect_async(_ssid, _password, sta_mode=True):
            _connection_start_time = ticks_ms()
        else:
            _status_message = "Failed to start connection"

    _connect.set_text(_get_status_text(view_manager))


def stop(view_manager) -> None:
    """Stop the app."""
    from gc import collect

    global _connect
    if _connect:
        del _connect
        _connect = None

    global _status_message
    global _connection_start_time
    global _ssid
    global _password

    _status_message = ""
    _connection_start_time = 0
    _ssid = ""
    _password = ""

    collect()
