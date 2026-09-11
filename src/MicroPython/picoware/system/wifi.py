"""WiFi - WiFi networking interface."""

from utime import ticks_diff, ticks_ms, sleep
from ujson import dumps, loads
from micropython import const

WIFI_STATE_INACTIVE = const(-1)
WIFI_STATE_IDLE = const(0)
WIFI_STATE_CONNECTING = const(1)
WIFI_STATE_CONNECTED = const(2)
WIFI_STATE_ISSUE = const(3)
WIFI_STATE_TIMEOUT = const(4)


class WiFi:
    """Class to manage WiFi functionality on a MicroPython device.

    Attributes:
        ssid (str): The SSID of the WiFi network.
        password (str): The password for the WiFi network.
        mode (int): The WiFi mode (STA_IF or AP_IF).
        wlan (network.WLAN): The WLAN object for managing WiFi connections.
        connection_start_time (int): The timestamp when the connection attempt started.
        connection_timeout (int): The timeout duration for WiFi connections in seconds.
        error (str): The last error message encountered during WiFi operations.
    """

    def __init__(self, thread_manager=None, timeout: int = 10) -> None:
        """Initialize the WiFi class.

        Args:
            thread_manager (ThreadManager): Optional ThreadManager instance for managed threading. Defaults to None.
            timeout (int): Connection timeout in seconds. Defaults to 10.
        """
        from picoware.system.boards import BOARD_FLIPPER_ZERO, BOARD_ID

        self._is_flipper = BOARD_ID == BOARD_FLIPPER_ZERO

        self._thread_lock = None
        if not self._is_flipper:
            try:
                from _thread import allocate_lock
                self._thread_lock = allocate_lock()
            except ImportError:
                pass

        self.ssid = ""
        self.password = ""
        self._wifi_uart = None
        self.error = ""
        self.wlan = None
        self.mode = 0
        if self._is_flipper:
            try:
                self._wifi_uart = WiFiUART(timeout_ms=timeout * 1000)
            except Exception as error:
                self._wifi_uart = None
                self.error = str(error)
        else:
            from network import STA_IF, WLAN
            self.mode = STA_IF
            self.wlan = WLAN(self.mode)
        self._state = WIFI_STATE_IDLE
        self.connection_start_time = None
        self.connection_timeout = timeout
        #
        self._thread = None
        self._thread_running = False
        self._thread_manager = thread_manager
        self._current_task = None
        #
        self._callback_connect: callable = None

    def __del__(self):
        """Destructor to clean up resources."""
        if self._is_flipper and self._wifi_uart:
            self._wifi_uart.close()
            del self._wifi_uart
            self._wifi_uart = None
            return
        self.reset()
        self.wlan = None
        self.callback_connect = None
        self.__close_thread()

    def __close_thread(self):
        """Internal method to close the background thread."""
        if self._is_flipper:
            return
        if self._current_task:
            self._current_task.stop()
            self._current_task = None
        if self._thread_lock is None:
            return
        with self._thread_lock:
            self._thread_running = False
            self._thread = None

    def _should_continue(self) -> bool:
        """Check if the operation should continue running."""
        if self._is_flipper or self._thread_lock is None:
            return False
        
        with self._thread_lock:
            if self._thread_manager is not None and self._current_task is not None:
                return self._thread_running and not self._current_task.should_stop
            return self._thread_running

    @property
    def callback_connect(self) -> callable:
        """Get the connection callback function."""
        if self._is_flipper:
            return self._callback_connect
        if self._thread_lock is None:
            return None

        with self._thread_lock:
            return self._callback_connect

    @callback_connect.setter
    def callback_connect(self, func: callable) -> None:
        """Set the connection callback function.

        The callback receives the Wi-Fi state and an error message (if any).

        Args:
            func (callable): The callback function to set.
        """
        if self._is_flipper:
            self._callback_connect = func
            return
        if self._thread_lock is None:
            return

        with self._thread_lock:
            self._callback_connect = func

    @property
    def device_ip(self):
        """Get the current device IP address."""
        if self._is_flipper:
            return self._wifi_uart.device_ip if self._wifi_uart else ""
        if self._thread_lock is None:
            return ""

        with self._thread_lock:
            return self.wlan.ifconfig()[0] if self.wlan else ""

    @property
    def last_error(self) -> str:
        """Get the last connection error message."""
        if self._is_flipper:
            if not self._wifi_uart:
                return self.error
            return self._wifi_uart.last_error

        if self._thread_lock is None:
            return ""

        with self._thread_lock:
            return self.error

    @property
    def mac_address(self) -> str:
        """Get the MAC address of the Wi-Fi interface."""
        if self._is_flipper:
            if not self._wifi_uart:
                return ""
            return self._wifi_uart.mac_address
        
        if self._thread_lock is None:
            return ""
        
        with self._thread_lock:
            mac = self.wlan.config("mac")
            return ":".join("{:02x}".format(b) for b in mac)

    @property
    def state(self) -> int:
        """Get the current Wi-Fi state."""
        if self._is_flipper:
            if not self._wifi_uart:
                return WIFI_STATE_INACTIVE
            return self._wifi_uart.state
        
        if self._thread_lock is None:
            return WIFI_STATE_INACTIVE
        
        with self._thread_lock:
            return self._state

    @property
    def timeout(self) -> int:
        """Get the connection timeout in seconds."""
        if self._is_flipper:
            return self.connection_timeout
        
        if self._thread_lock is None:
            return 0
        
        with self._thread_lock:
            return self.connection_timeout

    @timeout.setter
    def timeout(self, seconds: int) -> None:
        """Set the connection timeout in seconds.

        Args:
            seconds (int): The timeout in seconds.
        """
        if self._is_flipper:
            self.connection_timeout = seconds
            if self._wifi_uart:
                self._wifi_uart.timeout_ms = int(seconds * 1000)
            return

        if self._thread_lock is None:
            return

        with self._thread_lock:
            self.connection_timeout = seconds

    def connect(self, ssid: str, password: str = "", sta_mode: bool = True) -> bool:
        """Connect to a Wi-Fi network.

        Args:
            ssid (str): SSID of the Wi-Fi network.
            password (str): Password for the Wi-Fi network. Defaults to "".
            sta_mode (bool): True for station mode (STA_IF), False for access point mode (AP_IF). Defaults to True.

        Returns:
            bool: True if the connection succeeded, False otherwise.
        """
        if self._is_flipper:
            if not self._wifi_uart:
                return False
            connected = self._wifi_uart.connect(ssid, password, sta_mode)
            if connected:
                self.ssid = ssid
                self.password = password
                self.mode = 0 if sta_mode else 1
                self._state = WIFI_STATE_CONNECTED
            else:
                self._state = WIFI_STATE_ISSUE
            if self._callback_connect:
                self._callback_connect(self._state, self.last_error)
            return connected

        from network import STA_IF, AP_IF

        _mode = STA_IF if sta_mode else AP_IF

        # sync
        if _mode == STA_IF:
            # check if already connected
            if self.wlan.isconnected() and ssid == self.ssid:
                self._state = WIFI_STATE_CONNECTED
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
                        if not self._should_continue():
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

    def connect_async(
        self, ssid: str, password: str = "", sta_mode: bool = True
    ) -> bool:
        """Connect to a Wi-Fi network asynchronously.

        Args:
            ssid (str): SSID of the Wi-Fi network.
            password (str): Password for the Wi-Fi network. Defaults to "".
            sta_mode (bool): True for station mode (STA_IF), False for access point mode (AP_IF). Defaults to True.

        Returns:
            bool: True if the connection was started.
        """
        if self._is_flipper:
            # Flipper has no background thread; completion is synchronous.
            return self.connect(ssid, password, sta_mode)
        try:
            if self.wlan.isconnected() and ssid == self.ssid:
                self._state = WIFI_STATE_CONNECTED
                return True

            self._state = WIFI_STATE_CONNECTING
            if self._thread_manager:
                # Use ThreadManager
                from picoware.system.thread import ThreadTask

                task = ThreadTask(
                    "WiFi",
                    function=self.connect,
                    args=(ssid, password, sta_mode),
                )
                self._current_task = task
                self._thread_manager.add_task(task)
                return True

            if self._thread_lock is not None:
                import _thread

                # Start the request in a separate thread
                self._thread = _thread.start_new_thread(
                    self.connect,
                    (ssid, password, sta_mode),
                )
                return True

            self.error = "Threading not available."
            self._state = WIFI_STATE_ISSUE
            return False
        except Exception as e:
            self.error = f"Failed to start WiFi connection thread: {e}"
            self._state = WIFI_STATE_ISSUE
            return False

    def disconnect(self):
        """Disconnect from the Wi-Fi network."""
        if self._is_flipper:
            if self._wifi_uart:
                self._wifi_uart.disconnect()
            self._state = WIFI_STATE_IDLE
            return
        if self._thread_lock is None:
            return
        with self._thread_lock:
            self._thread_running = False
            self.wlan.disconnect()

    def is_connected(self):
        """Check if the device is connected to a Wi-Fi network."""
        if self._is_flipper:
            if not self._wifi_uart:
                return False
            return self._wifi_uart.is_connected()
        if self._thread_lock is None:
            return False
        with self._thread_lock:
            return self.wlan.isconnected()

    def scan(self) -> list:
        """Scan for available Wi-Fi networks."""
        if self._is_flipper:
            if not self._wifi_uart:
                return []
            ssids = self._wifi_uart.scan()
            if not ssids:
                return []
            return [(bytes(ssid, "utf-8"), 0, 0, 0, 0, 0) for ssid in ssids]
        self.wlan.active(True)
        return self.wlan.scan()

    def status(self) -> int:
        """Get the current Wi-Fi connection status."""
        if self._is_flipper:
            if not self._wifi_uart:
                return WIFI_STATE_INACTIVE
            return self._wifi_uart.status()
        
        from network import (
            STAT_IDLE,
            STAT_CONNECTING,
            STAT_GOT_IP,
            STAT_NO_AP_FOUND,
            STAT_WRONG_PASSWORD,
            STAT_CONNECT_FAIL,
        )

        if self._thread_lock is None:
            return WIFI_STATE_INACTIVE
        
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
        if self._is_flipper:
            if self._wifi_uart:
                self._wifi_uart.reset()
            self.ssid = self.password = ""
            self._state = WIFI_STATE_IDLE
            return
        if self._thread_lock is None:
            return
        with self._thread_lock:
            if self.wlan:
                self.wlan.active(False)
            self.ssid = ""
            self.password = ""
            self._state = WIFI_STATE_IDLE
            self.connection_start_time = None
            self.connection_timeout = 10  # seconds
            self.error = ""
        self.__close_thread()

