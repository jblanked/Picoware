import struct
import micropython
from micropython import const


micropython.alloc_emergency_exception_buf(100)


class PSRAM:
    """MicroPython PSRAM interface using bit-banged SPI."""

    # Constants
    PSRAM_SIZE = const(8 * 1024 * 1024)  # 8MB total
    HEAP_START = const(0x100000)  # Start heap at 1MB offset
    HEAP_SIZE = const(7 * 1024 * 1024)  # 7MB for heap

    # Pin definitions
    PIN_CS = const(20)
    PIN_SCK = const(21)
    PIN_MOSI = const(2)
    PIN_MISO = const(3)

    # PSRAM commands
    CMD_READ = const(0x0B)
    CMD_WRITE = const(0x02)
    CMD_RESET_ENABLE = const(0x66)
    CMD_RESET = const(0x99)

    @property
    def block_count(self):
        """Get number of allocated blocks."""
        return self._total_blocks

    @property
    def free_heap_size(self):
        """Get free heap size in bytes."""
        return self.HEAP_SIZE - self._total_used

    @property
    def is_ready(self):
        """Check if PSRAM is ready for use."""
        return self._hardware_initialized

    @property
    def total_heap_size(self):
        """Get total heap size available for allocation."""
        return self.HEAP_SIZE

    @property
    def total_size(self):
        """Get total PSRAM size in bytes."""
        return self.PSRAM_SIZE

    @property
    def used_heap_size(self):
        """Get used heap size in bytes."""
        return self._total_used

    def __init__(self):
        """Initialize PSRAM."""
        from machine import Pin

        # Initialize pins
        self.cs = Pin(self.PIN_CS, Pin.OUT, value=1)
        self.sck = Pin(self.PIN_SCK, Pin.OUT, value=0)
        self.mosi = Pin(self.PIN_MOSI, Pin.OUT, value=0)
        self.miso = Pin(self.PIN_MISO, Pin.IN)

        # Heap management variables
        self._hardware_initialized = False
        self._heap_head = 0
        self._total_used = 0
        self._total_blocks = 0

        # Initialize hardware
        self._init_hardware()

    def _init_hardware(self):
        """Initialize PSRAM hardware and heap."""
        if self._hardware_initialized:
            return True

        # PSRAM reset sequence
        self._reset_psram()

        # Initialize heap with a single free block
        self._heap_head = self.HEAP_START
        initial_block = struct.pack("<IBIIII", self.HEAP_SIZE, 1, 0, 0, 0, 0)
        self._write_raw(self._heap_head, initial_block)

        self._total_used = 0
        self._total_blocks = 0
        self._hardware_initialized = True

        return True

    @micropython.native
    def _read_raw(self, addr, length):
        """Read raw data from PSRAM address."""
        if not self._hardware_initialized and addr != self.HEAP_START:
            return b""

        cmd = bytearray(
            [
                self.CMD_READ,
                (addr >> 16) & 0xFF,
                (addr >> 8) & 0xFF,
                addr & 0xFF,
                0x00,  # Dummy byte for read
            ]
        )

        self.cs(0)
        self._spi_write(cmd)
        data = self._spi_read(length)
        self.cs(1)

        return data

    def _reset_psram(self):
        """Reset PSRAM chip."""
        from time import sleep_us

        # Reset enable
        self.cs(0)
        self._spi_write(bytes([self.CMD_RESET_ENABLE]))
        self.cs(1)
        sleep_us(50)

        # Reset command
        self.cs(0)
        self._spi_write(bytes([self.CMD_RESET]))
        self.cs(1)
        sleep_us(100)

    @micropython.native
    def _spi_read(self, length):
        """Read multiple bytes via SPI."""
        result = bytearray(length)
        for i in range(length):
            byte = 0
            # Unroll the bit loop for maximum speed
            # Bit 7 (MSB)
            self.sck(1)
            if self.miso():
                byte |= 0x80
            self.sck(0)
            # Bit 6
            self.sck(1)
            if self.miso():
                byte |= 0x40
            self.sck(0)
            # Bit 5
            self.sck(1)
            if self.miso():
                byte |= 0x20
            self.sck(0)
            # Bit 4
            self.sck(1)
            if self.miso():
                byte |= 0x10
            self.sck(0)
            # Bit 3
            self.sck(1)
            if self.miso():
                byte |= 0x08
            self.sck(0)
            # Bit 2
            self.sck(1)
            if self.miso():
                byte |= 0x04
            self.sck(0)
            # Bit 1
            self.sck(1)
            if self.miso():
                byte |= 0x02
            self.sck(0)
            # Bit 0 (LSB)
            self.sck(1)
            if self.miso():
                byte |= 0x01
            self.sck(0)

            result[i] = byte
        return bytes(result)

    @micropython.native
    def _spi_write(self, data):
        """Write buffer via SPI."""

        if not isinstance(data, (memoryview, bytes, bytearray)):
            data = memoryview(data)

        for byte in data:
            # Unroll the bit loop
            # Bit 7 (MSB)
            self.mosi((byte >> 7) & 1)
            self.sck(1)
            self.sck(0)
            # Bit 6
            self.mosi((byte >> 6) & 1)
            self.sck(1)
            self.sck(0)
            # Bit 5
            self.mosi((byte >> 5) & 1)
            self.sck(1)
            self.sck(0)
            # Bit 4
            self.mosi((byte >> 4) & 1)
            self.sck(1)
            self.sck(0)
            # Bit 3
            self.mosi((byte >> 3) & 1)
            self.sck(1)
            self.sck(0)
            # Bit 2
            self.mosi((byte >> 2) & 1)
            self.sck(1)
            self.sck(0)
            # Bit 1
            self.mosi((byte >> 1) & 1)
            self.sck(1)
            self.sck(0)
            # Bit 0 (LSB)
            self.mosi(byte & 1)
            self.sck(1)
            self.sck(0)

    @micropython.native
    def _write_raw(self, addr, data):
        """Write raw data to PSRAM address"""
        if not self._hardware_initialized and addr != self.HEAP_START:
            return

        if not isinstance(data, (memoryview, bytes, bytearray)):
            data = memoryview(data)

        self.cs(0)

        # Write command + address (4 bytes total)
        command_bytes = [
            self.CMD_WRITE,
            (addr >> 16) & 0xFF,
            (addr >> 8) & 0xFF,
            addr & 0xFF,
        ]
        for byte in command_bytes:
            self.mosi((byte >> 7) & 1)
            self.sck(1)
            self.sck(0)
            self.mosi((byte >> 6) & 1)
            self.sck(1)
            self.sck(0)
            self.mosi((byte >> 5) & 1)
            self.sck(1)
            self.sck(0)
            self.mosi((byte >> 4) & 1)
            self.sck(1)
            self.sck(0)
            self.mosi((byte >> 3) & 1)
            self.sck(1)
            self.sck(0)
            self.mosi((byte >> 2) & 1)
            self.sck(1)
            self.sck(0)
            self.mosi((byte >> 1) & 1)
            self.sck(1)
            self.sck(0)
            self.mosi(byte & 1)
            self.sck(1)
            self.sck(0)
        # Write data bytes
        for byte in data:
            self.mosi((byte >> 7) & 1)
            self.sck(1)
            self.sck(0)
            self.mosi((byte >> 6) & 1)
            self.sck(1)
            self.sck(0)
            self.mosi((byte >> 5) & 1)
            self.sck(1)
            self.sck(0)
            self.mosi((byte >> 4) & 1)
            self.sck(1)
            self.sck(0)
            self.mosi((byte >> 3) & 1)
            self.sck(1)
            self.sck(0)
            self.mosi((byte >> 2) & 1)
            self.sck(1)
            self.sck(0)
            self.mosi((byte >> 1) & 1)
            self.sck(1)
            self.sck(0)
            self.mosi(byte & 1)
            self.sck(1)
            self.sck(0)

        self.cs(1)

    @micropython.native
    def fill(self, addr, value, length, chunk_size=8192):
        """Fill PSRAM with a specific value."""
        if length <= 0:
            return

        max_chunk = min(chunk_size, length)
        chunk = bytes([value & 0xFF] * max_chunk)

        offset = 0
        while offset < length:
            remaining = length - offset
            if remaining >= max_chunk:
                self._write_raw(addr + offset, chunk)
                offset += max_chunk
            else:
                # Last partial chunk
                partial_chunk = chunk[:remaining]
                self._write_raw(addr + offset, partial_chunk)
                offset += remaining

    @micropython.native
    def free(self, addr):
        """Free previously allocated PSRAM memory."""
        if not self._hardware_initialized or addr == 0:
            return

        header_size = 21
        block_addr = addr - header_size
        block_data = self._read_raw(block_addr, header_size)

        if len(block_data) < header_size:
            return

        try:
            block_size, is_free, _, _, next_addr, prev_addr = struct.unpack(
                "<IBIIII", block_data
            )

            if is_free:
                return

            is_free = 1
            self._total_used -= block_size - header_size
            self._total_blocks -= 1

            block_data = struct.pack(
                "<IBIIII", block_size, is_free, 0, 0, next_addr, prev_addr
            )
            self._write_raw(block_addr, block_data)

        except Exception as e:
            print(f"Free error: {e}")
            return

    @micropython.native
    def malloc(self, size):
        """Allocate memory from PSRAM heap."""
        if not self._hardware_initialized or size == 0:
            return 0

        aligned_size = (size + 3) & ~3
        header_size = 21  # size(4) + is_free(1) + pad1(4) + pad2(4) + next(4) + prev(4) = 21 bytes
        total_size = aligned_size + header_size

        current_addr = self._heap_head
        while current_addr != 0:
            block_data = self._read_raw(current_addr, header_size)
            if len(block_data) < header_size:
                break

            try:
                block_size, is_free, _, _, next_addr, prev_addr = struct.unpack(
                    "<IBIIII", block_data
                )

                if is_free and block_size >= total_size:
                    if block_size > total_size + header_size + 16:
                        new_block_addr = current_addr + total_size
                        new_block_data = struct.pack(
                            "<IBIIII",
                            block_size - total_size,
                            1,
                            0,
                            0,
                            next_addr,
                            current_addr,
                        )
                        self._write_raw(new_block_addr, new_block_data)

                        if next_addr != 0:
                            next_block_data = self._read_raw(next_addr, header_size)
                            if len(next_block_data) == header_size:
                                (
                                    next_size,
                                    next_free,
                                    next_pad1,
                                    next_pad2,
                                    next_next,
                                    _,
                                ) = struct.unpack("<IBIIII", next_block_data)
                                updated_next = struct.pack(
                                    "<IBIIII",
                                    next_size,
                                    next_free,
                                    next_pad1,
                                    next_pad2,
                                    next_next,
                                    new_block_addr,
                                )
                                self._write_raw(next_addr, updated_next)

                        block_size = total_size
                        next_addr = new_block_addr

                    block_data = struct.pack(
                        "<IBIIII", block_size, 0, 0, 0, next_addr, prev_addr
                    )
                    self._write_raw(current_addr, block_data)

                    self._total_used += aligned_size
                    self._total_blocks += 1

                    return current_addr + header_size

                current_addr = next_addr

            except Exception as e:
                print(f"Struct unpack error: {e}")
                break

        return 0

    @micropython.native
    def memcpy(self, dest_addr, src_data, length=None):
        """Copy memory from one location to another."""
        if length is None:
            length = len(src_data)

        chunk_size = 8192  # 8KB chunks
        offset = 0

        while offset < length:
            remaining = length - offset
            current_chunk_size = min(chunk_size, remaining)
            chunk = src_data[offset : offset + current_chunk_size]
            self._write_raw(dest_addr + offset, chunk)
            offset += current_chunk_size

    @micropython.native
    def memset(self, addr, value, length):
        """Set memory region to a specific value"""
        if length <= 0:
            return

        if length <= 64:
            data = bytes([value & 0xFF] * length)
            self._write_raw(addr, data)
            return

        chunk_size = 64
        chunk_data = bytes([value & 0xFF] * chunk_size)

        offset = 0
        while offset < length:
            current_chunk_size = min(chunk_size, length - offset)
            if current_chunk_size == chunk_size:
                self._write_raw(addr + offset, chunk_data)
            else:
                self._write_raw(addr + offset, chunk_data[:current_chunk_size])
            offset += current_chunk_size

    @micropython.native
    def read(self, addr, length):
        """Read data bytes from PSRAM."""
        return self._read_raw(addr, length)

    @micropython.native
    def read8(self, addr):
        """Read 8-bit value from PSRAM."""
        data = self._read_raw(addr, 1)
        return data[0] if data else 0

    @micropython.native
    def read16(self, addr):
        """Read 16-bit value from PSRAM (little-endian)."""
        data = self._read_raw(addr, 2)
        return struct.unpack("<H", data)[0] if len(data) == 2 else 0

    @micropython.native
    def read32(self, addr):
        """Read 32-bit value from PSRAM (little-endian)."""
        data = self._read_raw(addr, 4)
        return struct.unpack("<I", data)[0] if len(data) == 4 else 0

    @micropython.native
    def read_uint8_array(self, addr, count):
        """Read array of uint8 values from PSRAM."""
        data = self._read_raw(addr, count)
        return list(data) if data else []

    @micropython.native
    def read_uint16_array(self, addr, count):
        """Read array of uint16 values from PSRAM."""
        data = self._read_raw(addr, count * 2)
        if len(data) == count * 2:
            return [
                struct.unpack("<H", data[i : i + 2])[0] for i in range(0, len(data), 2)
            ]
        return []

    @micropython.native
    def read_uint32_array(self, addr, count):
        """Read array of uint32 values from PSRAM."""
        data = self._read_raw(addr, count * 4)
        if len(data) == count * 4:
            return [
                struct.unpack("<I", data[i : i + 4])[0] for i in range(0, len(data), 4)
            ]
        return []

    @micropython.native
    def realloc(self, addr, new_size):
        """Reallocate PSRAM memory."""
        if new_size == 0:
            if addr != 0:
                self.free(addr)
            return 0

        if addr == 0:
            return self.malloc(new_size)

        header_size = 21
        block_addr = addr - header_size
        block_data = self._read_raw(block_addr, header_size)

        if len(block_data) < header_size:
            return 0

        try:
            block_size, _, _, _, _, _ = struct.unpack("<IBIIII", block_data)
            current_data_size = block_size - header_size
            aligned_new_size = (new_size + 3) & ~3

            if aligned_new_size <= current_data_size:
                return addr

            new_addr = self.malloc(new_size)
            if new_addr == 0:
                return 0

            data = self._read_raw(addr, current_data_size)
            self._write_raw(new_addr, data)
            self.free(addr)

            return new_addr
        except Exception:
            return 0

    @micropython.native
    def write(self, addr, data):
        """Write data bytes to PSRAM"""
        if isinstance(data, (bytes, bytearray, memoryview)):
            self._write_raw(addr, data)
        else:
            raise TypeError("Data must be bytes, bytearray, or memoryview")

    @micropython.native
    def write8(self, addr, value):
        """Write 8-bit value to PSRAM."""
        self._write_raw(addr, bytes([value & 0xFF]))

    @micropython.native
    def write16(self, addr, value):
        """Write 16-bit value to PSRAM (little-endian)."""
        data = struct.pack("<H", value)
        self._write_raw(addr, data)

    @micropython.native
    def write32(self, addr, value):
        """Write 32-bit value to PSRAM (little-endian)."""
        data = struct.pack("<I", value)
        self._write_raw(addr, data)

    @micropython.native
    def write_buffer(self, addr, buffer):
        """Write a buffer to PSRAM"""
        if not isinstance(buffer, (memoryview, bytes, bytearray)):
            buffer = memoryview(buffer)
        self._write_raw(addr, buffer)

    @micropython.native
    def write_buffer_chunked(self, addr, buffer, chunk_size=65536):
        """Write large buffer in chunks."""
        if not isinstance(buffer, (memoryview, bytes, bytearray)):
            buffer = memoryview(buffer)

        total_size = len(buffer)
        bytes_written = 0

        while bytes_written < total_size:
            remaining = total_size - bytes_written
            current_chunk_size = min(chunk_size, remaining)

            # Use memoryview slice for zero-copy
            chunk = buffer[bytes_written : bytes_written + current_chunk_size]
            self._write_raw(addr + bytes_written, chunk)

            bytes_written += current_chunk_size

    @micropython.native
    def write_bulk(self, addr, data, chunk_size=1024):
        """Write large amounts of data in chunks."""
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("Data must be bytes or bytearray")

        data_len = len(data)
        offset = 0

        while offset < data_len:
            current_chunk_size = min(chunk_size, data_len - offset)
            chunk = data[offset : offset + current_chunk_size]
            self._write_raw(addr + offset, chunk)
            offset += current_chunk_size

    @micropython.native
    def write_uint8_array(self, addr, values):
        """Write array of uint8 values to PSRAM."""
        if isinstance(values, (list, tuple)):
            data = bytearray(values)
        else:
            data = values
        self._write_raw(addr, data)

    @micropython.native
    def write_uint16_array(self, addr, values):
        """Write array of uint16 values to PSRAM."""
        if isinstance(values, (memoryview, bytes, bytearray)):
            # Already in binary format
            self._write_raw(addr, values)
        else:
            # Convert from list/tuple of integers
            data = bytearray()
            for value in values:
                data.extend(struct.pack("<H", value))
            self._write_raw(addr, data)

    @micropython.native
    def write_uint32_array(self, addr, values):
        """Write array of uint32 values to PSRAM."""
        if isinstance(values, (memoryview, bytes, bytearray)):
            # Already in binary format
            self._write_raw(addr, values)
        else:
            # Convert from list/tuple of integers
            data = bytearray()
            for value in values:
                data.extend(struct.pack("<I", value))
            self._write_raw(addr, data)
