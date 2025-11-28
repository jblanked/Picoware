_textbox = None
_text_editor_started = False
_filename: str = ""
_keyboard_just_started = False


def __start_text_editor(view_manager) -> None:
    """Start the text editor app"""
    from picoware.gui.textbox import TextBox

    global _textbox, _text_editor_started, _filename

    if _textbox is None:
        draw = view_manager.get_draw()
        _textbox = TextBox(
            draw,
            0,
            draw.size.y,
            view_manager.foreground_color,
            view_manager.background_color,
        )

        storage = view_manager.get_storage()
        if _filename:
            _textbox.set_text(storage.read(_filename))

    _text_editor_started = True


def __process_text_input(button: int, shift: bool) -> None:
    """Process text input and update the textbox"""
    from picoware.system.buttons import (
        BUTTON_CENTER,
        BUTTON_SPACE,
        BUTTON_A,
        BUTTON_B,
        BUTTON_C,
        BUTTON_D,
        BUTTON_E,
        BUTTON_F,
        BUTTON_G,
        BUTTON_H,
        BUTTON_I,
        BUTTON_J,
        BUTTON_K,
        BUTTON_L,
        BUTTON_M,
        BUTTON_N,
        BUTTON_O,
        BUTTON_P,
        BUTTON_Q,
        BUTTON_R,
        BUTTON_S,
        BUTTON_T,
        BUTTON_U,
        BUTTON_V,
        BUTTON_W,
        BUTTON_X,
        BUTTON_Y,
        BUTTON_Z,
        BUTTON_0,
        BUTTON_1,
        BUTTON_2,
        BUTTON_3,
        BUTTON_4,
        BUTTON_5,
        BUTTON_6,
        BUTTON_7,
        BUTTON_8,
        BUTTON_9,
        BUTTON_BACKSPACE,
        BUTTON_PERIOD,
        BUTTON_COMMA,
        BUTTON_SEMICOLON,
        BUTTON_MINUS,
        BUTTON_EQUAL,
        BUTTON_LEFT_BRACKET,
        BUTTON_RIGHT_BRACKET,
        BUTTON_SLASH,
        BUTTON_BACKSLASH,
        BUTTON_UNDERSCORE,
        BUTTON_COLON,
        BUTTON_SINGLE_QUOTE,
        BUTTON_DOUBLE_QUOTE,
    )

    global _textbox

    button_pressed = False

    character_map = {
        BUTTON_A: "a",
        BUTTON_B: "b",
        BUTTON_C: "c",
        BUTTON_D: "d",
        BUTTON_E: "e",
        BUTTON_F: "f",
        BUTTON_G: "g",
        BUTTON_H: "h",
        BUTTON_I: "i",
        BUTTON_J: "j",
        BUTTON_K: "k",
        BUTTON_L: "l",
        BUTTON_M: "m",
        BUTTON_N: "n",
        BUTTON_O: "o",
        BUTTON_P: "p",
        BUTTON_Q: "q",
        BUTTON_R: "r",
        BUTTON_S: "s",
        BUTTON_T: "t",
        BUTTON_U: "u",
        BUTTON_V: "v",
        BUTTON_W: "w",
        BUTTON_X: "x",
        BUTTON_Y: "y",
        BUTTON_Z: "z",
        #
        BUTTON_0: "0",
        BUTTON_1: "1",
        BUTTON_2: "2",
        BUTTON_3: "3",
        BUTTON_4: "4",
        BUTTON_5: "5",
        BUTTON_6: "6",
        BUTTON_7: "7",
        BUTTON_8: "8",
        BUTTON_9: "9",
        #
        BUTTON_CENTER: "\n",
        BUTTON_SPACE: " ",
        BUTTON_PERIOD: ".",
        BUTTON_COMMA: ",",
        BUTTON_SEMICOLON: ";",
        BUTTON_MINUS: "-",
        BUTTON_EQUAL: "=",
        BUTTON_LEFT_BRACKET: "[",
        BUTTON_RIGHT_BRACKET: "]",
        BUTTON_SLASH: "/",
        BUTTON_BACKSLASH: "\\",
        BUTTON_UNDERSCORE: "_",
        BUTTON_COLON: ":",
        BUTTON_SINGLE_QUOTE: "'",
        BUTTON_DOUBLE_QUOTE: '"',
    }

    if button in character_map:
        char_to_add = character_map[button]
        if shift and char_to_add.isalpha():
            char_to_add = char_to_add.upper()
        _textbox.current_text += char_to_add
        button_pressed = True
    elif button == BUTTON_BACKSPACE:
        _textbox.current_text = _textbox.current_text[:-1]
        button_pressed = True

    if button_pressed:
        _textbox.refresh()


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.system.vector import Vector
    from time import sleep

    draw = view_manager.get_draw()
    draw.text(
        Vector(10, 10), "Enter filename to edit:", view_manager.get_foreground_color()
    )
    draw.swap()
    sleep(2)
    kb = view_manager.get_keyboard()
    kb.set_response("")
    kb.run(force=True)

    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK

    global _textbox, _text_editor_started, _filename, _keyboard_just_started

    inp = view_manager.get_input_manager()
    but = inp.button
    kb = view_manager.get_keyboard()

    if but == BUTTON_BACK:
        inp.reset()
        view_manager.back()
    elif not _text_editor_started:
        if kb.is_finished:
            _filename = kb.get_response()
            __start_text_editor(view_manager)
            kb.reset()
            return
        if not _keyboard_just_started:
            _keyboard_just_started = True
            kb.run(force=True)
        else:
            kb.run()
    else:
        if not _textbox or but == -1:
            return
        inp.reset()
        __process_text_input(but, inp.was_capitalized)


def stop(view_manager) -> None:
    """Stop the app"""

    from gc import collect

    global _textbox, _text_editor_started, _filename, _keyboard_just_started

    if _textbox and _text_editor_started and _filename:
        storage = view_manager.get_storage()
        storage.write(_filename, _textbox.text)
        del _textbox
        _textbox = None

    kb = view_manager.get_keyboard()
    if kb:
        kb.reset()

    _text_editor_started = False
    _keyboard_just_started = False
    _filename = ""

    collect()
