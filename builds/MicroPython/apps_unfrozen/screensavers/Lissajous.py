# Animated Lissajous figures screensaver
# Draws x = sin(a*t + phase), y = sin(b*t) curves as rainbow line segments.

from math import sin as _math_sin
from micropython import const
from array import array
from picoware.system.buttons import BUTTON_BACK
from picoware.system.colors import TFT_BLACK
from picoware.system.vector import Vector

STEPS = const(300)  # line segments per frame
_SIN_SIZE = const(1024)  # must be power-of-2
_SIN_MASK = const(1023)
_TWO_PI = 6.28318530718
_SIN_SCALE = _SIN_SIZE / _TWO_PI  # radians -> LUT index

screen_size = None
phase = 0.0
color_phase = 0.0
a_freq = 3
b_freq = 2
morph_timer = 0
p1 = None
p2 = None

_sin_lut = None  # array('f', 1024)
_color_pal = None  # array('H', STEPS) -- one full rainbow revolution
_x_base = None  # array('H', STEPS+1) -- (a_freq*i*SIN_SIZE//STEPS)
_y_coords = None  # array('h', STEPS+1) -- pre-computed screen y values
_last_a = -1  # track when a_freq changes to rebuild _x_base
_last_b = -1  # track when b_freq changes to rebuild _y_coords


def _build_sin_lut() -> None:
    global _sin_lut
    _sin_lut = array(
        "f", (_math_sin(i * _TWO_PI / _SIN_SIZE) for i in range(_SIN_SIZE))
    )


def _build_color_pal() -> None:
    global _color_pal
    _color_pal = array("H", (0 for _ in range(STEPS)))
    for step_i in range(STEPS):
        hue = step_i / STEPS  # 0.0 .. <1.0
        h6 = hue * 6.0
        seg = int(h6) % 6
        f = h6 - int(h6)
        if seg == 0:
            r, g, b = 255, int(255 * f), 0
        elif seg == 1:
            r, g, b = int(255 * (1 - f)), 255, 0
        elif seg == 2:
            r, g, b = 0, 255, int(255 * f)
        elif seg == 3:
            r, g, b = 0, int(255 * (1 - f)), 255
        elif seg == 4:
            r, g, b = int(255 * f), 0, 255
        else:
            r, g, b = 255, 0, int(255 * (1 - f))
        _color_pal[step_i] = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def _build_x_base(a: int) -> None:
    global _x_base, _last_a
    _x_base = array(
        "H", ((a * i * _SIN_SIZE // STEPS) & _SIN_MASK for i in range(STEPS + 1))
    )
    _last_a = a


def _build_y_coords(b: int, cy: int, ry: int) -> None:
    global _y_coords, _last_b
    _y_coords = array(
        "h",
        (int(cy + ry * _math_sin(b * i * _TWO_PI / STEPS)) for i in range(STEPS + 1)),
    )
    _last_b = b


def start(view_manager) -> bool:
    global screen_size, phase, color_phase, a_freq, b_freq, morph_timer, p1, p2
    global _last_a, _last_b

    draw = view_manager.draw
    screen_size = Vector(draw.size.x, draw.size.y)
    phase = 0.0
    color_phase = 0.0
    a_freq = 3
    b_freq = 2
    morph_timer = 0
    p1 = Vector(0, 0)
    p2 = Vector(0, 0)
    _last_a = -1
    _last_b = -1

    _build_sin_lut()
    _build_color_pal()

    # Build x/y tables for initial frequencies
    cx = screen_size.x >> 1
    cy = screen_size.y >> 1
    _build_x_base(a_freq)
    _build_y_coords(b_freq, cy, cy - 4)

    draw.fill_screen(TFT_BLACK)
    draw.swap()
    return True


def run(view_manager) -> None:
    global phase, color_phase, a_freq, b_freq, morph_timer

    inp = view_manager.input_manager
    if inp.button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
        return

    draw = view_manager.draw
    draw.fill_screen(TFT_BLACK)

    cx = screen_size.x >> 1
    cy = screen_size.y >> 1
    rx = cx - 4

    phase = (phase + 0.02) % _TWO_PI
    color_phase = (color_phase + 0.004) % 1.0

    # Periodically morph a/b frequency ratio
    morph_timer += 1
    if morph_timer >= 350:
        morph_timer = 0
        a_freq = (a_freq % 5) + 1
        b_freq = b_freq + 1
        if b_freq > 5:
            b_freq = 1

    # Rebuild coord tables only when frequencies change
    if a_freq != _last_a:
        _build_x_base(a_freq)
    if b_freq != _last_b:
        _build_y_coords(b_freq, cy, cy - 4)

    # Phase offset into the LUT
    phase_idx = int(phase * _SIN_SCALE) & _SIN_MASK

    lut = _sin_lut
    xb = _x_base
    yc = _y_coords
    pal = _color_pal
    color_offset = int(color_phase * STEPS)
    mask = _SIN_MASK

    p1.x = int(cx + rx * lut[(xb[0] + phase_idx) & mask])
    p1.y = yc[0]

    for step_i in range(1, STEPS + 1):
        p2.x = int(cx + rx * lut[(xb[step_i] + phase_idx) & mask])
        p2.y = yc[step_i]
        draw.line_custom(p1, p2, pal[(color_offset + step_i) % STEPS])
        p1.x = p2.x
        p1.y = p2.y

    draw.swap()


def stop(view_manager) -> None:
    from gc import collect

    global screen_size, phase, color_phase, a_freq, b_freq, morph_timer, p1, p2
    global _sin_lut, _color_pal, _x_base, _y_coords, _last_a, _last_b

    screen_size = None
    phase = 0.0
    color_phase = 0.0
    a_freq = 3
    b_freq = 2
    morph_timer = 0
    p1 = None
    p2 = None
    _sin_lut = None
    _color_pal = None
    _x_base = None
    _y_coords = None
    _last_a = -1
    _last_b = -1

    collect()
