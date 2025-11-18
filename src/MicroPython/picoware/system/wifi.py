from micropython import const

WIFI_STATE_INACTIVE = const(-1)
WIFI_STATE_IDLE = const(0)
WIFI_STATE_CONNECTING = const(1)
WIFI_STATE_CONNECTED = const(2)
WIFI_STATE_ISSUE = const(3)
WIFI_STATE_TIMEOUT = const(4)


class WiFi:
    """Class to manage WiFi functionality on a MicroPython device."""

    def __init__(self):
        """
        Initialize the WiFi class.
        """
        from network import STA_IF, WLAN

        self.ssid = ""
        self.password = ""
        self.mode = STA_IF
        self.wlan = WLAN(self.mode)
        self.local_ip = None
        self.state = WIFI_STATE_IDLE
        self.connection_start_time = None
        self.connection_timeout = 10  # seconds
        self.connection_attempts = 0
        self.pending_ssid = ""
        self.pending_password = ""
        self.error = ""

    def __del__(self):
        """Destructor to clean up resources."""
        if self.wlan:
            self.wlan.active(False)
            del self.wlan
            self.wlan = None
        self.reset()

    @property
    def device_ip(self):
        """Get the current device IP address."""
        return self.wlan.ifconfig()[0] if self.wlan else ""

    @property
    def last_error(self):
        """Get the last connection error message."""
        return self.error

    def connect(
        self, ssid: str, password: str, sta_mode: bool = True, is_async: bool = False
    ) -> bool:
        """
        Connect to a Wi-Fi network.

        :param ssid: SSID of the Wi-Fi network.
        :param password: Password for the Wi-Fi network.
        :param sta_mode: If True, use station mode (STA_IF), otherwise use access point mode (AP_IF).
        :param is_async: If True, use asynchronous connection handling.
        """
        from time import sleep
        from network import STA_IF, AP_IF

        _mode = STA_IF if sta_mode else AP_IF

        if not is_async:
            # sync
            if _mode == STA_IF:
                try:
                    self.wlan.active(True)
                    if not self.wlan.isconnected():
                        self.wlan.connect(ssid, password)
                        while not self.wlan.isconnected():
                            sleep(1)
                    self.mode = _mode
                    self.ssid = ssid
                    self.password = password
                    self.local_ip = self.wlan.ifconfig()[0]
                    return True
                except Exception as e:
                    print("Error:", e)
                    return False

            try:
                self.wlan.config(ssid=ssid, password=password)
                self.wlan.active(True)
                self.mode = _mode
                self.ssid = ssid
                self.password = password
                self.local_ip = self.wlan.ifconfig()[0]
                return True
            except Exception as e:
                print("Failed to set up Access Point:", e)
                return False

        # async
        from utime import ticks_ms

        self.reset()
        self.pending_ssid = ssid
        self.pending_password = password
        self.state = WIFI_STATE_CONNECTING
        self.connection_start_time = ticks_ms()
        self.mode = _mode

        if _mode == STA_IF:
            self.wlan.active(True)
            self.wlan.connect(ssid, password)
        else:
            self.wlan.config(ssid=ssid, password=password)
            self.wlan.active(True)

        return True

    def disconnect(self):
        """Disconnect from the Wi-Fi network."""
        self.wlan.disconnect()

    def is_connected(self):
        """Check if the device is connected to a Wi-Fi network."""
        return self.wlan.isconnected()

    def scan(self) -> list:
        """Scan for available Wi-Fi networks."""
        self.wlan.active(True)
        return self.wlan.scan()

    def status(self) -> int:
        """Get the current Wi-Fi connection status."""
        from network import (
            STAT_IDLE,
            STAT_CONNECTING,
            STAT_GOT_IP,
            STAT_NO_AP_FOUND,
            STAT_WRONG_PASSWORD,
            STAT_CONNECT_FAIL,
        )

        status = self.wlan.status()

        if status == STAT_IDLE:
            return WIFI_STATE_IDLE
        if status == STAT_CONNECTING:
            return WIFI_STATE_CONNECTING
        if status == STAT_GOT_IP:
            return WIFI_STATE_CONNECTED
        if status == STAT_WRONG_PASSWORD:
            self.error = "Wrong password."
            return WIFI_STATE_ISSUE
        if status == STAT_NO_AP_FOUND:
            self.error = "No access point found."
            return WIFI_STATE_ISSUE
        if status == STAT_CONNECT_FAIL:
            self.error = "Failed to connect."
            return WIFI_STATE_ISSUE

        self.error = "Status not recognized so deemed inactive."
        return WIFI_STATE_INACTIVE

    def reset(self):
        """Reset the Wi-Fi configuration."""
        self.wlan.active(False)
        self.ssid = ""
        self.password = ""
        self.local_ip = None
        self.state = WIFI_STATE_IDLE
        self.connection_start_time = None
        self.connection_timeout = 10  # seconds
        self.connection_attempts = 0
        self.pending_ssid = ""
        self.pending_password = ""
        self.error = ""

    def update(self) -> bool:
        """Update the Wi-Fi connection state."""
        from utime import ticks_ms

        if self.state != WIFI_STATE_CONNECTING:
            return self.state == WIFI_STATE_CONNECTED

        # Check for timeout
        if self.connection_start_time and (ticks_ms() - self.connection_start_time) > (
            self.connection_timeout * 1000
        ):
            self.state = WIFI_STATE_TIMEOUT
            self.wlan.disconnect()
            self.connection_start_time = None
            self.connection_attempts = 0
            self.error = "Connection timed out."
            return False

        if self.status() == WIFI_STATE_CONNECTED:
            self.ssid = self.pending_ssid
            self.password = self.pending_password
            self.state = WIFI_STATE_CONNECTED
            self.connection_start_time = None
            self.connection_attempts = 0
            return True

        return False
