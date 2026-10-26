"""Bluetooth - Bluetooth Low Energy interface."""

# mostly adapted from MicroPython examples
# source 1: https://github.com/micropython/micropython/blob/master/examples/bluetooth/ble_simple_central.py
# source 2: https://github.com/micropython/micropython/blob/master/examples/bluetooth/ble_simple_peripheral.py
# source 3: https://github.com/micropython/micropython/blob/master/examples/bluetooth/ble_advertising.py

from micropython import const
import struct

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
_IRQ_GET_SECRET = const(29)
_IRQ_SET_SECRET = const(30)
_IRQ_PASSKEY_ACTION = const(31)

# Passkey actions
_PASSKEY_ACTION_NONE = const(0)
_PASSKEY_ACTION_INPUT = const(2)
_PASSKEY_ACTION_DISPLAY = const(3)
_PASSKEY_ACTION_NUMERIC_COMPARISON = const(4)

# Advertising types
_ADV_IND = const(0x00)
_ADV_DIRECT_IND = const(0x01)
_ADV_SCAN_IND = const(0x02)
_ADV_NONCONN_IND = const(0x03)
_ADV_SCAN_RSP = const(0x04)

# Advertising data types
_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_SHORT_NAME = const(0x08)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID16_COMPLETE = const(0x03)
_ADV_TYPE_UUID32_COMPLETE = const(0x05)
_ADV_TYPE_UUID128_COMPLETE = const(0x07)
_ADV_TYPE_APPEARANCE = const(0x19)
_ADV_MAX_PAYLOAD = const(31)

# Nordic UART Service UUIDs
_UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
_UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
_UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

# Bonding file path
_BONDING_FILE = "picoware/bluetooth/paired_devices.json"
_SECRETS_FILE = "picoware/bluetooth/secrets.json"

