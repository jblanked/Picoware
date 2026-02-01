# Animated plasma wave effect screensaver
from math import sin
from picoware.system.buttons import BUTTON_BACK
from picoware.system.colors import TFT_BLACK
from picoware.system.vector import Vector

screen_size = None
time_offset = 0
sample_rate = 8
size = None
pos = None


def plasma_color(value: float) -> int:
    """Convert plasma value (-1 to 1) to RGB565 color"""
    # Map value to 0-255
    val = int((value + 1.0) * 127.5)

    # Create a rainbow effect
    if val < 85:
        r = val * 3
        g = 255 - val * 3
        b = 0
    elif val < 170:
        val -= 85
        r = 255 - val * 3
        g = 0
        b = val * 3
    else:
        val -= 170
        r = 0
        g = val * 3
        b = 255 - val * 3

    # Convert to RGB565
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def start(view_manager) -> bool:
    """Start the app"""
    global screen_size, time_offset, size, pos

    draw = view_manager.draw
    screen_size = Vector(draw.size.x, draw.size.y)
    time_offset = 0
    size = Vector(sample_rate, sample_rate)
    pos = Vector(0, 0)

    draw.fill_screen(TFT_BLACK)
    draw.swap()

    return True


def run(view_manager) -> None:
    """Run the app"""
    global time_offset, pos

    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
        return

    draw = view_manager.draw

    # Draw plasma effect
    time_offset += 0.05
    cx = screen_size.x / 2
    cy = screen_size.y / 2

    for y in range(0, screen_size.y, sample_rate):
        for x in range(0, screen_size.x, sample_rate):
            # Calculate plasma value using multiple sine waves
            dx = x - cx
            dy = y - cy
            dist = (dx * dx + dy * dy) ** 0.5

            value = sin(dist * 0.05 + time_offset)
            value += sin(x * 0.03 + time_offset * 1.5)
            value += sin(y * 0.02 - time_offset * 2)
            value += sin((x + y) * 0.025 + time_offset)
            value /= 4.0

            color = plasma_color(value)

            pos.x, pos.y = x, y
            draw.fill_rectangle(pos, size, color)

    draw.swap()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global screen_size, time_offset, size, pos

    screen_size = None
    time_offset = 0
    size = None
    pos = None

    collect()
