"""
Patterns Screensaver - Picoware

Displays various animated geometric patterns
Press any key to exit.
"""

from picoware.system.buttons import BUTTON_BACK, BUTTON_CENTER
from picoware.system.vector import Vector
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


def start(view_manager) -> bool:
    """Initialize the screensaver."""
    global _demo_state, _frame_count, _scale, colors

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

    # Prompt to advance
    size = len("Press Center") * draw.font_size.x
    draw.text(
        Vector(draw.size.x // 2 - size // 2, draw.size.y // 2),
        "Press Center",
        color=TFT_WHITE,
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
        line_vec = Vector(cx, cy)
        size_vec = Vector(0, 0)
        r = int(150 * s)
        for i in range(0, 360, 10):
            angle = math.radians(i)
            size_vec.x = int(cx + r * math.cos(angle))
            size_vec.y = int(cy + r * math.sin(angle))
            draw.line_custom(line_vec, size_vec, colors[i // 10 % len(colors)])

    elif _demo_state == 1:
        # Concentric circles
        max_r = int(screen_min * 0.45)
        step = max(5, int(15 * s))
        for i, r in enumerate(range(10, max_r, step)):
            draw.circle(Vector(cx, cy), r, colors[i % len(colors)])

    elif _demo_state == 2:
        # Corner circles
        off = int(screen_min * 0.25)
        r = max(8, int(60 * s))
        draw.fill_circle(Vector(off, off), r, TFT_RED)
        draw.fill_circle(Vector(sw - off, off), r, TFT_GREEN)
        draw.fill_circle(Vector(off, sh - off), r, TFT_BLUE)
        draw.fill_circle(Vector(sw - off, sh - off), r, TFT_YELLOW)
        draw.fill_circle(Vector(cx, cy), max(6, int(50 * s)), TFT_WHITE)

    elif _demo_state == 3:
        # Nested rectangles
        pad = int(20 * s)
        init_size = screen_min - pad * 2
        step = max(5, int(15 * s))
        size_step = max(10, int(30 * s))
        rec_pos = Vector(pad, pad)
        rec_size = Vector(init_size, init_size)
        for i in range(6):
            rec_pos.x = pad + i * step
            rec_pos.y = pad + i * step
            rec_size.x = init_size - i * size_step
            rec_size.y = init_size - i * size_step
            draw.rect(rec_pos, rec_size, colors[i])

    elif _demo_state == 4:
        # Overlapping rects
        size = max(20, int(120 * s))
        pos1 = int(40 * s)
        pos2 = int(100 * s)
        pos3 = int(160 * s)
        draw.fill_rectangle(Vector(pos1, pos1), Vector(size, size), TFT_RED)
        draw.fill_rectangle(Vector(pos2, pos2), Vector(size, size), TFT_GREEN)
        draw.fill_rectangle(Vector(pos3, pos3), Vector(size, size), TFT_BLUE)

    elif _demo_state == 5:
        # Triangles
        mid_x = int(160 * s)
        top_y = int(20 * s)
        bottom_y = screen_min - int(40 * s)
        left_x = int(40 * s)
        right_x = int(280 * s)
        pt1 = Vector(mid_x, top_y)
        pt2 = Vector(left_x, bottom_y)
        pt3 = Vector(right_x, bottom_y)
        for i in range(6):
            off = i * int(25 * s)
            pt1.x = mid_x
            pt1.y = top_y + off
            pt2.x = left_x + off
            pt2.y = bottom_y - off
            pt3.x = right_x - off
            pt3.y = bottom_y - off
            draw.triangle(pt1, pt2, pt3, colors[i])

    elif _demo_state == 6:
        # Checkerboard
        grid = max(8, int(20 * s))
        cell = grid - 2
        rec_size = Vector(cell, cell)
        rec_pos = Vector(0, 0)
        for y in range(0, sh, grid):
            for x in range(0, sw, grid):
                rec_pos.x = x
                rec_pos.y = y
                if (x // grid + y // grid) % 2 == 0:
                    draw.fill_rectangle(rec_pos, rec_size, TFT_RED)
                else:
                    draw.fill_rectangle(rec_pos, rec_size, TFT_BLUE)

    elif _demo_state == 7:
        # Spiral circles
        for i in range(60):
            angle = math.radians(i * 15)
            r = int((10 + i * 2) * s)
            x = int(cx + r * math.cos(angle))
            y = int(cy + r * math.sin(angle))
            radius = max(2, int((5 + i // 10) * s))
            draw.circle(Vector(x, y), radius, colors[i % len(colors)])

    elif _demo_state == 8:
        # Starburst lines
        inner = int(50 * s)
        outer = int(150 * s)
        lin_pos = Vector(cx, cy)
        lin_size = Vector(0, 0)
        for i in range(0, 360, 5):
            angle = math.radians(i)
            lin_pos.x = int(cx + inner * math.cos(angle))
            lin_pos.y = int(cy + inner * math.sin(angle))
            lin_size.x = int(cx + outer * math.cos(angle))
            lin_size.y = int(cy + outer * math.sin(angle))
            draw.line_custom(lin_pos, lin_size, colors[i // 5 % len(colors)])

    elif _demo_state == 9:
        # Diamond grid
        step = max(20, int(40 * s))
        half = max(5, int(15 * s))
        pt1 = Vector(0, 0)
        pt2 = Vector(0, 0)
        pt3 = Vector(0, 0)
        for y in range(0, sh, step):
            for x in range(0, sw, step):
                gx = x + step // 2
                gy = y + step // 2
                pt1.x = gx
                pt1.y = gy - half
                pt2.x = gx - half
                pt2.y = gy
                pt3.x = gx
                pt3.y = gy + half
                c = colors[(x // step + y // step) % len(colors)]
                draw.triangle(pt1, pt2, pt3, c)
                pt1.x = gx
                pt1.y = gy - half
                pt2.x = gx + half
                pt2.y = gy
                pt3.x = gx
                pt3.y = gy + half
                draw.triangle(pt1, pt2, pt3, c)

    elif _demo_state == 10:
        # Concentric squares
        init_size = screen_min - int(20 * s)
        for i in range(15):
            size = init_size - i * int(20 * s)
            offset = i * int(10 * s)
            p = int(10 * s) + offset
            draw.rect(
                Vector(p, p),
                Vector(size, size),
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
