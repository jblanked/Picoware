"""Play optional SD startup assets using the display's available space."""

from gc import collect
from io import BytesIO
import os
from struct import unpack, unpack_from
from time import ticks_diff, ticks_ms

from picoware.system.vector import Vector


class LetteringOnly:
    """Keep the original letter fade, with a measured font and no ring."""

    def __getattr__(self, name):
        return getattr(self.display, name)

    def __init__(self, display, font, top):
        self.display = display
        self.font = font
        self.top = top

    def _circle(self, *args):
        pass

    def _text(self, x, y, text, color):
        # Keep even the initial letter animation inside its reserved line.
        self.display._text(x, self.top, text, color, self.font)


class StartupBear:
    """Reuse one frame buffer and restore the original on any read failure."""

    def __init__(self, display, path, original, layout=None):
        self._buffer = None
        self._codec = None
        self._display = display
        self._elapsed = 0
        self._frame = -1
        self._handle = None
        self._last_tick = None
        self._logo = original
        self._offsets = None
        self._packed = None
        self._position = None
        self._saved = None
        self._size = None
        try:
            if layout is None:
                layout = animation_layout(display)
            name, width, height, x, y, text_y, font, mono = layout
            self._handle = open(path, "rb")
            header = self._handle.read(20)
            if len(header) != 20:
                raise ValueError("Truncated startup header")
            magic, old_x, old_y, w, h, interval, reveal, loop, colors = unpack("<4s8H", header)
            if (magic, w, h, interval, reveal, loop, colors) != (
                b"BWM1" if mono else b"BWA1", width, height, 50, 52, 56, 1
            ):
                raise ValueError("Unsupported startup animation")
            self._offsets = self._handle.read(109 * 4)
            if len(self._offsets) != 109 * 4:
                raise ValueError("Truncated startup index")
            if self._offset(0) != 456 or self._offset(108) != os.stat(path)[6]:
                raise ValueError("Invalid startup index")
            for index in range(108):
                length = self._offset(index + 1) - self._offset(index)
                if not 0 < length <= width * height + 128:
                    raise ValueError("Invalid startup frame offset")
                if mono and length != ((width + 7) // 8) * height:
                    raise ValueError("Invalid monochrome frame size")
            self._buffer = bytearray(width * height)
            if mono:
                # No deflate dependency or temporary RGB expansion on Flipper.
                self._packed = bytearray(((width + 7) // 8) * height)
            else:
                self._codec = __import__("deflate")
            self._position = Vector(x, y)
            self._size = Vector(width, height)
            self._decode(0)
            proxy = LetteringOnly(display, font, text_y)
            self._saved = [(letter["target_x"], letter["target_y"]) for letter in original.letter_states]
            text_x = (display.size.x - display.len("Picoware", font)) // 2
            for letter in original.letter_states:
                letter["target_x"] = text_x
                letter["target_y"] = text_y
                letter["current_y"] = text_y
                text_x += display.len(letter["char"], font)
            original.display = proxy
        except Exception:
            self.close()
            raise

    def _decode(self, frame):
        start = self._offset(frame)
        length = self._offset(frame + 1) - start
        self._handle.seek(start)
        if self._packed is not None:
            if self._handle.readinto(self._packed) != len(self._packed):
                raise ValueError("Truncated monochrome frame")
            width, height = self._size.x, self._size.y
            stride = (width + 7) // 8
            for y in range(height):
                for x in range(width):
                    self._buffer[y * width + x] = 255 if self._packed[y * stride + x // 8] & (128 >> (x % 8)) else 0
        else:
            packed = self._handle.read(length)
            if len(packed) != length:
                raise ValueError("Truncated startup frame")
            with BytesIO(packed) as stream:
                with self._codec.DeflateIO(stream, self._codec.ZLIB, 12) as decoder:
                    if decoder.readinto(self._buffer) != len(self._buffer) or decoder.read(1):
                        raise ValueError("Invalid startup frame size")
        self._frame = frame

    def _offset(self, index):
        return unpack_from("<I", self._offsets, index * 4)[0]

    def close(self):
        """Release SD resources and restore the original logo placement."""
        handle = self._handle
        self._handle = None
        self._buffer = self._codec = self._offsets = self._packed = None
        self._position = self._size = None
        self._logo.display = self._display
        if self._saved is not None:
            for letter, position in zip(self._logo.letter_states, self._saved):
                letter["target_x"], letter["target_y"] = position
                letter["current_y"] = position[1]
            self._saved = None
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


def animation_layout(display, desktop=None):
    """Fit the complete artwork and wordmark below the actual desktop header."""
    from picoware.system.boards import BOARD_FLIPPER_ZERO, BOARD_ID

    width, height = display.size.x, display.size.y
    mono = BOARD_ID == BOARD_FLIPPER_ZERO
    margin = max(2, min(width, height) // 40)
    gap = max(2, min(width, height) // 60)
    top = (display.font_size.y + 1 if mono else max(18, display.font_size.y + 5)) + gap
    if desktop is not None:
        top = max(desktop.time_pos.y, desktop.battery_pos.y) + display.font_size.y
        if desktop.draw_name:
            top = max(top, desktop.name_pos.y + display.font_size.y)
        if desktop.draw_icons:
            top = max(top, desktop.wifi_pos.y + desktop.wifi_size.y,
                      desktop.bluetooth_pos.y + desktop.bluetooth_size.y)
        top += gap
    font = max(display.font, 4 if min(width, height) >= 600 else
               2 if min(width, height) >= 400 else 1 if min(width, height) >= 200 else 0)
    while font > 0 and (display.len("Picoware", font) > width - 2 * margin or
                        display.get_font(font).height > (height - top) // 3):
        font -= 1
    text_height = display.get_font(font).height
    # Keep the already approved PicoCalc composition and existing SD file.
    if width == 320 and height == 320 and top <= 64 and display.font == 0:
        return ("startup_bear.bin", 208, 184, 56, 64, 230, 0, False)
    limit = min(width - 2 * margin, height - top - margin - gap - text_height,
                min(width, height) * 7 // 10)
    sizes = (40,) if mono else (80, 112, 160, 224)
    size = 0
    for candidate in sizes:
        if candidate <= limit:
            size = candidate
    if not size or display.len("Picoware", font) > width - 2 * margin:
        raise ValueError("No startup layout fits this display")
    y = top + (height - top - margin - size - gap - text_height) // 2
    name = "startup_bear_mono_40.bin" if mono else "startup_bear_%d.bin" % size
    return (name, size, size, (width - size) // 2, y, y + size + gap, font, mono)


def create_animation(display, storage, original, desktop=None):
    """Use the matching SD asset when available; unavailable storage is normal."""
    from picoware.system.boards import BOARD_HAS_SD

    try:
        if BOARD_HAS_SD and storage.active:
            layout = animation_layout(display, desktop)
            if storage.mount_vfs():
                return StartupBear(
                    display, storage.vfs_prefix + "/picoware/assets/" + layout[0], original, layout
                )
    except Exception:
        collect()
    return original
