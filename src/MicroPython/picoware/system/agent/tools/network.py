"""Network tools for the agent."""

from picoware.system.agent.tools.tool import Tool, Parameters, Property

def network_get_info(view_manager) -> dict:
    """Get network information about the device.

    Args:
        view_manager (ViewManager): The view manager for system access.

    Returns:
        dict: A dict of device and network info.
    """
    from picoware.system.system import System
    syst = System()
    _info = {
        "is_wifi_connected": False,
        "board_id": syst.board_id,
        "board_name": syst.board_name,
        "device_name": syst.device_name,
        "free_heap": syst.free_heap,
        "free_psram": syst.free_psram,
        "freq": syst.freq,
        "has_audio": syst.has_audio,
        "has_wifi": syst.has_wifi,
        "free_flash": syst.free_flash,
        "total_flash": syst.total_flash,
        "used_flash": syst.used_flash,
        "total_heap": syst.total_heap,
        "total_psram": syst.total_psram,
        "used_heap": syst.used_heap,
        "used_psram": syst.used_psram,
        "version": syst.version,
    }
    if not view_manager.has_wifi:
        return _info
    _wifi = view_manager.wifi
    _info.update({
        "is_wifi_connected": _wifi.is_connected(),
        "wifi_status": _wifi.status(),
        "wifi_state": _wifi.state,
        "wifi_mac_address": _wifi.mac_address,
    })
    return _info

def network_scan_wifi(view_manager) -> list:
    """Scan for available Wi-Fi networks.

    Args:
        view_manager (ViewManager): The view manager for Wi-Fi access.

    Returns:
        list: A list of SSID strings with signal strength.
    """
    if not view_manager.has_wifi:
        return []
    ssids: list[str] = []

    results = view_manager.wifi.scan()
    
    for ssid, bssid, channel, rssi, authmode, hidden in results:
        _ssid = ssid.decode("utf-8")
        if len(_ssid) == 0:
            _ssid = "<hidden>"
        if _ssid not in ssids:
            ssids.append(f"{_ssid} ({rssi}dB)")
    return ssids

def network_scan_ble(view_manager, timeout_ms: int = 3000) -> list:
    """Scan for nearby Bluetooth devices.

    Args:
        view_manager (ViewManager): The view manager for system access.
        timeout_ms (int): Scan duration in milliseconds. Defaults to 3000.

    Returns:
        list: A list of device name and address strings.
    """
    if not view_manager.has_wifi:
        return []
    from picoware.system.bluetooth import Bluetooth
    from picoware.applications.bluetooth.scan import bluetooth_callback, _scanned_devices
    from utime import ticks_ms, ticks_diff
    ble = Bluetooth()
    ble.callback = bluetooth_callback
    if not ble.scan():
        return []
    devices = []
    now = ticks_ms()
    # wait for the timeout
    while ticks_diff(ticks_ms(), now) < timeout_ms:
        pass
    for _, addr, name, rssi in _scanned_devices:
        addr_str = ":".join("{:02X}".format(b) for b in addr)
        if name:
            devices.append(f"{name} ({addr_str}, {rssi}dB)")
        else:
            devices.append(f"{addr_str} ({rssi}dB)")
    return devices

    

def network_send_request(view_manager, url, method="GET", headers=None, data=None):
    """Send an HTTP request and return the response text.

    Args:
        view_manager (ViewManager): The view manager for thread access.
        url (str): The URL to send the request to.
        method (str): The HTTP method. Defaults to "GET".
        headers (dict or None): Optional request headers. Defaults to None.
        data (str or None): Optional request body data. Defaults to None.

    Returns:
        str: The response text.
    """
    from picoware.system.http import HTTP
    http = HTTP(thread_manager=view_manager.thread_manager)
    response = http.request(method, url, headers=headers, data=data)
    return response.text

TOOL_NETWORK_GET_INFO = Tool(
    name="network_get_info",
    description="Get network information",
    parameters=Parameters(properties=[]),
)

TOOL_NETWORK_SCAN_WIFI = Tool(
    name="network_scan_wifi",
    description="Scan for available Wi-Fi networks and return a list of SSIDs.",
    parameters=Parameters(properties=[]),
)

TOOL_NETWORK_SCAN_BLE = Tool(
    name="network_scan_ble",
    description="Scan for nearby Bluetooth devices and return a list of device names and addresses.",
    parameters=Parameters(properties=[
            Property(
                name="timeout_ms",
                type="integer",
                description="The duration to scan for Bluetooth devices in milliseconds (default: 3000).",
            ),
        ]
    ),
)

TOOL_NETWORK_SEND_REQUEST = Tool(
    name="network_send_request",
    description="Send an HTTP request and return the response.",
    parameters=Parameters(
        properties=[
            Property(
                name="url",
                type="string",
                description="The URL to send the request to.",
                required=True,
            ),
            Property(
                name="method",
                type="string",
                description="The HTTP method to use (e.g. GET, POST).",
            ),
            Property(
                name="headers",
                type="object",
                description="Optional HTTP headers to include in the request.",
            ),
            Property(
                name="data",
                type="string",
                description="Optional data to include in the request body (for POST requests).",
            ),
        ]
    ),
)