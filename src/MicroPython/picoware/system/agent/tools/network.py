"""Network tools for the agent."""

from micropython import const
from picoware.system.agent.tools.tool import Tool, Parameters, Property


MAX_NETWORK_RESPONSE_BYTES = const(8192)
MAX_NETWORK_SPOOL_BYTES = const(262144)
NETWORK_RESPONSE_PATH = "picoware/settings/agent_network_response.tmp"


def _decode_utf8_device_safe(value) -> str:
    """Decode UTF-8 while replacing malformed bytes on MicroPython.

    MicroPython does not consistently implement CPython's ``errors`` argument
    for ``bytes.decode``.  Keep the common valid path allocation-light and use
    an equal-sized sanitized copy only after a decoding failure.
    """
    raw = bytes(value)
    try:
        return raw.decode("utf-8")
    except UnicodeError:
        sanitized = bytearray(raw)
        size = len(sanitized)
        index = 0
        while index < size:
            first = sanitized[index]
            length = 0
            if first <= 0x7F:
                length = 1
            elif 0xC2 <= first <= 0xDF and index + 1 < size:
                second = sanitized[index + 1]
                if 0x80 <= second <= 0xBF:
                    length = 2
            elif 0xE0 <= first <= 0xEF and index + 2 < size:
                second = sanitized[index + 1]
                third = sanitized[index + 2]
                second_ok = (
                    0xA0 <= second <= 0xBF if first == 0xE0 else
                    0x80 <= second <= 0x9F if first == 0xED else
                    0x80 <= second <= 0xBF
                )
                if second_ok and 0x80 <= third <= 0xBF:
                    length = 3
            elif 0xF0 <= first <= 0xF4 and index + 3 < size:
                second = sanitized[index + 1]
                third = sanitized[index + 2]
                fourth = sanitized[index + 3]
                second_ok = (
                    0x90 <= second <= 0xBF if first == 0xF0 else
                    0x80 <= second <= 0x8F if first == 0xF4 else
                    0x80 <= second <= 0xBF
                )
                if (
                    second_ok and 0x80 <= third <= 0xBF
                    and 0x80 <= fourth <= 0xBF
                ):
                    length = 4
            if length:
                index += length
            else:
                sanitized[index] = 0x3F
                index += 1
        return bytes(sanitized).decode("utf-8")


class NetworkResponseStreamSink:
    """Spool a response to SD while retaining only bounded tool text."""

    __slots__ = (
        "storage", "path", "file", "http", "body", "total_bytes",
        "spooled_bytes", "truncated", "error",
    )

    def __init__(self, storage=None, path: str = NETWORK_RESPONSE_PATH, http=None):
        self.storage = storage
        self.path = path
        self.file = None
        self.http = http
        self.body = bytearray()
        self.total_bytes = 0
        self.spooled_bytes = 0
        self.truncated = False
        self.error = ""
        if storage is not None:
            storage.remove(path)
            self.file = storage.file_open(path)
            if self.file is None:
                self.error = "could not open the temporary network response spool"

    def write(self, value) -> None:
        if not isinstance(value, (bytes, bytearray)) or not value:
            return

        value_length = len(value)
        accepted = min(
            value_length,
            max(0, MAX_NETWORK_SPOOL_BYTES - self.total_bytes),
        )
        chunk_value = value[:accepted]
        self.total_bytes += accepted

        remaining = MAX_NETWORK_RESPONSE_BYTES - len(self.body)
        if remaining > 0:
            self.body.extend(chunk_value[:remaining])
        if accepted > remaining or accepted < value_length:
            self.truncated = True

        if self.file is not None and chunk_value:
            if not self.storage.file_write(self.file, chunk_value, "wb"):
                self.error = "could not write the temporary network response spool"
                if self.http is not None:
                    self.http.close()
                return
            self.spooled_bytes += len(chunk_value)
        if self.total_bytes >= MAX_NETWORK_SPOOL_BYTES:
            self.truncated = True
            if self.http is not None:
                self.http.close()

    def flush(self) -> None:
        return

    def close(self) -> None:
        if self.file is not None:
            try:
                self.storage.file_close(self.file)
            except OSError:
                pass
            self.file = None

    def text(self) -> str:
        text = _decode_utf8_device_safe(self.body)
        if self.truncated:
            text += "\n[Response truncated to fit device memory.]"
        return text


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
    """Send an HTTP request and return its response text.

    Args:
        view_manager (ViewManager): The view manager for thread access.
        url (str): The URL to send the request to.
        method (str): The HTTP method. Defaults to "GET".
        headers (dict or None): Optional request headers. Defaults to None.
        data (str or None): Optional request body data. Defaults to None.

    Returns:
        str: The response text, prefixed with its HTTP status on failure.
    """
    from picoware.system.http import HTTP
    http = HTTP(thread_manager=view_manager.thread_manager)
    storage = getattr(view_manager, "storage", None)
    sink = NetworkResponseStreamSink(storage, http=http)
    response = None
    try:
        if sink.error:
            return "Request failed: " + sink.error
        response = http.request(
            method,
            url,
            headers=headers,
            data=data,
            timeout=30,
            storage=storage,
            stream_sink=sink,
        )
        if response is None:
            if sink.body:
                return sink.text()
            return "Request failed: no response"
        text = sink.text()
        if sink.error:
            return "Request failed: " + sink.error
        if 200 <= response.status_code <= 299:
            return text
        return "HTTP " + str(response.status_code) + ": " + text
    finally:
        if response is not None:
            response.close()
        sink.close()
        if storage is not None:
            storage.remove(NETWORK_RESPONSE_PATH)

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
    description="Send an HTTP request and return the response text.",
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
