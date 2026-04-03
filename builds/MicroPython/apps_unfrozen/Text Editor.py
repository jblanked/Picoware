_textbox = None
_text_editor_started = False
_filename: str = ""
_keyboard_just_started = False


def __start_text_editor(view_manager) -> None:
    """Start the text editor app"""
    from picoware.gui.text_editor import TextEditor

    global _textbox, _text_editor_started, _filename

    if _textbox is None:
        _textbox = TextEditor(
            view_manager,
        )
        if _filename:
            _textbox.load_file(_filename)

    _text_editor_started = True


def start(view_manager) -> bool:
    """Start the app"""
    kb = view_manager.keyboard
    kb.title = "Enter filename to edit:"
    kb.response = ""
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
            _filename = kb.response
            __start_text_editor(view_manager)
            kb.reset()
            return
        if not _keyboard_just_started:
            _keyboard_just_started = True
            kb.run(force=True)
        else:
            kb.run()
    else:
        _textbox.run()


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
