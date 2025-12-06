class Bluetooth:
    """A class to manage Bluetooth functionality."""

    def __init__(self):
        from bluetooth import BLE

        self._ble = BLE()
        self._ble.active(True)
        self._ble.irq(self.__irq)

    def __del__(self):
        """Clean up Bluetooth resources."""
        if self._ble:
            self._ble.active(False)
            del self._ble
            self._ble = None

    def __irq(self, event, data):
        """Handle Bluetooth IRQ events."""
        pass
