from micropython import const

hi = const(b"Hello World")
clr = 0


def start(view_manager) -> bool:
    """Start the app."""
    from picoware.system.vector import Vector

    draw = view_manager.get_draw()

    draw.clear()

    draw.text(Vector(130, 160), "Press Enter :D")

    draw.swap()

    return True


def run(view_manager):
    """Run the app."""
    from picoware.system.buttons import BUTTON_BACK, BUTTON_CENTER
    from picoware.system.vector import Vector
    from picoware.system.colors import (
        TFT_WHITE,
        TFT_BLUE,
        TFT_RED,
        TFT_YELLOW,
        TFT_GREEN,
    )
    from random import randint

    global clr

    input_manager = view_manager.input_manager
    button = input_manager.button

    choices = {0: TFT_WHITE, 1: TFT_BLUE, 2: TFT_RED, 3: TFT_YELLOW, 4: TFT_GREEN}

    if button == BUTTON_CENTER:
        input_manager.reset()

        draw = view_manager.get_draw()
        draw.clear()
        draw.text(Vector(130, 160), hi, choices.get(clr))
        draw.swap()

        clr = randint(0, 4)

    elif button == BUTTON_BACK:
        input_manager.reset()
        view_manager.back()


def stop(view_manager):
    """Stop the app."""
    from gc import collect

    global clr

    clr = 0

    collect()
