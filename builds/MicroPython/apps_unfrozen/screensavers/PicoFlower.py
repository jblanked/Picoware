# original from https://github.com/flashgordon77
# https://www.youtube.com/shorts/9l2e5ybXaVk

from micropython import const

# Petal layout
NUM_PETALS = const(12)
CX = 0
CY = 0

shift = 0
petal_length = 0
rec_pos = None
rec_size = None
pixel_pos = None


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

    ELLIPSE_MASK_FILL = 0x10
    ELLIPSE_MASK_ALL = 0x0F
    ELLIPSE_MASK_Q1 = 0x01
    ELLIPSE_MASK_Q2 = 0x02
    ELLIPSE_MASK_Q3 = 0x04
    ELLIPSE_MASK_Q4 = 0x08

    def draw_ellipse_points(display, cx, cy, x_counter, y_counter, col, mask):
        if mask & ELLIPSE_MASK_FILL:
            if mask & ELLIPSE_MASK_Q1:
                rec_pos.x = cx
                rec_pos.y = cy - y_counter
                rec_size.x = x_counter + 1
                rec_size.y = 1
                display.fill_rectangle(rec_pos, rec_size, col)

            if mask & ELLIPSE_MASK_Q2:
                rec_pos.x = cx - x_counter
                rec_pos.y = cy - y_counter
                rec_size.x = x_counter + 1
                rec_size.y = 1
                display.fill_rectangle(rec_pos, rec_size, col)

            if mask & ELLIPSE_MASK_Q3:
                rec_pos.x = cx - x_counter
                rec_pos.y = cy + y_counter
                rec_size.x = x_counter + 1
                rec_size.y = 1
                display.fill_rectangle(rec_pos, rec_size, col)

            if mask & ELLIPSE_MASK_Q4:
                rec_pos.x = cx
                rec_pos.y = cy + y_counter
                rec_size.x = x_counter + 1
                rec_size.y = 1
                display.fill_rectangle(rec_pos, rec_size, col)
        else:
            if mask & ELLIPSE_MASK_Q1:
                pixel_pos.x = cx + x_counter
                pixel_pos.y = cy - y_counter
                display.pixel(pixel_pos, col)
            if mask & ELLIPSE_MASK_Q2:
                pixel_pos.x = cx - x_counter
                pixel_pos.y = cy - y_counter
                display.pixel(pixel_pos, col)
            if mask & ELLIPSE_MASK_Q3:
                pixel_pos.x = cx - x_counter
                pixel_pos.y = cy + y_counter
                display.pixel(pixel_pos, col)
            if mask & ELLIPSE_MASK_Q4:
                pixel_pos.x = cx + x_counter
                pixel_pos.y = cy + y_counter
                display.pixel(pixel_pos, col)

    mask = ELLIPSE_MASK_FILL if fill else 0
    if m is not None:
        mask |= m & ELLIPSE_MASK_ALL
    else:
        mask |= ELLIPSE_MASK_ALL

    if xr == 0 and yr == 0:
        if mask & ELLIPSE_MASK_ALL:
            pixel_pos.x = cx
            pixel_pos.y = cy
            display.pixel(pixel_pos, color)
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
    global CX, CY
    draw = view_manager.draw
    CX = draw.size.x // 2
    CY = draw.size.y // 2

    global rec_pos, rec_size, pixel_pos, petal_length
    from picoware.system.vector import Vector

    rec_pos = Vector(0, 0)
    rec_size = Vector(0, 0)
    pixel_pos = Vector(0, 0)
    petal_length = min(draw.size.x, draw.size.y) // 8
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

    input_manager = view_manager.input_manager
    input_button = input_manager.button

    if input_button in (BUTTON_LEFT, BUTTON_BACK):
        input_manager.reset()
        view_manager.back()
        return

    global shift

    draw = view_manager.draw

    draw.fill_screen(TFT_BLACK)

    # Draw center (yellow)
    __ellipse(draw, CX, CY, 32, 32, TFT_YELLOW, True)

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

    for i in range(NUM_PETALS):
        angle = i * (2 * pi / NUM_PETALS)
        px = int(CX + 100 * cos(angle))
        py = int(CY + 100 * sin(angle))
        color = petal_colors[(i + shift) % len(petal_colors)]

        # Draw filled circle for the petal
        __ellipse(draw, px, py, petal_length, petal_length, color, True)

    draw.swap()

    shift = (shift + 1) % len(petal_colors)


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global rec_pos, rec_size, pixel_pos, shift, petal_length
    shift = 0
    petal_length = 0
    if rec_pos is not None:
        del rec_pos
        rec_pos = None
    if rec_size is not None:
        del rec_size
        rec_size = None
    if pixel_pos is not None:
        del pixel_pos
        pixel_pos = None
    collect()
