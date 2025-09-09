_screensavers = None
_screensavers_index = 0


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.gui.menu import Menu

    global _screensavers
    global _screensavers_index
    if _screensavers is None:
        _screensavers = Menu(
            view_manager.draw,
            "Screensavers",
            0,
            320,
            view_manager.get_foreground_color(),
            view_manager.get_background_color(),
            view_manager.get_selected_color(),
            view_manager.get_foreground_color(),
            2,
        )
        _screensavers.add_item("Spiro")
        _screensavers.set_selected(_screensavers_index)

        _screensavers.draw()
    return True


def run(view_manager) -> None:
    """Run the app."""
    from picoware.system.view import View
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_CENTER,
        BUTTON_RIGHT,
    )

    global _screensavers
    if not _screensavers:
        return
    global _screensavers_index

    input_manager = view_manager.input_manager
    button: int = input_manager.get_last_button()

    if button == BUTTON_UP:
        input_manager.reset(True)
        _screensavers.scroll_up()
    elif button == BUTTON_DOWN:
        input_manager.reset(True)
        _screensavers.scroll_down()
    elif button in (BUTTON_BACK, BUTTON_LEFT):
        _screensavers_index = 0
        input_manager.reset(True)
        view_manager.back()
    elif button in (BUTTON_CENTER, BUTTON_RIGHT):
        input_manager.reset(True)
        _screensavers_index = _screensavers.get_selected_index()

        if _screensavers_index == 0:
            from picoware.applications.screensavers import spiro

            view_manager.add(
                View("screensavers_spiro", spiro.run, spiro.start, spiro.stop)
            )
            view_manager.switch_to("screensavers_spiro")


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _screensavers
    if _screensavers is not None:
        del _screensavers
        _screensavers = None
    collect()
