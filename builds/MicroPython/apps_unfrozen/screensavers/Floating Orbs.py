from picoware.system.buttons import BUTTON_BACK
from picoware.system.colors import  TFT_WHITE
from math import sin as _sin

_orbs = []
_colors = []
_velocities = []
_frame = 0
is_flipper = None


def start(view_manager):
    '''Start the screensaver'''
    from picoware.system.vector import Vector
    from picoware.system.colors import (
        TFT_RED, TFT_GREEN, TFT_BLUE, TFT_YELLOW,
        TFT_CYAN, TFT_MAGENTA, TFT_ORANGE, TFT_PINK,
        TFT_WHITE, TFT_SKYBLUE, TFT_VIOLET,
    )
    from picoware.system.boards import BOARD_ID, BOARD_FLIPPER_ZERO
    from random import randint, choice, seed
    from time import ticks_ms

    global _orbs, _colors, _velocities, _frame, is_flipper

    is_flipper = BOARD_ID == BOARD_FLIPPER_ZERO

    seed(ticks_ms())
    _frame = 0

    draw = view_manager.draw
    size = draw.size

    _orbs = []
    _colors = []
    _velocities = []

    palette = [
        TFT_RED, TFT_GREEN, TFT_BLUE, TFT_YELLOW,
        TFT_CYAN, TFT_MAGENTA, TFT_ORANGE, TFT_PINK,
        TFT_WHITE, TFT_SKYBLUE, TFT_VIOLET,
    ]
    if is_flipper:
        for i in range(len(palette)):
            if palette[i] != TFT_BLACK:
                palette[i] = TFT_WHITE

    orb_count = 20
    for _ in range(orb_count):
        x = randint(20, size.x - 20)
        y = randint(20, size.y - 20)
        r = randint(5, 25)
        _orbs.append(Vector(x, y, r))
        _colors.append(choice(palette))
        vx = randint(-3, 3)
        vy = randint(-3, 3)
        if vx == 0:
            vx = 1
        if vy == 0:
            vy = 1
        _velocities.append(Vector(vx, vy, 0))

    return True


def run(view_manager):
    '''Run the screensaver'''

    global _frame

    button = view_manager.button

    if button == BUTTON_BACK:
        view_manager.back()
        return

    draw = view_manager.draw
    size = draw.size

    _frame += 1

    draw.erase()

    for i, orb in enumerate(_orbs):
        v = _velocities[i]
        r = int(orb.z)
        color = _colors[i]

        wobble_x = _sin(_frame * 0.02 + i) * 0.5
        wobble_y = _sin(_frame * 0.03 + i * 1.3) * 0.5

        orb.x += v.x + wobble_x
        orb.y += v.y + wobble_y

        if orb.x - r < 0:
            orb.x = r
            v.x = -v.x
        elif orb.x + r > size.x:
            orb.x = size.x - r
            v.x = -v.x

        if orb.y - r < 0:
            orb.y = r
            v.y = -v.y
        elif orb.y + r > size.y:
            orb.y = size.y - r
            v.y = -v.y

        glow_radius = r + 6
        for g in range(4):
            fade = int(255 * (1.0 - g / 4.0))
            gc = _fade_color(color, fade // 4)
            gr = glow_radius - g * 2
            if gr > 0:
                draw._fill_circle(int(orb.x), int(orb.y), gr, gc)

        draw._fill_circle(int(orb.x), int(orb.y), r, color)

        hr = r // 3
        if hr < 2:
            hr = 2
        draw._fill_circle(int(orb.x) - hr // 2, int(orb.y) - hr // 2, hr, _fade_color(color, 200))

        if _frame % 15 == 0:
            for j in range(i + 1, len(_orbs)):
                other = _orbs[j]
                dx = orb.x - other.x
                dy = orb.y - other.y
                dist = (dx * dx + dy * dy) ** 0.5
                if dist < 80:
                    alpha = int(80 * (1.0 - dist / 80.0))
                    line_color = _fade_color(TFT_WHITE, alpha)
                    draw._line(
                        int(orb.x), int(orb.y),
                        int(other.x), int(other.y),
                        line_color,
                    )

    draw.swap()


def stop(view_manager):
    '''Stop the screensaver'''
    from gc import collect

    global _orbs, _colors, _velocities, _frame, is_flipper

    if _orbs:
        _orbs.clear()
    if _colors:
        _colors.clear()
    if _velocities:
        _velocities.clear()
    _frame = 0
    is_flipper = None

    collect()


def _fade_color(color, opacity):
    '''Fade an RGB565 color by opacity (0-255)'''
    if opacity >= 255:
        return color
    r = (color >> 11) & 0x1F
    g = (color >> 5) & 0x3F
    b = color & 0x1F
    r = (r * opacity) // 255
    g = (g * opacity) // 255
    b = (b * opacity) // 255
    return (r << 11) | (g << 5) | b
