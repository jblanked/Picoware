"""Virtual FlipperHTTP Wi-Fi board. Never accesses a physical UART/radio."""

import json
import network
import sim_runtime


class FlipperHTTP:
    def __init__(self):
        self._input = b""
        self._wlan = network.WLAN(network.STA_IF)

    def _command(self, command):
        if command == "[PING]":
            return "[PONG]\n"
        if command == "[WIFI/DISCONNECT]":
            self._wlan.disconnect()
            self._wlan.active(False)
            return ""  # Disconnect is a fire-and-forget command.
        if command == "[WIFI/SCAN]":
            if sim_runtime.network_mode == "off":
                return "[ERROR] Wi-Fi disabled\n"
            # Scanning must not change an existing station/AP connection.
            networks = [item[0].decode() for item in network.WLAN(network.STA_IF).scan()]
            return "[GET/SUCCESS]\n" + json.dumps({"networks": networks}) + "\n[GET/END]\n"
        if command == "[WIFI/STATUS]":
            return ("true" if self._wlan.isconnected() else "false") + "\n"
        if command == "[IP/ADDRESS]":
            return (self._wlan.ifconfig()[0] if self._wlan.isconnected() else "0.0.0.0") + "\n"
        for prefix, mode in (("[WIFI/SAVE]", network.STA_IF), ("[WIFI/AP]", network.AP_IF)):
            if command.startswith(prefix):
                if sim_runtime.network_mode == "off":
                    return "[ERROR] Wi-Fi disabled\n"
                try:
                    data = json.loads(command[len(prefix):])
                    ssid = data["ssid"]
                    password = data.get("password", "")
                    if not isinstance(ssid, str) or not ssid or not isinstance(password, str):
                        raise ValueError("invalid credentials")
                except (ValueError, KeyError, TypeError):
                    return "[ERROR] Invalid Wi-Fi configuration\n"
                self._wlan.disconnect()
                self._wlan.active(False)
                self._wlan = network.WLAN(mode)
                if mode == network.AP_IF:
                    self._wlan.config(ssid=ssid, password=password)
                self._wlan.active(True)
                if mode == network.STA_IF:
                    self._wlan.connect(ssid, password)
                if not self._wlan.isconnected():
                    return "[ERROR] Wi-Fi connection failed\n"
                return "[WIFI/CONNECTED]\n" if mode == network.STA_IF else "[AP/CONNECTED]\n"
        return "[ERROR] Unsupported FlipperHTTP command\n"

    def feed(self, data):
        if not getattr(sim_runtime, "flipper_wifi_attached", True):
            self._input = b""
            return b""
        self._input += bytes(data)
        if len(self._input) > 4096:
            self._input = b""
            return b"[ERROR] Command too long\n"
        response = ""
        while b"\n" in self._input:
            line, self._input = self._input.split(b"\n", 1)
            try:
                response += self._command(line.rstrip(b"\r").decode())
            except UnicodeError:
                response += "[ERROR] Invalid command encoding\n"
        return response.encode()
