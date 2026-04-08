from micropython import const

STATE_BROWSER = const(0)
STATE_PLAYING = const(1)

_state = STATE_BROWSER
gb = None
_file_browser = None


def start(view_manager) -> bool:
    """Start the app"""
    if not view_manager.has_psram:
        view_manager.alert("PSRAM not available...")
        return False

    # first show info screen about connection
    d = view_manager.draw
    fg = view_manager.foreground_color
    d.erase()
    d._text(0, 0, "GameBoy Emulator (PSRAM, 60 FPS)", fg)
    d._text(0, 20, "Up arrow is the Up key", fg)
    d._text(0, 40, "Down arrow is the Down key", fg)
    d._text(0, 60, "Left arrow is the Left key", fg)
    d._text(0, 80, "Right arrow is the Right key", fg)
    d._text(0, 100, "Right bracket is the A key", fg)
    d._text(0, 120, "Left bracket is the B key", fg)
    d._text(0, 140, "Equal sign is the Start key", fg)
    d._text(0, 160, "Minus sign is the Select key", fg)
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

    view_manager.freq(True)  # set to lower frequency

    from picoware.gui.file_browser import FileBrowser
    from picoware.system.gameboy import GameBoy

    global gb, _file_browser, _state

    _state = STATE_BROWSER
    gb = GameBoy()

    _file_browser = FileBrowser(view_manager, allowed_extensions=["gb", "gbc"])

    return True


def run(view_manager) -> None:
    """Run the app"""
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
    """Stop the app"""
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

    view_manager.freq()  # set back to higher frequency

    collect()
