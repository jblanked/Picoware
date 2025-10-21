from picoware.system.vector import Vector


class Image:
    """
    Represents an image with RGB565 pixel data for MicroPython.
    The raw pixel data is stored in self._raw and can be used by the Draw class.
    """

    def __init__(self):
        self.size = Vector(0, 0)
        self._raw = None
        self.is_8bit = True

    def __del__(self) -> None:
        if self._raw:
            del self._raw
            self._raw = None
        if self.size:
            del self.size
            self.size = None

    def from_path(self, path: str) -> bool:
        """Load a 16‑bit BMP from disk into raw RGB565 data."""
        try:
            self._load_bmp(path)
            return True
        except (OSError, ValueError) as e:
            print(f"Error loading image: {e}")
            return False

    def from_byte_array(self, data, size, is_8bit: bool = True) -> bool:
        """
        Create an image from raw byte array

        data: bytes, bytearray, or memoryview containing pixel data
        size: Vector(width, height)
        is_8bit: if True, data is 8-bit
        """
        from sys import byteorder

        if not isinstance(data, memoryview):
            data = memoryview(data)

        bytes_per_pixel = 1 if is_8bit else 2
        expected = size.x * size.y * bytes_per_pixel
        if len(data) != expected:
            raise ValueError(f"Data length {len(data)} != expected {expected}")

        self.size = size
        self.is_8bit = is_8bit

        if is_8bit or byteorder == "little":
            self._raw = data
        else:
            # big-endian 16-bit
            buf = bytearray(len(data))
            i = 0
            while i < len(data):
                buf[i] = data[i + 1]
                buf[i + 1] = data[i]
                i += 2
            self._raw = buf

        return True

    def _load_bmp(self, path):
        """Read BMP header + pixel data into self._raw as little‑endian RGB565 bytes."""
        with open(path, "rb") as f:
            if f.read(2) != b"BM":
                raise ValueError("Not a BMP file")
            _ = f.read(8)  # file size + reserved
            data_offset = int.from_bytes(f.read(4), "little")
            _ = int.from_bytes(f.read(4), "little")  # header_size
            w = int.from_bytes(f.read(4), "little")
            h = int.from_bytes(f.read(4), "little")
            self.size = Vector(w, h)
            # skip remaining header
            f.seek(data_offset, 1)

            # BMP rows are padded to 4-byte boundaries. We'll just read 2 bytes per pixel.
            raw = bytearray(w * h * 2)
            row_bytes = w * 2
            padding = (4 - (row_bytes % 4)) % 4
            for row in range(h):
                # BMP is bottom‑up
                row_data = f.read(row_bytes)
                f.read(padding)
                # write into raw so that (0,0) is top‑left
                dest = (h - 1 - row) * row_bytes
                raw[dest : dest + row_bytes] = row_data
            self._raw = raw

    def from_string(self, image_str: str):
        """
        Create a tiny monochrome‑style RGB565 image from ASCII art:
        \".\" or \"f\" → 0x0000, \"1\" → 0xFFFF, etc.
        """
        rows = image_str.strip("\n").split("\n")
        h = len(rows)
        w = len(rows[0])
        self.size = Vector(w, h)
        raw = bytearray(w * h * 2)

        def encode(c):
            return {
                ".": 0x0000,
                "f": 0x0000,
                "1": 0xFFFF,
                "2": 0xF904,
                "3": 0xFC98,
                "4": 0xFC06,
                "5": 0xFFA1,
                "6": 0x24F4,
                "7": 0x7ECA,
                "8": 0x0215,
                "9": 0x879F,
                "a": 0xC05E,
                "b": 0xFC9F,
                "c": 0x50CA,
                "d": 0xACF0,
                "e": 0x7B07,
            }.get(c, 0x0020)

        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                v = encode(ch)
                idx = 2 * (y * w + x)
                raw[idx] = v & 0xFF
                raw[idx + 1] = v >> 8

        self._raw = raw

    def get_pixel(self, x: int, y: int) -> int:
        """Get RGB565 pixel value at coordinates (x, y)."""
        if not (0 <= x < self.size.x and 0 <= y < self.size.y):
            return 0x0000

        idx = 2 * (y * self.size.x + x)
        return self._raw[idx] | (self._raw[idx + 1] << 8)
