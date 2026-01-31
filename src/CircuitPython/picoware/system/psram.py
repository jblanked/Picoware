import picoware_psram as _psram


class PSRAM:
    """MicroPython PSRAM interface using C module with automatic GC-managed objects."""

    def __init__(self):
        """Initialize PSRAM using C module."""
        if not _psram.is_ready():
            _psram.init()

    def __del__(self):
        """Deinitialize PSRAM on object deletion."""
        if _psram.is_ready():
            _psram.collect()

    @property
    def free_heap_size(self):
        """Get free PSRAM memory in bytes."""
        return _psram.mem_free()

    @property
    def total_heap_size(self):
        """Get total PSRAM memory size in bytes."""
        return _psram.SIZE

    @property
    def used_heap_size(self):
        """Get used PSRAM memory in bytes."""
        return _psram.SIZE - _psram.mem_free()

    def collect(self) -> int:
        """Compact PSRAM free list, Returns the total moved"""
        return _psram.collect()

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
        return _psram.malloc(data)

    def mem_free(self) -> int:
        """Get free PSRAM memory in bytes."""
        return _psram.mem_free()
