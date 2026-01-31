from board import GP0, GP1
from microcontroller import Pin
from time import monotonic, sleep


class UART:
    """Class to control a UART interface on a Raspberry Pi Pico device."""

    def __init__(
        self,
        tx_pin: Pin = GP0,
        rx_pin: Pin = GP1,
        baudrate: int = 115200,
        timeout: float = 5.0,
    ):
        from busio import UART as busio_UART

        self.uart = busio_UART(tx=tx_pin, rx=rx_pin, baudrate=baudrate, timeout=timeout)

    def available(self) -> int:
        """Return the number of bytes available to read from the UART interface."""
        return self.uart.in_waiting

    def clear_buffer(self) -> None:
        """Clear the UART buffer."""
        while self.available() > 0:
            self.uart.read(1)

    def read(self, size=1) -> bytes:
        """Read data from the UART interface."""
        return self.uart.read(size)

    def read_line(self) -> str:
        """Read a line of data from the UART interface."""
        line = self.uart.readline()
        if line:
            return line.decode("utf-8").strip()
        return ""

    def read_string(self, size=1) -> str:
        """Read a string of data from the UART interface."""
        string = self.uart.read(size)
        if string:
            return string.decode("utf-8").strip()
        return ""

    def read_until(self, terminator: str, timeout: float = 5.0) -> str:
        """Read data from the UART interface until a terminator string is found."""
        received_data = ""
        start_time = monotonic()
        while monotonic() - start_time < timeout:
            if self.available() > 0:
                char = self.uart.read(1).decode("utf-8")
                received_data += char
                if received_data.endswith(terminator):
                    received_data = received_data[: -len(terminator)]
                    break
            else:
                sleep(0.01)
        return received_data.strip()

    def print(self, data: str) -> None:
        """Write a string of data to the UART interface."""
        self.uart.write(data.encode("utf-8"))

    def println(self, data: str) -> None:
        """Write a string of data to the UART interface with a newline."""
        self.uart.write((data + "\n").encode("utf-8"))

    def write(self, data: bytes) -> None:
        """Write bytes to the UART interface."""
        self.uart.write(data)
