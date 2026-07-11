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

# Scale factor and derived values (set in start())
scale = 1.0
cube_size = 50
focal = 256

# Generated in start()
LINES = []


def _make_lines(s):
    """Generate the 12 lines of a cube with given half-size s"""
    return [
        # Front Face
        ((-s, -s, s), (s, -s, s)),
        ((s, -s, s), (s, s, s)),
        ((s, s, s), (-s, s, s)),
        ((-s, s, s), (-s, -s, s)),
        # Back Face
        ((-s, -s, -s), (s, -s, -s)),
        ((s, -s, -s), (s, s, -s)),
        ((s, s, -s), (-s, s, -s)),
        ((-s, s, -s), (-s, -s, -s)),
        # Edge Lines
        ((-s, -s, s), (-s, -s, -s)),
        ((s, -s, s), (s, -s, -s)),
        ((-s, s, s), (-s, s, -s)),
        ((s, s, s), (s, s, -s)),
    ]


def set_vars():
    """Sets the global vars for the 3d transform"""
    from math import sin, cos

    global xx, xy, xz, yx, yy, yz, zx, zy, zz, fact, Xan, Yan

    Xan2 = Xan / fact  # Degrees to radians
    Yan2 = Yan / fact

    # Zan is zero
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

    global focal

    tft.fill_screen(TFT_BLACK)  # Clear screen

    # Convert 3D to 2D
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
            rx1 = int(focal * (xv1 / zvt1) + Xoff)
            ry1 = int(focal * (yv1 / zvt1) + Yoff)
            Ok = 1  # Point 1 valid

        # Transform second point
        xv2 = (x2 * xx) + (y2 * xy) + (z2 * xz)
        yv2 = (x2 * yx) + (y2 * yy) + (z2 * yz)
        zv2 = (x2 * zx) + (y2 * zy) + (z2 * zz)

        zvt2 = zv2 - Zoff

        if zvt2 < -5:
            rx2 = int(focal * (xv2 / zvt2) + Xoff)
            ry2 = int(focal * (yv2 / zvt2) + Yoff)
        else:
            Ok = 0

        if Ok == 1:
            # Color by line index
            if i < 4:
                color = TFT_RED  # Front face (red/cyan)
            elif i > 7:
                color = TFT_DARKGREEN  # Edge lines (dark green)
            else:
                color = TFT_BLUE  # Back face (blue)
            tft._line(rx1, ry1, rx2, ry2, color)

    tft.swap()  # Swap buffers


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.system.colors import TFT_BLACK

    global fact, Xoff, Yoff, Zoff, Xan, Yan, scale, cube_size, focal, LINES

    draw = view_manager.draw
    draw.fill_screen(TFT_BLACK)
    draw.swap()

    fact = 180 / 3.14159259  # Degrees to radians

    # Scale relative to 320px base
    screen_min = min(draw.size.x, draw.size.y)
    scale = screen_min / 320
    cube_size = max(int(50 * scale), 15)
    focal = max(int(256 * scale), 80)
    LINES = _make_lines(cube_size)

    Xoff = (
        draw.size.x // 2
    )  # Center of 3D space on screen
    Yoff = draw.size.y // 2
    Zoff = int(550 * scale)  # Z offset (closer = bigger)

    Xan = 0
    Yan = 0

    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_LEFT, BUTTON_BACK

    global Xan, Yan, Zoff, inc, scale

    input_manager = view_manager.input_manager
    input_button = input_manager.button
    draw = view_manager.draw
    if input_button in (BUTTON_LEFT, BUTTON_BACK):
        view_manager.back()
        input_manager.reset()
        return

    # Rotate 1 degree per frame
    Xan += 1
    Yan += 1

    Yan = Yan % 360
    Xan = Xan % 360  # Prevents overflow

    set_vars()  # Update transform vars

    # Zoom in/out on Z axis
    # Min Zoff = smaller screen dim
    zoff_min = max(min(draw.size.x, draw.size.y), 80)
    zoff_max = max(int(500 * scale), 150)
    Zoff += inc
    if Zoff > zoff_max:
        inc = -1  # Switch to zoom in
    elif Zoff < zoff_min:
        inc = 1  # Switch to zoom out

    render_image(draw)  # Render


def stop(view_manager) -> None:
    """Stop the app"""
    from picoware.system.colors import TFT_BLACK
    from gc import collect

    global inc, xx, xy, xz, yx, yy, yz, zx, zy, zz, fact, Xan, Yan, Xoff, Yoff, Zoff
    global scale, cube_size, focal, LINES

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

    scale = 1.0
    cube_size = 50
    focal = 256
    LINES = []

    draw = view_manager.draw
    draw.fill_screen(TFT_BLACK)
    draw.swap()

    collect()
