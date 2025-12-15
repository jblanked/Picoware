"""
Patterns Screensaver - Picoware

Displays various animated geometric patterns
Press any key to exit.
"""

_demo_state = 0
_frame_count = 0


def start(view_manager) -> bool:
    """Initialize the screensaver."""
    global _demo_state, _frame_count
    from picoware.system.colors import TFT_BLACK, TFT_WHITE

    draw = view_manager.get_draw()
    draw.fill_screen(TFT_BLACK)

    _demo_state = 0
    _frame_count = 0

    # tell user to press center to advance
    from picoware.system.vector import Vector

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
    global _demo_state
    from picoware.system.vector import Vector
    from picoware.system.colors import (
        TFT_RED,
        TFT_GREEN,
        TFT_BLUE,
        TFT_YELLOW,
        TFT_CYAN,
        TFT_VIOLET,
        TFT_WHITE,
        TFT_BLACK,
    )

    # Clear screen
    draw.fill_screen(TFT_BLACK)

    colors = [
        TFT_RED,
        TFT_GREEN,
        TFT_BLUE,
        TFT_YELLOW,
        TFT_CYAN,
        TFT_VIOLET,
        TFT_WHITE,
    ]

    if _demo_state == 0:
        # Pattern 1: Lines radiating from center
        import math

        cx, cy = draw.size.x // 2, draw.size.y // 2
        line_vec = Vector(cx, cy)
        size_vec = Vector(0, -150)
        for i in range(0, 360, 10):
            angle = math.radians(i)
            size_vec.x = int(cx + 150 * math.cos(angle))
            size_vec.y = int(cy + 150 * math.sin(angle))
            draw.line_custom(line_vec, size_vec, colors[i // 10 % len(colors)])

    elif _demo_state == 1:
        # Pattern 2: Concentric circles
        size_vec = Vector(draw.size.x // 2, draw.size.y // 2)
        for i, r in enumerate(range(10, 160, 15)):
            draw.circle(size_vec, r, colors[i % len(colors)])

    elif _demo_state == 2:
        # Pattern 3: Filled circles in corners
        draw.fill_circle(Vector(80, 80), 60, TFT_RED)
        draw.fill_circle(Vector(240, 80), 60, TFT_GREEN)
        draw.fill_circle(Vector(80, 240), 60, TFT_BLUE)
        draw.fill_circle(Vector(240, 240), 60, TFT_YELLOW)
        draw.fill_circle(Vector(160, 160), 50, TFT_WHITE)

    elif _demo_state == 3:
        # Pattern 4: Nested rectangles
        rec_pos = Vector(20, 20)
        rec_size = Vector(280, 280)
        for i in range(6):
            rec_pos.x = 20 + i * 15
            rec_pos.y = 20 + i * 15
            rec_size.x = 280 - i * 30
            rec_size.y = 280 - i * 30
            draw.rect(rec_pos, rec_size, colors[i])

    elif _demo_state == 4:
        # Pattern 5: Overlapping filled rectangles
        draw.fill_rectangle(Vector(40, 40), Vector(120, 120), TFT_RED)
        draw.fill_rectangle(Vector(100, 100), Vector(120, 120), TFT_GREEN)
        draw.fill_rectangle(Vector(160, 160), Vector(120, 120), TFT_BLUE)

    elif _demo_state == 5:
        # Pattern 6: Triangles
        point_1 = Vector(160, 20)
        point_2 = Vector(40, 280)
        point_3 = Vector(280, 280)
        for i in range(6):
            offset = i * 25
            point_1.x = 160
            point_1.y = 20 + offset
            point_2.x = 40 + offset
            point_2.y = 280 - offset
            point_3.x = 280 - offset
            point_3.y = 280 - offset
            draw.triangle(
                point_1,
                point_2,
                point_3,
                colors[i],
            )

    elif _demo_state == 6:
        # Pattern 7: Checkerboard
        rec_size = Vector(18, 18)
        rec_pos = Vector(0, 0)
        for y in range(0, 320, 20):
            for x in range(0, 320, 20):
                rec_pos.x = x
                rec_pos.y = y
                if (x // 20 + y // 20) % 2 == 0:
                    draw.fill_rectangle(rec_pos, rec_size, TFT_RED)
                else:
                    draw.fill_rectangle(rec_pos, rec_size, TFT_BLUE)

    elif _demo_state == 7:
        # Pattern 8: Spiral of circles
        import math

        circ_pos = Vector(draw.size.x // 2, draw.size.y // 2)
        for i in range(60):
            angle = math.radians(i * 15)
            r = 10 + i * 2
            circ_pos.x = int(160 + r * math.cos(angle))
            circ_pos.y = int(160 + r * math.sin(angle))
            radius = 5 + i // 10
            draw.circle(circ_pos, radius, colors[i % len(colors)])

    elif _demo_state == 9:
        # Pattern 10: Starburst lines
        lin_pos = Vector(draw.size.x // 2, draw.size.y // 2)
        lin_size = Vector(0, 0)
        for i in range(0, 360, 5):
            import math

            angle = math.radians(i)
            lin_pos.x = int(160 + 50 * math.cos(angle))
            lin_pos.y = int(160 + 50 * math.sin(angle))
            lin_size.x = int(160 + 150 * math.cos(angle))
            lin_size.y = int(160 + 150 * math.sin(angle))
            draw.line_custom(lin_pos, lin_size, colors[i // 5 % len(colors)])

    elif _demo_state == 10:
        # Pattern 11: Diamond grid
        point_1 = Vector(0, 0)
        point_2 = Vector(0, 0)
        point_3 = Vector(0, 0)
        for y in range(0, draw.size.y, 40):
            for x in range(0, draw.size.x, 40):
                cx = x + 20
                cy = y + 20
                point_1.x = cx
                point_1.y = cy - 15
                point_2.x = cx - 15
                point_2.y = cy
                point_3.x = cx
                point_3.y = cy + 15
                draw.triangle(
                    point_1,
                    point_2,
                    point_3,
                    colors[(x // 40 + y // 40) % len(colors)],
                )
                point_1.x = cx
                point_1.y = cy - 15
                point_2.x = cx + 15
                point_2.y = cy
                point_3.x = cx
                point_3.y = cy + 15
                draw.triangle(
                    point_1,
                    point_2,
                    point_3,
                    colors[(x // 40 + y // 40) % len(colors)],
                )

    elif _demo_state == 11:
        # Pattern 12: Concentric squares
        rec_pos = Vector(0, 0)
        rec_size = Vector(0, 0)
        for i in range(15):
            size = 300 - i * 20
            offset = i * 10
            rec_pos.x = 10 + offset
            rec_pos.y = 10 + offset
            rec_size.x = size
            rec_size.y = size
            draw.rect(
                rec_pos,
                rec_size,
                colors[i % len(colors)],
            )


def run(view_manager) -> None:
    """Run the screensaver - auto-advance patterns."""
    global _demo_state, _frame_count
    from picoware.system.buttons import BUTTON_BACK, BUTTON_CENTER

    inp = view_manager.get_input_manager()
    draw = view_manager.get_draw()

    # Exit on any button press
    if inp.button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
    elif inp.button == BUTTON_CENTER:
        inp.reset()
        _demo_state = (_demo_state + 1) % 12
        _draw_pattern(draw)
        draw.swap()


def stop(view_manager) -> None:
    """Cleanup."""
    from gc import collect

    collect()
