"""
REPL App for Picoware
Copyright (c) 2026 JBlanked
GPL-3.0 License
https://www.github.com/jblanked/Picoware
Last Updated: 2026-05-07
"""

from micropython import const
from picoware.system.decorator import keyboard_required

_PROMPT = const(">>> ")
_PROMPT_CONT = const("... ")

_text_editor = None
_repl_context = {}
_multiline_buffer = []
_history = []
_history_index = 0
_history_draft = ""


def __parse(text: str) -> str:
    """Execute input text and return the output as a string.

    Args:
        text (str): The input to execute.

    Returns:
        str: The executed output.
    """
    global _repl_context

    _output = []

    def _capture_print(*args, sep=" ", end="\n", file=None):
        """Capture print output into the result buffer.

        Args:
            sep (str): Separator between values. Defaults to " ".
            end (str): Line ending. Defaults to "\n".
            file (object): Ignored output stream. Defaults to None.
        """
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
    """Return True if line opens a multi-line block and needs continuation.

    Args:
        line (str): The line to check.

    Returns:
        bool: True if more input is needed.
    """
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


def _replace_current_input(value: str) -> None:
    """Replace the input on the current prompt line."""
    global _text_editor

    text = _text_editor.current_text
    cursor = _text_editor.cursor
    pos_main = text.rfind(_PROMPT, 0, cursor)
    pos_cont = text.rfind(_PROMPT_CONT, 0, cursor)
    if pos_main >= pos_cont:
        _start = pos_main + len(_PROMPT)
    else:
        _start = pos_cont + len(_PROMPT_CONT)
    end = text.find("\n", _start)
    if end == -1:
        end = len(text)
    new_text = text[:_start] + value + text[end:]
    _text_editor.set_text(new_text)
    _text_editor.cursor = _start + len(value)


def _show_previous_input() -> None:
    """Load the previous input from command history."""
    global _history_index, _history_draft

    if not _history:
        return
    if _history_index == len(_history):
        _history_draft = _get_current_input()
    _history_index = max(0, _history_index - 1)
    _replace_current_input(_history[_history_index])


def _show_next_input() -> None:
    """Load the next input from command history."""
    global _history_index

    if _history_index >= len(_history):
        return
    _history_index += 1
    if _history_index == len(_history):
        _replace_current_input(_history_draft)
    else:
        _replace_current_input(_history[_history_index])


def _commit_input(output: str) -> None:
    """Append the output and a new prompt to the editor's existing text.

    Args:
        output (str): The output to append.
    """
    global _text_editor

    suffix = "\n" + output + "\n" + _PROMPT if output else "\n" + _PROMPT
    new_text = _text_editor.current_text + suffix
    _text_editor.set_text(new_text)
    _text_editor.cursor = len(new_text)


def _record_input(value: str) -> None:
    """Add a non-empty input to command history."""
    global _history, _history_index, _history_draft

    if value.strip():
        _history.append(value)
    _history_index = len(_history)
    _history_draft = ""


def _continue_input() -> None:
    """Append a continuation prompt for multi-line input."""
    global _text_editor

    new_text = _text_editor.current_text + "\n" + _PROMPT_CONT
    _text_editor.set_text(new_text)
    _text_editor.cursor = len(new_text)


@keyboard_required
def start(view_manager) -> bool:
    """Start the app.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True on success.
    """
    from picoware.gui.text_editor import TextEditor

    view_manager.freq(True)  # set to lower frequency
    view_manager.storage.mount_vfs()

    global _text_editor, _repl_context, _multiline_buffer
    global _history, _history_index, _history_draft

    _repl_context = {}
    _multiline_buffer = []
    _history = []
    _history_index = 0
    _history_draft = ""

    if _text_editor is None:
        _text_editor = TextEditor(view_manager, cursor_movement=False)
        _text_editor.set_text(_PROMPT)
        _text_editor.cursor = len(_PROMPT)

    return _text_editor is not None


def run(view_manager) -> None:
    """Run the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_CENTER,
        BUTTON_DOWN,
        BUTTON_UP,
    )

    global _text_editor, _multiline_buffer, _history_index

    if _text_editor is None:
        return

    inp = view_manager.input_manager
    but = inp.button

    if but == BUTTON_BACK:
        inp.reset()
        _multiline_buffer = []
        view_manager.back()
        return

    if but in (BUTTON_UP, BUTTON_DOWN) and not _multiline_buffer:
        inp.reset()
        _text_editor.cursor = len(_text_editor.current_text)
        if but == BUTTON_UP:
            _show_previous_input()
        else:
            _show_next_input()
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
                command = "\n".join(_multiline_buffer)
                _record_input(command)
                output = __parse(command)
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
                _record_input(current_line)
                output = __parse(current_line)
                _commit_input(output)
        return

    if not _text_editor.run():
        inp.reset()
        _multiline_buffer = []
        view_manager.back()


def stop(view_manager) -> None:
    """Stop the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """

    from gc import collect

    global _text_editor, _repl_context, _multiline_buffer

    if _text_editor is not None:
        del _text_editor
        _text_editor = None

    _repl_context = {}
    _multiline_buffer = []
    view_manager.storage.unmount_vfs()
    view_manager.freq()  # set back to higher frequency

    collect()
