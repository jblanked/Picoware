# Original from https://github.com/Bodmer/TFT_eSPI/blob/master/examples/480%20x%20320/Demo_3D_cube/Demo_3D_cube.ino

# Global variables for 3D transformation
inc = -2

xx = 0.0
xy = 0.0
xz = 0.0
yx = 0.0
yy = 0.0
yz = 0.0
zx = 0.0
zy = 0.0
zz = 0.0

fact = 0.0

Xan = 0
Yan = 0

Xoff = 0
Yoff = 0
Zoff = 0

line_1 = None
line_2 = None

# Define the 12 lines of the cube
# Each line has two 3D points (x, y, z)
LINES = [
    # Front Face
    ((-50, -50, 50), (50, -50, 50)),
    ((50, -50, 50), (50, 50, 50)),
    ((50, 50, 50), (-50, 50, 50)),
    ((-50, 50, 50), (-50, -50, 50)),
    # Back Face
    ((-50, -50, -50), (50, -50, -50)),
    ((50, -50, -50), (50, 50, -50)),
    ((50, 50, -50), (-50, 50, -50)),
    ((-50, 50, -50), (-50, -50, -50)),
    # Edge Lines
    ((-50, -50, 50), (-50, -50, -50)),
    ((50, -50, 50), (50, -50, -50)),
    ((-50, 50, 50), (-50, 50, -50)),
    ((50, 50, 50), (50, 50, -50)),
]


def set_vars():
    """Sets the global vars for the 3d transform"""
    from math import sin, cos

    global xx, xy, xz, yx, yy, yz, zx, zy, zz, fact, Xan, Yan

    Xan2 = Xan / fact  # convert degrees to radians
    Yan2 = Yan / fact

    # Zan is assumed to be zero
    s1 = sin(Yan2)
    s2 = sin(Xan2)

    c1 = cos(Yan2)
    c2 = cos(Xan2)

    xx = c1
    xy = 0
    xz = -s1

    yx = s1 * s2
    yy = c2
    yz = c1 * s2

    zx = s1 * c2
    zy = -s2
    zz = c1 * c2


def render_image(tft):
    """Render the 3D cube"""
    from picoware.system.colors import (
        TFT_BLACK,
        TFT_BLUE,
        TFT_RED,
        TFT_DARKGREEN,
    )

    global xx, xy, xz, yx, yy, yz, zx, zy, zz, Xoff, Yoff, Zoff

    tft.fill_screen(TFT_BLACK)  # clear the screen before drawing the new lines

    # Process all lines and convert 3D to 2D
    for i, line in enumerate(LINES):
        p0, p1 = line
        x1, y1, z1 = p0
        x2, y2, z2 = p1

        Ok = 0  # defaults to not OK

        # Transform first point
        xv1 = (x1 * xx) + (y1 * xy) + (z1 * xz)
        yv1 = (x1 * yx) + (y1 * yy) + (z1 * yz)
        zv1 = (x1 * zx) + (y1 * zy) + (z1 * zz)

        zvt1 = zv1 - Zoff

        if zvt1 < -5:
            rx1 = int(256 * (xv1 / zvt1) + Xoff)
            ry1 = int(256 * (yv1 / zvt1) + Yoff)
            Ok = 1  # ok we are alright for point 1

        # Transform second point
        xv2 = (x2 * xx) + (y2 * xy) + (z2 * xz)
        yv2 = (x2 * yx) + (y2 * yy) + (z2 * yz)
        zv2 = (x2 * zx) + (y2 * zy) + (z2 * zz)

        zvt2 = zv2 - Zoff

        if zvt2 < -5:
            rx2 = int(256 * (xv2 / zvt2) + Xoff)
            ry2 = int(256 * (yv2 / zvt2) + Yoff)
        else:
            Ok = 0

        if Ok == 1:
            # Choose color based on line index
            if i < 4:
                color = TFT_RED  # Front face (red/cyan)
            elif i > 7:
                color = TFT_DARKGREEN  # Edge lines (dark green)
            else:
                color = TFT_BLUE  # Back face (blue)
            line_1.x = rx1
            line_1.y = ry1
            line_2.x = rx2
            line_2.y = ry2
            tft.line_custom(line_1, line_2, color)

    tft.swap()  # swap the buffers to show the new lines


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.system.colors import TFT_BLACK
    from picoware.system.vector import Vector

    global fact, Xoff, Yoff, Zoff, Xan, Yan, line_1, line_2

    draw = view_manager.draw
    draw.fill_screen(TFT_BLACK)
    draw.swap()

    fact = 180 / 3.14159259  # conversion from degrees to radians

    Xoff = (
        draw.size.x // 2
    )  # Position the centre of the 3d conversion space into the centre of the TFT screen
    Yoff = draw.size.y // 2
    Zoff = 550  # Z offset in 3D space (smaller = closer and bigger rendering)

    Xan = 0
    Yan = 0

    line_1 = Vector(0, 0)
    line_2 = Vector(0, 0)

    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_LEFT, BUTTON_BACK

    global Xan, Yan, Zoff, inc

    input_manager = view_manager.input_manager
    input_button = input_manager.button
    draw = view_manager.draw
    if input_button in (BUTTON_LEFT, BUTTON_BACK):
        view_manager.back()
        input_manager.reset()
        return

    # Rotate around x and y axes in 1 degree increments
    Xan += 1
    Yan += 1

    Yan = Yan % 360
    Xan = Xan % 360  # prevents overflow

    set_vars()  # sets up the global vars to do the 3D conversion

    # Zoom in and out on Z axis within limits
    # the cube intersects with the screen for values < 160
    Zoff += inc
    if Zoff > 500:
        inc = -1  # Switch to zoom in
    elif Zoff < draw.size.x:
        inc = 1  # Switch to zoom out

    render_image(draw)  # go draw it!


def stop(view_manager) -> None:
    """Stop the app"""
    from picoware.system.colors import TFT_BLACK
    from gc import collect

    global inc, xx, xy, xz, yx, yy, yz, zx, zy, zz, fact, Xan, Yan, Xoff, Yoff, Zoff, line_1, line_2

    inc = -2

    xx = 0.0
    xy = 0.0
    xz = 0.0
    yx = 0.0
    yy = 0.0
    yz = 0.0
    zx = 0.0
    zy = 0.0
    zz = 0.0

    fact = 0.0
    Xan = 0
    Yan = 0
    Xoff = 0
    Yoff = 0
    Zoff = 0

    line_1 = None
    line_2 = None

    draw = view_manager.draw
    draw.fill_screen(TFT_BLACK)
    draw.swap()

    collect()
