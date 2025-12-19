_textbox = None
_text_editor_started = False
_filename: str = ""
_keyboard_just_started = False


def __start_text_editor(view_manager) -> None:
    """Start the text editor app"""
    from picoware.gui.textbox import TextBox

    global _textbox, _text_editor_started, _filename

    if _textbox is None:
        draw = view_manager.draw
        _textbox = TextBox(
            draw,
            0,
            draw.size.y,
            view_manager.foreground_color,
            view_manager.background_color,
        )

        storage = view_manager.storage
        if _filename:
            _textbox.set_text(storage.read(_filename))

    _text_editor_started = True


def __process_text_input(button: int, shift: bool) -> None:
    """Process text input and update the textbox"""
    from picoware.system import buttons

    global _textbox

    button_pressed = False

    character_map = {
        buttons.BUTTON_A: "a",
        buttons.BUTTON_B: "b",
        buttons.BUTTON_C: "c",
        buttons.BUTTON_D: "d",
        buttons.BUTTON_E: "e",
        buttons.BUTTON_F: "f",
        buttons.BUTTON_G: "g",
        buttons.BUTTON_H: "h",
        buttons.BUTTON_I: "i",
        buttons.BUTTON_J: "j",
        buttons.BUTTON_K: "k",
        buttons.BUTTON_L: "l",
        buttons.BUTTON_M: "m",
        buttons.BUTTON_N: "n",
        buttons.BUTTON_O: "o",
        buttons.BUTTON_P: "p",
        buttons.BUTTON_Q: "q",
        buttons.BUTTON_R: "r",
        buttons.BUTTON_S: "s",
        buttons.BUTTON_T: "t",
        buttons.BUTTON_U: "u",
        buttons.BUTTON_V: "v",
        buttons.BUTTON_W: "w",
        buttons.BUTTON_X: "x",
        buttons.BUTTON_Y: "y",
        buttons.BUTTON_Z: "z",
        #
        buttons.BUTTON_0: "0",
        buttons.BUTTON_1: "1",
        buttons.BUTTON_2: "2",
        buttons.BUTTON_3: "3",
        buttons.BUTTON_4: "4",
        buttons.BUTTON_5: "5",
        buttons.BUTTON_6: "6",
        buttons.BUTTON_7: "7",
        buttons.BUTTON_8: "8",
        buttons.BUTTON_9: "9",
        #
        buttons.BUTTON_CENTER: "\n",
        buttons.BUTTON_SPACE: " ",
        buttons.BUTTON_PERIOD: ".",
        buttons.BUTTON_QUESTION: "?",
        buttons.BUTTON_COMMA: ",",
        buttons.BUTTON_SEMICOLON: ";",
        buttons.BUTTON_MINUS: "-",
        buttons.BUTTON_EQUAL: "=",
        buttons.BUTTON_LEFT_BRACKET: "[",
        buttons.BUTTON_LEFT_BRACE: "{",
        buttons.BUTTON_RIGHT_BRACKET: "]",
        buttons.BUTTON_RIGHT_BRACE: "}",
        buttons.BUTTON_SLASH: "/",
        buttons.BUTTON_BACKSLASH: "\\",
        buttons.BUTTON_UNDERSCORE: "_",
        buttons.BUTTON_COLON: ":",
        buttons.BUTTON_SINGLE_QUOTE: "'",
        buttons.BUTTON_DOUBLE_QUOTE: '"',
        buttons.BUTTON_PLUS: "+",
        #
        buttons.BUTTON_EXCLAMATION: "!",
        buttons.BUTTON_AT: "@",
        buttons.BUTTON_HASH: "#",
        buttons.BUTTON_DOLLAR: "$",
        buttons.BUTTON_PERCENT: "%",
        buttons.BUTTON_CARET: "^",
        buttons.BUTTON_AMPERSAND: "&",
        buttons.BUTTON_ASTERISK: "*",
        buttons.BUTTON_LEFT_PARENTHESIS: "(",
        buttons.BUTTON_RIGHT_PARENTHESIS: ")",
        buttons.BUTTON_LESS_THAN: "<",
        buttons.BUTTON_GREATER_THAN: ">",
        buttons.BUTTON_BACK_TICK: "`",
        buttons.BUTTON_TILDE: "~",
        buttons.BUTTON_PIPE: "|",
    }

    if button in character_map:
        char_to_add = character_map[button]
        if shift and char_to_add.isalpha():
            char_to_add = char_to_add.upper()
        _textbox.current_text += char_to_add
        button_pressed = True
    elif button == buttons.BUTTON_BACKSPACE:
        _textbox.current_text = _textbox.current_text[:-1]
        button_pressed = True

    if button_pressed:
        _textbox.refresh()


def start(view_manager) -> bool:
    """Start the app"""
    kb = view_manager.keyboard
    kb.title = "Enter filename to edit:"
    kb.set_response("")
    kb.run(force=True)
    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK

    global _textbox, _text_editor_started, _filename, _keyboard_just_started

    inp = view_manager.input_manager
    but = inp.button
    kb = view_manager.keyboard

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
        storage = view_manager.storage
        storage.write(_filename, _textbox.text)
        del _textbox
        _textbox = None

    kb = view_manager.keyboard
    if kb:
        kb.reset()

    _text_editor_started = False
    _keyboard_just_started = False
    _filename = ""

    collect()
