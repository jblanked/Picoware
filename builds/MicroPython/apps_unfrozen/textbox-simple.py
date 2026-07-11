_textbox = None


def start(view_manager):
    """Start the app"""
    from picoware.gui.textbox import TextBox

    global _textbox

    if _textbox is None:
        draw = view_manager.draw
        _textbox = TextBox(draw, 0, draw.size.y)

        _textbox.set_text(
            "This is a textbox app example with word wrapping so that you can see how it works. It even has scrolling too! Enjoy using Picoware!"
        )

    return True


def run(view_manager):
    """Run the app"""
    from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_BACK

    button = view_manager.button

    if button == BUTTON_UP:
        _textbox.scroll_up()
    elif button == BUTTON_DOWN:
        _textbox.scroll_down()
    elif button == BUTTON_BACK:
        view_manager.back()


def stop(view_manager):
    """Stop the app"""
    from gc import collect

    global _textbox

    if _textbox:
        del _textbox
        _textbox = None

    collect()
