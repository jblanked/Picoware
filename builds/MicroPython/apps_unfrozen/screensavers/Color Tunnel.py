# Color Tunnel screensaver
# Classic demo-scene vortex: concentric colour rings rush toward the viewer
# while the pattern gently rotates.  Rendered in coarse tiles for speed.
from micropython import const
from picoware.system.buttons import BUTTON_BACK
from picoware.system.colors import TFT_BLACK
from picoware.system.vector import Vector

screen_size = None
time_val = 0.0
pos = None
tile_vec = None
palette = None

TILE = const(3)  # pixel size of each rendered tile (square)
RING_SIZE = const(11)  # radial pixel distance per colour ring
NUM_COLORS = const(32)  # must be a power of 2


def _build_palette() -> list:
    """Build a vivid NUM_COLORS-entry rainbow palette"""
    pal = []
    for i in range(NUM_COLORS):
        h6 = (i / NUM_COLORS) * 6.0
        seg = int(h6) % 6
        f = h6 - int(h6)
        if seg == 0:
            r, g, b = 255, int(255 * f), 0
        elif seg == 1:
            r, g, b = int(255 * (1 - f)), 255, 0
        elif seg == 2:
            r, g, b = 0, 255, int(255 * f)
        elif seg == 3:
            r, g, b = 0, int(255 * (1 - f)), 255
        elif seg == 4:
            r, g, b = int(255 * f), 0, 255
        else:
            r, g, b = 255, 0, int(255 * (1 - f))
        pal.append(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3))
    return pal


def start(view_manager) -> bool:
    """Start the app"""
    global screen_size, time_val, pos, tile_vec, palette

    draw = view_manager.draw
    screen_size = Vector(draw.size.x, draw.size.y)
    time_val = 0.0
    pos = Vector(0, 0)
    tile_vec = Vector(TILE, TILE)
    palette = _build_palette()

    draw.fill_screen(TFT_BLACK)
    draw.swap()
    return True


def run(view_manager) -> None:
    """Run the app"""
    global time_val

    inp = view_manager.input_manager
    if inp.button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
        return

    draw = view_manager.draw
    time_val += 0.07

    # Integer time offset for ring animation (rings zoom toward the viewer)
    t_int = int(time_val * RING_SIZE)

    cx = screen_size.x >> 1
    cy = screen_size.y >> 1

    for y in range(0, screen_size.y, TILE):
        dy = y - cy
        dy2 = dy * dy
        for x in range(0, screen_size.x, TILE):
            dx = x - cx

            # Radial distance (integer approximation)
            r = int((dx * dx + dy2) ** 0.5)

            # Which ring band are we in?  Rings flow toward centre over time.
            ring = ((r + t_int) // RING_SIZE) & (NUM_COLORS - 1)

            # Two-sector checker (diagonal quadrants) adds a rotating twist
            sector = int(dx >= 0) ^ int(dy >= 0)
            color_idx = (ring + sector * (NUM_COLORS >> 1)) & (NUM_COLORS - 1)

            pos.x = x
            pos.y = y
            draw.fill_rectangle(pos, tile_vec, palette[color_idx])

    draw.swap()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global screen_size, time_val, pos, tile_vec, palette

    screen_size = None
    time_val = 0.0
    pos = None
    tile_vec = None
    palette = None

    collect()
