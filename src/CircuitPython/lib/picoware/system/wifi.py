from wifi import radio as wradio


class WiFi:
    """A class to manage WiFi connections."""

    def __init__(self) -> None:
        self.network = wradio

    def connect(self, ssid: str, password: str, timeout: float = 5.0) -> bool:
        """Connect to a WiFi network in STA mode."""
        try:
            self.network.connect(ssid=ssid, password=password, timeout=timeout)
            return True
        except Exception as e:
            print(f"Failed to connect to WiFi: {e}")
            return False

    def ip_address(self) -> str:
        """Return the IP address of the device."""
        return self.network.ipv4_address

    def is_connected(self) -> bool:
        """Return True if the device is connected to WiFi, False otherwise."""
        return self.network.connected

    def disconnect(self) -> None:
        """Disconnect from the WiFi network."""
        self.network.enabled = False

    def scan(self) -> list:
        '''Scan for available WiFi networks and return a list of SSIDs."""'''
        networks = []
        ssids = []
        for network in self.network.start_scanning_networks():
            networks.append(network)
        self.network.stop_scanning_networks()
        networks = sorted(networks, key=lambda net: net.rssi, reverse=True)
        for network in networks:
            ssid = network.ssid
            if len(ssid) > 0 and ssid not in ssids:
                ssids.append(ssid)
        return ssids
