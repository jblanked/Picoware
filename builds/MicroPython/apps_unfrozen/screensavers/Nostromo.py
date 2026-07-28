"""Nostromo-inspired terminal screensaver for Picoware.

The display cycles through a registration card, system bootstrap, MU/TH/UR
address matrix, inquiry terminal, and orbital approach plot.  All visible text
uses the original 7x9 bitmap alphabet below; Picoware's built-in font is never
used.
"""

from micropython import const
from utime import ticks_diff, ticks_ms

from picoware.system.buttons import BUTTON_NONE
from picoware.system.boards import (
    BOARD_CROWPANEL_10_1,
    BOARD_FLIPPER_ZERO,
    BOARD_ID,
)


_FONT_W = const(7)
_FONT_H = const(9)
_FONT_ADVANCE = const(8)
_FONT_ROWS = const(9)
_FONT_PUNCT = ".,:/+-=[]<>?%_*#!|^~$@"
_FONT_PUNCT_BASE = const(37)

# Original slab-serif terminal alphabet.  Rows are MSB-first; the high seven
# bits form each 7-pixel row.  The last eight characters are custom instrument
# symbols: beacon, data stack, alert, bus, route arrow, waveform, ship, target.
_FONT_DATA = (
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00"  # SPACE
    b"\x7c\xc6\xca\xd2\xe2\xc2\xc2\x7c\x00"  # 0
    b"\x30\x70\x30\x30\x30\x30\x30\xfc\x00"  # 1
    b"\x7c\xc6\x06\x0c\x18\x30\x60\xfe\x00"  # 2
    b"\xfc\x06\x06\x7c\x06\x06\xc6\x7c\x00"  # 3
    b"\x0c\x1c\x2c\x4c\x8c\xfe\x0c\x0c\x00"  # 4
    b"\xfe\xc0\xc0\xfc\x06\x06\xc6\x7c\x00"  # 5
    b"\x3c\x60\xc0\xfc\xc6\xc6\xc6\x7c\x00"  # 6
    b"\xfe\x06\x0c\x18\x30\x30\x30\x30\x00"  # 7
    b"\x7c\xc6\xc6\x7c\xc6\xc6\xc6\x7c\x00"  # 8
    b"\x7c\xc6\xc6\xc6\x7e\x06\x0c\x78\x00"  # 9
    b"\x38\x6c\xc6\xc6\xfe\xc6\xc6\xc6\x00"  # A
    b"\xf8\xcc\xc6\xfc\xc6\xc6\xcc\xf8\x00"  # B
    b"\x7c\xc6\xc0\xc0\xc0\xc0\xc6\x7c\x00"  # C
    b"\xf8\xcc\xc6\xc6\xc6\xc6\xcc\xf8\x00"  # D
    b"\xfe\xc0\xc0\xfc\xc0\xc0\xc0\xfe\x00"  # E
    b"\xfe\xc0\xc0\xfc\xc0\xc0\xc0\xc0\x00"  # F
    b"\x7c\xc6\xc0\xc0\xde\xc6\xc6\x7c\x00"  # G
    b"\xc6\x82\x82\xfe\x82\x82\x82\xc6\x00"  # H
    b"\xfe\x38\x38\x38\x38\x38\x38\xfe\x00"  # I
    b"\x3e\x0c\x0c\x0c\x0c\xcc\xcc\x78\x00"  # J
    b"\xc6\x8c\x98\xf0\x98\x8c\x86\xc6\x00"  # K
    b"\xc0\x80\x80\x80\x80\x80\xc0\xfe\x00"  # L
    b"\xc6\xee\xaa\xaa\x82\x82\x82\xc6\x00"  # M
    b"\xc6\xe2\xb2\x9a\x8e\x86\x82\xc6\x00"  # N
    b"\x7c\xc6\xc6\xc6\xc6\xc6\xc6\x7c\x00"  # O
    b"\xfc\xc6\xc6\xfc\xc0\xc0\xc0\xc0\x00"  # P
    b"\x7c\xc6\xc6\xc6\xc6\xd6\xcc\x7a\x00"  # Q
    b"\xfc\xc6\xc6\xfc\xd8\xcc\xc6\xc6\x00"  # R
    b"\x7c\xc6\xc0\x7c\x06\x06\xc6\x7c\x00"  # S
    b"\xfe\x38\x38\x38\x38\x38\x38\x38\x00"  # T
    b"\xc6\x82\x82\x82\x82\x82\xc6\x7c\x00"  # U
    b"\xc6\x82\x82\x82\x82\x44\x28\x10\x00"  # V
    b"\xc6\x82\x82\x82\xaa\xaa\xee\x44\x00"  # W
    b"\xc6\x44\x28\x10\x28\x44\x82\xc6\x00"  # X
    b"\xc6\x82\x44\x28\x10\x10\x10\x38\x00"  # Y
    b"\xfe\x06\x0c\x18\x30\x60\xc0\xfe\x00"  # Z
    b"\x00\x00\x00\x00\x00\x00\x30\x30\x00"  # .
    b"\x00\x00\x00\x00\x00\x30\x30\x20\x40"  # ,
    b"\x00\x30\x30\x00\x00\x30\x30\x00\x00"  # :
    b"\x02\x06\x0c\x18\x30\x60\xc0\x80\x00"  # /
    b"\x00\x10\x10\x7c\x10\x10\x00\x00\x00"  # +
    b"\x00\x00\x00\x7c\x00\x00\x00\x00\x00"  # -
    b"\x00\x00\x7c\x00\x7c\x00\x00\x00\x00"  # =
    b"\x3c\x30\x30\x30\x30\x30\x30\x3c\x00"  # [
    b"\x78\x18\x18\x18\x18\x18\x18\x78\x00"  # ]
    b"\x04\x18\x60\xc0\x60\x18\x04\x00\x00"  # <
    b"\x40\x30\x0c\x06\x0c\x30\x40\x00\x00"  # >
    b"\x7c\xc6\x06\x0c\x18\x00\x18\x18\x00"  # ?
    b"\xc4\xc8\x10\x20\x40\x8c\x0c\x00\x00"  # %
    b"\x00\x00\x00\x00\x00\x00\x00\xfe\x00"  # _
    b"\x00\x92\x54\x38\xfe\x38\x54\x92\x00"  # * BEACON
    b"\x54\xfe\x54\xfe\x54\xfe\x54\x00\x00"  # # DATA STACK
    b"\x38\x38\x38\x38\x38\x00\x38\x38\x00"  # ! ALERT
    b"\x10\x10\x10\x10\x10\x10\x10\x10\x00"  # | DATA BUS
    b"\x10\x38\x7c\xd6\x10\x10\x10\x00\x00"  # ^ ROUTE
    b"\x00\x00\xc6\x6c\x38\x6c\xc6\x00\x00"  # ~ WAVEFORM
    b"\x10\x38\xfe\x7c\x38\x6c\xc6\x82\x00"  # $ SHIP
    b"\x38\x44\x92\xba\xba\x92\x44\x38\x00"  # @ TARGET
)

