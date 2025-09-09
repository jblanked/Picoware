_library = None
_library_index = 0


def start(view_manager) -> bool:
    """Start the app."""
    from picoware.gui.menu import Menu

    global _library
    global _library_index
    if _library is None:
        _library = Menu(
            view_manager.draw,
            "Library",
            0,
            320,
            view_manager.get_foreground_color(),
            view_manager.get_background_color(),
            view_manager.get_selected_color(),
            view_manager.get_foreground_color(),
            2,
        )
        _library.add_item("System")
        _library.add_item("WiFi")
        _library.add_item("Screensavers")
        _library.set_selected(_library_index)

        _library.draw()
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

    global _library
    if not _library:
        return
    global _library_index

    input_manager = view_manager.input_manager
    button: int = input_manager.get_last_button()

    if button == BUTTON_UP:
        input_manager.reset(True)
        _library.scroll_up()
    elif button == BUTTON_DOWN:
        input_manager.reset(True)
        _library.scroll_down()
    elif button in (BUTTON_BACK, BUTTON_LEFT):
        _library_index = 0
        input_manager.reset(True)
        view_manager.back()
    elif button in (BUTTON_CENTER, BUTTON_RIGHT):
        input_manager.reset(True)
        _library_index = _library.get_selected_index()

        if _library_index == 0:
            from picoware.applications.system import system

            view_manager.add(View("system", system.run, system.start, system.stop))
            view_manager.switch_to("system")
        elif _library_index == 1:
            from picoware.applications.wifi import wifi

            view_manager.add(View("wifi", wifi.run, wifi.start, wifi.stop))
            view_manager.switch_to("wifi")
        elif _library_index == 2:
            from picoware.applications.screensavers import screensavers

            view_manager.add(
                View(
                    "screensavers",
                    screensavers.run,
                    screensavers.start,
                    screensavers.stop,
                )
            )
            view_manager.switch_to("screensavers")


def stop(view_manager) -> None:
    """Stop the app."""
    from gc import collect

    global _library
    if _library:
        del _library
        _library = None
    collect()
