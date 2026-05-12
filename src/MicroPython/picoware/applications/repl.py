"""
REPL App for Picoware
Copyright (c) 2026 JBlanked
GPL-3.0 License
https://www.github.com/jblanked/Picoware
Last Updated: 2026-05-07
"""

from micropython import const

_PROMPT = const(">>> ")
_PROMPT_CONT = const("... ")

_text_editor = None
_repl_context = {}
_multiline_buffer = []


def __parse(text: str) -> str:
    """Execute input text and return the output as a string."""
    global _repl_context

    _output = []

    def _capture_print(*args, sep=" ", end="\n", file=None):
        _output.append(sep.join(str(a) for a in args) + end)

    _repl_context["print"] = _capture_print

    result_str = ""
    try:
        try:
            result = eval(text, _repl_context)
            lines = []
            if _output:
                lines.append("".join(_output).rstrip("\n"))
            if result is not None:
                lines.append(repr(result))
            result_str = "\n".join(lines)
        except SyntaxError:
            exec(text, _repl_context)
            if _output:
                result_str = "".join(_output).rstrip("\n")
    except Exception as e:
        result_str = f"{type(e).__name__}: {e}"

    return result_str


def _is_incomplete(line: str) -> bool:
    """Return True if line opens a multi-line block and needs continuation."""
    stripped = line.rstrip()
    if not stripped:
        return False
    # Unclosed bracket, paren, or brace
    if stripped.count("(") + stripped.count("[") + stripped.count("{") > stripped.count(
        ")"
    ) + stripped.count("]") + stripped.count("}"):
        return True
    # Explicit line continuation
    if stripped.endswith("\\"):
        return True
    # Try to compile; success means it is already a complete statement
    try:
        compile(stripped, "<stdin>", "exec")
        return False
    except SyntaxError:
        # Block opener (if/for/while/def/class/else/elif/try/except/finally/with)
        return stripped.endswith(":")


def _get_current_input() -> str:
    """Return the text between the last prompt and the cursor."""
    global _text_editor
    if _text_editor is None:
        return ""
    text = _text_editor.current_text
    cursor = _text_editor.cursor
    pos_main = text.rfind(_PROMPT, 0, cursor)
    pos_cont = text.rfind(_PROMPT_CONT, 0, cursor)
    if pos_main == -1 and pos_cont == -1:
        return text[:cursor].strip()
    if pos_main >= pos_cont:
        return text[pos_main + len(_PROMPT) : cursor]
    return text[pos_cont + len(_PROMPT_CONT) : cursor]


def _commit_input(output: str) -> None:
    """Append the output and a new prompt to the editor's existing text."""
    global _text_editor

    suffix = "\n" + output + "\n" + _PROMPT if output else "\n" + _PROMPT
    new_text = _text_editor.current_text + suffix
    _text_editor.set_text(new_text)
    _text_editor.cursor = len(new_text)


def _continue_input() -> None:
    """Append a continuation prompt for multi-line input."""
    global _text_editor

    new_text = _text_editor.current_text + "\n" + _PROMPT_CONT
    _text_editor.set_text(new_text)
    _text_editor.cursor = len(new_text)


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.gui.text_editor import TextEditor

    view_manager.freq(True)  # set to lower frequency

    global _text_editor, _repl_context, _multiline_buffer

    _repl_context = {}
    _multiline_buffer = []

    if _text_editor is None:
        _text_editor = TextEditor(view_manager)
        _text_editor.set_text(_PROMPT)
        _text_editor.cursor = len(_PROMPT)

    return _text_editor is not None


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK, BUTTON_CENTER

    global _text_editor, _multiline_buffer

    if _text_editor is None:
        return

    inp = view_manager.input_manager
    but = inp.button

    if but == BUTTON_BACK:
        inp.reset()
        _multiline_buffer = []
        view_manager.back()
        return

    if but == BUTTON_CENTER:
        inp.reset()
        current_line = _get_current_input()

        if current_line.strip() == "clear":
            _multiline_buffer = []
            _text_editor.set_text(_PROMPT)
            _text_editor.cursor = len(_PROMPT)
            return

        if _multiline_buffer:
            if not current_line.strip():
                # Empty continuation line → execute the accumulated block
                output = __parse("\n".join(_multiline_buffer))
                _multiline_buffer = []
                _commit_input(output)
            else:
                _multiline_buffer.append(current_line)
                _continue_input()
        else:
            if _is_incomplete(current_line):
                _multiline_buffer.append(current_line)
                _continue_input()
            else:
                output = __parse(current_line)
                _commit_input(output)
        return

    if not _text_editor.run():
        inp.reset()
        _multiline_buffer = []
        view_manager.back()


def stop(view_manager) -> None:
    """Stop the app"""

    from gc import collect

    global _text_editor, _repl_context, _multiline_buffer

    if _text_editor is not None:
        del _text_editor
        _text_editor = None

    _repl_context = {}
    _multiline_buffer = []

    view_manager.freq()  # set back to higher frequency

    collect()
