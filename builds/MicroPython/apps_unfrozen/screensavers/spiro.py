# Original from https://github.com/Bodmer/TFT_eSPI/blob/master/examples/320%20x%20240/TFT_Spiro/TFT_Spiro.ino
from micropython import const
from math import cos, sin
from random import randint
from picoware.system.buttons import BUTTON_LEFT, BUTTON_BACK
from picoware.system.colors import TFT_BLACK
from picoware.system.vector import Vector

DEG2RAD = const(0.0174532925)  # Convert angles in degrees to radians
sp_sx = 0.0
sp_sy = 0.0
x0 = 0
x1 = 0
yy0 = 0
yy1 = 0
spiro_elapsed = 10
vec1 = None
vec2 = None


def rainbow(value: int) -> int:
    """
    Convert a value (0-127) to a spectrum color from blue through to red.
    Returns a 16-bit color value.
    """
    # Value is expected to be in range 0-127
    # The value is converted to a spectrum colour from 0 = blue through to red = blue
    red = 0  # Red is the top 5 bits of a 16-bit colour value
    green = 0  # Green is the middle 6 bits
    blue = 0  # Blue is the bottom 5 bits

    quadrant = value // 32

    if quadrant == 0:
        blue = 31
        green = 2 * (value % 32)
        red = 0
    elif quadrant == 1:
        blue = 31 - (value % 32)
        green = 63
        red = 0
    elif quadrant == 2:
        blue = 0
        green = 63
        red = value % 32
    elif quadrant == 3:
        blue = 0
        green = 63 - 2 * (value % 32)
        red = 31

    return (red << 11) + (green << 5) + blue


def random_range(min_val: int, max_val: int) -> int:
    """Generate a random number in the range [min_val, max_val)"""
    if max_val <= min_val:
        return min_val
    return min_val + randint(0, max_val - min_val - 1)


def map_value(x: int, in_min: int, in_max: int, out_min: int, out_max: int) -> int:
    """Map a value from one range to another"""
    if in_max == in_min:
        return out_min
    return (x - in_min) * (out_max - out_min) // (in_max - in_min) + out_min


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.system.colors import TFT_BLACK

    global vec1, vec2
    vec1 = Vector(0, 0)
    vec2 = Vector(0, 0)
    draw = view_manager.draw
    draw.fill_screen(TFT_BLACK)
    draw.swap()
    return True


def run(view_manager) -> None:
    """Run the app"""
    global spiro_elapsed, sp_sx, sp_sy, x0, x1, yy0, yy1

    input_button = view_manager.input_manager.button

    if input_button in (BUTTON_LEFT, BUTTON_BACK):
        view_manager.back()
        spiro_elapsed = 0
        view_manager.input_manager.reset()
        return

    if spiro_elapsed > 10:
        spiro_elapsed = 0
        tft = view_manager.draw

        tft.fill_screen(TFT_BLACK)
        n = random_range(2, 23)
        r = random_range(20, 100)

        # First spirograph pattern
        vec_1 = vec1
        for i in range(360 * n):
            sp_sx = cos((i / n - 90) * DEG2RAD)
            sp_sy = sin((i / n - 90) * DEG2RAD)
            x0 = int(sp_sx * (120 - r) + 159)
            yy0 = int(sp_sy * (120 - r) + 119)

            sp_sy = cos(((i % 360) - 90) * DEG2RAD)
            sp_sx = sin(((i % 360) - 90) * DEG2RAD)
            x1 = int(sp_sx * r + x0)
            yy1 = int(sp_sy * r + yy0)

            color = rainbow(map_value(i % 360, 0, 360, 0, 127))
            vec_1.x = x1
            vec_1.y = yy1
            tft.pixel(vec_1, color)

        # Second spirograph pattern with different radius
        r = random_range(20, 100)
        vec_2 = vec2
        for i in range(360 * n):
            sp_sx = cos((i / n - 90) * DEG2RAD)
            sp_sy = sin((i / n - 90) * DEG2RAD)
            x0 = int(sp_sx * (120 - r) + 159)
            yy0 = int(sp_sy * (120 - r) + 119)

            sp_sy = cos(((i % 360) - 90) * DEG2RAD)
            sp_sx = sin(((i % 360) - 90) * DEG2RAD)
            x1 = int(sp_sx * r + x0)
            yy1 = int(sp_sy * r + yy0)

            color = rainbow(map_value(i % 360, 0, 360, 0, 127))
            vec_2.x = x1
            vec_2.y = yy1
            tft.pixel(vec_2, color)

        tft.swap()

    spiro_elapsed += 1


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    draw = view_manager.draw
    draw.fill_screen(view_manager.background_color)
    draw.swap()

    global sp_sx, sp_sy, x0, x1, yy0, yy1, spiro_elapsed, vec1, vec2

    sp_sx = 0.0
    sp_sy = 0.0
    x0 = 0
    x1 = 0
    yy0 = 0
    yy1 = 0
    spiro_elapsed = 10
    vec1 = None
    vec2 = None

    collect()
