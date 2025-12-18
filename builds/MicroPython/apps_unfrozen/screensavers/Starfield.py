# Animates white pixels to simulate flying through a star field
# Original from https://github.com/Bodmer/TFT_eSPI/tree/master/examples/320%20x%20240/TFT_Starfield

from micropython import const

NSTARS = const(128)  # Number of stars

za: int = -1
zb: int = -1
zc: int = -1
zx: int = -1

sx = [0] * NSTARS
sy = [0] * NSTARS
sz = [0] * NSTARS


def __rng() -> int:
    global za, zb, zc, zx
    zx = (zx + 1) & 0xFF  # Keep within 8-bit range
    za = (za ^ zc ^ zx) & 0xFF
    zb = (zb + za) & 0xFF
    zc = ((zc + (zb >> 1)) ^ za) & 0xFF
    return zc


def start(view_manager) -> bool:
    """Start the app"""
    import random
    from picoware.system.colors import TFT_BLACK

    global za, zb, zc, zx, sx, sy, sz

    za = random.randint(0, 255)
    zb = random.randint(0, 255)
    zc = random.randint(0, 255)
    zx = random.randint(0, 255)

    # Initialize star data
    for i in range(NSTARS):
        sx[i] = 0
        sy[i] = 0
        sz[i] = 0

    draw = view_manager.draw
    draw.fill_screen(TFT_BLACK)  # Black background
    draw.swap()

    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_LEFT, BUTTON_BACK
    from picoware.system.colors import TFT_BLACK
    from picoware.system.vector import Vector

    global sx, sy, sz

    input_manager = view_manager.input_manager
    input_button = input_manager.button

    if input_button in (BUTTON_LEFT, BUTTON_BACK):
        view_manager.back()
        input_manager.reset()
        return

    tft = view_manager.draw
    spawn_depth_variation = 255
    pixel_vector = Vector(0, 0)
    screen_size = tft.size
    screen_size_half = Vector(screen_size.x // 2, screen_size.y // 2)
    for i in range(NSTARS):
        if sz[i] <= 1:
            rng_x = __rng()
            rng_y = __rng()
            sx[i] = (
                screen_size_half.x - (screen_size_half.x * 0.75) + rng_x
            )  # Range: 40 to 295
            sy[i] = rng_y  # Range: 0 to 255
            sz[i] = spawn_depth_variation
            if spawn_depth_variation > 1:
                spawn_depth_variation -= 1
        else:
            if sz[i] > 0:
                # Cast to int and be careful with order of operations to avoid overflow
                old_screen_x = int(
                    (int(sx[i]) - screen_size_half.x) * 256 // sz[i]
                    + screen_size_half.x
                )
                old_screen_y = int(
                    (int(sy[i]) - screen_size_half.y) * 256 // sz[i]
                    + screen_size_half.y
                )

                if (
                    0 <= old_screen_x < screen_size.x
                    and 0 <= old_screen_y < screen_size.y
                ):
                    pixel_vector.x = old_screen_x
                    pixel_vector.y = old_screen_y
                    tft.pixel(pixel_vector, TFT_BLACK)

                sz[i] -= 2
                if sz[i] > 1:
                    screen_x = int(
                        (int(sx[i]) - screen_size_half.x) * 256 // sz[i]
                        + screen_size_half.x
                    )
                    screen_y = int(
                        (int(sy[i]) - screen_size_half.y) * 256 // sz[i]
                        + screen_size_half.y
                    )

                    if 0 <= screen_x < screen_size.x and 0 <= screen_y < screen_size.y:
                        r = g = b = 255 - sz[i]
                        color = tft.color565(r, g, b)
                        pixel_vector.x = screen_x
                        pixel_vector.y = screen_y
                        tft.pixel(pixel_vector, color)
                    else:
                        sz[i] = 0

    tft.swap()


def stop(view_manager) -> None:
    """Stop the app"""
    from picoware.system.colors import TFT_BLACK
    from gc import collect

    draw = view_manager.draw
    draw.fill_screen(TFT_BLACK)  # Black background
    draw.swap()

    global sx, sy, sz
    sx = [0] * NSTARS
    sy = [0] * NSTARS
    sz = [0] * NSTARS

    collect()