# RGB565 phosphor palette sampled by eye from the film's green, cyan, amber,
# red, and blue CRT displays.
_BLACK = const(0x0000)
_CRT_BLACK = const(0x0020)
if BOARD_ID == BOARD_FLIPPER_ZERO:
    _GREEN_DIM = 0xFFFF
    _GREEN = 0xFFFF
    _GREEN_BRIGHT = 0xFFFF
    _CYAN = 0xFFFF
    _BLUE_DIM = 0xFFFF
    _AMBER = 0xFFFF
    _RED = 0xFFFF
    _BOOT_MAGENTA = 0x0000
else:
    _GREEN_DIM = 0x11C4
    _GREEN = 0x3E0E
    _GREEN_BRIGHT = 0x9FFA
    _CYAN = 0x6598
    _BLUE_DIM = 0x11B2
    _AMBER = 0xE5C7
    _RED = 0xB1C6
    _BOOT_MAGENTA = 0x816A

_FRAME_MS = const(80)
_SCENE_BOOT = const(0)
_SCENE_MATRIX = const(1)
_SCENE_INTERFACE = const(2)
_SCENE_APPROACH = const(3)
_SCENE_DURATIONS = (6500, 9000, 12500, 10500)

_BOOT_LABELS = (
    "SYS 056",
    "MOTHER CORE",
    "NAV MATRIX",
    "HYPERSLEEP",
    "LIFE SUPPORT",
    "TOW CONTROL",
    "INTERFACE 2037",
    "FLIGHT RECORDER",
)
_BOOT_CODES = ("R 0", "N N", "SM2078", "N5 E", "A3004", "M2083", "READY", "LINK")

_MATRIX_LEFT = (
    "CRFX     OM2077AM",
    "ATTITUDE SM2078",
    "WASTE HT 2080",
    "RAD      2081",
    "VENT     2082AM",
    "NAV      M2083",
    "TIME     M2084",
    "GAL POS  270 RX",
    "COMM LINK 2086SC",
    "INTERFACE 2037",
    "ATTN     2087SC",
    "OVERLOCK M2091",
)
_MATRIX_RIGHT = (
    "L ALIGN  SM2093",
    "PHOTO R  SM2094",
    "MAINS    N5 E",
    "IUA      SM2096",
    "2LA      SM2097",
    "3RA      SM2098",
    "4LHA     SM2099",
    "GRAV GRID M203",
    "INERTIAL M203AM",
    "DECK A   A3003",
    "DECK B   A3004",
    "LIFE SUP 096",
)
_COMPACT_MATRIX = (
    "CRFX 2077",
    "ATT 2078",
    "WASTE 2080",
    "NAV 2083",
    "TIME 2084",
    "LIFE 096",
)

_INQUIRY_TEXT = (
    "READY FOR INQUIRY\n"
    "\n"
    "> SHIP STATUS\n"
    "PROCESSING REQUEST\n"
    "\n"
    "NAVIGATION: ONLINE\n"
    "LIFE SUPPORT: NOMINAL\n"
    "TOW CONTROL: STANDBY\n"
    "CREW MONITOR: ACTIVE\n"
    "\n"
    "AWAITING INPUT _"
)

# Sixteen-step integer sine table, scaled by 256.
_TRIG = (0, 98, 181, 237, 256, 237, 181, 98, 0, -98, -181, -237, -256, -237, -181, -98)

_screen_w = 0
_screen_h = 0
_content_x = 0
_content_y = 0
_content_w = 0
_content_h = 0
_compact = False
_scene = 0
_scene_started = 0
_last_frame = 0
_frame = 0
_random_state = 0x180924
_text_buffer = None
_blank_buffer = None
_plate_blank_buffer = None
_text_view = None
_blank_view = None
_plate_blank_view = None


def _glyph_index(character):
    """Return the packed-font index for one character."""
    if not character:
        return 0
    value = ord(character[0])
    if value == 32:
        return 0
    if 48 <= value <= 57:
        return 1 + value - 48
    if 65 <= value <= 90:
        return 11 + value - 65
    if 97 <= value <= 122:
        return 11 + value - 97
    punct = _FONT_PUNCT.find(character[0])
    if punct >= 0:
        return _FONT_PUNCT_BASE + punct
    return _FONT_PUNCT_BASE + _FONT_PUNCT.find("?")


def _fill_rect(draw, x, y, width, height, color):
    """Draw a clipped filled rectangle without allocating Vector objects."""
    if width <= 0 or height <= 0:
        return
    left = max(0, x)
    top = max(0, y)
    right = min(_screen_w, x + width)
    bottom = min(_screen_h, y + height)
    if left < right and top < bottom:
        draw._fill_rectangle(left, top, right - left, bottom - top, color)


