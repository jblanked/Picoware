"""WiFi Connect - Connect to a WiFi network."""

from utime import ticks_ms

_connect = None
_status_message: str = ""
_connection_start_time = 0
_ssid = ""
_password = ""
_is_flipper = False


def __connect_callback(state: int, error: str) -> None:
    """Callback for Wi-Fi connection status updates.

    Args:
        state (int): The Wi-Fi connection state.
        error (str): The connection error message.
    """
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
    """Build the connection status text.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.

    Returns:
        str: The status text to display.
    """
    global _status_message

    extension = "\n" if _is_flipper else "\n\n"

    wifi = view_manager.wifi
    if _is_flipper:
        text = f"Network {_ssid}\n"
    else:
        text = f"WiFi Setup{extension}"
        text += "Network: " + _ssid + "\n"


    if wifi.is_connected():
        _status_message = "Connected successfully!"
        text += "MAC Address: " + wifi.mac_address + "\n"
        text += "IP Address: " + wifi.device_ip + extension
        text += "Status: " + _status_message + extension
        
    else:
        
        text += "MAC Address: " + wifi.mac_address + extension
        text += "Status: " + _status_message + extension
        from picoware.system.wifi import (
            WIFI_STATE_IDLE,
            WIFI_STATE_CONNECTING,
            WIFI_STATE_CONNECTED,
            WIFI_STATE_TIMEOUT,
        )

        state = wifi.status()

        if state == WIFI_STATE_IDLE:
            text += f"Ready to connect{extension}"
        elif state == WIFI_STATE_CONNECTING:
            elapsed = (ticks_ms() - wifi.connection_start_time) // 1000
            text += f"Connecting... ({elapsed}s){extension}"
        elif state == WIFI_STATE_CONNECTED:
            text += f"Connected!{extension}"
        elif state == WIFI_STATE_TIMEOUT:
            text += f"Connection timeout{extension}"

    if not _is_flipper:
        text += "Press RIGHT to connect\n"
        text += "Press BACK to go back\n"
        text += "Press UP to disconnect"

    return text


def start(view_manager) -> bool:
    """Start the app and load the saved WiFi credentials.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.

    Returns:
        bool: True if the app started, False if no credentials are saved.
    """
    from picoware.applications.wifi.utils import load_wifi_password, load_wifi_ssid
    from picoware.system.boards import BOARD_FLIPPER_ZERO

    global _connect, _ssid, _password, _is_flipper
    _is_flipper = view_manager.board_id == BOARD_FLIPPER_ZERO

    _ssid = load_wifi_ssid(view_manager)
    _password = load_wifi_password(view_manager)

    if not _ssid:
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
    """Run the app and handle connection input.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_LEFT,
        BUTTON_UP,
        BUTTON_RIGHT,
        BUTTON_DOWN,
    )

    global _connect
    if _connect is None:
        return

    global _status_message
    global _connection_start_time

    button: int = view_manager.button
    wifi = view_manager.wifi

    if button == BUTTON_BACK:
        view_manager.back()
        return

    if button == BUTTON_UP and not _is_flipper:
        wifi.disconnect()
        _status_message = "Disconnected"
    elif button in (BUTTON_UP, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_DOWN):
        wifi.reset()
        _status_message = "Starting connection..."
        wifi.callback_connect = __connect_callback
        if wifi.connect_async(_ssid, _password, sta_mode=True):
            _connection_start_time = ticks_ms()
        else:
            _status_message = "Failed to start connection"

    _connect.set_text(_get_status_text(view_manager))


def stop(view_manager) -> None:
    """Stop the app and clean up.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
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
