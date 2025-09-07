_desktop = None


def start(view_manager) -> bool:
    """Start the loading animation."""
    from picoware.gui.desktop import Desktop

    global _desktop
    if _desktop is None:
        _desktop = Desktop(view_manager.draw)
    return True


def run(view_manager) -> None:
    """Animate the loading spinner."""
    from picoware.system.buttons import BUTTON_BACK

    global _desktop
    if _desktop:
        _desktop.draw_header()
        _desktop.display.swap()

    button: int = view_manager.input_manager.get_last_button()

    if button == BUTTON_BACK:
        from picoware.applications import system_info
        from picoware.system.view import View

        view_manager.add(
            View("system_info", system_info.run, system_info.start, system_info.stop)
        )
        view_manager.switch_to("system_info")


def stop(view_manager) -> None:
    """Stop the loading animation."""
    from gc import collect

    global _desktop
    if _desktop:
        del _desktop
        _desktop = None
    collect()