def _draw_glyph(draw, x, y, glyph_index, color, scale=1):
    """Render one packed glyph, coalescing adjacent pixels into row runs."""
    if scale < 1:
        scale = 1
    width = _FONT_W * scale
    height = _FONT_H * scale
    if x >= _screen_w or y >= _screen_h or x + width <= 0 or y + height <= 0:
        return

    offset = glyph_index * _FONT_ROWS
    row = 0
    while row < _FONT_H:
        bits = _FONT_DATA[offset + row]
        column = 0
        while column < _FONT_W:
            mask = 0x80 >> column
            if bits & mask:
                start = column
                column += 1
                while column < _FONT_W and bits & (0x80 >> column):
                    column += 1
                _fill_rect(
                    draw,
                    x + start * scale,
                    y + row * scale,
                    (column - start) * scale,
                    scale,
                    color,
                )
            else:
                column += 1
        row += 1


def _rgb565_to_332(color):
    """Convert Picoware's RGB565 palette to the native packed blit format."""
    return ((color >> 8) & 0xE0) | ((color >> 6) & 0x1C) | ((color >> 3) & 0x03)


def _blit_text_line(draw, x, y, text, color, scale=1):
    """Rasterize one custom-font line and send it as one framebuffer blit."""
    if not text or x < 0 or y < 0 or x >= _screen_w or y >= _screen_h:
        return
    if scale < 1:
        scale = 1
    # CrowPanel's LCD binding accepts RGB565 buffers only; its internal
    # framebuffer makes the direct run renderer inexpensive enough there.
    if BOARD_ID == BOARD_CROWPANEL_10_1:
        advance = _FONT_ADVANCE * scale
        for index in range(len(text)):
            glyph_x = x + index * advance
            if glyph_x >= _screen_w:
                break
            _draw_glyph(draw, glyph_x, y, _glyph_index(text[index]), color, scale)
        return

    width = min(_text_width(text, scale), _screen_w - x)
    height = min(_FONT_H * scale, _screen_h - y)
    if width <= 0 or height <= 0:
        return

    size = width * height
    if _text_view is None or size > len(_text_buffer):
        # This only applies to direct unit calls before start(); normal
        # screensaver rendering uses the reusable buffers allocated there.
        pixels = bytearray(size)
        pixel_view = memoryview(pixels)
    else:
        _text_view[:size] = _blank_view[:size]
        pixel_view = _text_view[:size]

    packed_color = _rgb565_to_332(color)
    advance = _FONT_ADVANCE * scale
    for character_index in range(len(text)):
        glyph_offset = _glyph_index(text[character_index]) * _FONT_ROWS
        glyph_x = character_index * advance
        if glyph_x >= width:
            break
        for source_row in range(_FONT_H):
            bits = _FONT_DATA[glyph_offset + source_row]
            if not bits:
                continue
            for source_column in range(_FONT_W):
                if not bits & (0x80 >> source_column):
                    continue
                pixel_x = glyph_x + source_column * scale
                if pixel_x >= width:
                    continue
                pixel_y = source_row * scale
                for scale_y in range(scale):
                    target_y = pixel_y + scale_y
                    if target_y >= height:
                        break
                    row_offset = target_y * width
                    for scale_x in range(scale):
                        target_x = pixel_x + scale_x
                        if target_x < width:
                            pixel_view[row_offset + target_x] = packed_color

    draw._bytearray(x, y, width, height, pixel_view)


def _draw_plate_glyph(draw, x, y, glyph_index, color, scale=2):
    """Render a thin connected skeleton glyph for the vessel identity plate."""
    if scale < 1:
        scale = 1
    offset = glyph_index * _FONT_ROWS
    row = 0
    while row < _FONT_H:
        bits = _FONT_DATA[offset + row]
        column = 0
        while column < _FONT_W:
            mask = 0x80 >> column
            if bits & mask:
                point_x = x + column * scale
                point_y = y + row * scale
                _fill_rect(draw, point_x, point_y, 1, 1, color)
                if column + 1 < _FONT_W and bits & (0x80 >> (column + 1)):
                    _fill_rect(draw, point_x, point_y, scale + 1, 1, color)
                if row + 1 < _FONT_H and _FONT_DATA[offset + row + 1] & mask:
                    _fill_rect(draw, point_x, point_y, 1, scale + 1, color)
            column += 1
        row += 1


