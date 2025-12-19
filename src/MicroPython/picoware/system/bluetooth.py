from micropython import const

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_RESULT = const(9)
_IRQ_GATTC_SERVICE_DONE = const(10)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE = const(12)
_IRQ_GATTC_DESCRIPTOR_RESULT = const(13)
_IRQ_GATTC_DESCRIPTOR_DONE = const(14)
_IRQ_GATTC_READ_RESULT = const(15)
_IRQ_GATTC_READ_DONE = const(16)
_IRQ_GATTC_WRITE_DONE = const(17)
_IRQ_GATTC_NOTIFY = const(18)
_IRQ_GATTC_INDICATE = const(19)
_IRQ_GATTS_INDICATE_DONE = const(20)
_IRQ_MTU_EXCHANGED = const(21)
_IRQ_ENCRYPTION_UPDATE = const(28)
_IRQ_PASSKEY_ACTION = const(31)

# Passkey actions
_PASSKEY_ACTION_NONE = const(0)
_PASSKEY_ACTION_INPUT = const(2)
_PASSKEY_ACTION_DISPLAY = const(3)
_PASSKEY_ACTION_NUMERIC_COMPARISON = const(4)

# Bonding file path
_BONDING_FILE = const(b"picoware/bluetooth/paired_devices.json")


