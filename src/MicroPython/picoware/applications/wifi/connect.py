_connect = None
_status_message: str = ""
_wifi_saved: bool = False
_connection_initiated = False
_last_update = 0
_connection_start_time = 0


def _get_status_text(view_manager) -> str:
    from picoware.applications.wifi.utils import load_wifi_ssid

    global _status_message
    global _wifi_saved

    wifi = view_manager.get_wifi()
    ssid = load_wifi_ssid(view_manager)
    text = "WiFi Setup\n\n"
    text += "Network: " + ssid + "\n"
    text += "Status: " + _status_message + "\n\n"

    if wifi.is_connected():
        text += "IP Address: " + wifi.device_ip + "\n"
        text += "Connected!\n\n"
        _status_message = "Connected successfully!"
        if not _wifi_saved:
            from picoware.applications.wifi.utils import save_wifi_settings

            _wifi_saved = save_wifi_settings(
                view_manager.get_storage(),
                wifi.ssid,
                wifi.password,
            )
    else:
        state = wifi.status()
        from picoware.system.wifi import WiFiState

        if state == WiFiState.IDLE:
            text += "Ready to connect\n\n"
        elif state == WiFiState.CONNECTING:
            from utime import ticks_ms

            elapsed = (ticks_ms() - wifi.connection_start_time) // 1000
            text += "Connecting... (" + str(elapsed) + "s)\n\n"
        elif state == WiFiState.CONNECTED:
            text += "Connected!\n\n"
        elif state == WiFiState.FAILED:
            text += "Connection failed\n\n"
        elif state == WiFiState.TIMEOUT:
            text += "Connection timeout\n\n"

    text += "Press RIGHT to connect\n"
    text += "Press LEFT/BACK to go back\n"
    text += "Press UP to disconnect"

    return text


def start(view_manager) -> bool:
    """Start the app."""

    global _connect

    if _connect is None:
        from picoware.gui.textbox import TextBox

        global _connection_initiated
        global _last_update
        global _connection_start_time
        global _status_message

        _connect = TextBox(
            view_manager.draw,
            0,
            320,
            view_manager.get_foreground_color(),
            view_manager.get_background_color(),
        )

        if _connect is None:
            return False

        # Reset state
        _connection_initiated = False
        _last_update = 0
        _connection_start_time = 0
        _status_message = (
            "Connected" if view_manager.get_wifi().is_connected() else "Initialized"
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
    from picoware.applications.wifi.utils import load_wifi_password, load_wifi_ssid
    from picoware.system.wifi import WiFiState
    from utime import ticks_ms

    global _connect
    if _connect is None:
        return

    global _status_message
    global _connection_initiated
    global _connection_start_time
    global _last_update

    input_manager = view_manager.input_manager
    button: int = input_manager.get_last_button()
    wifi = view_manager.get_wifi()
    ssid = load_wifi_ssid(view_manager)
    password = load_wifi_password(view_manager)

    if button in (BUTTON_BACK, BUTTON_LEFT):
        input_manager.reset(True)
        view_manager.back()
        return

    if button == BUTTON_UP:
        wifi.disconnect()
        _status_message = "Disconnected"
        input_manager.reset()
    elif button == BUTTON_RIGHT:
        input_manager.reset()
        state = wifi.status()
        if state == WiFiState.IDLE:
            _status_message = "Starting connection..."
            if wifi.connect(ssid, password, sta_mode=True, is_async=True):
                _connection_initiated = True
                _connection_start_time = wifi.connection_start_time
                _status_message = "Connecting..."
            else:
                _status_message = "Failed to start connection"
        elif state in (WiFiState.FAILED, WiFiState.TIMEOUT):
            wifi.reset()
            _status_message = "Retrying..."
            if wifi.connect(ssid, password, sta_mode=True, is_async=True):
                _connection_initiated = True
                _connection_start_time = wifi.connection_start_time
                _status_message = "Connecting..."
            else:
                _status_message = "Failed to start connection"

    if _connection_initiated:
        # call update to advance the connection process
        wifi.update()

        # update status based on current state
        state = wifi.status()

        if state == WiFiState.CONNECTED:
            _status_message = "Connected successfully!"
            _connection_initiated = False
        elif state == WiFiState.FAILED:
            _status_message = "Connection failed"
            _connection_initiated = False
        elif state == WiFiState.TIMEOUT:
            _status_message = "Connection timeout"
            _connection_initiated = False

        _connect.set_text(_get_status_text(view_manager))
        _last_update = ticks_ms()
    else:
        current_time = ticks_ms()
        if current_time - _last_update > 250:
            _connect.set_text(_get_status_text(view_manager))
            _last_update = current_time


def stop(view_manager) -> None:
    """Stop the app."""
    from gc import collect

    global _connect
    if _connect:
        del _connect
        _connect = None

    global _status_message
    global _wifi_saved
    global _connection_initiated
    global _last_update
    global _connection_start_time

    _status_message = ""
    _wifi_saved = False
    _connection_initiated = False
    _last_update = 0
    _connection_start_time = 0

    collect()
