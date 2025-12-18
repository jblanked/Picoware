_text = ""


def start(view_manager):

    global _text

    st = view_manager.storage

    st.write("test.txt", "hi")

    _text = st.read("test.txt")

    return True


def run(view_manager):

    from picoware.system.buttons import BUTTON_BACK
    from picoware.system.vector import Vector

    inp = view_manager.input_manager
    draw = view_manager.draw
    but = inp.get_last_button()

    if but == BUTTON_BACK:
        inp.reset()
        view_manager.back()
    else:
        draw.text(Vector(160, 160), _text)
        draw.swap()


def stop(view_manager):
    from gc import collect

    collect()
