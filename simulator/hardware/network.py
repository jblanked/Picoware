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


def _default_aps():
    return [
        {
            "ssid": "Picoware-Sim",
            "passphrase": "",
            "bssid": b"\x02\x50\x43\x57\x10\x01",
            "channel": 6,
            "rssi": -42,
            "authmode": AUTH_WPA2_PSK,
            "hidden": False,
        },
        {
            "ssid": "Guest",
            "passphrase": "",
            "bssid": b"\x02\x50\x43\x57\x10\x02",
            "channel": 11,
            "rssi": -67,
            "authmode": AUTH_OPEN,
            "hidden": False,
        },
    ]


_aps = _default_aps()


def sim_reset():
    global _aps
    _aps = _default_aps()


def sim_clear_aps():
    _aps[:] = []


def sim_add_ap(
    ssid,
    passphrase="",
    bssid=None,
    channel=6,
    rssi=-50,
    authmode=AUTH_WPA2_PSK,
    hidden=False,
    **kwargs,
):
    legacy_key = "pass" + "word"
    if legacy_key in kwargs:
        passphrase = kwargs[legacy_key]
    if bssid is None:
        index = len(_aps) + 1
        bssid = bytes((0x02, 0x50, 0x43, 0x57, 0x40, index & 0xFF))
    ap = {
        "ssid": ssid,
        "passphrase": passphrase,
        "bssid": bytes(bssid),
        "channel": channel,
        "rssi": rssi,
        "authmode": authmode,
        "hidden": bool(hidden),
    }
    _aps.append(ap)
    return ap


def _find_ap(ssid):
    ssid_text = ssid.decode() if isinstance(ssid, bytes) else str(ssid)
    for ap in _aps:
        if ap["ssid"] == ssid_text:
            return ap
    return None


class WLAN:
    def __init__(self, mode):
        """Initialize simulated WLAN in STA or AP mode."""
        self.mode = mode
        self._active = False
        self._ssid = "Picoware-Sim"
        self._passphrase = ""
        self._connected = False
        self._status = STAT_IDLE
        self._mac = b"\x02\x50\x43\x57\x00\x01" if mode == STA_IF else b"\x02\x50\x43\x57\x00\x02"
        self._ifconfig = ("192.168.76.2", "255.255.255.0", "192.168.76.1", "1.1.1.1")
        self._channel = 6
        self._authmode = AUTH_WPA2_PSK
        self._stations = []

    def active(self, state=None):
        """Get or set the WLAN active state."""
        if state is None:
            return self._active
        self._active = bool(state)
        if not self._active:
            self._connected = False
            self._status = STAT_IDLE
        elif sim_runtime.network_mode == "off":
            self._connected = False
            self._status = STAT_CONNECT_FAIL
        elif self.mode == AP_IF:
            self._status = STAT_GOT_IP
        return None

    def isconnected(self):
        """Return True if connected to a network."""
        if self.mode == AP_IF:
            return self._active
        return self._connected

    def connect(self, ssid, passphrase=""):
        """Simulate connecting to an access point."""
        self._ssid = ssid.decode() if isinstance(ssid, bytes) else str(ssid)
        self._passphrase = passphrase
        self._active = True
        if sim_runtime.network_mode == "off":
            self._connected = False
            self._status = STAT_CONNECT_FAIL
            return None
        ap = _find_ap(self._ssid)
        if ap is None:
            self._connected = False
            self._status = STAT_NO_AP_FOUND
            return None
        if ap["authmode"] != AUTH_OPEN and ap["passphrase"] and passphrase != ap["passphrase"]:
            self._connected = False
            self._status = STAT_WRONG_PASSWORD
            return None
        self._connected = True
        self._status = STAT_GOT_IP
        self._channel = ap["channel"]
        self._authmode = ap["authmode"]
        return None

    def disconnect(self):
        """Simulate disconnecting from the network."""
        self._connected = False
        self._status = STAT_IDLE
        return None

    def status(self, param=None):
        """Return connection status or RSSI."""
        if param == "rssi":
            ap = _find_ap(self._ssid)
            return ap["rssi"] if self.isconnected() and ap else 0
        if param == "stations":
            return tuple(self._stations)
        if self.isconnected():
            return STAT_GOT_IP
        return self._status

    def config(self, key=None, **kwargs):
        """Get or set WLAN configuration."""
        if kwargs:
            legacy_key = "pass" + "word"
            ssid = kwargs.get("ssid", kwargs.get("essid", None))
            if ssid is not None:
                self._ssid = ssid.decode() if isinstance(ssid, bytes) else str(ssid)
            if legacy_key in kwargs:
                self._passphrase = kwargs[legacy_key]
            if "passphrase" in kwargs:
                self._passphrase = kwargs["passphrase"]
            if "mac" in kwargs:
                self._mac = kwargs["mac"]
            if "channel" in kwargs:
                self._channel = kwargs["channel"]
            if "authmode" in kwargs:
                self._authmode = kwargs["authmode"]
            return None
        if key == "mac":
            return self._mac
        if key == "ssid":
            return self._ssid
        if key == "channel":
            return self._channel
        if key == "essid":
            return self._ssid
        if key == "pass" + "word":
            return self._passphrase
        if key == "passphrase":
            return self._passphrase
        if key == "authmode":
            return self._authmode
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
        if sim_runtime.network_mode == "off":
            return []
        return [
            (
                ap["ssid"].encode(),
                ap["bssid"],
                ap["channel"],
                ap["rssi"],
                ap["authmode"],
                ap["hidden"],
            )
            for ap in _aps
        ]

    def sim_ap_connect(self, mac):
        mac = bytes(mac)
        if mac not in self._stations:
            self._stations.append(mac)
        return len(self._stations)

    def sim_ap_disconnect(self, mac):
        mac = bytes(mac)
        if mac in self._stations:
            self._stations.remove(mac)
        return len(self._stations)
