"""Network tools for the agent."""

from picoware.system.agent.tools.tool import Tool, Parameters, Property


def network_get_time_info(view_manager) -> dict:
    """Return the Picoware clock state in a model-friendly format.

    The RTC value is only authoritative when ``clock_is_set`` is true. The
    Time service sets that flag after either an NTP update or a manual date
    and time update.
    """
    offset = int(getattr(view_manager, "gmt_offset", 0))
    sign = "+" if offset >= 0 else "-"
    info = {
        "clock_is_set": False,
        "clock_is_fetching": False,
        "current_local_datetime": "",
        "gmt_offset_hours": offset,
        "utc_offset": "{}{:02d}:00".format(sign, abs(offset)),
    }

    clock = getattr(view_manager, "time", None)
    if clock is None:
        return info

    info["clock_is_set"] = bool(clock.is_set)
    info["clock_is_fetching"] = bool(clock.is_fetching)
    rtc = clock.rtc
    if rtc is None:
        return info

    try:
        value = rtc.datetime()
        info["current_local_datetime"] = (
            "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}".format(
                value[0],
                value[1],
                value[2],
                value[4],
                value[5],
                value[6],
            )
        )
    except (IndexError, OSError, TypeError, ValueError):
        pass
    return info


def network_get_info(view_manager) -> dict:
    """Get device, network, and current clock information.

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
    _info.update(network_get_time_info(view_manager))
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
    """Fetch one URL through an SD spool and return a bounded text excerpt.

    Args:
        view_manager (ViewManager): The view manager for thread access.
        url (str): The URL to send the request to.
        method (str): The HTTP method. Defaults to "GET".
        headers (dict or None): Optional request headers. Defaults to None.
        data (str or None): Optional request body data. Defaults to None.

    Returns:
        dict: Structured status and at most 8192 bytes of response text.
    """
    from picoware.system.http import HTTP
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "invalid_url", "message": "URL must use HTTP or HTTPS"}
    if len(url) > 2048:
        return {"ok": False, "error": "invalid_url", "message": "URL is longer than 2048 characters"}
    method = str(method or "GET").upper()
    if method not in ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"):
        return {"ok": False, "error": "invalid_method", "message": "unsupported HTTP method"}

    storage = view_manager.storage
    spool_path = "picoware/settings/agent_network_response.tmp"
    response = None
    http = HTTP(thread_manager=view_manager.thread_manager)
    storage.remove(spool_path)
    try:
        response = http.request(
            method,
            url,
            headers=headers,
            data=data,
            timeout=30,
            save_to_file=spool_path,
            storage=storage,
        )
        if response is None:
            return {"ok": False, "error": "request_failed", "message": "request returned no response"}
        status = int(getattr(response, "status_code", 0))
        size = storage.size(spool_path) if storage.exists(spool_path) else 0
        count = min(size, 8192)
        content = ""
        if count:
            try:
                content = storage.read(spool_path, "r", 0, count)
            except Exception:
                content = "[binary response omitted]"
        return {
            "ok": 200 <= status <= 299,
            "status_code": status,
            "url": url,
            "content": content,
            "response_bytes": size,
            "truncated": size > count,
        }
    except Exception as exc:
        return {"ok": False, "error": "request_failed", "message": str(exc)[:240]}
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass
        storage.remove(spool_path)

TOOL_NETWORK_GET_INFO = Tool(
    name="network_get_info",
    description=(
        "Get device, network, and current clock information. Call this at "
        "most once per user request and use the returned result."
    ),
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
    description="Fetch one known HTTP URL and return a bounded response excerpt. Do not use it as a search engine.",
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