class Bluetooth:
    """A class to manage Bluetooth functionality as both central and peripheral device.

    This class provides a unified interface for:
    - Central mode: Scan for, connect to, and communicate with BLE peripherals
    - Peripheral mode: Advertise, accept connections, and communicate with BLE centrals

    Example (Peripheral mode):
        bt = Bluetooth()
        bt.start_peripheral(name="MyDevice")
        bt.on_write(lambda data: print("Received:", data))
        while True:
            if bt.is_peripheral_connected:
                bt.send("Hello from peripheral!")
            time.sleep(1)

    Example (Central mode):
        bt = Bluetooth()
        bt.on_notify(lambda data: print("Received:", data))
        bt.scan(callback=my_scan_callback)
        # After finding device...
        bt.connect(addr_type, addr)
        bt.write("Hello from central!")
    """

    def __init__(self, storage=None):
        """Initialize Bluetooth.

        Args:
            storage (Storage): Storage instance for saving paired device keys. Defaults to None.
        """
        from ubluetooth import BLE

        if storage is not None:
            storage.mkdir("picoware/bluetooth")

        self._ble = BLE()
        bonding_configured = self._configure_bonding()
        print(
            f"[BT] Security config: bond={bonding_configured}, "
            "mitm=False, io=3, le_secure=False"
        )
        self._callback = None
        self._scanning = False
        self._scan_data = {}
        self._conn_handle = None
        self._connected = False
        self._connected_addr = None
        self._encrypted = False
        self._bonded = False
        self._auto_discover = False
        self._services_discovering = False
        self._storage = storage
        self._secrets = {}
        self._secrets_dirty = False
        self._paired_devices = None  # Cached paired-device dict
        self._load_secrets()

        # Peripheral mode handles (GATT server)
        self._tx_handle = None  # TX characteristic handle (for sending notifications)
        self._rx_handle = None  # RX characteristic handle (for receiving writes)
        self._central_connections = set()  # Connected centrals (peripheral mode)
        self._write_callback = None  # Callback when data received from central
        self._peripheral_registered = False

        # Central mode handles (GATT client)
        self._peripheral_tx_handle = (
            None  # Remote TX handle (for receiving notifications)
        )
        self._peripheral_rx_handle = None  # Remote RX handle (for writing data)
        self._notify_callback = None  # Callback when data received from peripheral
        self._scan_callback = None  # Callback for scan results

        # Service discovery results
        self._services = []
        self._characteristics = []
        self._start_handle = None
        self._end_handle = None

        # Pairing state
        self._pairing = False
        self._passkey = None
        self._passkey_action = None
        self._passkey_conn_handle = None
        self._ble.irq(self.__irq)
        self._ble.active(True)

    def __del__(self):
        """Clean up Bluetooth resources."""
        if self._ble is not None:
            if self._connected and self._conn_handle is not None:
                try:
                    self._ble.gap_disconnect(self._conn_handle)
                except Exception:
                    pass
            # Disconnect all central connections (peripheral mode)
            for conn_handle in list(self._central_connections):
                try:
                    self._ble.gap_disconnect(conn_handle)
                except Exception:
                    pass
            self._ble.active(False)
            del self._ble
            self._ble = None
        self._callback = None
        self._write_callback = None
        self._notify_callback = None
        self._scan_callback = None
        self._tx_handle = None
        self._rx_handle = None
        self._peripheral_tx_handle = None
        self._peripheral_rx_handle = None
        self._services.clear()
        self._characteristics.clear()
        self._central_connections.clear()
        self._passkey = None
        self._passkey_action = None
        self._passkey_conn_handle = None
        self._secrets.clear()

    @property
    def callback(self):
        """Get the current Bluetooth callback."""
        return self._callback

    @callback.setter
    def callback(self, func: callable):
        """Set the Bluetooth callback function.

        The callback receives (event, data) where event is one of the _IRQ_* constants.

        Args:
            func (callable): The callback function to set.
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
        """Check if connected to a peripheral (central mode)."""
        return self._connected

    @property
    def is_discovering_services(self) -> bool:
        """Check if service discovery is in progress."""
        return self._services_discovering

    @property
    def is_peripheral_connected(self) -> bool:
        """Check if any central is connected (peripheral mode)."""
        return len(self._central_connections) > 0

    @property
    def central_connections(self) -> set:
        """Get the set of connected central device handles (peripheral mode)."""
        return self._central_connections

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
        """Handle Bluetooth IRQ events for both central and peripheral modes.

        Args:
            event (int): The IRQ event constant.
            data (tuple): Event-specific data.
        """
        try:
            return self.__irq_impl(event, data)
        except Exception as e:
            # Never let an exception escape: the BLE port permanently
            # disables the IRQ handler when one does, freezing the app.
            print(f"[Bluetooth] IRQ handler error (event {event}): {e}")
        return None

    def __irq_impl(self, event, data):
        """Process a Bluetooth IRQ event (called by __irq)."""
        if event == _IRQ_GET_SECRET:
            return self._get_secret(data)
        if event == _IRQ_SET_SECRET:
            return self._set_secret(data)

        _data = None

        if event == _IRQ_CENTRAL_CONNECT:
            # A central device connected to us (peripheral mode)
            conn_handle, addr_type, addr = data
            self._central_connections.add(conn_handle)
            _data = (conn_handle, addr_type, addr)

        elif event == _IRQ_CENTRAL_DISCONNECT:
            # A central device disconnected from us (peripheral mode)
            conn_handle, addr_type, addr = data
            self._central_connections.discard(conn_handle)
            self._clear_pairing_state(conn_handle)
            # Restart advertising to allow new connections
            if self._peripheral_registered:
                self._start_advertising()
            _data = (conn_handle, addr_type, addr)

        elif event == _IRQ_GATTS_WRITE:
            # A central wrote to one of our characteristics (peripheral mode)
            conn_handle, value_handle = data
            value = self._ble.gatts_read(value_handle)
            if value_handle == self._rx_handle and self._write_callback:
                self._write_callback(value)
            _data = (conn_handle, value_handle, value)

        # ===== CENTRAL MODE EVENTS (when acting as GATT client) =====
        elif event == _IRQ_SCAN_RESULT:
            # A single scan result
            addr_type, addr, adv_type, rssi, adv_data = data
            key = (addr_type, bytes(addr))
            previous = self._scan_data.get(key)
            if adv_type == _ADV_SCAN_RSP:
                if previous is None:
                    primary_type, primary_data = None, b""
                else:
                    primary_type, primary_data, _ = previous
                response_data = bytes(adv_data)
            else:
                primary_type = adv_type
                primary_data = bytes(adv_data)
                response_data = previous[2] if previous is not None else b""

            self._scan_data[key] = (primary_type, primary_data, response_data)
            combined_data = primary_data + response_data
            _data = (addr_type, addr, adv_type, rssi, combined_data)

            # If scan callback is set, call it for each result
            if self._scan_callback:
                if primary_type in (_ADV_IND, _ADV_DIRECT_IND):
                    name = self.decode_name(combined_data)
                    self._scan_callback(addr_type, bytes(addr), name, rssi, combined_data)

        elif event == _IRQ_SCAN_DONE:
            # Scan duration finished or manually stopped
            self._scanning = False
            self._scan_data.clear()
            _data = None

        elif event == _IRQ_PERIPHERAL_CONNECT:
            # Successfully connected to a peripheral (central mode)
            conn_handle, addr_type, addr = data
            self._conn_handle = conn_handle
            self._connected = True
            self._connected_addr = ":".join("{:02X}".format(b) for b in addr)
            self._encrypted = False
            self._bonded = False
            print(f"[BT] Connected to peripheral, handle {conn_handle}")
            _data = (conn_handle, addr_type, addr)

        elif event == _IRQ_PERIPHERAL_DISCONNECT:
            # Disconnected from peripheral (central mode)
            conn_handle, addr_type, addr = data
            self._conn_handle = None
            self._connected = False
            self._connected_addr = None
            self._encrypted = False
            self._bonded = False
            self._services_discovering = False
            self._peripheral_tx_handle = None
            self._peripheral_rx_handle = None
            self._start_handle = None
            self._end_handle = None
            self._clear_pairing_state(conn_handle)
            _data = (conn_handle, addr_type, addr)

        elif event == _IRQ_GATTC_SERVICE_RESULT:
            # Found a service on remote device (central mode)
            conn_handle, start_handle, end_handle, uuid = data
            # Some ports pass UUIDs backed by temporary callback storage.
            # Copy them before keeping the result beyond this IRQ.
            uuid_str = str(uuid)
            self._services.append((start_handle, end_handle, uuid_str))
            # Check for UART service
            if _UART_SERVICE_UUID.lower() in uuid_str.lower():
                self._start_handle = start_handle
                self._end_handle = end_handle
            _data = (conn_handle, start_handle, end_handle, uuid_str)

        elif event == _IRQ_GATTC_SERVICE_DONE:
            # Service discovery complete (central mode)
            conn_handle, status = data
            self._services_discovering = False
            print(
                f"[BT] Service discovery done, status {status}, "
                f"{len(self._services)} services"
            )
            _data = (conn_handle, status)

        elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
            # Found a characteristic on remote device (central mode)
            conn_handle, end_handle, value_handle, properties, uuid = data
            # Characteristic UUIDs can have the same temporary lifetime.
            uuid_str = str(uuid)
            self._characteristics.append((value_handle, properties, uuid_str))
            # Check for UART RX/TX characteristics
            uuid_upper = uuid_str.upper()
            if _UART_RX_CHAR_UUID in uuid_upper:
                self._peripheral_rx_handle = value_handle
            elif _UART_TX_CHAR_UUID in uuid_upper:
                self._peripheral_tx_handle = value_handle
            _data = (conn_handle, end_handle, value_handle, properties, uuid_str)

        elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:
            # Characteristic discovery complete (central mode)
            conn_handle, status = data
            print(
                f"[BT] Characteristic discovery done, status {status}, "
                f"{len(self._characteristics)} characteristics"
            )
            _data = (conn_handle, status)

        elif event == _IRQ_GATTC_WRITE_DONE:
            # Write operation completed (central mode)
            conn_handle, value_handle, status = data
            _data = (conn_handle, value_handle, status)

        elif event == _IRQ_GATTC_NOTIFY:
            # Received notification from peripheral (central mode)
            conn_handle, value_handle, notify_data = data
            if self._notify_callback:
                self._notify_callback(notify_data)
            _data = (conn_handle, value_handle, notify_data)

        elif event == _IRQ_GATTC_READ_RESULT:
            # Read operation result (central mode)
            conn_handle, value_handle, char_data = data
            _data = (conn_handle, value_handle, char_data)

        elif event == _IRQ_ENCRYPTION_UPDATE:
            # Encryption/bonding state changed
            conn_handle, encrypted, authenticated, bonded, key_size = data
            print(
                f"[BT] Encryption update: encrypted={encrypted}, "
                f"bonded={bonded}, key_size={key_size}"
            )
            if self._conn_handle == conn_handle:
                self._encrypted = bool(encrypted)
                self._bonded = bool(bonded)
            self._clear_pairing_state(conn_handle)
            _data = (conn_handle, encrypted, authenticated, bonded, key_size)

        elif event == _IRQ_PASSKEY_ACTION:
            # Passkey action required during pairing
            conn_handle, action, passkey = data
            print(
                f"[BT] Passkey action: handle={conn_handle}, "
                f"action={action}, value={passkey}"
            )
            self._passkey = passkey
            self._passkey_action = action
            self._passkey_conn_handle = conn_handle
            _data = (conn_handle, action, passkey)

        else:
            # Handle other events generically
            _data = data

        if self._callback:
            self._callback(event, _data)
            if event == _IRQ_GATTC_SERVICE_DONE:
                print("[BT] Service-done application callback returned")
            elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:
                print("[BT] Characteristic-done application callback returned")
            if event in (_IRQ_GATTC_SERVICE_DONE, _IRQ_GATTC_CHARACTERISTIC_DONE):
                print(f"[BT] Application callback returned for GATT event {event}")

        if (
            event == _IRQ_GATTC_SERVICE_DONE
            and _data is not None
            and _data[1] == 0
            and self._auto_discover
            and self._connected
            and self._conn_handle == _data[0]
            and self._start_handle is not None
            and self._end_handle is not None
        ):
            if not self.discover_characteristics(
                self._start_handle, self._end_handle
            ):
                if self._callback:
                    self._callback(
                        _IRQ_GATTC_CHARACTERISTIC_DONE, (_data[0], -1)
                    )

        if event == _IRQ_PERIPHERAL_CONNECT and self._auto_discover:
            self.discover_services()

    def _clear_pairing_state(self, conn_handle):
        """Clear pairing metadata when its connection is no longer pairing."""
        if (
            self._passkey_conn_handle is None
            or self._passkey_conn_handle == conn_handle
        ):
            self._pairing = False
            self._passkey = None
            self._passkey_action = None
            self._passkey_conn_handle = None

    def _load_secrets(self) -> None:
        """Load BLE security secrets from local storage."""
        if self._storage is None or not self._storage.exists(_SECRETS_FILE):
            return
        try:
            data: dict = self._storage.deserialize(_SECRETS_FILE)
            if not data:
                return
            import binascii

            for sec_type, key_hex, value_hex in data:
                self._secrets[(int(sec_type), binascii.unhexlify(key_hex))] = (
                    binascii.unhexlify(value_hex)
                )
        except Exception as e:
            print(f"[Bluetooth] Load BLE secrets error: {e}")

    def _get_secret(self, data):
        sec_type, index, key = data
        if key is not None:
            return self._secrets.get((sec_type, bytes(key)))

        current_index = 0
        for (stored_type, _), value in self._secrets.items():
            if stored_type == sec_type:
                if current_index == index:
                    return value
                current_index += 1
        return None

    def _set_secret(self, data) -> bool:
        sec_type, key, value = data
        secret_key = (sec_type, bytes(key))
        if value:
            self._secrets[secret_key] = bytes(value)
        elif secret_key in self._secrets:
            del self._secrets[secret_key]
        else:
            return False
        self._secrets_dirty = self._storage is not None
        return True

    def flush_secrets(self) -> bool:
        """Persist pending BLE secrets outside the Bluetooth IRQ callback."""
        if not self._secrets_dirty:
            return True
        if self._storage is None:
            self._secrets_dirty = False
            return True

        try:
            import binascii

            entries = []
            for (sec_type, key), value in self._secrets.items():
                entries.append(
                    (
                        sec_type,
                        binascii.hexlify(key).decode("ascii"),
                        binascii.hexlify(value).decode("ascii"),
                    )
                )
            if not self._storage.serialize(entries, _SECRETS_FILE):
                print("[Bluetooth] Save BLE secrets error")
                self._secrets_dirty = False
                return False
        except Exception as e:
            print(f"[Bluetooth] Save BLE secrets error: {e}")
            self._secrets_dirty = False
            return False

        self._secrets_dirty = False
        return True

    def _configure_bonding(self):
        """Enable BLE bonding when the current port supports it."""
        try:
            self._ble.config(bond=True, mitm=False, io=3, le_secure=False)
        except Exception as e:
            print(f"[Bluetooth] Bonding configuration error: {e}")
            return False
        return True

    def _advertising_payload(
        self, name=None, services=None, appearance=0, include_flags=True
    ):
        """Generate advertising payload.

        Args:
            name (str): Device name to advertise. Defaults to None.
            services (list): List of service UUIDs to advertise. Defaults to None.
            appearance (int): Device appearance code. Defaults to 0.

        Returns:
            bytearray: The advertising payload.
        """
        from ubluetooth import UUID

        payload = bytearray()

        def _append(adv_type, value):
            """Append an advertising data structure to the payload.

            Args:
                adv_type (int): The advertising data type.
                value (bytes): The payload value.
            """
            nonlocal payload
            if len(payload) + len(value) + 2 > _ADV_MAX_PAYLOAD:
                raise ValueError("Advertising payload exceeds 31 bytes")
            payload += struct.pack("BB", len(value) + 1, adv_type) + value

        if include_flags:
            # Flags: general discoverable, BR/EDR not supported
            _append(_ADV_TYPE_FLAGS, struct.pack("B", 0x06))

        if name:
            name_bytes = name.encode("utf-8") if isinstance(name, str) else bytes(name)
            max_name_length = _ADV_MAX_PAYLOAD - len(payload) - 2
            name_type = _ADV_TYPE_NAME
            if len(name_bytes) > max_name_length:
                name_bytes = name_bytes[:max_name_length]
                while name_bytes:
                    try:
                        name_bytes.decode("utf-8")
                        break
                    except UnicodeError:
                        name_bytes = name_bytes[:-1]
                name_type = _ADV_TYPE_SHORT_NAME
            _append(name_type, name_bytes)

        if services:
            for uuid in services:
                if isinstance(uuid, str):
                    uuid = UUID(uuid)
                b = bytes(uuid)
                if len(b) == 2:
                    _append(_ADV_TYPE_UUID16_COMPLETE, b)
                elif len(b) == 4:
                    _append(_ADV_TYPE_UUID32_COMPLETE, b)
                elif len(b) == 16:
                    _append(_ADV_TYPE_UUID128_COMPLETE, b)

        if appearance:
            _append(_ADV_TYPE_APPEARANCE, struct.pack("<H", appearance))

        return payload

    def _start_advertising(self, interval_us=500000):
        """Start advertising with the registered payload.

        Args:
            interval_us (int): Advertising interval in microseconds. Defaults to 500000.
        """
        if hasattr(self, "_adv_payload") and self._adv_payload:
            self._ble.gap_advertise(
                interval_us,
                adv_data=self._adv_payload,
                resp_data=getattr(self, "_scan_response", None),
            )

    def advertise(self, interval_us=None, name="Picoware"):
        """Start or stop BLE advertising to make this device discoverable.

        Args:
            interval_us (int): Advertising interval in microseconds. None stops advertising. Defaults to None.
            name (str): Device name to advertise. Defaults to "Picoware".

        Returns:
            bool: True if advertising started or stopped successfully.
        """

        try:
            if interval_us is None:
                # Stop advertising
                self._ble.gap_advertise(None)
                return True
            if not self.register():
                return False

            gap_name = name.decode("utf-8") if isinstance(name, bytes) else name
            try:
                self._ble.config(gap_name=gap_name)
            except Exception as e:
                print(f"[Bluetooth] GAP name configuration error: {e}")
            self._configure_bonding()
            self._adv_payload = self._advertising_payload(name=name)
            self._scan_response = self._advertising_payload(
                services=[_UART_SERVICE_UUID], include_flags=False
            )
            self._ble.gap_advertise(
                interval_us,
                adv_data=self._adv_payload,
                resp_data=self._scan_response,
            )
            return True
        except Exception as e:
            print(f"[Bluetooth] Advertise error: {e}")
            return False

    def connect(self, addr_type, addr, timeout_ms=10000, auto_discover=True):
        """Connect to a BLE peripheral device (central mode).

        Args:
            addr_type (int): Address type (0 = public, 1 = random).
            addr (bytes): Device address as bytes.
            timeout_ms (int): Connection timeout in milliseconds. Defaults to 10000.
            auto_discover (bool): Whether to automatically discover services. Defaults to True.

        Returns:
            bool: True if the connection was initiated successfully.
        """
        if self._connected:
            return False

        # Clear previous discovery state
        self._services = []
        self._characteristics = []
        self._peripheral_tx_handle = None
        self._peripheral_rx_handle = None
        self._start_handle = None
        self._end_handle = None
        self._services_discovering = False
        self._auto_discover = bool(auto_discover)

        try:
            self._ble.gap_connect(addr_type, addr, timeout_ms)
            return True
        except Exception as e:
            print(f"[Bluetooth] Connect error: {e}")
            return False

    def decode_name(self, adv_data) -> str:
        """Decode device name from advertising data.

        Args:
            adv_data (bytes): Raw advertising data bytes.

        Returns:
            str: The device name or empty string if not found.
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

        Works for both modes:
        - Central mode: Disconnects from the connected peripheral
        - Peripheral mode: Disconnects a specific central if conn_handle provided

        Args:
            conn_handle (int): Connection handle to disconnect. Uses the current connection if None. Defaults to None.
        """
        handle = conn_handle if conn_handle is not None else self._conn_handle
        if handle is not None:
            try:
                self._ble.gap_disconnect(handle)
            except Exception:
                pass
            finally:
                if handle == self._conn_handle:
                    # Central mode disconnection
                    self._conn_handle = None
                    self._connected = False
                    self._connected_addr = None
                    self._encrypted = False
                    self._bonded = False
                    self._services_discovering = False
                    self._peripheral_tx_handle = None
                    self._peripheral_rx_handle = None
                elif handle in self._central_connections:
                    # Peripheral mode disconnection (handled by IRQ)
                    pass

    def discover_characteristics(self, start_handle, end_handle):
        """Discover characteristics for a service.

        Results are delivered via callback with _IRQ_GATTC_CHARACTERISTIC_RESULT events.

        Args:
            start_handle (int): Service start handle.
            end_handle (int): Service end handle.

        Returns:
            bool: True if discovery was initiated.
        """
        if not self._connected or self._conn_handle is None:
            return False

        print(
            f"[BT] Discovering characteristics {start_handle}-{end_handle} "
            f"(handle {self._conn_handle})"
        )
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

        print(f"[BT] Discovering services (handle {self._conn_handle})")
        self._services = []
        self._services_discovering = True
        try:
            self._ble.gattc_discover_services(self._conn_handle)
            return True
        except Exception as e:
            self._services_discovering = False
            print(f"[Bluetooth] Service discovery error: {e}")
            return False

    def is_device_paired(self, addr: str) -> bool:
        """Check if a device address is in the paired devices list.

        Args:
            addr (str): The device address to check.

        Returns:
            bool: True if the device is paired.
        """
        if (
            self._connected
            and self._connected_addr == addr
            and self._encrypted
            and self._bonded
        ):
            return True
        devices = self.load_paired_devices()
        return addr in devices

    def load_paired_devices(self) -> dict:
        """Load paired devices from storage.

        Returns:
            dict: Dictionary of paired devices {addr: {name, paired}}
        """
        if self._paired_devices is not None:
            return self._paired_devices
        if self._storage is None or not self._storage.exists(_BONDING_FILE):
            self._paired_devices = {}
            return self._paired_devices
        devices = self._storage.deserialize(_BONDING_FILE)
        self._paired_devices = devices if isinstance(devices, dict) else {}
        return self._paired_devices

    def pair(self):
        """Initiate pairing/bonding with the connected device.

        Call this after connecting to establish an encrypted bond.
        The device will be remembered for future connections.
        """
        if not self._connected or self._conn_handle is None:
            print("[Bluetooth] Not connected.")
            return False

        self._pairing = True
        print(
            f"[BT] Starting pairing (handle {self._conn_handle}, "
            f"encrypted={self._encrypted}, bonded={self._bonded})"
        )
        try:
            # Request pairing - this triggers _IRQ_ENCRYPTION_UPDATE or _IRQ_PASSKEY_ACTION
            self._ble.gap_pair(self._conn_handle)
            print("[BT] Pairing request submitted to BLE stack")
            return True
        except Exception as e:
            print(f"[Bluetooth] Pair error: {e}")
            self._pairing = False
            return False

    def passkey_reply(self, accept=True, passkey=None):
        """Reply to a passkey request during pairing.

        Args:
            accept (bool): Whether to accept the pairing. Defaults to True.
            passkey (int): The passkey to use for input actions. Defaults to None.

        Returns:
            bool: True if the passkey response was sent.
        """
        conn_handle = self._passkey_conn_handle
        action = self._passkey_action
        if conn_handle is None or action is None:
            return False

        if action == _PASSKEY_ACTION_INPUT:
            if not accept:
                try:
                    self._ble.gap_disconnect(conn_handle)
                    return True
                except Exception as e:
                    print(f"[Bluetooth] Passkey rejection error: {e}")
                    return False
            if passkey is None:
                return False
            reply_passkey = int(passkey)
        elif action == _PASSKEY_ACTION_NUMERIC_COMPARISON:
            reply_passkey = 1 if accept else 0
        elif action == _PASSKEY_ACTION_DISPLAY:
            if not accept:
                try:
                    self._ble.gap_disconnect(conn_handle)
                    return True
                except Exception as e:
                    print(f"[Bluetooth] Passkey rejection error: {e}")
                    return False
            reply_passkey = self._passkey
        else:
            return False

        try:
            self._ble.gap_passkey(conn_handle, action, reply_passkey)
            return True
        except Exception as e:
            print(f"[Bluetooth] Passkey reply error: {e}")
            return False

    def read(self, handle):
        """Read data from a characteristic.

        Result is delivered via callback with _IRQ_GATTC_READ_RESULT event.

        Args:
            handle (int): Characteristic handle to read from.

        Returns:
            bool: True if the read was initiated.
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
            addr (str): Device address string to remove.

        Returns:
            bool: True if the device was removed.
        """
        if self._storage is None:
            return False

        try:
            devices = self.load_paired_devices()
            if addr in devices:
                del devices[addr]
                return self._storage.serialize(devices, _BONDING_FILE)
        except Exception as e:
            print(f"[Bluetooth] Remove paired device error: {e}")
        return False

    def save_paired_device(self, addr: str, name: str = ""):
        """Save a paired device to storage.

        Args:
            addr (str): Device address string.
            name (str): Device name. Defaults to "".

        Returns:
            bool: True if the device was saved.
        """
        if self._storage is None:
            return False

        try:
            # Load existing paired devices
            devices = self.load_paired_devices()

            # Add or update device
            devices[addr] = {"name": name, "paired": True}

            # Save back to storage
            return self._storage.serialize(devices, _BONDING_FILE)
        except Exception as e:
            print(f"[Bluetooth] Save paired device error: {e}")
            return False

    def scan(
        self,
        duration_ms=5000,
        interval_us=30000,
        window_us=30000,
        active=True,
        callback=None,
    ):
        """Start scanning for BLE devices (central mode).

        Args:
            duration_ms (int): How long to scan in milliseconds. Defaults to 5000; 0 scans continuously.
            interval_us (int): Scan interval in microseconds. Defaults to 30000.
            window_us (int): Scan window in microseconds. Defaults to 30000.
            active (bool): Whether to request scan response data. Defaults to True.
            callback (callable): Optional callback for scan results (addr_type, addr, name, rssi, adv_data). Defaults to None.

        Returns:
            bool: True if the scan started successfully.
        """
        if callback:
            self._scan_callback = callback
        self._scan_data = {}
        self._scanning = True
        try:
            self._ble.gap_scan(duration_ms, interval_us, window_us, active)
            return True
        except Exception as e:
            print(f"[Bluetooth] Scan error: {e}")
            self._scanning = False
            return False

    def scan_stop(self):
        """Stop an ongoing scan."""
        self._ble.gap_scan(None)
        self._scanning = False
        self._scan_data = {}

    def register(self):
        """Register the device as a GATT server with UART service.

        This allows the device to accept incoming connections and
        provide services/characteristics to connected centrals.

        Returns:
            bool: True if registration successful
        """
        if self._peripheral_registered:
            return True

        try:
            from ubluetooth import UUID

            _FLAG_READ = const(0x0002)
            _FLAG_WRITE_NO_RESPONSE = const(0x0004)
            _FLAG_WRITE = const(0x0008)
            _FLAG_NOTIFY = const(0x0010)

            # Nordic UART Service (NUS)
            BLE_NUS = UUID(_UART_SERVICE_UUID)
            BLE_RX = (UUID(_UART_RX_CHAR_UUID), _FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE)
            BLE_TX = (UUID(_UART_TX_CHAR_UUID), _FLAG_READ | _FLAG_NOTIFY)

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
                    self._tx_handle,
                    self._rx_handle,
                ),
            ) = self._ble.gatts_register_services(SERVICES)
            self._peripheral_registered = True
            return True
        except Exception as e:
            print(f"[Bluetooth] Register error: {e}")
            return False

    def start_peripheral(self, name="Picoware", interval_us=500000):
        """Start as a BLE peripheral (GATT server) with UART service.

        Registers the UART service and starts advertising so central devices
        can connect and communicate.

        Args:
            name (str): Device name to advertise. Defaults to "Picoware".
            interval_us (int): Advertising interval in microseconds. Defaults to 500000.

        Returns:
            bool: True if started successfully.
        """
        if not self.register():
            return False
        return self.advertise(interval_us=interval_us, name=name)

    def stop_peripheral(self):
        """Stop peripheral mode (stop advertising).

        Returns:
            bool: True if stopped successfully
        """
        return self.advertise(interval_us=None)

    def send(self, data):
        """Send data to all connected central devices (peripheral mode).

        Sends a notification to all connected centrals.

        Args:
            data (bytes or str): Data to send.

        Returns:
            bool: True if sent to at least one central.
        """
        if not self._central_connections or self._tx_handle is None:
            return False

        if isinstance(data, str):
            data = data.encode()

        sent = False
        for conn_handle in self._central_connections:
            try:
                self._ble.gatts_notify(conn_handle, self._tx_handle, data)
                sent = True
            except Exception as e:
                print(f"[Bluetooth] Send error: {e}")

        return sent

    def on_write(self, callback):
        """Set callback for when data is received from a central (peripheral mode).

        The callback receives the data bytes as its argument.

        Args:
            callback (callable): Function to call with received data.
        """
        self._write_callback = callback

    def on_notify(self, callback):
        """Set callback for when data is received from a peripheral (central mode).

        The callback receives the data bytes as its argument.

        Args:
            callback (callable): Function to call with received data.
        """
        self._notify_callback = callback

    def on_scan(self, callback):
        """Set callback for scan results (central mode).

        The callback receives (addr_type, addr, name, rssi, adv_data) per device.

        Args:
            callback (callable): Function to call for each scan result.
        """
        self._scan_callback = callback

    def subscribe(self, handle=None, notify=True):
        """Subscribe to notifications from a characteristic (central mode).

        Args:
            handle (int): Characteristic value handle. Uses the UART TX handle if None. Defaults to None.
            notify (bool): True for notifications, False to unsubscribe. Defaults to True.

        Returns:
            bool: True if the subscription request was sent.
        """
        if not self._connected or self._conn_handle is None:
            print("[Bluetooth] Not connected.")
            return False

        if handle is None:
            handle = self._peripheral_tx_handle

        if handle is None:
            print("[Bluetooth] No TX characteristic to subscribe to")
            return False

        # CCCD handle is typically value_handle + 1
        cccd_handle = handle + 1
        print(f"[BT] Subscribing to TX handle {handle} (CCCD {cccd_handle})")
        value = b"\x01\x00" if notify else b"\x00\x00"

        try:
            self._ble.gattc_write(self._conn_handle, cccd_handle, value, 1)
            return True
        except Exception as e:
            print(f"[Bluetooth] Subscribe error: {e}")
            return False

    def write(self, data, handle=None, response=False):
        """Write data to the connected peripheral (central mode).

        Args:
            data (bytes or str): Data to write.
            handle (int): Characteristic handle to write to. Uses the UART RX handle if None. Defaults to None.
            response (bool): Whether to request a write response. Defaults to False.

        Returns:
            bool: True if the write was initiated.
        """
        if not self._connected or self._conn_handle is None:
            return False

        if handle is None:
            handle = self._peripheral_rx_handle

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

    def is_uart_ready(self) -> bool:
        """Check if UART service is fully discovered and ready (central mode).

        Returns:
            bool: True if both TX and RX handles are discovered
        """
        return (
            self._connected
            and self._peripheral_tx_handle is not None
            and self._peripheral_rx_handle is not None
        )

    def scan_for_uart_devices(self, callback, duration_ms=5000):
        """Scan for devices advertising the UART service (central mode).

        Args:
            callback (callable): Function called with (addr_type, addr, name) per UART device found.
            duration_ms (int): Scan duration in milliseconds. Defaults to 5000.

        Returns:
            bool: True if the scan started.
        """
        from ubluetooth import UUID

        uart_uuid = UUID(_UART_SERVICE_UUID)
        found_devices = []

        def _scan_filter(addr_type, addr, name, rssi, adv_data):
            """Filter scan results for UART service devices.

            Args:
                addr_type (int): Address type of the device.
                addr (bytes): Device address.
                name (str): Advertised device name.
                rssi (int): Signal strength.
                adv_data (bytes): Raw advertising data.
            """
            # Check if UART service UUID is in the advertising data
            services = self.decode_services(adv_data)
            for svc in services:
                if str(svc) == str(uart_uuid):
                    addr_key = bytes(addr)
                    if addr_key not in found_devices:
                        found_devices.append(addr_key)
                        callback(addr_type, addr, name)
                    break

        self._scan_callback = _scan_filter
        return self.scan(duration_ms=duration_ms)

    def decode_services(self, adv_data) -> list:
        """Decode service UUIDs from advertising data.

        Args:
            adv_data (bytes): Raw advertising data bytes.

        Returns:
            list: List of UUID objects found in the advertising data.
        """
        from ubluetooth import UUID

        services = []
        i = 0
        while i + 1 < len(adv_data):
            length = adv_data[i]
            if length == 0:
                break
            ad_type = adv_data[i + 1]
            data = adv_data[i + 2 : i + 1 + length]

            # UUID types: 16-bit, 32-bit, 128-bit (complete or incomplete)
            if ad_type in (0x02, 0x03):  # 16-bit UUIDs
                for j in range(0, len(data), 2):
                    if j + 2 <= len(data):
                        services.append(UUID(data[j : j + 2]))
            elif ad_type in (0x04, 0x05):  # 32-bit UUIDs
                for j in range(0, len(data), 4):
                    if j + 4 <= len(data):
                        services.append(UUID(data[j : j + 4]))
            elif ad_type in (0x06, 0x07):  # 128-bit UUIDs
                for j in range(0, len(data), 16):
                    if j + 16 <= len(data):
                        services.append(UUID(data[j : j + 16]))

            i += 1 + length
        return services
