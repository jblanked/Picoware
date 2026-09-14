"""
Patterns Screensaver - Picoware

Displays various animated geometric patterns
Press any key to exit.
"""

from picoware.system.buttons import BUTTON_BACK, BUTTON_CENTER
from picoware.system.colors import (
    TFT_RED,
    TFT_GREEN,
    TFT_BLUE,
    TFT_YELLOW,
    TFT_WHITE,
    TFT_BLACK,
    TFT_CYAN,
    TFT_VIOLET,
)

_demo_state = 0
_frame_count = 0
_scale = 1.0
colors = []
is_flipper = None


def start(view_manager) -> bool:
    """Initialize the screensaver."""
    global _demo_state, _frame_count, _scale, colors, is_flipper
    from picoware.system.boards import BOARD_ID, BOARD_FLIPPER_ZERO

    is_flipper = BOARD_ID == BOARD_FLIPPER_ZERO

    draw = view_manager.draw
    draw.fill_screen(TFT_BLACK)

    _demo_state = 0
    _frame_count = 0
    _scale = min(draw.size.x, draw.size.y) / 320

    colors = [
        TFT_RED,
        TFT_GREEN,
        TFT_BLUE,
        TFT_YELLOW,
        TFT_CYAN,
        TFT_VIOLET,
        TFT_WHITE,
    ]
    if is_flipper:
        for i, color in enumerate(colors):
            if color != TFT_BLACK:
                colors[i] = TFT_WHITE

    # Prompt to advance
    size = draw.len("Press Center")
    draw._text(
        draw.size.x // 2 - size // 2, 
        draw.size.y // 2,
        "Press Center",
        TFT_WHITE,
    )

    draw.swap()

    return True


def _draw_pattern(draw):
    """Draw the current pattern to the display."""
    global _demo_state, _scale
    import math

    # Clear screen
    draw.fill_screen(TFT_BLACK)

    s = _scale
    sw, sh = draw.size.x, draw.size.y
    cx, cy = sw // 2, sh // 2
    screen_min = min(sw, sh)

    if _demo_state == 0:
        # Radiating lines
        r = int(150 * s)
        for i in range(0, 360, 10):
            angle = math.radians(i)
            draw._line(cx, cy, cx + r * math.cos(angle), cy + r * math.sin(angle), colors[i // 10 % len(colors)])

    elif _demo_state == 1:
        # Concentric circles
        max_r = int(screen_min * 0.45)
        step = max(5, int(15 * s))
        for i, r in enumerate(range(10, max_r, step)):
            draw._circle(cx, cy, r, colors[i % len(colors)])

    elif _demo_state == 2:
        # Corner circles
        off = int(screen_min * 0.25)
        r = max(8, int(60 * s))
        draw._fill_circle(off, off, r, TFT_RED)
        draw._fill_circle(sw - off, off, r, TFT_GREEN)
        draw._fill_circle(off, sh - off, r, TFT_BLUE)
        draw._fill_circle(sw - off, sh - off, r, TFT_YELLOW)
        draw._fill_circle(cx, cy, max(6, int(50 * s)), TFT_WHITE)

    elif _demo_state == 3:
        # Nested rectangles
        pad = int(20 * s)
        init_size = screen_min - pad * 2
        step = max(5, int(15 * s))
        size_step = max(10, int(30 * s))
        for i in range(6):
            draw._rectangle(pad + i * step, pad + i * step, init_size - i * size_step, init_size - i * size_step, colors[i])

    elif _demo_state == 4:
        # Overlapping rects
        size = max(20, int(120 * s))
        pos1 = 40 * s
        pos2 = 100 * s
        pos3 = 160 * s
        draw._fill_rectangle(pos1, pos1, size, size, TFT_RED)
        draw._fill_rectangle(pos2, pos2, size, size, TFT_GREEN)
        draw._fill_rectangle(pos3, pos3, size, size, TFT_BLUE)

    elif _demo_state == 5:
        # Triangles
        mid_x = 160 * s
        top_y = 20 * s
        bottom_y = screen_min - 40 * s
        left_x = 40 * s
        right_x = 280 * s
        for i in range(6):
            off = i * 25 * s
            draw._triangle(mid_x, top_y + off, left_x + off, bottom_y - off, right_x - off, bottom_y - off, colors[i])

    elif _demo_state == 6:
        # Checkerboard
        grid = max(8, int(20 * s))
        cell = grid - 2
        for y in range(0, sh, grid):
            for x in range(0, sw, grid):
                if (x // grid + y // grid) % 2 == 0:
                    draw._fill_rectangle(x, y, cell, cell, TFT_RED)
                else:
                    draw._fill_rectangle(x, y, cell, cell, TFT_BLUE)

    elif _demo_state == 7:
        # Spiral circles
        for i in range(60):
            angle = math.radians(i * 15)
            r = int((10 + i * 2) * s)
            x = int(cx + r * math.cos(angle))
            y = int(cy + r * math.sin(angle))
            radius = max(2, int((5 + i // 10) * s))
            draw._circle(x, y, radius, colors[i % len(colors)])

    elif _demo_state == 8:
        # Starburst lines
        inner = int(50 * s)
        outer = int(150 * s)
        for i in range(0, 360, 5):
            angle = math.radians(i)
            lin_pos_x = cx + inner * math.cos(angle)
            lin_pos_y = cy + inner * math.sin(angle)
            lin_size_x = cx + outer * math.cos(angle)
            lin_size_y = cy + outer * math.sin(angle)
            draw._line(lin_pos_x, lin_pos_y, lin_size_x, lin_size_y, colors[i // 5 % len(colors)])

    elif _demo_state == 9:
        # Diamond grid
        step = max(20, int(40 * s))
        half = max(5, int(15 * s))
        for y in range(0, sh, step):
            for x in range(0, sw, step):
                gx = x + step // 2
                gy = y + step // 2
                c = colors[(x // step + y // step) % len(colors)]
                draw._triangle(gx, gy - half, gx - half, gy, gx, gy + half, c)
                draw._triangle(gx, gy - half, gx + half, gy, gx, gy + half, c)

    elif _demo_state == 10:
        # Concentric squares
        init_size = screen_min - int(20 * s)
        for i in range(15):
            size = init_size - i * int(20 * s)
            offset = i * int(10 * s)
            p = int(10 * s) + offset
            draw._rectangle(
                p,
                p,
                size,
                size,
                colors[i % len(colors)],
            )


def run(view_manager) -> None:
    """Run the screensaver - auto-advance patterns."""
    global _demo_state, _frame_count

    inp = view_manager.input_manager
    draw = view_manager.draw

    # Exit on button
    if inp.button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
    elif inp.button == BUTTON_CENTER:
        inp.reset()
        _draw_pattern(draw)
        _demo_state = (_demo_state + 1) % 11
        draw.swap()


def stop(view_manager) -> None:
    """Cleanup."""
    from gc import collect

    global colors, _scale
    colors = []
    _scale = 1.0

    collect()