class WiFiUART:
    """FlipperHTTP Wi-Fi client using a newline-buffered UART transport."""

    def __del__(self):
        self.close()

    def __init__(self, uart=None, timeout_ms: int = 5000):
        self.uart = uart
        self.error = ""
        self._timeout_ms = max(0, int(timeout_ms))
        self._owns_uart = uart is None
        if self._owns_uart:
            from picoware.system.uart import UART

            self.uart = UART(timeout=self._timeout_ms)
        self.timeout_ms = self._timeout_ms
        if self._owns_uart and not self.ping():
            error = self.error or "FlipperHTTP board not connected"
            self.close()
            raise RuntimeError(error)

    @property
    def device_ip(self):
        response = self.__send_and_wait("[IP/ADDRESS]")
        return "" if "[ERROR]" in response else response

    def close(self):
        """Release only a UART owned by this client; safe to call repeatedly."""
        uart = getattr(self, "uart", None)
        self.uart = None
        if uart is not None and getattr(self, "_owns_uart", False):
            uart.__del__()

    @property
    def last_error(self):
        return self.error

    @property
    def mac_address(self):
        """FlipperHTTP does not expose a MAC command in this interface."""
        return ""

    @property
    def state(self):
        response = self.__send_and_wait("[WIFI/STATUS]")
        if "[ERROR]" in response:
            return WIFI_STATE_ISSUE
        return WIFI_STATE_CONNECTED if "true" in response.lower() else WIFI_STATE_IDLE

    def __send_and_wait(self, command: str) -> str:
        if self.uart is None:
            self.error = "[ERROR] UART is closed"
            return self.error
        self.error = ""
        if hasattr(self.uart, "clear"):
            self.uart.clear()
        start = ticks_ms()
        self.uart.println(command)
        while self.uart.is_sending:
            if ticks_diff(ticks_ms(), start) >= self.timeout_ms:
                self.error = "[ERROR] UART transmit timed out"
                return self.error
            sleep(0.001)
        data = self.uart.read_line()
        if not data:
            self.error = "[ERROR] No data returned"
            return self.error
        if "[ERROR]" in data:
            self.error = data
        return data

    def connect(self, ssid: str, password: str = "", sta_mode: bool = True) -> bool:
        if sta_mode:
            payload = dumps({"ssid": ssid, "password": password})
            response = self.__send_and_wait("[WIFI/SAVE]" + payload)
            return "[ERROR]" not in response
        response = self.__send_and_wait("[WIFI/AP]" + dumps({"ssid": ssid}))
        return "[AP/CONNECTED]" in response

    def connect_async(self, ssid: str, password: str = "", sta_mode: bool = True) -> bool:
        """Flipper's threadless implementation completes synchronously."""
        return self.connect(ssid, password, sta_mode)

    def disconnect(self) -> None:
        if self.uart is not None:
            # The device need not acknowledge disconnect. The next transaction
            # clears any delayed acknowledgement before sending its command.
            self.uart.println("[WIFI/DISCONNECT]")

    def is_connected(self) -> bool:
        return self.state == WIFI_STATE_CONNECTED

    def ping(self) -> bool:
        return "PONG" in self.__send_and_wait("[PING]")

    def scan(self) -> list:
        response = self.__send_and_wait("[WIFI/SCAN]")
        if "[GET/SUCCESS]" not in response:
            return []
        # read_line preserves subsequent lines even if all arrive in one read.
        response = self.uart.read_line()
        if not response:
            self.error = "[ERROR] Missing scan response"
            return []
        try:
            networks = loads(response)["networks"]
            if not isinstance(networks, list) or any(not isinstance(ssid, str) for ssid in networks):
                raise ValueError("networks must be a list of SSIDs")
            return networks
        except (ValueError, KeyError, TypeError) as error:
            self.error = "[ERROR] Invalid scan response: " + str(error)
            return []

    def status(self) -> int:
        return self.state

    def reset(self) -> None:
        self.disconnect()
        if self.uart is not None and hasattr(self.uart, "clear"):
            self.uart.clear()
        self.error = ""

    @property
    def timeout_ms(self):
        return self._timeout_ms

    @timeout_ms.setter
    def timeout_ms(self, value):
        self._timeout_ms = max(0, int(value))
        if self.uart is not None:
            self.uart.timeout = self._timeout_ms
