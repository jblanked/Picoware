import random


def start(view_manager) -> bool:
    """Start the app"""
    draw = view_manager.draw
    draw.clear()
    _pos = draw.scale(130, 160)
    draw._text(_pos[0], _pos[1], "Press Enter :D", draw.foreground)
    draw.swap()
    return True


def run(view_manager):
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK, BUTTON_CENTER
    from picoware.system.vector import Vector
    from picoware.system.colors import TFT_WHITE, TFT_BLUE, TFT_RED, TFT_YELLOW

    input_manager = view_manager.input_manager
    button = input_manager.button

    colors = [TFT_WHITE, TFT_BLUE, TFT_RED, TFT_YELLOW]

    if button == BUTTON_CENTER:
        input_manager.reset()

        draw = view_manager.draw
        draw.clear()

        # Randomly select color and shape
        color_choice = random.choice(colors)
        shape_choice = random.randint(0, 3)

        if shape_choice == 0:
            draw._circle(
                draw.size.x // 2, draw.size.y // 2, draw.size.x // 10, color_choice
            )
        elif shape_choice == 1:
            _pos = draw.scale(150, 160)
            _size = draw.scale(20, 20)
            draw.rect(
                Vector(_pos[0], _pos[1]), Vector(_size[0], _size[1]), color_choice
            )
        elif shape_choice == 2:
            _start = draw.scale(10, 160)
            _end = draw.scale(180, 160)
            draw.line_custom(
                Vector(_start[0], _start[1]), Vector(_end[0], _end[1]), color_choice
            )
        elif shape_choice == 3:
            _pos = draw.scale(150, 160)
            _size = draw.scale(30, 30)
            draw.fill_round_rectangle(
                Vector(_pos[0], _pos[1]), Vector(_size[0], _size[1]), 5, color_choice
            )

        draw.swap()

    elif button == BUTTON_BACK:
        input_manager.reset()
        view_manager.back()


def stop(view_manager):
    """Stop the app"""
    from gc import collect

    collect()
