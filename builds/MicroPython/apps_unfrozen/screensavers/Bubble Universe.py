# originally from https://github.com/movievertigo/Adafruit-DVI-HSTX-BubbleUniverse/blob/main/BubbleUniverse.ino
# original algorithm from https://x.com/yuruyurau/status/1226846058728177665
# translated directly from https://github.com/pelrun/picocalc-bubbleuniverse/blob/main/main.c

from micropython import const
from utime import ticks_ms
from array import array
from picoware.system.vector import Vector
from picoware.system.colors import TFT_WHITE, TFT_BLACK
from picoware.system.buttons import (
    BUTTON_HOME,
    BUTTON_UP,
    BUTTON_DOWN,
    BUTTON_LEFT,
    BUTTON_RIGHT,
    BUTTON_MINUS,
    BUTTON_EQUAL,
    BUTTON_DELETE,
    BUTTON_SPACE,
    BUTTON_ESCAPE,
    BUTTON_CENTER,
    BUTTON_BACK,
)

CURVECOUNT = const(256)
CURVESTEP = const(16)
ITERATIONS = const(64)
SCREENWIDTH = 0
SCREENHEIGHT = 0

PI = const(3.1415926535897932384626433832795)
SINTABLEPOWER = const(12)
SINTABLEENTRIES = const(1 << SINTABLEPOWER)
ANG1INC = const((CURVESTEP * SINTABLEENTRIES) // 235)
ANG2INC = (CURVESTEP * SINTABLEENTRIES) // int(2 * PI)
SCALEMUL = 0

SCALESPEED = const(1.04)
MOVESPEED = const(2.0)
ANIMSPEEDCHANGE = const(0.02)

speed: float = 0.0
old_speed: float = 0.0
size: float = 0.0
x_offset: int = 0
y_offset: int = 0
animation_time: int = 0

sin_table = None
cos_table = None
palette = None

old_time: int = 0
fps: str = ""

pixel_vec = None

screen_center_x = 0
screen_center_y = 0


def __reset_values() -> None:
    """Reset global values"""
    global speed, old_speed, size, x_offset, y_offset, pixel_vec
    speed = 0.2
    old_speed = 0.0
    size = 1.0
    x_offset = 0
    y_offset = 0


def __create_sin_table() -> None:
    """Create separate sine and cosine tables for performance"""
    from math import sin

    global sin_table, cos_table, palette

    sin_table = array("h", (0 for _ in range(SINTABLEENTRIES)))
    cos_table = array("h", (0 for _ in range(SINTABLEENTRIES)))

    for i in range(SINTABLEENTRIES):
        sin_val = int(sin(i * 2 * PI / SINTABLEENTRIES) * SINTABLEENTRIES / (2 * PI))
        cos_val = int(
            sin((i + SINTABLEENTRIES // 4) * 2 * PI / SINTABLEENTRIES)
            * SINTABLEENTRIES
            / (2 * PI)
        )
        sin_table[i] = sin_val
        cos_table[i] = cos_val

    palette = array("H", (0 for _ in range(64 * 64)))
    for i in range(0, CURVECOUNT, CURVESTEP):
        curve = i >> 2
        for j in range(ITERATIONS):
            palette[curve * 64 + j] = __calculate_color(i, j)


def __poll_keyboard(button: int) -> None:
    """Poll the keyboard for input"""
    if button == -1:
        return

    global speed, old_speed, size, x_offset, y_offset

    if button in (BUTTON_HOME, BUTTON_ESCAPE):
        __reset_values()

    if button == BUTTON_MINUS:
        speed -= ANIMSPEEDCHANGE / size
    if button == BUTTON_EQUAL:
        speed += ANIMSPEEDCHANGE / size

    if button == BUTTON_CENTER:
        size *= SCALESPEED
        x_offset = int(x_offset * SCALESPEED)
        y_offset = int(y_offset * SCALESPEED)

    if button == BUTTON_DELETE:
        size /= SCALESPEED
        x_offset = int(x_offset / SCALESPEED)
        y_offset = int(y_offset / SCALESPEED)

    if button == BUTTON_SPACE:
        temp = speed
        speed = old_speed
        old_speed = temp

    if button == BUTTON_LEFT:
        x_offset += int(MOVESPEED)
    if button == BUTTON_RIGHT:
        x_offset -= int(MOVESPEED)
    if button == BUTTON_UP:
        y_offset += int(MOVESPEED)
    if button == BUTTON_DOWN:
        y_offset -= int(MOVESPEED)


def __calculate_color(curve_index: int, iteration: int) -> int:
    """Calculate RGB565 color for a given curve and iteration"""

    i = curve_index >> 1  # Divide by 2
    red_level = (i >> 4) & 0x07  # Extract bits 4-6 for red (0-7)
    green_level = iteration >> 2  # Use top 4 bits of iteration for green (0-15)

    # Calculate RGB values
    red = (255 * red_level) // 7
    green = (255 * green_level) // 15
    blue = (510 - (red + green)) >> 1

    # Convert to RGB565
    return ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)


def __render(draw) -> None:
    """Render the bubble universe"""

    global animation_time, size, x_offset, y_offset, sin_table, cos_table

    ang1_start = int(animation_time)
    ang2_start = int(animation_time)

    for i in range(0, CURVECOUNT, CURVESTEP):
        x = 0
        y = 0
        for j in range(ITERATIONS):
            idx1 = (ang1_start + x) & (SINTABLEENTRIES - 1)
            idx2 = (ang2_start + y) & (SINTABLEENTRIES - 1)

            sin1 = sin_table[idx1]
            cos1 = cos_table[idx1]
            sin2 = sin_table[idx2]
            cos2 = cos_table[idx2]

            # Calculate new x and y
            x = sin1 + sin2
            y = cos1 + cos2

            # Calculate pixel position
            pX = int((x * SCALEMUL * size) / (1 << SINTABLEPOWER)) + x_offset
            pY = int((y * SCALEMUL * size) / (1 << SINTABLEPOWER)) + y_offset

            # Check bounds and draw pixel
            if abs(pX) < SCREENWIDTH // 2 and abs(pY) < SCREENHEIGHT // 2:
                screen_x = screen_center_x + pX
                screen_y = screen_center_y + pY

                # Calculate color directly
                color = palette[(i >> 2) * 64 + j]

                pixel_vec.x = screen_x
                pixel_vec.y = screen_y
                draw.pixel(pixel_vec, color)

        ang1_start += ANG1INC
        ang2_start += ANG2INC


def start(view_manager) -> bool:
    """Start the app"""

    draw = view_manager.draw
    draw.fill_screen(TFT_BLACK)
    draw.text(Vector(10, 10), "Bubble Universe by Movie Vertigo", TFT_WHITE)
    draw.swap()

    global old_time, SCREENWIDTH, SCREENHEIGHT, SCALEMUL, pixel_vec, screen_center_x, screen_center_y

    pixel_vec = Vector(0, 0)

    SCREENWIDTH = draw.size.x
    SCREENHEIGHT = draw.size.y
    SCALEMUL = int(SCREENHEIGHT * PI / 2)

    # Calculate screen center
    screen_center_x = SCREENWIDTH // 2
    screen_center_y = SCREENHEIGHT // 2

    __create_sin_table()
    __reset_values()
    old_time = ticks_ms()

    return True


def run(view_manager) -> None:
    """Run the app"""
    input_manager = view_manager.input_manager
    input_button = input_manager.button

    if input_button == BUTTON_BACK:
        view_manager.back()
        input_manager.reset()
        return

    global animation_time, old_time

    time = ticks_ms()
    delta_time = time - old_time
    animation_time += delta_time * speed
    old_time = time

    draw = view_manager.draw

    draw.fill_screen(TFT_BLACK)

    __render(draw)

    __poll_keyboard(input_button)

    draw.swap()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global sin_table, cos_table, palette, pixel_vec, screen_center_x, screen_center_y
    sin_table = None
    cos_table = None
    palette = None
    pixel_vec = None
    screen_center_x = 0
    screen_center_y = 0
    __reset_values()

    collect()
