import random


def start(view_manager) -> bool:
    from picoware.system.vector import Vector

    draw = view_manager.draw
    draw.clear()
    draw.text(Vector(130, 160), "Press Enter :D")
    draw.swap()
    return True


def run(view_manager):
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
            draw.circle(Vector(160, 160), 30, color_choice)
        elif shape_choice == 1:
            draw.rect(Vector(150, 160), Vector(20, 20), color_choice)
        elif shape_choice == 2:
            draw.line_custom(Vector(10, 160), Vector(180, 160), color_choice)
        elif shape_choice == 3:
            draw.fill_round_rectangle(Vector(150, 160), Vector(30, 30), 5, color_choice)

        draw.swap()

    elif button == BUTTON_BACK:
        input_manager.reset()
        view_manager.back()


def stop(view_manager):
    from gc import collect

    collect()
