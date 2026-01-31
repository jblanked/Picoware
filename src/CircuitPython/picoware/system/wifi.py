from micropython import const

WIFI_STATE_INACTIVE = const(-1)
WIFI_STATE_IDLE = const(0)
WIFI_STATE_CONNECTING = const(1)
WIFI_STATE_CONNECTED = const(2)
WIFI_STATE_ISSUE = const(3)
WIFI_STATE_TIMEOUT = const(4)


class WiFi:
    """A class to manage WiFi connections."""

    def __init__(self) -> None:
        from wifi import radio as wradio

        self._network = wradio
        self._state = WIFI_STATE_IDLE

    @property
    def radio(self):
        """Get the underlying radio object."""
        return self._network

    @property
    def state(self) -> int:
        """Get the current WiFi state."""
        return self._state

    def connect(self, ssid: str, password: str, timeout: float = 5.0) -> bool:
        """Connect to a WiFi network in STA mode."""
        try:
            self._state = WIFI_STATE_CONNECTING
            self._network.connect(ssid=ssid, password=password, timeout=timeout)
            self._state = WIFI_STATE_CONNECTED
            return True
        except Exception as e:
            print(f"Failed to connect to WiFi: {e}")
            self._state = WIFI_STATE_ISSUE
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

    def scan(self) -> list:
        '''Scan for available WiFi networks and return a list of SSIDs."""'''
        networks = []
        ssids = []
        try:
            for network in self._network.start_scanning_networks():
                networks.append(network)
            self._network.stop_scanning_networks()
            networks = sorted(networks, key=lambda net: net.rssi, reverse=True)
            for network in networks:
                ssid = network.ssid
                if len(ssid) > 0 and ssid not in ssids:
                    ssids.append(ssid)
        except Exception as e:
            print(f"WiFi scan error: {e}")
        return ssids
