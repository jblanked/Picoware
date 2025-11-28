class UART:
    """Class representing a UART (Universal Asynchronous Receiver-Transmitter) interface."""

    def __init__(
        self,
        tx_pin: int = 4,
        rx_pin: int = 5,
        baud_rate: int = 115200,
        timeout: int = 2000,
    ) -> None:
        """Initialize the UART interface."""
        from machine import UART as MachineUART
        from machine import Pin

        self._uart = MachineUART(1, baudrate=baud_rate, tx=Pin(tx_pin), rx=Pin(rx_pin))
        self._uart.init()
        self._timeout = timeout  # milliseconds

    def __del__(self):
        """Deinitialize the UART interface."""
        self._uart.deinit()
        del self._uart
        self._uart = None

    @property
    def has_data(self) -> bool:
        """Check if there is data available to read from the UART interface."""
        return self._uart.any() > 0

    @property
    def is_sending(self) -> bool:
        """Check if the UART interface is currently sending data."""
        return self._uart.txdone()

    def clear(self) -> None:
        """Clear the serial buffer"""
        while self._uart.any() > 0:
            self._uart.read()

    def flush(self):
        """Flush the UART interface."""
        self._uart.flush()

    def println(self, message: str):
        """Write a message followed by a newline to the UART interface."""
        self._uart.write(message + "\n")

    def read_into(self, buffer: bytearray) -> int:
        """Read data from the UART interface into a buffer."""
        return self._uart.readinto(buffer)

    def read_line(self) -> str:
        """Read a line from the UART interface with timeout handling."""
        from time import ticks_ms

        start_time = ticks_ms()
        message = ""

        while (ticks_ms() - start_time) < self._timeout:
            if self._uart.any() > 0:
                try:
                    raw_data = self._uart.read()
                    if raw_data:
                        # Reset the timeout when data is read
                        start_time = ticks_ms()
                        message += raw_data.decode()

                        if "\n" in message:
                            message = message.strip("\n")
                            return message
                except Exception as e:
                    continue

        # Timeout reached with no newline received
        return None

    def read_serial_line(self) -> str:
        """Read a line from the UART interface."""
        data = ""
        try:
            raw_data = self._uart.read()
            if raw_data:  # Ensures raw_data isn't empty before decoding
                data = raw_data.decode()
        except Exception as e:
            pass  # raw_data is empty/None
        return data

    def set_callback(self, callback):
        """Set an interrupt handler to be called when a UART event occurs."""
        self._uart.irq(handler=callback)

    def write(self, message: bytes):
        """Write a message to the UART interface."""
        self._uart.write(message)
