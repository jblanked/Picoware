_counter_textbox = None
_counter_value = 0


def _update_display():
    """Update the counter display"""
    global _counter_textbox, _counter_value

    text = f"Counter App\n\nCurrent Value: {_counter_value}\n\nControls:\nUP - Increment (+1)\nDOWN - Decrement (-1)\nCENTER - Reset to 0\nLEFT/BACK - Exit"
    _counter_textbox.set_text(text)


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.gui.textbox import TextBox

    global _counter_textbox, _counter_value

    if _counter_textbox:
        del _counter_textbox
        _counter_textbox = None

    _counter_value = 0

    _counter_textbox = TextBox(
        view_manager.draw,
        0,
        view_manager.draw.size.y,
        view_manager.get_foreground_color(),
        view_manager.get_background_color(),
    )

    _update_display()

    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_LEFT,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_CENTER,
    )

    global _counter_textbox, _counter_value

    if not _counter_textbox:
        return

    input_manager = view_manager.input_manager
    button = input_manager.get_last_button()

    if button in (BUTTON_BACK, BUTTON_LEFT):
        input_manager.reset()
        view_manager.back()
    elif button == BUTTON_UP:
        input_manager.reset()
        _counter_value += 1
        _update_display()
    elif button == BUTTON_DOWN:
        input_manager.reset()
        _counter_value -= 1
        _update_display()
    elif button == BUTTON_CENTER:
        input_manager.reset()
        _counter_value = 0
        _update_display()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _counter_textbox, _counter_value
    if _counter_textbox:
        del _counter_textbox
        _counter_textbox = None
    _counter_value = 0
    collect()
