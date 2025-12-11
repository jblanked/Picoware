_file_browser = None


def __alert(view_manager, message: str, back: bool = True) -> None:
    """Show an alert"""

    from picoware.gui.alert import Alert
    from picoware.system.buttons import BUTTON_BACK

    draw = view_manager.get_draw()
    draw.clear()
    _alert = Alert(
        draw,
        message,
        view_manager.get_foreground_color(),
        view_manager.get_background_color(),
    )
    _alert.draw("Alert")

    # Wait for user to acknowledge
    inp = view_manager.get_input_manager()
    while True:
        button = inp.button
        if button == BUTTON_BACK:
            inp.reset()
            break

    if back:
        view_manager.back()


def start(view_manager) -> bool:
    """Start the app"""
    if not view_manager.has_sd_card:
        __alert(view_manager, "File Browser app requires an SD card")
        return False

    global _file_browser

    if _file_browser is None:
        from picoware.gui.file_browser import FileBrowser, FILE_BROWSER_MANAGER

        _file_browser = FileBrowser(view_manager, FILE_BROWSER_MANAGER)

    return True


def run(view_manager) -> None:
    """Run the app"""

    if not _file_browser.run():
        view_manager.back()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _file_browser

    if _file_browser is not None:
        del _file_browser
        _file_browser = None

    # Clean up memory
    collect()
