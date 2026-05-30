_text = ""


def start(view_manager) -> bool:
    """Start the app"""
    global _text

    st = view_manager.storage

    st.write("test.txt", "hi")

    _text = st.read("test.txt")

    return True


def run(view_manager):
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK

    inp = view_manager.input_manager
    draw = view_manager.draw
    but = inp.button

    if but == BUTTON_BACK:
        inp.reset()
        view_manager.back()
    else:
        draw._text(draw.size.x // 2, draw.size.y // 2, _text, draw.foreground)
        draw.swap()


def stop(view_manager):
    """Stop the app"""
    from gc import collect

    collect()
