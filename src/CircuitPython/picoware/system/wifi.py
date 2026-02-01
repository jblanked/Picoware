from micropython import const

WIFI_STATE_INACTIVE = const(-1)
WIFI_STATE_IDLE = const(0)
WIFI_STATE_CONNECTING = const(1)
WIFI_STATE_CONNECTED = const(2)
WIFI_STATE_ISSUE = const(3)
WIFI_STATE_TIMEOUT = const(4)


class WiFi:
    """A class to manage WiFi connections."""

    def __init__(self, timeout: int = 5) -> None:
        from wifi import radio as wradio

        self._callback_connect: callable = None
        self._error = ""
        self._network = wradio
        self._state = WIFI_STATE_IDLE
        self._timeout = timeout
        self.connection_start_time = None
        self.connection_timeout = timeout

    @property
    def callback_connect(self) -> callable:
        """Get the connection callback function."""
        return self._callback_connect

    @callback_connect.setter
    def callback_connect(self, func: callable) -> None:
        """Set the connection callback function."""
        self._callback_connect = func

    @property
    def device_ip(self) -> str:
        """Get the device's IP address."""
        return str(self._network.ipv4_address)

    @property
    def last_error(self) -> str:
        """Get the last error message."""
        return self._error

    @property
    def mac_address(self) -> str:
        """Get the MAC address of the device."""
        return ":".join(["{:02x}".format(b) for b in self._network.mac_address])

    @property
    def radio(self):
        """Get the underlying radio object."""
        return self._network

    @property
    def state(self) -> int:
        """Get the current WiFi state."""
        return self._state

    @property
    def timeout(self) -> int:
        """Get the connection timeout value."""
        return self._timeout

    @timeout.setter
    def timeout(self, value: int) -> None:
        """Set the connection timeout value."""
        self._timeout = value

    def connect(self, ssid: str, password: str) -> bool:
        """Connect to a WiFi network in STA mode."""
        try:
            self._network.enabled = True
            self._state = WIFI_STATE_CONNECTING
            self._network.connect(ssid=ssid, password=password, timeout=self._timeout)
            self._state = WIFI_STATE_CONNECTED
            self._error = ""
            if self._callback_connect:
                self._callback_connect(self._state, self._error)
            return True
        except Exception as e:
            print(f"Failed to connect to WiFi: {e}")
            self._error = str(e)
            self._state = WIFI_STATE_ISSUE
            if self._callback_connect:
                self._callback_connect(self._state, self._error)
            return False

    def ip_address(self) -> str:
        """Return the IP address of the device."""
        return self._network.ipv4_address

    def is_connected(self) -> bool:
        """Return True if the device is connected to WiFi, False otherwise."""
        return self._network.connected

    def disconnect(self) -> None:
        """Disconnect from the WiFi network."""
        self._network.enabled = False

    def reset(self):
        """Reset the Wi-Fi configuration."""
        self._error = ""
        self._network.enabled = False
        self._state = WIFI_STATE_IDLE
        self.connection_start_time = None
        self.connection_timeout = 10  # seconds

    def scan(self) -> list:
        '''Scan for available WiFi networks and return a list of SSIDs."""'''
        try:
            networks = []
            for network in self._network.start_scanning_networks():
                if network.ssid in [n.ssid for n in networks]:
                    continue
                networks.append(network)
            self._network.stop_scanning_networks()
            return sorted(networks, key=lambda net: net.rssi, reverse=True)
        except Exception as e:
            print(f"WiFi scan error: {e}")
            return []

    def status(self) -> str:
        """Return a string representation of the current WiFi status."""
        if not self._network:
            return WIFI_STATE_INACTIVE
        if not self._network.enabled:
            return WIFI_STATE_INACTIVE
        if self._network.connected:
            return WIFI_STATE_CONNECTED
        return WIFI_STATE_IDLE
