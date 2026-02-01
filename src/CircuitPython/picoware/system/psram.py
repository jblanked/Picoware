try:
    import picoware_psram as _psram

    PSRAM_AVAILABLE = True
except ImportError:
    PSRAM_AVAILABLE = False


class PSRAM:
    """MicroPython PSRAM interface using C module with automatic GC-managed objects."""

    def __init__(self):
        """Initialize PSRAM using C module."""
        if PSRAM_AVAILABLE:
            if not _psram.is_ready():
                _psram.init()

    def __del__(self):
        """Deinitialize PSRAM on object deletion."""
        if PSRAM_AVAILABLE:
            if _psram.is_ready():
                _psram.collect()

    @property
    def free_heap_size(self) -> int:
        """Get free PSRAM memory in bytes."""
        if PSRAM_AVAILABLE:
            return _psram.mem_free()
        from gc import mem_free

        return mem_free()

    @property
    def is_ready(self) -> bool:
        """Check if PSRAM is ready for use."""
        return _psram.is_ready()

    @property
    def next_free_addr(self) -> int:
        """Get the next free PSRAM memory address."""
        if PSRAM_AVAILABLE:
            return _psram.get_next_free()
        return 0

    @property
    def total_heap_size(self) -> int:
        """Get total PSRAM memory size in bytes."""
        if PSRAM_AVAILABLE:
            return _psram.SIZE
        return 0

    @property
    def used_heap_size(self) -> int:
        """Get used PSRAM memory in bytes."""
        if PSRAM_AVAILABLE:
            return _psram.SIZE - _psram.mem_free()
        from gc import mem_alloc

        return mem_alloc()

    def collect(self) -> int:
        """Compact PSRAM free list, Returns the total moved"""
        if PSRAM_AVAILABLE:
            return _psram.collect()
        return 0

    def deinit(self):
        """Deinitialize PSRAM."""
        if PSRAM_AVAILABLE:
            if _psram.is_ready():
                _psram.deinit()

    def malloc(self, data):
        """Allocate PSRAM-backed Python object (GC-managed).

        Args:
            data: Python object to store in PSRAM (str, int, float, bytes, bytearray, dict, bool, function, list, or tuple instance).

        Returns:
            PSRAM object that behaves like the original type but stores data in PSRAM.
            Memory is automatically freed when object is garbage collected.

        Example:
            text = psram.malloc("hello world")
            print(text)  # "hello world"
            number = psram.malloc(42)
            print(number + 10)  # 52
        """
        if PSRAM_AVAILABLE:
            return _psram.malloc(data)
        return data

    def memcpy(self, dest_addr, src_addr, length):
        """Copy memory from one PSRAM location to another."""
        if PSRAM_AVAILABLE:
            _psram.copy(src_addr, dest_addr, length)

    def memset(self, addr, value, length):
        """Set memory region to a specific byte value using DMA-optimized fill."""
        if length <= 0:
            return
        if PSRAM_AVAILABLE:
            _psram.fill(addr, value & 0xFF, length)

    def mem_free(self) -> int:
        """Get free PSRAM memory in bytes."""
        if PSRAM_AVAILABLE:
            return _psram.mem_free()
        from gc import mem_free

        return mem_free()

    def read(self, addr, length) -> bytes:
        """Read data bytes from PSRAM."""
        if PSRAM_AVAILABLE:
            return _psram.read(addr, length)
        return b""

    def read_into(self, addr, buffer) -> int:
        """Read data directly into an existing buffer (zero-copy)."""
        if PSRAM_AVAILABLE:
            return _psram.read_into(addr, buffer)
        return 0

    def write(self, addr, data) -> bool:
        """Write data bytes to PSRAM."""
        if PSRAM_AVAILABLE:
            try:
                if isinstance(data, (bytes, bytearray, memoryview)):
                    _psram.write(addr, data)
                elif isinstance(data, str):
                    # Convert string to bytes
                    _psram.write(addr, data.encode("utf-8"))
                else:
                    print("Data must be bytes, bytearray, memoryview, or str")
                    return False

                return True
            except Exception as e:
                print("PSRAM write error:", e)
                return False
        return False
