from utime import ticks_ms, sleep
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
        from _thread import allocate_lock

        self.ssid = ""
        self.password = ""
        self.mode = STA_IF
        self.wlan = WLAN(self.mode)
        self._state = WIFI_STATE_IDLE
        self.connection_start_time = None
        self.connection_timeout = 10  # seconds
        self.error = ""
        #
        self._thread = None
        self._thread_running = False
        self._thread_lock = allocate_lock()
        #
        self._callback_connect: callable = None

    def __del__(self):
        """Destructor to clean up resources."""
        if self.wlan:
            self.wlan.active(False)
            del self.wlan
            self.wlan = None
        self.reset()
        self.callback_connect = None
        self.__close_thread()

    def __close_thread(self):
        """Internal method to close the background thread."""
        with self._thread_lock:
            self._thread_running = False
            self._thread = None

    @property
    def callback_connect(self) -> callable:
        """Get the connection callback function."""
        _callback = None
        with self._thread_lock:
            _callback = self._callback_connect
        return _callback

    @callback_connect.setter
    def callback_connect(self, func: callable) -> None:
        """
        Set the connection callback function.

        The callback function should accept two arguments: the Wi-Fi state and an error message (if any).
        """
        with self._thread_lock:
            self._callback_connect = func

    @property
    def device_ip(self):
        """Get the current device IP address."""
        addr = ""
        with self._thread_lock:
            return self.wlan.ifconfig()[0] if self.wlan else ""
        return addr

    @property
    def last_error(self) -> str:
        """Get the last connection error message."""
        error = ""
        with self._thread_lock:
            error = self.error
        return error

    @property
    def state(self) -> int:
        """Get the current Wi-Fi state."""
        _state = 0
        with self._thread_lock:
            _state = self._state
        return _state

    def connect(self, ssid: str, password: str, sta_mode: bool = True) -> bool:
        """
        Connect to a Wi-Fi network.

        :param ssid: SSID of the Wi-Fi network.
        :param password: Password for the Wi-Fi network.
        :param sta_mode: If True, use station mode (STA_IF), otherwise use access point mode (AP_IF).
        """
        from network import STA_IF, AP_IF

        _mode = STA_IF if sta_mode else AP_IF

        # sync
        if _mode == STA_IF:
            # check if already connected
            if self.wlan.isconnected() and self.ssid == self.wlan.config("ssid"):
                return True
            try:
                self._thread_running = True
                self._state = WIFI_STATE_CONNECTING
                self.connection_start_time = ticks_ms()
                self.wlan.active(True)
                if not self.wlan.isconnected():
                    self.wlan.connect(ssid, password)
                    while not self.wlan.isconnected():
                        if self.connection_start_time and (
                            ticks_ms() - self.connection_start_time
                        ) > (self.connection_timeout * 1000):
                            self._state = WIFI_STATE_TIMEOUT
                            self.wlan.disconnect()
                            self.connection_start_time = None
                            self.error = "Connection timed out."
                            if self._callback_connect:
                                self._callback_connect(self._state, self.error)
                            self._thread_running = False
                            self._thread = None
                            return False
                        if not self._thread_running:
                            return False
                        sleep(0.1)
                self.mode = _mode
                self.ssid = ssid
                self.password = password
                self._state = WIFI_STATE_CONNECTED
                self.connection_start_time = None
                self.error = ""
                if self._callback_connect:
                    self._callback_connect(self._state, self.error)
                self._thread_running = False
                self._thread = None
                return True
            except Exception as e:
                self.error = f"Error: {e}"
                return False

        try:
            self.wlan.config(ssid=ssid, password=password)
            self.wlan.active(True)
            self.mode = _mode
            self.ssid = ssid
            self.password = password
            return True
        except Exception as e:
            self.error = f"Failed to set up Access Point: {e}"
            return False

    def connect_async(self, ssid: str, password: str, sta_mode: bool = True) -> bool:
        """
        Connect to a Wi-Fi network.

        :param ssid: SSID of the Wi-Fi network.
        :param password: Password for the Wi-Fi network.
        :param sta_mode: If True, use station mode (STA_IF), otherwise use access point mode (AP_IF).
        """
        try:
            import _thread

            # Start the request in a separate thread
            self._thread = _thread.start_new_thread(
                self.connect,
                (ssid, password, sta_mode),
            )
            return True
        except Exception as e:
            self.error = f"Failed to start WiFi connection thread: {e}"
            return False

    def disconnect(self):
        """Disconnect from the Wi-Fi network."""
        with self._thread_lock:
            self.wlan.disconnect()

    def is_connected(self):
        """Check if the device is connected to a Wi-Fi network."""
        status = False
        with self._thread_lock:
            status = self.wlan.isconnected()
        return status

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

        with self._thread_lock:
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
        with self._thread_lock:
            self.wlan.active(False)
            self.ssid = ""
            self.password = ""
            self._state = WIFI_STATE_IDLE
            self.connection_start_time = None
            self.connection_timeout = 10  # seconds
            self.error = ""
        self.__close_thread()