def _draw_text(draw, x, y, text, color, scale=1, max_width=0):
    """Render text with the custom font and optional hard wrapping."""
    start_x = x
    advance = _FONT_ADVANCE * scale
    line_height = (_FONT_H + 2) * scale
    available = min(max_width, _screen_w - start_x) if max_width > 0 else _screen_w - start_x
    characters_per_line = max(1, (available + scale) // advance)
    line = ""
    for character in text:
        if character == "\n":
            _blit_text_line(draw, start_x, y, line, color, scale)
            line = ""
            y += line_height
            continue
        if len(line) >= characters_per_line:
            _blit_text_line(draw, start_x, y, line, color, scale)
            line = ""
            y += line_height
        if y >= _screen_h:
            break
        line += character
    if line and y < _screen_h:
        _blit_text_line(draw, start_x, y, line, color, scale)


def _draw_plate_text(draw, x, y, text, color, scale=2):
    advance = _FONT_ADVANCE * scale
    for character in text:
        _draw_plate_glyph(draw, x, y, _glyph_index(character), color, scale)
        x += advance


def _blit_plate_text(draw, x, y, text, color, background, scale=2):
    """Batch the plotted identity lettering over its solid plate color."""
    if (
        BOARD_ID == BOARD_CROWPANEL_10_1
        or _text_view is None
        or _plate_blank_view is None
        or not text
    ):
        _draw_plate_text(draw, x, y, text, color, scale)
        return

    width = min(_text_width(text, scale), _screen_w - x)
    height = min(_FONT_H * scale, _screen_h - y)
    size = width * height
    if width <= 0 or height <= 0 or size > len(_text_buffer):
        _draw_plate_text(draw, x, y, text, color, scale)
        return

    background_view = (
        _plate_blank_view if background == _BOOT_MAGENTA else _blank_view
    )
    _text_view[:size] = background_view[:size]
    packed_color = _rgb565_to_332(color)
    advance = _FONT_ADVANCE * scale

    for character_index in range(len(text)):
        glyph_offset = _glyph_index(text[character_index]) * _FONT_ROWS
        glyph_x = character_index * advance
        if glyph_x >= width:
            break
        for source_row in range(_FONT_H):
            bits = _FONT_DATA[glyph_offset + source_row]
            for source_column in range(_FONT_W):
                mask = 0x80 >> source_column
                if not bits & mask:
                    continue
                point_x = glyph_x + source_column * scale
                point_y = source_row * scale
                if point_x < width and point_y < height:
                    _text_view[point_y * width + point_x] = packed_color
                if source_column + 1 < _FONT_W and bits & (mask >> 1):
                    for offset in range(scale + 1):
                        target_x = point_x + offset
                        if target_x < width:
                            _text_view[point_y * width + target_x] = packed_color
                if (
                    source_row + 1 < _FONT_H
                    and _FONT_DATA[glyph_offset + source_row + 1] & mask
                ):
                    for offset in range(scale + 1):
                        target_y = point_y + offset
                        if target_y < height:
                            _text_view[target_y * width + point_x] = packed_color

    draw._bytearray(x, y, width, height, _text_view[:size])


def _text_width(text, scale=1):
    """Return custom-font width for a single line."""
    if not text:
        return 0
    return len(text) * _FONT_ADVANCE * scale - scale


def _draw_centered(draw, center_x, y, text, color, scale=1):
    _draw_text(draw, center_x - _text_width(text, scale) // 2, y, text, color, scale)


def _draw_plate_frame(draw, x, y, width, height, divider_y, color):
    """Draw an irregular stepped enclosure like a plotted technical plate."""
    step = 7
    draw._line(x + step, y, x + width - step - 1, y, color)
    draw._line(x, y + step, x, y + height - step - 1, color)
    draw._line(x + width - 1, y + step, x + width - 1, y + height - step - 1, color)
    draw._line(x + step, y + height - 1, x + width - step - 1, y + height - 1, color)
    draw._line(x, y + step, x + step, y, color)
    draw._line(x + width - step - 1, y, x + width - 1, y + step, color)
    draw._line(x, y + height - step - 1, x + step, y + height - 1, color)
    draw._line(
        x + width - step - 1,
        y + height - 1,
        x + width - 1,
        y + height - step - 1,
        color,
    )
    draw._line(x + 3, divider_y, x + width - 4, divider_y, color)


def _draw_typed(draw, x, y, text, resolved, color, max_width):
    """Draw resolved text plus one amber pre-resolution character."""
    start_x = x
    line_height = _FONT_H + 2
    characters_per_line = max(1, (max_width + 1) // _FONT_ADVANCE)
    count = min(resolved, len(text))
    index = 0
    line = ""
    marked_line = False
    while index < count:
        character = text[index]
        if character == "\n":
            _blit_text_line(draw, start_x, y, line, color)
            if marked_line and line:
                draw._line(
                    start_x,
                    y + _FONT_H,
                    start_x + _text_width(line) - 1,
                    y + _FONT_H,
                    color,
                )
            line = ""
            y += line_height
            marked_line = False
        else:
            if len(line) >= characters_per_line:
                _blit_text_line(draw, start_x, y, line, color)
                if marked_line:
                    draw._line(
                        start_x,
                        y + _FONT_H,
                        start_x + _text_width(line) - 1,
                        y + _FONT_H,
                        color,
                    )
                line = ""
                y += line_height
                marked_line = False
            if not line and character == ">":
                marked_line = True
            line += character
        index += 1

    if line:
        _blit_text_line(draw, start_x, y, line, color)

    if count < len(text) and y < _screen_h - _FONT_H:
        character = text[count]
        if character != "\n":
            if len(line) >= characters_per_line:
                line = ""
                y += line_height
            cursor_x = start_x + len(line) * _FONT_ADVANCE
            wrong = 1 + ((_frame * 11 + count * 7) % (len(_FONT_DATA) // _FONT_ROWS - 1))
            _draw_glyph(draw, cursor_x, y, wrong, _AMBER)


def _rand():
    """Small deterministic generator; avoids importing random."""
    global _random_state
    _random_state = (1103515245 * _random_state + 12345) & 0x7FFFFFFF
    return _random_state


def _clear(draw, color=_CRT_BLACK):
    draw.fill_screen(color)


def _draw_frame_effects(draw, color):
    """Add restrained beam roll, signal noise, and a curved CRT mask."""
    x = _content_x
    y = _content_y
    width = _content_w
    height = _content_h
    if width <= 2 or height <= 2:
        return

    beam_y = y + (_frame * 5) % height
    draw._line(x + 1, beam_y, x + width - 2, beam_y, color)

    noise_count = 5 if _compact else 12
    for _ in range(noise_count):
        px = x + 2 + _rand() % max(1, width - 4)
        py = y + 2 + _rand() % max(1, height - 4)
        draw._pixel(px, py, _GREEN_DIM if _scene != _SCENE_APPROACH else _BLUE_DIM)

    if _frame > 0 and _frame % 47 == 0:
        band_y = y + 2 + _rand() % max(1, height - 4)
        _fill_rect(draw, x + 1, band_y, width - 2, 2, _BLACK)

def _render_registration(draw, elapsed):
    """Red registration card seen during the ship's wake sequence."""
    x = _content_x
    y = _content_y
    width = _content_w
    height = _content_h
    _clear(draw, _BLACK)

    if elapsed < 350:
        lamp_y = y + height // 2
        draw._pixel(x + width // 2 - 36, lamp_y, _CYAN)
        draw._pixel(x + width // 2 - 12, lamp_y, _RED)
        draw._pixel(x + width // 2 + 12, lamp_y, _AMBER)
        draw._pixel(x + width // 2 + 36, lamp_y, _GREEN)
        return

    flicker = (elapsed // 90) % 19 == 0
    if not flicker:
        _fill_rect(draw, x, y, width, height, _BOOT_MAGENTA)

    box_width = min(width - 12, max(164, _text_width("180924609", 2) + 20))
    box_height = 70
    box_x = x + (width - box_width) // 2
    box_y = y + max(8, (height - box_height) // 2)

    _draw_plate_frame(draw, box_x, box_y, box_width, box_height, box_y + 34, _CYAN)

    scale = 2 if box_width >= 160 else 1
    title_x = box_x + (box_width - _text_width("NOSTROMO", scale)) // 2
    number_x = box_x + (box_width - _text_width("180924609", scale)) // 2
    plate_background = _BLACK if flicker else _BOOT_MAGENTA
    _blit_plate_text(
        draw,
        title_x,
        box_y + 8,
        "NOSTROMO",
        _CYAN,
        plate_background,
        scale,
    )
    _blit_plate_text(
        draw,
        number_x,
        box_y + 42,
        "180924609",
        _CYAN,
        plate_background,
        scale,
    )

    _draw_glyph(
        draw,
        box_x + 3,
        box_y + 2,
        _glyph_index("1"),
        _GREEN_BRIGHT,
    )
    _draw_glyph(
        draw,
        box_x + box_width - 10,
        box_y + box_height - 12,
        _glyph_index("1"),
        _GREEN_BRIGHT,
    )


def _render_bootstrap(draw, elapsed):
    _clear(draw)
    x = _content_x
    y = _content_y
    width = _content_w
    height = _content_h

    header = "BOOTSTRAP // 180924609" if width >= 220 else "BOOT // 180924609"
    _draw_text(draw, x + 8, y + 8, header, _CYAN)
    draw._line(x + 8, y + 22, x + width - 9, y + 22, _GREEN_DIM)

    progress = min(100, max(0, (elapsed - 2300) * 100 // 4000))
    bar_x = x + 8
    bar_y = y + 30
    bar_width = width - 16
    draw._rectangle(bar_x, bar_y, bar_width, 7, _GREEN_DIM)
    _fill_rect(draw, bar_x + 2, bar_y + 2, (bar_width - 4) * progress // 100, 3, _GREEN)
    _draw_text(draw, bar_x, bar_y + 12, "LOAD " + str(progress) + "%", _GREEN_BRIGHT)

    first_y = bar_y + 30
    row_height = 15 if height >= 260 else 12
    visible_rows = max(1, min(len(_BOOT_LABELS), (height - 72) // row_height))
    completed = min(visible_rows, max(0, (elapsed - 2300) // 380))
    code_x = x + max(128, width - 72)

    for index in range(visible_rows):
        row_y = first_y + index * row_height
        if index < completed:
            color = _GREEN
        elif index == completed:
            color = _AMBER
        else:
            color = _GREEN_DIM
        _draw_text(draw, x + 8, row_y, ">", color)
        _draw_text(draw, x + 24, row_y, _BOOT_LABELS[index], color)
        if code_x < x + width - 8:
            _draw_text(draw, code_x, row_y, _BOOT_CODES[index], color)

    footer_y = y + height - 19
    draw._line(x + 8, footer_y - 5, x + width - 9, footer_y - 5, _GREEN_DIM)
    footer = "SYSTEM READY _" if progress >= 100 and (_frame // 5) % 2 else "SYSTEM CHECK"
    _draw_text(draw, x + 8, footer_y, footer, _GREEN_BRIGHT if progress >= 100 else _GREEN_DIM)


def _render_boot(draw, elapsed):
    if elapsed < 2300:
        _render_registration(draw, elapsed)
    else:
        _render_bootstrap(draw, elapsed)


def _render_matrix(draw, elapsed):
    _clear(draw)
    x = _content_x
    y = _content_y
    width = _content_w
    height = _content_h

    header = "OVERMONITORING ADDRESS MATRIX" if width >= 250 else "ADDRESS MATRIX"
    _draw_text(draw, x + 8, y + 8, header, _GREEN_BRIGHT)

    first_y = y + 27
    row_height = 15 if height >= 280 else 12
    max_rows = max(1, (height - 68) // row_height)
    rows = min(len(_MATRIX_LEFT), max_rows)

    if width >= 300:
        for index in range(rows):
            row_y = first_y + index * row_height
            _draw_text(draw, x + 8, row_y, _MATRIX_LEFT[index], _GREEN)
            _draw_text(draw, x + 164, row_y, _MATRIX_RIGHT[index], _GREEN)
    else:
        total_rows = min(max_rows, len(_MATRIX_LEFT) + len(_MATRIX_RIGHT))
        for index in range(total_rows):
            row_y = first_y + index * row_height
            if index < len(_MATRIX_LEFT):
                line = _MATRIX_LEFT[index]
            else:
                line = _MATRIX_RIGHT[index - len(_MATRIX_LEFT)]
            _draw_text(draw, x + 8, row_y, line, _GREEN)
        rows = total_rows

    sweep_height = max(1, rows * row_height)
    sweep_y = first_y + (_frame * 4) % sweep_height
    _fill_rect(draw, x + 4, sweep_y - 2, width - 8, 6, _GREEN_DIM)
    draw._line(x + 4, sweep_y + 1, x + width - 5, sweep_y + 1, _GREEN_BRIGHT)

    glitch_row = (_frame // 3) % max(1, rows)
    glitch_x = x + 8 + ((_frame * 5) % max(1, (width - 24) // _FONT_ADVANCE)) * _FONT_ADVANCE
    _draw_glyph(
        draw,
        glitch_x,
        first_y + glitch_row * row_height,
        1 + (_frame * 7) % (len(_FONT_DATA) // _FONT_ROWS - 1),
        _AMBER,
    )

    footer_y = y + height - 19
    _draw_text(draw, x + 8, footer_y, "00000005", _GREEN)
    _draw_text(draw, x + width // 2 - 24, footer_y, "ZW S18", _GREEN)
    _draw_text(draw, x + width - 32, footer_y, "@", _GREEN_BRIGHT)


def _draw_core(draw):
    """Draw MU/TH/UR's octagonal circuit-board identity."""
    x = _content_x
    y = _content_y
    width = _content_w
    height = _content_h
    center_x = x + width // 2
    center_y = y + height // 2 - 8
    radius = max(28, min(width, height) // 3)
    half = radius // 2
    points = (
        (center_x - half, center_y - radius),
        (center_x + half, center_y - radius),
        (center_x + radius, center_y - half),
        (center_x + radius, center_y + half),
        (center_x + half, center_y + radius),
        (center_x - half, center_y + radius),
        (center_x - radius, center_y + half),
        (center_x - radius, center_y - half),
    )
    for index in range(8):
        first = points[index]
        second = points[(index + 1) & 7]
        draw._line(first[0], first[1], second[0], second[1], _CYAN)

    for index in range(1, 7):
        offset = index * radius // 8
        color = _GREEN if index & 1 else _GREEN_DIM
        draw._line(
            center_x - radius + 8,
            center_y - offset,
            center_x - 12,
            center_y - offset,
            color,
        )
        draw._line(
            center_x + 12,
            center_y + offset,
            center_x + radius - 8,
            center_y + offset,
            color,
        )
        draw._line(
            center_x - offset,
            center_y + 12,
            center_x - offset,
            center_y + radius - 8,
            color,
        )
        draw._line(
            center_x + offset,
            center_y - radius + 8,
            center_x + offset,
            center_y - 12,
            color,
        )

    _draw_centered(draw, center_x, center_y - 9, "MOTHER", _GREEN_BRIGHT)
    _draw_centered(draw, center_x, center_y + 5, "6000", _GREEN)
    _draw_centered(draw, center_x, y + height - 20, "INTERFACE 2037", _CYAN)


def _render_interface(draw, elapsed):
    _clear(draw)
    if elapsed < 1800:
        _draw_core(draw)
        return

    x = _content_x
    y = _content_y
    width = _content_w
    height = _content_h
    scale = 2 if width >= 230 and height >= 210 else 1
    _draw_text(draw, x + 8, y + 10, "INTERFACE 2037", _GREEN_BRIGHT, scale)
    header_bottom = y + 10 + (_FONT_H + 3) * scale

    body_y = header_bottom + 10
    if elapsed < 2300:
        bloom_x = x + 8 + (elapsed - 1800) * max(1, width - 16) // 500
        _fill_rect(draw, x + 8, body_y - 2, width - 16, 8, _GREEN_DIM)
        _fill_rect(draw, max(x + 8, bloom_x - 24), body_y - 1, 30, 6, _GREEN_BRIGHT)
    resolved = max(0, (elapsed - 2300) // 60)
    _draw_typed(draw, x + 8, body_y, _INQUIRY_TEXT, resolved, _GREEN, width - 16)

    _draw_text(draw, x + 8, y + height - 18, "6000 SERIES", _GREEN_DIM)


def _terrain_x(center_x, width, depth, column):
    spread = width * depth // 16
    return center_x + (column - 4) * spread // 4


def _terrain_y(top_y, height, depth, column, phase):
    point_y = top_y + height * depth * depth // 64
    ridge = _TRIG[(column * 3 + depth + phase) & 15]
    point_y += ridge * max(1, depth * height // 90) // 256
    return point_y


def _render_approach(draw, elapsed):
    _clear(draw, _BLACK)
    x = _content_x
    y = _content_y
    width = _content_w
    height = _content_h
    side_width = 88 if width >= 290 else 0

    _draw_text(draw, x + 8, y + 7, "APPROACH PARK ORBIT", _CYAN)
    _draw_text(draw, x + width - 48, y + 7, "777A0", _RED)

    plot_left = x + 8
    plot_top = y + 25
    plot_right = x + width - side_width - 8
    plot_bottom = y + height - 11
    plot_width = max(40, plot_right - plot_left)
    plot_height = max(40, plot_bottom - plot_top)
    corner = 12
    draw._line(plot_left, plot_top, plot_left + corner, plot_top, _BLUE_DIM)
    draw._line(plot_left, plot_top, plot_left, plot_top + corner, _BLUE_DIM)
    draw._line(plot_right - corner, plot_top, plot_right, plot_top, _BLUE_DIM)
    draw._line(plot_right, plot_top, plot_right, plot_top + corner, _BLUE_DIM)
    draw._line(plot_left, plot_bottom - corner, plot_left, plot_bottom, _BLUE_DIM)
    draw._line(plot_left, plot_bottom, plot_left + corner, plot_bottom, _BLUE_DIM)
    draw._line(plot_right, plot_bottom - corner, plot_right, plot_bottom, _BLUE_DIM)
    draw._line(plot_right - corner, plot_bottom, plot_right, plot_bottom, _BLUE_DIM)

    for index in range(18):
        star_x = plot_left + 3 + (index * 47 + 13) % max(1, plot_width - 6)
        star_y = plot_top + 3 + (index * 83 + 29) % max(1, plot_height - 6)
        if (index + _frame // 6) % 4:
            draw._pixel(star_x, star_y, _GREEN_DIM)

    center_x = plot_left + plot_width // 2
    center_y = plot_top + plot_height // 2
    terrain_top = plot_top + plot_height // 3
    terrain_height = max(20, plot_bottom - terrain_top - 2)
    phase = _frame // 4
    for depth in range(1, 9):
        previous_x = _terrain_x(center_x, plot_width, depth, 0)
        previous_y = _terrain_y(terrain_top, terrain_height, depth, 0, phase)
        for column in range(1, 9):
            point_x = _terrain_x(center_x, plot_width, depth, column)
            point_y = _terrain_y(
                terrain_top, terrain_height, depth, column, phase
            )
            draw._line(
                previous_x,
                previous_y,
                point_x,
                point_y,
                _CYAN if depth in (4, 8) else _GREEN_DIM,
            )
            previous_x = point_x
            previous_y = point_y
        if depth > 1:
            for column in range(9):
                previous_x = _terrain_x(
                    center_x, plot_width, depth - 1, column
                )
                previous_y = _terrain_y(
                    terrain_top, terrain_height, depth - 1, column, phase
                )
                point_x = _terrain_x(center_x, plot_width, depth, column)
                point_y = _terrain_y(
                    terrain_top, terrain_height, depth, column, phase
                )
                draw._line(previous_x, previous_y, point_x, point_y, _GREEN_DIM)

    corridor_left = center_x - max(8, plot_width // 10)
    corridor_right = center_x + max(8, plot_width // 10)
    draw._line(center_x - 2, terrain_top, corridor_left, plot_bottom, _CYAN)
    draw._line(center_x + 2, terrain_top, corridor_right, plot_bottom, _CYAN)

    half_width = max(1, plot_width // 2)
    horizon_base = plot_bottom - max(12, plot_height // 8)
    previous_x = plot_left
    delta = previous_x - center_x
    previous_y = horizon_base - (half_width * half_width - delta * delta) // max(1, plot_width * 4)
    point_x = plot_left + 8
    while point_x <= plot_right:
        delta = point_x - center_x
        point_y = horizon_base - (half_width * half_width - delta * delta) // max(1, plot_width * 4)
        draw._line(previous_x, previous_y, point_x, point_y, _AMBER)
        previous_x = point_x
        previous_y = point_y
        point_x += 8

    ship_x = plot_left + 8 + (_frame * 3) % max(9, plot_width - 24)
    ship_y = plot_top + 12 + _TRIG[(_frame // 2) & 15] * max(5, plot_height // 12) // 256
    _draw_glyph(draw, ship_x, ship_y, _glyph_index("$"), _CYAN)

    if side_width:
        side_x = plot_right + 9
        draw._line(side_x, plot_top, side_x, plot_bottom, _BLUE_DIM)
        altitude = 1532 - (_frame * 7) % 900
        vector = 78 + (_frame % 20)
        _draw_text(draw, side_x + 6, plot_top + 7, "ALTITUDE", _CYAN)
        _draw_text(draw, side_x + 6, plot_top + 20, str(altitude), _GREEN_BRIGHT)
        _draw_text(draw, side_x + 6, plot_top + 46, "COURSE", _CYAN)
        _draw_text(draw, side_x + 6, plot_top + 59, "N .36", _GREEN)
        _draw_text(draw, side_x + 6, plot_top + 84, "VECTOR", _CYAN)
        _draw_text(draw, side_x + 6, plot_top + 97, str(vector) + ".26", _GREEN)
        _draw_text(draw, side_x + 6, plot_top + 122, "AUTODEC", _CYAN)
        _draw_text(draw, side_x + 6, plot_top + 135, "-" + str((elapsed // 10) % 9999), _RED)
        _draw_text(draw, side_x + 6, plot_bottom - 16, "LOCK @", _GREEN_BRIGHT)
    elif height >= 180:
        _draw_text(
            draw,
            plot_left + 5,
            plot_bottom - 17,
            "ALT " + str(1532 - (_frame * 7) % 900),
            _GREEN,
        )
        _draw_text(draw, plot_right - 55, plot_bottom - 17, "53 1L", _RED)


def _render_compact(draw, elapsed):
    """Readable fallback for 128x64 and short landscape displays."""
    _clear(draw)
    x = _content_x
    y = _content_y
    width = _content_w
    height = _content_h
    center_x = x + width // 2

    if _scene == _SCENE_BOOT and elapsed < 2300:
        _fill_rect(draw, x, y, width, height, _BOOT_MAGENTA)
        scale = 2 if width >= 155 and height >= 70 else 1
        box_x = x + 3
        box_width = width - 6
        box_height = min(height - 6, _FONT_H * scale * 2 + 16)
        box_y = y + (height - box_height) // 2
        divider_y = box_y + _FONT_H * scale + 7
        _draw_plate_frame(
            draw, box_x, box_y, box_width, box_height, divider_y, _CYAN
        )
        title_x = center_x - _text_width("NOSTROMO", scale) // 2
        number_x = center_x - _text_width("180924609", scale) // 2
        _blit_plate_text(
            draw,
            title_x,
            box_y + 3,
            "NOSTROMO",
            _CYAN,
            _BOOT_MAGENTA,
            scale,
        )
        _blit_plate_text(
            draw,
            number_x,
            divider_y + 4,
            "180924609",
            _CYAN,
            _BOOT_MAGENTA,
            scale,
        )
        return

    if _scene == _SCENE_MATRIX:
        title = "ADDRESS MATRIX" if width >= 120 else "ADDR MATRIX"
        _draw_text(draw, x + 4, y + 3, title, _GREEN_BRIGHT)
        row_height = 12
        rows = min(len(_COMPACT_MATRIX), max(1, (height - 18) // row_height))
        for index in range(rows):
            _draw_text(
                draw,
                x + 4,
                y + 17 + index * row_height,
                _COMPACT_MATRIX[index],
                _GREEN,
            )
        sweep_y = y + 17 + (_frame * 3) % max(1, rows * row_height)
        _fill_rect(draw, x + 2, sweep_y - 1, width - 4, 4, _GREEN_DIM)
        draw._line(x + 2, sweep_y, x + width - 3, sweep_y, _GREEN_BRIGHT)
        return

    if _scene == _SCENE_APPROACH and width >= 150 and height >= 100:
        _render_approach(draw, elapsed)
        return

    if _scene == _SCENE_BOOT:
        title = "NOSTROMO"
        line_1 = "180924609"
        line_2 = "SYS 056 ACTIVE"
        color = _CYAN
    elif _scene == _SCENE_MATRIX:
        title = "MOTHER 2037"
        line_1 = "ADDRESS MATRIX"
        line_2 = "CRFX OM2077"
        color = _GREEN_BRIGHT
    elif _scene == _SCENE_INTERFACE:
        title = "INTERFACE"
        line_1 = "READY FOR QUERY"
        line_2 = "> STATUS _"
        color = _GREEN_BRIGHT
    else:
        title = "PARK ORBIT"
        line_1 = "ALT 1532"
        line_2 = "VECTOR 78.26"
        color = _CYAN

    if width < 120:
        if _scene == _SCENE_BOOT:
            line_1 = "180924609"
            line_2 = "SYS ACTIVE"
        elif _scene == _SCENE_MATRIX:
            line_1 = "ADDR MATRIX"
            line_2 = "CRFX 2077"
        elif _scene == _SCENE_INTERFACE:
            line_1 = "READY"
            line_2 = "> STATUS"
        else:
            line_1 = "ALT 1532"
            line_2 = "VECTOR 78"

    _draw_centered(draw, center_x, y + 3, title, color)
    resolved = 1 + (elapsed // 140) % max(1, len(line_1))
    _draw_typed(draw, x + 4, y + 17, line_1, resolved, _GREEN, width - 8)
    if height >= 44:
        _draw_text(draw, x + 4, y + 31, line_2, _AMBER if (_frame // 5) & 1 else _GREEN)
        if _scene == _SCENE_INTERFACE:
            underline_width = min(width - 8, _text_width(line_2))
            draw._line(x + 4, y + 41, x + 4 + underline_width, y + 41, _GREEN)


def _render(draw, elapsed):
    if _compact:
        _render_compact(draw, elapsed)
    elif _scene == _SCENE_BOOT:
        _render_boot(draw, elapsed)
    elif _scene == _SCENE_MATRIX:
        _render_matrix(draw, elapsed)
    elif _scene == _SCENE_INTERFACE:
        _render_interface(draw, elapsed)
    else:
        _render_approach(draw, elapsed)

    effect_color = _BLUE_DIM if _scene == _SCENE_APPROACH else _GREEN_DIM
    _draw_frame_effects(draw, effect_color)


def start(view_manager):
    """Initialize the screensaver."""
    global _screen_w, _screen_h, _content_x, _content_y, _content_w, _content_h
    global _compact, _scene, _scene_started, _last_frame, _frame, _random_state
    global _text_buffer, _blank_buffer, _plate_blank_buffer
    global _text_view, _blank_view, _plate_blank_view

    draw = view_manager.draw
    _screen_w = draw.size.x
    _screen_h = draw.size.y
    # The film's terminals are predominantly 4:3 CRT islands.  Preserve that
    # framing on Picoware's square display and letterbox other aspect ratios.
    _content_w = min(304, _screen_w)
    _content_h = _content_w * 3 // 4
    if _content_h > _screen_h:
        _content_h = _screen_h
        _content_w = min(_content_w, _content_h * 4 // 3)
    _content_x = max(0, (_screen_w - _content_w) // 2)
    _content_y = max(0, (_screen_h - _content_h) // 2)
    _compact = _content_w < 230 or _content_h < 150
    _scene = _SCENE_BOOT
    _scene_started = ticks_ms()
    _last_frame = _scene_started - _FRAME_MS
    _frame = 0
    _random_state = 0x180924
    if BOARD_ID != BOARD_CROWPANEL_10_1:
        buffer_size = max(1, _content_w * _FONT_H * 2)
        _text_buffer = bytearray(buffer_size)
        _blank_buffer = bytearray(buffer_size)
        _plate_blank_buffer = bytearray(buffer_size)
        plate_color = _rgb565_to_332(_BOOT_MAGENTA)
        if plate_color:
            for index in range(buffer_size):
                _plate_blank_buffer[index] = plate_color
        _text_view = memoryview(_text_buffer)
        _blank_view = memoryview(_blank_buffer)
        _plate_blank_view = memoryview(_plate_blank_buffer)
    else:
        _text_buffer = None
        _blank_buffer = None
        _plate_blank_buffer = None
        _text_view = None
        _blank_view = None
        _plate_blank_view = None

    _render(draw, 0)
    draw.swap()
    return True


def run(view_manager):
    """Advance one non-blocking animation tick."""
    global _scene, _scene_started, _last_frame, _frame

    # A screensaver should dismiss immediately on any real input.  The button
    # used to launch it is reset by ViewManager before this view's first tick.
    if view_manager.button != BUTTON_NONE:
        view_manager.input_manager.reset()
        view_manager.back()
        return

    now = ticks_ms()
    if ticks_diff(now, _last_frame) < _FRAME_MS:
        return
    _last_frame = now

    elapsed = ticks_diff(now, _scene_started)
    if elapsed >= _SCENE_DURATIONS[_scene]:
        _scene = (_scene + 1) % len(_SCENE_DURATIONS)
        _scene_started = now
        elapsed = 0
        _frame = 0

    _render(view_manager.draw, elapsed)
    view_manager.draw.swap()
    _frame += 1


def stop(view_manager):
    """Release state and leave a clean framebuffer."""
    from gc import collect

    global _screen_w, _screen_h, _content_x, _content_y, _content_w, _content_h
    global _compact, _scene, _scene_started, _last_frame, _frame
    global _text_buffer, _blank_buffer, _plate_blank_buffer
    global _text_view, _blank_view, _plate_blank_view

    _screen_w = 0
    _screen_h = 0
    _content_x = 0
    _content_y = 0
    _content_w = 0
    _content_h = 0
    _compact = False
    _scene = 0
    _scene_started = 0
    _last_frame = 0
    _frame = 0
    _text_view = None
    _blank_view = None
    _plate_blank_view = None
    _text_buffer = None
    _blank_buffer = None
    _plate_blank_buffer = None
    collect()
