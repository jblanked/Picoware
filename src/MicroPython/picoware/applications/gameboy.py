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

    inp = view_manager.input_manager
    button = inp.button

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
        inp.reset()
        if gb is not None:
            gb.stop()
            del gb
            gb = None
        view_manager.back()
        return

    if gb is not None:
        gb.run(button)
        if button != -1:
            inp.reset()


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

    collect()
