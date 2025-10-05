# original from https://github.com/flashgordon77
# https://www.youtube.com/shorts/9l2e5ybXaVk

from micropython import const

# Petal layout
NUM_PETALS = const(12)
PETAL_LENGTH = const(40)  # how far it stretches outward
CX = const(160)
CY = const(160)

shift = 0


def __ellipse(display, cx, cy, xr, yr, color, fill=False, m=None):
    """
    Draw an ellipse at the given location. Radii xr and yr define the geometry; equal values cause a circle to be drawn.
    The color parameter defines the color.
    The optional fill parameter can be set to True to fill the ellipse. Otherwise just a one pixel outline is drawn.
    The optional m parameter enables drawing to be restricted to certain quadrants of the ellipse.
    The LS four bits determine which quadrants are to be drawn, with bit 0 specifying Q1, b1 Q2, b2 Q3 and b3 Q4.
    Quadrants are numbered counterclockwise with Q1 being top right.

    cx: x center
    cy: y center
    xr: x radius
    yr: y radius
    color: color
    fill: fill flag
    m: quadrants mask
    """
    from picoware.system.vector import Vector

    ELLIPSE_MASK_FILL = 0x10
    ELLIPSE_MASK_ALL = 0x0F
    ELLIPSE_MASK_Q1 = 0x01
    ELLIPSE_MASK_Q2 = 0x02
    ELLIPSE_MASK_Q3 = 0x04
    ELLIPSE_MASK_Q4 = 0x08

    def draw_ellipse_points(display, cx, cy, x_counter, y_counter, col, mask):
        if mask & ELLIPSE_MASK_FILL:
            if mask & ELLIPSE_MASK_Q1:
                display.fill_rectangle(
                    Vector(cx, cy - y_counter), Vector(x_counter + 1, 1), col
                )
            if mask & ELLIPSE_MASK_Q2:
                display.fill_rectangle(
                    Vector(cx - x_counter, cy - y_counter),
                    Vector(x_counter + 1, 1),
                    col,
                )
            if mask & ELLIPSE_MASK_Q3:
                display.fill_rectangle(
                    Vector(cx - x_counter, cy + y_counter),
                    Vector(x_counter + 1, 1),
                    col,
                )
            if mask & ELLIPSE_MASK_Q4:
                display.fill_rectangle(
                    Vector(cx, cy + y_counter), Vector(x_counter + 1, 1), col
                )
        else:
            if mask & ELLIPSE_MASK_Q1:
                display.pixel(Vector(cx + x_counter, cy - y_counter), col)
            if mask & ELLIPSE_MASK_Q2:
                display.pixel(Vector(cx - x_counter, cy - y_counter), col)
            if mask & ELLIPSE_MASK_Q3:
                display.pixel(Vector(cx - x_counter, cy + y_counter), col)
            if mask & ELLIPSE_MASK_Q4:
                display.pixel(Vector(cx + x_counter, cy + y_counter), col)

    mask = ELLIPSE_MASK_FILL if fill else 0
    if m is not None:
        mask |= m & ELLIPSE_MASK_ALL
    else:
        mask |= ELLIPSE_MASK_ALL

    if xr == 0 and yr == 0:
        if mask & ELLIPSE_MASK_ALL:
            display.pixel(Vector(cx, cy), color)
        return

    two_asquare = 2 * xr * xr
    two_bsquare = 2 * yr * yr
    x_counter = xr
    y_counter = 0
    xchange = yr * yr * (1 - 2 * xr)
    ychange = xr * xr
    ellipse_error = 0
    stoppingx = two_bsquare * xr
    stoppingy = 0

    while stoppingx >= stoppingy:  # 1st set of points,  y' > -1
        draw_ellipse_points(display, cx, cy, x_counter, y_counter, color, mask)
        y_counter += 1
        stoppingy += two_asquare
        ellipse_error += ychange
        ychange += two_asquare
        if (2 * ellipse_error + xchange) > 0:
            x_counter -= 1
            stoppingx -= two_bsquare
            ellipse_error += xchange
            xchange += two_bsquare
    # 1st point set is done start the 2nd set of points
    x_counter = 0
    y_counter = yr
    xchange = yr * yr
    ychange = xr * xr * (1 - 2 * yr)
    ellipse_error = 0
    stoppingx = 0
    stoppingy = two_asquare * yr
    while stoppingx <= stoppingy:  # // 2nd set of points, y' < -1
        draw_ellipse_points(display, cx, cy, x_counter, y_counter, color, mask)
        x_counter += 1
        stoppingx += two_bsquare
        ellipse_error += xchange
        xchange += two_bsquare
        if (2 * ellipse_error + ychange) > 0:
            y_counter -= 1
            stoppingy -= two_asquare
            ellipse_error += ychange
            ychange += two_asquare


def start(view_manager) -> bool:
    """Start the app"""
    # nothing to do here..
    return True


def run(view_manager) -> None:
    """Run the app"""
    from math import pi, cos, sin
    from picoware.system.buttons import BUTTON_LEFT, BUTTON_BACK
    from picoware.system.colors import (
        TFT_BLACK,
        TFT_RED,
        TFT_GREEN,
        TFT_BLUE,
        TFT_YELLOW,
        TFT_CYAN,
        TFT_VIOLET,
        TFT_ORANGE,
        TFT_PINK,
        TFT_DARKGREEN,
        TFT_DARKCYAN,
        TFT_BROWN,
        TFT_SKYBLUE,
    )

    input_manager = view_manager.get_input_manager()
    input_button = input_manager.get_last_button()

    if input_button in (BUTTON_LEFT, BUTTON_BACK):
        view_manager.back()
        input_manager.reset(True)
        return

    global shift

    draw = view_manager.get_draw()

    draw.fill_screen(TFT_BLACK)

    # Draw center (yellow)
    __ellipse(draw, CX, CY, 32, 32, TFT_YELLOW, True)

    for i in range(NUM_PETALS):
        angle = i * (2 * pi / NUM_PETALS)
        px = int(CX + 100 * cos(angle))
        py = int(CY + 100 * sin(angle))
        petal_colors = [
            TFT_RED,
            TFT_GREEN,
            TFT_BLUE,
            TFT_YELLOW,
            TFT_CYAN,
            TFT_VIOLET,
            TFT_ORANGE,
            TFT_PINK,
            TFT_DARKGREEN,
            TFT_DARKCYAN,
            TFT_BROWN,
            TFT_SKYBLUE,
            TFT_RED,
            TFT_GREEN,
        ]
        color = petal_colors[(i + shift) % len(petal_colors)]

        # Draw filled circle for the petal
        __ellipse(draw, px, py, PETAL_LENGTH, PETAL_LENGTH, color, True)

    draw.swap()

    shift = (shift + 1) % len(petal_colors)


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    collect()
