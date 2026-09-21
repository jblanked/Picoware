"""Game Boy - Emulator for Game Boy ROMs."""

from micropython import const
from picoware.system.decorator import storage_required, psram_required

STATE_BROWSER = const(0)
STATE_PLAYING = const(1)

_state = STATE_BROWSER
gb = None
_file_browser = None


@storage_required
@psram_required
def start(view_manager) -> bool:
    """Start the app.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True on success.
    """
    # first show info screen about connection
    d = view_manager.draw
    fg = view_manager.foreground_color
    d.erase()
    _text = """GameBoy Emulator (PSRAM, 60 FPS)
Controls:
Up arrow is the Up key
Down arrow is the Down key
Left arrow is the Left key
Right arrow is the Right key
Right bracket is the A key
Left bracket is the B key
Equal sign is the Start key
Minus sign is the Select key

    """
    d._text(0, 0, _text, fg)
    d.swap()

    inp = view_manager.input_manager
    inp.reset()
    while True:
        but = inp.button
        if but != -1:
            inp.reset()
            if but == 5:  # back
                return False
            break

    from picoware.gui.file_browser import FileBrowser
    from picoware.system.gameboy import GameBoy

    global gb, _file_browser, _state

    _state = STATE_BROWSER
    gb = GameBoy()

    _file_browser = FileBrowser(view_manager, allowed_extensions=["gb", "gbc"])

    return True


def run(view_manager) -> None:
    """Run the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    global gb, _file_browser, _state

    button = view_manager.button

    if _state == STATE_BROWSER:
        if _file_browser is None:
            view_manager.back()
            return

        continue_browsing = _file_browser.run()

        if not continue_browsing:
            selected_path = _file_browser.path

            del _file_browser
            _file_browser = None

            # check if gb or gbc file
            if (
                selected_path
                and ".gb" not in selected_path
                and ".gbc" not in selected_path
            ):
                view_manager.alert("Please select a .gb or .gbc file!")
                view_manager.back()
                return

            _state = STATE_PLAYING
            view_manager.alert(
                f"Starting game: {selected_path}. Press BACK to start (this may take a moment)..."
            )
            view_manager.draw.erase()
            view_manager.draw.swap()
            gb.start(selected_path)
        return

    # STATE_PLAYING
    if button == 5:  # back
        if gb is not None:
            gb.stop()
            del gb
            gb = None
        view_manager.back()
        return

    if gb is not None:
        gb.run(button)


def stop(view_manager) -> None:
    """Stop the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from gc import collect

    global gb, _file_browser, _state

    if _file_browser is not None:
        del _file_browser
        _file_browser = None

    if gb is not None:
        gb.stop()
        del gb
        gb = None

    _state = STATE_BROWSER

    collect()