class Bluetooth:
    """A class to manage Bluetooth functionality as a central device."""

    def __init__(self, storage=None):
        """Initialize Bluetooth.

        Args:
            storage: Storage instance for saving paired device keys
        """
        from ubluetooth import BLE

        self._ble = BLE()
        self._ble.active(True)
        self._ble.irq(self.__irq)
        self._callback = None
        self._scanning = False
        self._conn_handle = None
        self._connected = False
        self._connected_addr = None
        self._storage = storage

        self._tx = None
        self._rx = None

        # Service discovery results
        self._services = []
        self._characteristics = []
        self._write_handle = None

        # Pairing state
        self._pairing = False
        self._passkey = None

    def __del__(self):
        """Clean up Bluetooth resources."""
        if self._ble is not None:
            if self._connected and self._conn_handle is not None:
                try:
                    self._ble.gap_disconnect(self._conn_handle)
                except Exception:
                    pass
            self._ble.active(False)
            del self._ble
            self._ble = None
        self._callback = None
        self._tx = None
        self._rx = None
        self._services.clear()
        self._characteristics.clear()
        self._write_handle = None
        self._passkey = None

    @property
    def callback(self):
        """Get the current Bluetooth callback."""
        return self._callback

    @callback.setter
    def callback(self, func: callable):
        """Set the Bluetooth callback function.

        The callback receives (event, data) where event is one of the _IRQ_* constants.
        """
        self._callback = func

    @property
    def characteristics(self) -> list:
        """Get discovered characteristics."""
        return self._characteristics

    @property
    def connected_address(self) -> str:
        """Get the address of the connected device."""
        return self._connected_addr

    @property
    def is_pairing(self) -> bool:
        """Check if currently in pairing process."""
        return self._pairing

    @property
    def is_scanning(self) -> bool:
        """Check if Bluetooth is currently scanning."""
        return self._scanning

    @property
    def is_connected(self) -> bool:
        """Check if connected to a peripheral."""
        return self._connected

    @property
    def mac_address(self) -> str:
        """Get the MAC address of this Bluetooth device."""
        addr = self._ble.config("mac")
        if isinstance(addr, tuple):
            addr = addr[1]  # (addr_type, addr_bytes)
        return ":".join("{:02X}".format(b) for b in addr)

    @property
    def passkey(self) -> int:
        """Get the current passkey during pairing (if any)."""
        return self._passkey

    @property
    def services(self) -> list:
        """Get discovered services."""
        return self._services

    def __irq(self, event, data):
        """Handle Bluetooth IRQ events."""
        _data = None

        if event == _IRQ_SCAN_RESULT:
            # A single scan result
            addr_type, addr, adv_type, rssi, adv_data = data
            _data = (addr_type, addr, adv_type, rssi, adv_data)

        elif event == _IRQ_SCAN_DONE:
            # Scan duration finished or manually stopped
            self._scanning = False
            _data = None

        elif event == _IRQ_PERIPHERAL_CONNECT:
            # Successfully connected to a peripheral
            conn_handle, addr_type, addr = data
            self._conn_handle = conn_handle
            self._connected = True
            self._connected_addr = ":".join("{:02X}".format(b) for b in addr)
            _data = (conn_handle, addr_type, addr)

        elif event == _IRQ_PERIPHERAL_DISCONNECT:
            # Disconnected from peripheral
            conn_handle, addr_type, addr = data
            self._conn_handle = None
            self._connected = False
            self._connected_addr = None
            self._write_handle = None
            _data = (conn_handle, addr_type, addr)

        elif event == _IRQ_GATTC_SERVICE_RESULT:
            # Found a service
            conn_handle, start_handle, end_handle, uuid = data
            self._services.append((start_handle, end_handle, uuid))
            _data = (conn_handle, start_handle, end_handle, uuid)

        elif event == _IRQ_GATTC_SERVICE_DONE:
            # Service discovery complete
            conn_handle, status = data
            _data = (conn_handle, status)

        elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
            # Found a characteristic
            conn_handle, end_handle, value_handle, properties, uuid = data
            self._characteristics.append((value_handle, properties, uuid))
            # Check if this characteristic is writable
            if properties & 0x08:  # Write property
                self._write_handle = value_handle
            _data = (conn_handle, end_handle, value_handle, properties, uuid)

        elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:
            # Characteristic discovery complete
            conn_handle, status = data
            _data = (conn_handle, status)

        elif event == _IRQ_GATTC_WRITE_DONE:
            # Write operation completed
            conn_handle, value_handle, status = data
            _data = (conn_handle, value_handle, status)

        elif event == _IRQ_GATTC_NOTIFY:
            # Received notification from peripheral
            conn_handle, value_handle, notify_data = data
            _data = (conn_handle, value_handle, notify_data)

        elif event == _IRQ_GATTC_READ_RESULT:
            # Read operation result
            conn_handle, value_handle, char_data = data
            _data = (conn_handle, value_handle, char_data)

        elif event == _IRQ_ENCRYPTION_UPDATE:
            # Encryption/bonding state changed
            conn_handle, encrypted, authenticated, bonded, key_size = data
            self._pairing = False
            _data = (conn_handle, encrypted, authenticated, bonded, key_size)

        elif event == _IRQ_PASSKEY_ACTION:
            # Passkey action required during pairing
            conn_handle, action, passkey = data
            self._passkey = passkey
            _data = (conn_handle, action, passkey)

        else:
            # Handle other events generically
            _data = data

        if self._callback:
            self._callback(event, _data)

    def advertise(self, interval_us=None, name="Picoware"):
        """Start or stop BLE advertising to make this device discoverable.

        Args:
            interval_us: Advertising interval in microseconds (None to stop advertising)
            name: Device name to advertise

        Returns:
            bool: True if advertising started/stopped successfully
        """

        try:
            if interval_us is None:
                # Stop advertising
                self._ble.gap_advertise(None)
                return True
            self.register()
            _name = bytes(name, "UTF-8")
            adv_data = (
                bytearray(b"\x02\x01\x02") + bytearray((len(_name) + 1, 0x09)) + _name
            )
            self._ble.gap_advertise(interval_us, adv_data)
            return True
        except Exception as e:
            print(f"[Bluetooth] Advertise error: {e}")
            return False

    def connect(self, addr_type, addr, timeout_ms=10000):
        """Connect to a BLE peripheral device.

        Args:
            addr_type: Address type (0 = public, 1 = random)
            addr: Device address as bytes
            timeout_ms: Connection timeout in milliseconds

        Returns:
            bool: True if connection initiated successfully
        """
        if self._connected:
            return False

        self._services = []
        self._characteristics = []
        self._write_handle = None

        try:
            self._ble.gap_connect(addr_type, addr, timeout_ms)
            return True
        except Exception as e:
            print(f"[Bluetooth] Connect error: {e}")
            return False

    def decode_name(self, adv_data) -> str:
        """Decode device name from advertising data.

        Args:
            adv_data: Raw advertising data bytes

        Returns:
            str: Device name or empty string if not found
        """
        i = 0
        while i + 1 < len(adv_data):
            length = adv_data[i]
            if length == 0:
                break
            ad_type = adv_data[i + 1]
            # 0x08 = Shortened Local Name, 0x09 = Complete Local Name
            if ad_type in (0x08, 0x09):
                try:
                    return adv_data[i + 2 : i + 1 + length].decode("utf-8")
                except Exception:
                    pass
            i += 1 + length
        return ""

    def disconnect(self, conn_handle=None):
        """Disconnect from a device.

        Args:
            conn_handle: Connection handle to disconnect (uses current if None)
        """
        handle = conn_handle if conn_handle is not None else self._conn_handle
        if handle is not None:
            try:
                self._ble.gap_disconnect(handle)
            except Exception:
                pass
            finally:
                if handle == self._conn_handle:
                    self._conn_handle = None
                    self._connected = False
                    self._connected_addr = None
                    self._write_handle = None

    def discover_characteristics(self, start_handle, end_handle):
        """Discover characteristics for a service.

        Args:
            start_handle: Service start handle
            end_handle: Service end handle

        Results will be delivered via callback with _IRQ_GATTC_CHARACTERISTIC_RESULT events.
        """
        if not self._connected or self._conn_handle is None:
            return False

        self._characteristics = []
        try:
            self._ble.gattc_discover_characteristics(
                self._conn_handle, start_handle, end_handle
            )
            return True
        except Exception as e:
            print(f"[Bluetooth] Characteristic discovery error: {e}")
            return False

    def discover_services(self):
        """Discover services on the connected peripheral.

        Results will be delivered via callback with _IRQ_GATTC_SERVICE_RESULT events.
        """
        if not self._connected or self._conn_handle is None:
            return False

        self._services = []
        try:
            self._ble.gattc_discover_services(self._conn_handle)
            return True
        except Exception as e:
            print(f"[Bluetooth] Service discovery error: {e}")
            return False

    def is_device_paired(self, addr: str) -> bool:
        """Check if a device address is in the paired devices list."""
        devices = self.load_paired_devices()
        return addr in devices

    def load_paired_devices(self) -> dict:
        """Load paired devices from storage.

        Returns:
            dict: Dictionary of paired devices {addr: {name, paired}}
        """
        if self._storage is None:
            return {}

        try:
            data = self._storage.read(_BONDING_FILE)
            if data:
                import json

                return json.loads(data)
        except Exception as e:
            print(f"[Bluetooth] Load paired devices error: {e}")
        return {}

    def pair(self):
        """Initiate pairing/bonding with the connected device.

        Call this after connecting to establish an encrypted bond.
        The device will be remembered for future connections.
        """
        if not self._connected or self._conn_handle is None:
            return False

        self._pairing = True
        try:
            # Request pairing - this triggers _IRQ_ENCRYPTION_UPDATE or _IRQ_PASSKEY_ACTION
            self._ble.gap_pair(self._conn_handle)
            return True
        except Exception as e:
            print(f"[Bluetooth] Pair error: {e}")
            self._pairing = False
            return False

    def passkey_reply(self, accept=True, passkey=None):
        """Reply to a passkey request during pairing.

        Args:
            accept: Whether to accept the pairing
            passkey: The passkey to use (for input actions)
        """
        if self._conn_handle is None:
            return

        if passkey is None:
            passkey = 0
        self._ble.gap_passkey(
            self._conn_handle,
            _PASSKEY_ACTION_INPUT if passkey else _PASSKEY_ACTION_NUMERIC_COMPARISON,
            passkey if accept else 0,
        )

    def read(self, handle):
        """Read data from a characteristic.

        Args:
            handle: Characteristic handle to read from

        Result will be delivered via callback with _IRQ_GATTC_READ_RESULT event.
        """
        if not self._connected or self._conn_handle is None:
            return False

        try:
            self._ble.gattc_read(self._conn_handle, handle)
            return True
        except Exception as e:
            print(f"[Bluetooth] Read error: {e}")
            return False

    def remove_paired_device(self, addr: str):
        """Remove a paired device from storage.

        Args:
            addr: Device address string to remove
        """
        if self._storage is None:
            return False

        try:
            devices = self.load_paired_devices()
            if addr in devices:
                del devices[addr]
                import json

                data = json.dumps(devices)
                self._storage.write(_BONDING_FILE, data)
                return True
        except Exception as e:
            print(f"[Bluetooth] Remove paired device error: {e}")
        return False

    def save_paired_device(self, addr: str, name: str = ""):
        """Save a paired device to storage.

        Args:
            addr: Device address string
            name: Device name (optional)
        """
        if self._storage is None:
            return False

        try:
            # Load existing paired devices
            devices = self.load_paired_devices()

            # Add or update device
            devices[addr] = {"name": name, "paired": True}

            # Save back to storage
            import json

            data = json.dumps(devices)
            self._storage.write(_BONDING_FILE, data)
            return True
        except Exception as e:
            print(f"[Bluetooth] Save paired device error: {e}")
            return False

    def scan(self, duration_ms=5000, interval_us=30000, window_us=30000, active=True):
        """Start scanning for BLE devices.

        Args:
            duration_ms: How long to scan in milliseconds (default 5 seconds, set to 0 for continuous
            interval_us: Scan interval in microseconds
            window_us: Scan window in microseconds
            active: If True, request scan response data for device names (default True)
        """
        self._scanning = True
        self._ble.gap_scan(duration_ms, interval_us, window_us, active)

    def scan_stop(self):
        """Stop an ongoing scan."""
        self._ble.gap_scan(None)
        self._scanning = False

    def register(self):
        """Register the device as a GATT server.

        This allows the device to accept incoming connections and
        provide services/characteristics to connected centrals.
        """
        try:
            from ubluetooth import UUID, FLAG_WRITE, FLAG_NOTIFY

            # Nordic UART Service (NUS)
            NUS_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
            RX_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
            TX_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

            BLE_NUS = UUID(NUS_UUID)
            BLE_RX = (UUID(RX_UUID), FLAG_WRITE)
            BLE_TX = (UUID(TX_UUID), FLAG_NOTIFY)

            BLE_UART = (
                BLE_NUS,
                (
                    BLE_TX,
                    BLE_RX,
                ),
            )
            SERVICES = (BLE_UART,)
            (
                (
                    self._tx,
                    self._rx,
                ),
            ) = self._ble.gatts_register_services(SERVICES)
            return True
        except Exception as e:
            print(f"[Bluetooth] Register error: {e}")
            return False

    def subscribe(self, handle, notify=True):
        """Subscribe to notifications from a characteristic.

        Args:
            handle: Characteristic value handle
            notify: True for notifications, False to unsubscribe
        """
        if not self._connected or self._conn_handle is None:
            return False

        # CCCD handle is typically value_handle + 1
        cccd_handle = handle + 1
        value = b"\x01\x00" if notify else b"\x00\x00"

        try:
            self._ble.gattc_write(self._conn_handle, cccd_handle, value, 1)
            return True
        except Exception as e:
            print(f"[Bluetooth] Subscribe error: {e}")
            return False

    def write(self, data, handle=None, response=False):
        """Write data to the connected peripheral.

        Args:
            data: Data to write (bytes or str)
            handle: Characteristic handle to write to (uses discovered writable handle if None)
            response: Whether to request a write response

        Returns:
            bool: True if write was initiated
        """
        if not self._connected or self._conn_handle is None:
            return False

        if handle is None:
            handle = self._write_handle

        if handle is None:
            print("[Bluetooth] No writable characteristic found")
            return False

        if isinstance(data, str):
            data = data.encode()

        try:
            self._ble.gattc_write(self._conn_handle, handle, data, 1 if response else 0)
            return True
        except Exception as e:
            print(f"[Bluetooth] Write error: {e}")
            return False
