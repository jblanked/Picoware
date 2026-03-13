# Aurora Borealis (Northern Lights) screensaver
# Simulates shimmering curtains of colour using layered sine-wave bands.

from math import sin as _math_sin
from micropython import const
from array import array
from picoware.system.buttons import BUTTON_BACK
from picoware.system.colors import TFT_BLACK
from picoware.system.vector import Vector

COL_W = const(6)
NUM_BANDS = const(8)
_SIN_SIZE = const(1024)  # LUT entries (power-of-2 for cheap modulo)
_TWO_PI = 6.28318530718
_SIN_SCALE = _SIN_SIZE / _TWO_PI  # multiply angle (radians) -> LUT index
_N_LEVELS = const(64)  # colour-palette intensity steps

screen_size = None
time_val = 0.0
pos = None
strip_size = None
_sin_lut = None  # array('f', 1024) -- shared sin lookup table
_band_pals = None  # list of 8 x array('H', 64) -- per-band RGB565 palettes
_falloff_lut = None  # array('f', band_h+1) -- falloff[abs_dy] pre-computed


def _build_tables(band_h: int) -> None:
    global _sin_lut, _band_pals, _falloff_lut

    # Sin LUT: 1024 floats covering one full period
    _sin_lut = array(
        "f", (_math_sin(i * _TWO_PI / _SIN_SIZE) for i in range(_SIN_SIZE))
    )

    # Aurora band colours (R, G, B)
    _BAND_COLORS = [
        (0, 220, 110),  # emerald green
        (0, 160, 255),  # sky blue
        (140, 0, 255),  # violet
        (0, 255, 80),  # vivid green
        (0, 120, 255),  # bright blue
        (255, 0, 255),  # magenta
        (0, 255, 160),  # aquamarine
        (255, 0, 140),  # fuchsia
    ]

    # Per-band RGB565 palettes: level 0 = black, level N-1 = full brightness.
    # pulse_max = 0.9, falloff_max = 1.0 -> intensity_max = 0.9
    # int(0.9 * 63) = 56, safely within bounds
    _band_pals = []
    for r0, g0, b0 in _BAND_COLORS:
        pal = array("H", (0 for _ in range(_N_LEVELS)))
        for lvl in range(_N_LEVELS):
            t = lvl / (_N_LEVELS - 1)
            r = int(r0 * t)
            g = int(g0 * t)
            b = int(b0 * t)
            pal[lvl] = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        _band_pals.append(pal)

    # Falloff LUT: linear drop-off from curtain centre (abs_dy=0) to edge
    _falloff_lut = array("f", (0.0 for _ in range(band_h + 1)))
    for d in range(band_h + 1):
        _falloff_lut[d] = max(0.0, 1.0 - (d / band_h) * 1.7)


def start(view_manager) -> bool:
    """Start the app"""
    global screen_size, time_val, pos, strip_size

    draw = view_manager.draw
    screen_size = Vector(draw.size.x, draw.size.y)
    time_val = 0.0
    pos = Vector(0, 0)
    strip_size = Vector(COL_W, 1)

    _build_tables(screen_size.y >> 3)  # band_h = h // 8

    draw.fill_screen(TFT_BLACK)
    draw.swap()
    return True


def run(view_manager) -> None:
    """Run the app"""
    global time_val

    inp = view_manager.input_manager
    if inp.button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
        return

    draw = view_manager.draw
    draw.fill_screen(TFT_BLACK)
    time_val += 0.05

    w = screen_size.x
    h = screen_size.y
    band_h = h >> 3  # h // 8

    lut = _sin_lut
    pals = _band_pals
    falloff = _falloff_lut
    nlm1 = _N_LEVELS - 1
    p = pos
    sv = strip_size

    for band in range(NUM_BANDS):
        base_y = int(h * (0.08 + band * 0.14))
        pulse = (
            0.45
            + 0.45 * lut[int((time_val * 1.1 + band * 2.3) * _SIN_SCALE) % _SIN_SIZE]
        )
        pal = pals[band]
        scale1 = band_h * 0.55
        scale2 = band_h * 0.3
        t1 = time_val + band * 1.3
        t2 = -time_val * 0.6 + band * 0.9

        for x in range(0, w, COL_W):
            fx = x / w
            wave = (
                lut[int((fx * 4.5 + t1) * _SIN_SCALE) % _SIN_SIZE] * scale1
                + lut[int((fx * 7.0 + t2) * _SIN_SCALE) % _SIN_SIZE] * scale2
            )
            center_y = base_y + int(wave)

            for dy in range(-band_h, band_h + 1):
                y = center_y + dy
                if not (0 <= y < h):
                    continue
                f = falloff[dy if dy >= 0 else -dy] * pulse
                if f <= 0.05:
                    continue
                p.x = x
                p.y = y
                draw.fill_rectangle(p, sv, pal[int(f * nlm1)])

    draw.swap()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global screen_size, time_val, pos, strip_size, _sin_lut, _band_pals, _falloff_lut

    screen_size = None
    time_val = 0.0
    pos = None
    strip_size = None
    _sin_lut = None
    _band_pals = None
    _falloff_lut = None

    collect()
