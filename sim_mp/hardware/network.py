import sim_runtime

STA_IF = 0
AP_IF = 1

STAT_IDLE = 0
STAT_CONNECTING = 1
STAT_WRONG_PASSWORD = -3
STAT_NO_AP_FOUND = -2
STAT_CONNECT_FAIL = -1
STAT_GOT_IP = 3

AUTH_OPEN = 0
AUTH_WPA2_PSK = 3


class WLAN:
    def __init__(self, mode):
        """Initialize simulated WLAN in STA or AP mode."""
        self.mode = mode
        self._active = False
        self._ssid = "Picoware-Sim"
        self._password = ""
        self._connected = sim_runtime.network_mode != "off" and mode == STA_IF
        self._status = STAT_GOT_IP if self._connected else STAT_IDLE
        self._mac = b"\x02\x50\x43\x57\x00\x01" if mode == STA_IF else b"\x02\x50\x43\x57\x00\x02"
        self._ifconfig = ("192.168.76.2", "255.255.255.0", "192.168.76.1", "1.1.1.1")

    def active(self, state=None):
        """Get or set the WLAN active state."""
        if state is None:
            return self._active
        self._active = bool(state)
        if not self._active:
            self._connected = False
            self._status = STAT_IDLE
        elif sim_runtime.network_mode != "off" and self.mode == STA_IF:
            self._connected = True
            self._status = STAT_GOT_IP
        return None

    def isconnected(self):
        """Return True if connected to a network."""
        if sim_runtime.network_mode != "off" and self.mode == STA_IF and self._active:
            return True
        return self._connected

    def connect(self, ssid, password=""):
        """Simulate connecting to an access point."""
        self._ssid = ssid
        self._password = password
        self._active = True
        self._connected = True
        self._status = STAT_GOT_IP
        return None

    def disconnect(self):
        """Simulate disconnecting from the network."""
        self._connected = False
        self._status = STAT_IDLE
        return None

    def status(self, param=None):
        """Return connection status or RSSI."""
        if param == "rssi":
            return -42 if self.isconnected() else 0
        if self.isconnected():
            return STAT_GOT_IP
        return self._status

    def config(self, key=None, **kwargs):
        """Get or set WLAN configuration."""
        if kwargs:
            if "ssid" in kwargs:
                self._ssid = kwargs["ssid"]
            if "password" in kwargs:
                self._password = kwargs["password"]
            if "mac" in kwargs:
                self._mac = kwargs["mac"]
            return None
        if key == "mac":
            return self._mac
        if key == "ssid":
            return self._ssid
        if key == "channel":
            return 6
        if key == "essid":
            return self._ssid
        return None

    def ifconfig(self, config=None):
        """Get or set the IP configuration tuple."""
        if config is not None:
            self._ifconfig = tuple(config)
            return None
        if self.isconnected() or self.mode == AP_IF:
            return self._ifconfig
        return ("0.0.0.0", "255.255.255.0", "0.0.0.0", "0.0.0.0")

    def scan(self):
        """Return a simulated list of visible access points."""
        if not self._active:
            self._active = True
        return [
            (b"Picoware-Sim", b"\x02\x50\x43\x57\x10\x01", 6, -42, AUTH_WPA2_PSK, False),
            (b"Guest", b"\x02\x50\x43\x57\x10\x02", 11, -67, AUTH_OPEN, False),
        ]
