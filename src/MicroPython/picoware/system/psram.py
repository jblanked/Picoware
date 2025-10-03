import struct
import picoware_psram as _psram


class PSRAM:
    """MicroPython PSRAM interface using a C module for hardware access."""

    # Constants
    PSRAM_SIZE = 8 * 1024 * 1024  # 8MB total
    HEAP_START = 0x100000  # Start heap at 1MB offset
    HEAP_SIZE = 7 * 1024 * 1024  # 7MB for heap

    def __init__(self):
        """Initialize PSRAM using C module."""
        # Heap management variables
        self._hardware_initialized = False
        self._heap_head = 0
        self._total_used = 0
        self._total_blocks = 0

        # Initialize hardware via C module
        self._init_hardware()

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
        return _psram.is_ready()

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

    def _init_hardware(self):
        """Initialize PSRAM hardware and heap using C module."""
        if self._hardware_initialized:
            return True

        # Initialize hardware via C module
        _psram.init()

        # Initialize heap with a single free block
        self._heap_head = self.HEAP_START
        initial_block = struct.pack("<IBIIII", self.HEAP_SIZE, 1, 0, 0, 0, 0)
        _psram.write(self._heap_head, initial_block)

        self._total_used = 0
        self._total_blocks = 0
        self._hardware_initialized = True

        return True

    def free(self, addr):
        """Free previously allocated PSRAM memory."""
        if not self._hardware_initialized or addr == 0:
            return

        header_size = 21
        block_addr = addr - header_size
        block_data = _psram.read(block_addr, header_size)

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
            _psram.write(block_addr, block_data)

        except Exception as e:
            print(f"Free error: {e}")
            return

    def malloc(self, size):
        """Allocate memory from PSRAM heap."""
        if not self._hardware_initialized or size == 0:
            return 0

        aligned_size = (size + 3) & ~3
        header_size = 21  # size(4) + is_free(1) + pad1(4) + pad2(4) + next(4) + prev(4) = 21 bytes
        total_size = aligned_size + header_size

        current_addr = self._heap_head
        while current_addr != 0:
            block_data = _psram.read(current_addr, header_size)
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
                        _psram.write(new_block_addr, new_block_data)

                        if next_addr != 0:
                            next_block_data = _psram.read(next_addr, header_size)
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
                                _psram.write(next_addr, updated_next)

                        block_size = total_size
                        next_addr = new_block_addr

                    block_data = struct.pack(
                        "<IBIIII", block_size, 0, 0, 0, next_addr, prev_addr
                    )
                    _psram.write(current_addr, block_data)

                    self._total_used += aligned_size
                    self._total_blocks += 1

                    return current_addr + header_size

                current_addr = next_addr

            except Exception as e:
                print(f"Struct unpack error: {e}")
                break

        return 0

    def memcpy(self, dest_addr, src_addr, length):
        """Copy memory from one PSRAM location to another."""
        _psram.copy(src_addr, dest_addr, length)

    def memset(self, addr, value, length):
        """Set memory region to a specific value (limited by speed)."""
        # Use C module's single-byte writes (slow but works)
        if length <= 0:
            return

        # For small lengths, write directly
        if length <= 64:
            data = bytes([value & 0xFF] * length)
            _psram.write(addr, data)
            return

        # For larger lengths, use chunks
        chunk_size = 256
        chunk_data = bytes([value & 0xFF] * chunk_size)

        offset = 0
        while offset < length:
            current_chunk_size = min(chunk_size, length - offset)
            if current_chunk_size == chunk_size:
                _psram.write(addr + offset, chunk_data)
            else:
                _psram.write(addr + offset, chunk_data[:current_chunk_size])
            offset += current_chunk_size

    def read(self, addr, length):
        """Read data bytes from PSRAM."""
        return _psram.read(addr, length)

    def read8(self, addr):
        """Read 8-bit value from PSRAM."""
        return _psram.read8(addr)

    def read16(self, addr):
        """Read 16-bit value from PSRAM (little-endian)."""
        return _psram.read16(addr)

    def read32(self, addr):
        """Read 32-bit value from PSRAM (little-endian)."""
        return _psram.read32(addr)

    def read_uint8_array(self, addr, count):
        """Read array of uint8 values from PSRAM."""
        data = _psram.read(addr, count)
        return list(data) if data else []

    def read_uint16_array(self, addr, count):
        """Read array of uint16 values from PSRAM."""
        data = _psram.read(addr, count * 2)
        if len(data) == count * 2:
            return [
                struct.unpack("<H", data[i : i + 2])[0] for i in range(0, len(data), 2)
            ]
        return []

    def read_uint32_array(self, addr, count):
        """Read array of uint32 values from PSRAM."""
        data = _psram.read(addr, count * 4)
        if len(data) == count * 4:
            return [
                struct.unpack("<I", data[i : i + 4])[0] for i in range(0, len(data), 4)
            ]
        return []

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
        block_data = _psram.read(block_addr, header_size)

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

            data = _psram.read(addr, current_data_size)
            _psram.write(new_addr, data)
            self.free(addr)

            return new_addr
        except Exception:
            return 0

    def write(self, addr, data):
        """Write data bytes to PSRAM."""
        if isinstance(data, (bytes, bytearray, memoryview)):
            _psram.write(addr, data)
        elif isinstance(data, str):
            # Convert string to bytes
            _psram.write(addr, data.encode("utf-8"))
        else:
            raise TypeError("Data must be bytes, bytearray, memoryview, or str")

    def write8(self, addr, value):
        """Write 8-bit value to PSRAM."""
        _psram.write8(addr, value)

    def write16(self, addr, value):
        """Write 16-bit value to PSRAM (little-endian)."""
        _psram.write16(addr, value)

    def write32(self, addr, value):
        """Write 32-bit value to PSRAM (little-endian)."""
        _psram.write32(addr, value)

    def write_buffer(self, addr, buffer):
        """Write a buffer to PSRAM."""
        if not isinstance(buffer, (memoryview, bytes, bytearray)):
            buffer = memoryview(buffer)
        _psram.write(addr, buffer)

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
            _psram.write(addr + bytes_written, chunk)

            bytes_written += current_chunk_size

    def write_bulk(self, addr, data, chunk_size=1024):
        """Write large amounts of data in chunks."""
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("Data must be bytes or bytearray")

        data_len = len(data)
        offset = 0

        while offset < data_len:
            current_chunk_size = min(chunk_size, data_len - offset)
            chunk = data[offset : offset + current_chunk_size]
            _psram.write(addr + offset, chunk)
            offset += current_chunk_size

    def write_uint8_array(self, addr, values):
        """Write array of uint8 values to PSRAM."""
        if isinstance(values, (list, tuple)):
            data = bytearray(values)
        else:
            data = values
        _psram.write(addr, data)

    def write_uint16_array(self, addr, values):
        """Write array of uint16 values to PSRAM."""
        if isinstance(values, (memoryview, bytes, bytearray)):
            # Already in binary format
            _psram.write(addr, values)
        else:
            # Convert from list/tuple of integers
            data = bytearray()
            for value in values:
                data.extend(struct.pack("<H", value))
            _psram.write(addr, data)

    def write_uint32_array(self, addr, values):
        """Write array of uint32 values to PSRAM."""
        if isinstance(values, (memoryview, bytes, bytearray)):
            # Already in binary format
            _psram.write(addr, values)
        else:
            # Convert from list/tuple of integers
            data = bytearray()
            for value in values:
                data.extend(struct.pack("<I", value))
            _psram.write(addr, data)
