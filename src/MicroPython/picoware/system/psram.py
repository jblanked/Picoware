"""PSRAM - External PSRAM memory management."""

import picoware_psram


class PSRAMObject(picoware_psram.Object):
    """Python wrapper around the underlying C PSRAM object.

    Behaves like the original Python type (str, int, float, bytes, bytearray,
    dict, bool, function, list, or tuple) but stores its data in PSRAM memory.
    Memory management is automatic: when a PSRAMObject is garbage collected,
    its associated PSRAM memory is freed.

    Methods:
        - __str__(): Return string representation of the PSRAM object.
        - __del__(): Automatically free PSRAM memory when the object is garbage collected.
        - value(): Get the value stored in PSRAM, automatically converting it back to the original Python type.
        - length(): Get the length of the data stored in PSRAM (for strings, bytes, lists, etc.).
        - addr(): Get the PSRAM memory address where the data is stored .
    """


class PSRAM(picoware_psram.PSRAM):
    """MicroPython PSRAM interface with automatic GC-managed objects.

    Provides a high-level and low-level interface to PSRAM memory for
    allocating, managing, and utilizing PSRAM in MicroPython applications.

    Methods:
        - is_ready: Check if PSRAM is initialized and ready for use.
        - size: Get total PSRAM memory size in bytes.
        - test: Run a PSRAM test to verify functionality.
        - write: Write data to PSRAM memory at a specific address.
        - write8: Write an 8-bit value to a specific PSRAM address.
        - write16: Write a 16-bit value to a specific PSRAM address.
        - write32: Write a 32-bit value to a specific PSRAM address.
        - write32_bulk: Write multiple 32-bit values to PSRAM starting at a specific address.
        - read: Read data from PSRAM memory at a specific address.
        - read8: Read an 8-bit value from a specific PSRAM address.
        - read16: Read a 16-bit value from a specific PSRAM address.
        - read32: Read a 32-bit value from a specific PSRAM address.
        - read32_bulk: Read multiple 32-bit values from PSRAM starting at a specific address.
        - fill: Fill a region of PSRAM memory with a specific byte value.
        - copy: Copy data from one PSRAM location to another.
        - alloc_object: Allocate PSRAM memory for a Python object and return a PSRAMObject
        - get_next_free: Get the next free PSRAM memory address.
        - mem_free: Get the amount of free PSRAM memory in bytes.
        - collect: Compact PSRAM free list, Returns the total moved.
        - malloc: Allocate PSRAM memory for the given data and return a PSRAMObject.
        - memcpy: Copy memory from one PSRAM location to another.
        - memset: Set memory region to a specific byte value using DMA-optimized fill.
    """

    @property
    def free_heap_size(self) -> int:
        """Get free PSRAM memory in bytes."""
        return self.mem_free()

    @property
    def next_free_addr(self) -> int:
        """Get the next free PSRAM memory address."""
        return self.get_next_free()

    @property
    def total_heap_size(self) -> int:
        """Get total PSRAM memory size in bytes."""
        return picoware_psram.SIZE

    @property
    def used_heap_size(self) -> int:
        """Get used PSRAM memory in bytes."""
        return picoware_psram.SIZE - self.mem_free()

    def from_file(self, storage, addr, file_path, chunk_size: int = 2048) -> int:
        """Load data from a file into PSRAM memory.

        Args:
            storage (object): Storage instance used to read the file.
            addr (int): PSRAM address to write the data to.
            file_path (str): Path of the file to load.
            chunk_size (int): Number of bytes to read per chunk. Defaults to 2048.

        Returns:
            int: The size of the data loaded, or -1 if the file could not be opened.
        """
        file = storage.file_open(file_path)
        if not file:
            return -1
        _addr = addr
        buffer = bytearray(chunk_size)
        while True:
            bytes_read = storage.file_readinto(file, buffer)
            if bytes_read <= 0:
                break
            self.write(_addr, buffer[:bytes_read])
            _addr += bytes_read
            if bytes_read < chunk_size:
                break
        storage.file_close(file)
        return _addr - addr

    def malloc(self, data) -> PSRAMObject:
        """Allocate PSRAM memory for the given data.

        Args:
            data (object): The Python object to store in PSRAM.

        Returns:
            PSRAMObject: A PSRAMObject wrapping the data.
        """
        return self.alloc_object(data)

    def memcpy(self, dest_addr, src_addr, length):
        """Copy memory from one PSRAM location to another.

        Args:
            dest_addr (int): Destination PSRAM address.
            src_addr (int): Source PSRAM address.
            length (int): Number of bytes to copy.
        """
        self.copy(src_addr, dest_addr, length)

    def memset(self, addr, value, length):
        """Set a memory region to a specific byte value.

        Args:
            addr (int): PSRAM address of the region.
            value (int): Byte value to fill with.
            length (int): Number of bytes to fill.
        """
        if length <= 0:
            return
        self.fill(addr, value & 0xFF, length)
