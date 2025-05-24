from sys import byteorder as sys_byteorder
from gc import collect as free
from displayio import release_displays
from framebufferio import FramebufferDisplay
from adafruit_framebuf import (
    FrameBuffer,
    RGB565,
)  # https://circuitpython.org/libraries - add to the /lib folder

from .vector import Vector

SEEK_CUR = 1


class Image:
    """
    Represents an image. On CircuitPython this uses adafruit_framebuf.FrameBuffer
    for pixel manipulation, and displayio + framebufferio to put it on-screen.
    """

    def __init__(self):
        self.size = Vector(0, 0)
        self.buffer = None
        self._raw = None  # bytearray for framebuf

    def from_path(self, path: str) -> bool:
        """Load a 16‑bit BMP from disk into a FrameBuffer."""
        try:
            self._load_bmp(path)
            self._make_framebuffer()
            return True
        except Exception as e:
            print(e)
            return False

    def from_byte_array(self, data: bytearray, size: Vector) -> bool:
        """
        Create an image from a raw RGB565 byte array.

        data: bytes or bytearray length == width*height*2
        """
        expected = size.x * size.y * 2
        if len(data) != expected:
            raise ValueError(
                f"Data length {len(data)} != expected {expected} for {size.x}×{size.y}"
            )

        self.size = Vector(size.x, size.y)

        # ensure little‑endian
        buf = bytearray(data)
        if sys_byteorder != "little":
            for i in range(0, len(buf), 2):
                buf[i], buf[i + 1] = buf[i + 1], buf[i]
            free()

        self._raw = buf
        self.buffer = FrameBuffer(
            buf, size.x, size.y, RGB565
        )  # :contentReference[oaicite:0]{index=0}
        return True

    def _load_bmp(self, path):
        """Read BMP header + pixel data into self._raw as little‑endian RGB565 bytes."""
        with open(path, "rb") as f:
            if f.read(2) != b"BM":
                raise ValueError("Not a BMP file")
            _ = f.read(8)  # file size + reserved
            data_offset = int.from_bytes(f.read(4), "little")
            header_size = int.from_bytes(f.read(4), "little")
            w = int.from_bytes(f.read(4), "little")
            h = int.from_bytes(f.read(4), "little")
            self.size = Vector(w, h)
            # skip remaining header
            f.seek(data_offset, SEEK_CUR)

            # BMP rows are padded to 4-byte boundaries. We'll just read 2 bytes per pixel.
            raw = bytearray(w * h * 2)
            idx = 0
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

    def _make_framebuffer(self):
        """Wrap self._raw in a FrameBuffer for drawing operations."""
        w, h = self.size.x, self.size.y
        self.buffer = FrameBuffer(
            self._raw, w, h, RGB565
        )  # :contentReference[oaicite:1]{index=1}

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
        self.buffer = FrameBuffer(
            raw, w, h, RGB565
        )  # :contentReference[oaicite:2]{index=2}

    def show_on(self, fb_native):
        """
        Copy this FrameBuffer into a native framebuffer (e.g. a picodvi.Framebuffer),
        then attach it to the display.
        """
        # fb_native must implement .pixel(x,y,color) or expose a buffer protocol
        for y in range(self.size.y):
            for x in range(self.size.x):
                fb_native.pixel(x, y, self.buffer.pixel(x, y))

        release_displays()  # :contentReference[oaicite:3]{index=3}
        disp = FramebufferDisplay(fb_native, auto_refresh=True)
        return disp
