# Fire effect screensaver with rising flames
from random import randint
from picoware.system.buttons import BUTTON_BACK
from picoware.system.colors import TFT_BLACK
from picoware.system.vector import Vector

screen_size = None
fire_buffer = []
fire_palette = []
width = 0
height = 0
pos = None
size = None
pixel_w = 0
pixel_h = 0


def start(view_manager) -> bool:
    """Start the app"""
    global screen_size, fire_buffer, fire_palette, width, height, pos, size, pixel_w, pixel_h

    draw = view_manager.draw
    screen_size = Vector(draw.size.x, draw.size.y)

    width = screen_size.x // 4
    height = screen_size.y // 4

    # Pre-calculate fire color palette (0-255)
    fire_palette = []
    for value in range(256):
        if value < 85:
            # Black to red
            r = value * 3
            g = 0
            b = 0
        elif value < 170:
            # Red to yellow
            r = 255
            g = (value - 85) * 3
            b = 0
        else:
            # Yellow to white
            r = 255
            g = 255
            b = (value - 170) * 3
        # Convert to RGB565
        fire_palette.append(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3))

    # Initialize fire buffer
    fire_buffer = [[0 for _ in range(width)] for _ in range(height)]

    pixel_w = screen_size.x // width
    pixel_h = screen_size.y // height

    pos = Vector(0, 0)
    size = Vector(pixel_w, pixel_h)

    draw.fill_screen(TFT_BLACK)
    draw.swap()

    return True


def run(view_manager) -> None:
    """Run the app"""
    global fire_buffer

    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
        return

    draw = view_manager.draw

    # Generate fire at the bottom row
    bottom_row = fire_buffer[height - 1]
    for x in range(width):
        bottom_row[x] = randint(200, 255)

    # Propagate fire upward with cooling
    for y in range(height - 1):
        curr_row = fire_buffer[y]
        next_row = fire_buffer[y + 1]

        for x in range(width):
            # Average neighboring pixels with cooling factor
            total = next_row[x]
            count = 1

            # Check below-left
            if x > 0:
                total += next_row[x - 1]
                count += 1

            # Check below-right
            if x < width - 1:
                total += next_row[x + 1]
                count += 1

            avg = total // count
            # Cool down the fire as it rises
            cooling = randint(0, 10)
            curr_row[x] = max(0, avg - cooling)

    # Draw fire buffer to screen
    draw.fill_screen(TFT_BLACK)

    for y in range(height):
        row = fire_buffer[y]
        y_pos = y * pixel_h
        for x in range(width):
            value = row[x]
            if value > 0:
                color = fire_palette[value]
                pos.x = x * pixel_w
                pos.y = y_pos
                draw.fill_rectangle(pos, size, color)

    draw.swap()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global screen_size, fire_buffer, fire_palette, width, height, pos, size, pixel_w, pixel_h

    screen_size = None
    fire_buffer = []
    fire_palette = []
    width = 0
    height = 0
    pos = None
    size = None
    pixel_w = 0
    pixel_h = 0

    collect()
