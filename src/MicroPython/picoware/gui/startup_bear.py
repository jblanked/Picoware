"""Stream the optional PicoCalc desktop bear from the SD card."""

import deflate
from gc import collect
from io import BytesIO
import os
from struct import unpack, unpack_from
from time import ticks_diff, ticks_ms

from picoware.system.vector import Vector


class LetteringOnly:
    """Keep the original animated lettering without its ring."""

    def __getattr__(self, name):
        return getattr(self.display, name)

    def __init__(self, display):
        self.display = display

    def _circle(self, *args):
        pass


class StartupBear:
    """Reuse one RGB332 frame buffer; revert to the original on read failure."""

    def __init__(self, display, path, original):
        self._buffer = None
        self._display = display
        self._elapsed = 0
        self._frame = -1
        self._handle = None
        self._last_tick = None
        self._logo = original
        self._offsets = None
        self._position = None
        self._shift = 0
        self._size = None
        try:
            self._handle = open(path, "rb")
            header = self._handle.read(20)
            if len(header) != 20 or unpack("<4s8H", header) != (
                b"BWA1", 56, 64, 208, 184, 50, 52, 56, 1
            ):
                raise ValueError("Unsupported startup animation")
            self._offsets = self._handle.read(109 * 4)
            if len(self._offsets) != 109 * 4:
                raise ValueError("Truncated startup index")
            if self._offset(0) != 456 or self._offset(108) != os.stat(path)[6]:
                raise ValueError("Invalid startup index")
            for index in range(108):
                if not 0 < self._offset(index + 1) - self._offset(index) <= 40960:
                    raise ValueError("Invalid startup frame offset")
            self._buffer = bytearray(208 * 184)
            self._position = Vector(56, 64)
            self._size = Vector(208, 184)
            self._decode(0)
            proxy = LetteringOnly(display)
            self._shift = 230 - original.center_y
            for letter in original.letter_states:
                letter["current_y"] += self._shift
                letter["target_y"] += self._shift
            original.display = proxy
        except Exception:
            self.close()
            raise

    def _decode(self, frame):
        start = self._offset(frame)
        length = self._offset(frame + 1) - start
        self._handle.seek(start)
        packed = self._handle.read(length)
        if len(packed) != length:
            raise ValueError("Truncated startup frame")
        with BytesIO(packed) as stream:
            with deflate.DeflateIO(stream, deflate.ZLIB, 12) as decoder:
                if decoder.readinto(self._buffer) != len(self._buffer) or decoder.read(1):
                    raise ValueError("Invalid startup frame size")
        self._frame = frame

    def _offset(self, index):
        return unpack_from("<I", self._offsets, index * 4)[0]

    def close(self):
        """Release SD resources and restore the original logo placement."""
        handle = self._handle
        self._handle = None
        self._buffer = self._offsets = self._position = self._size = None
        self._logo.display = self._display
        for letter in self._logo.letter_states:
            letter["current_y"] -= self._shift
            letter["target_y"] -= self._shift
        self._shift = 0
        if handle is not None:
            try:
                handle.close()
            except OSError:
                pass
        collect()

    def draw(self):
        if self._handle is not None:
            try:
                now = ticks_ms()
                if self._last_tick is not None:
                    self._elapsed += max(0, ticks_diff(now, self._last_tick))
                self._last_tick = now
                if self._elapsed >= 2600:
                    self._elapsed = 2600 + (self._elapsed - 2600) % 2800
                frame = self._elapsed // 50
                if frame != self._frame:
                    self._decode(frame)
                    if frame % 16 == 0:
                        collect()
                self._display.image_bytearray(self._position, self._size, self._buffer)
            except Exception:
                # Do not retry SD access every desktop frame after a failure.
                self.close()
        self._logo.draw()


def create_animation(display, storage, original):
    """Use the SD animation when available; missing storage is normal."""
    try:
        if display.size.x == 320 and display.size.y == 320 and storage.active:
            if storage.mount_vfs():
                return StartupBear(
                    display, storage.vfs_prefix + "/picoware/assets/startup_bear.bin", original
                )
    except Exception:
        collect()
    return original
