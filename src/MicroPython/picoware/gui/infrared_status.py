"""Small animated infrared status screen, using packed Picoware bear sprites."""

from time import ticks_diff
from picoware.gui.ir_bear_frames import LISTENING, SAVED, NO_SIGNAL


class InfraredStatus:
    """Draw at 5 fps while reusing one RGB332 frame buffer."""

    def __init__(self):
        self._pixels = bytearray(48 * 48)
        self._frames = LISTENING
        self._started = 0
        self._loop = True
        self._last_draw = None

    def begin(self, state, now):
        self._frames = {"listening": LISTENING, "saved": SAVED,
                        "no_signal": NO_SIGNAL}[state]
        self._started = now
        self._loop = state == "listening"
        self._last_draw = None

    def draw(self, view_manager, now, title, lines, footer):
        draw = view_manager.draw
        index = max(0, ticks_diff(now, self._started)) // 200
        if self._loop:
            index %= len(self._frames)
        else:
            index = min(index, len(self._frames) - 1)
        foreground = view_manager.foreground_color
        background = view_manager.background_color
        signature = (index, title, lines, footer, foreground, background)
        if signature == self._last_draw:
            return
        self._last_draw = signature

        # Source bits: 0 = bear, 1 = background. Match the active UI colors.
        fg = ((foreground >> 8) & 0xE0) | ((foreground >> 6) & 0x1C) | ((foreground >> 3) & 3)
        bg = ((background >> 8) & 0xE0) | ((background >> 6) & 0x1C) | ((background >> 3) & 3)
        offset = 0
        for packed in self._frames[index]:
            for bit in range(7, -1, -1):
                self._pixels[offset] = bg if packed & (1 << bit) else fg
                offset += 1

        # This 124 x 64 composition fits Flipper and stays centered elsewhere.
        left = max(0, (draw.size.x - 124) // 2)
        top = max(0, (draw.size.y - 64) // 2)
        text_x = left + 52
        text_columns = max(1, (draw.size.x - text_x - 2) // 6)
        draw.erase()
        draw._text(left, top, "PICOWARE", foreground, 0)
        draw._bytearray(left, top + 8, 48, 48, self._pixels)
        draw._text(text_x, top + 12, title[:text_columns], foreground, 0)
        for line_index, line in enumerate(lines[:3]):
            draw._text(text_x, top + 25 + line_index * 10,
                       line[:text_columns], foreground, 0)
        draw._text(left, top + 56, footer[:20], foreground, 0)
        draw.swap()
