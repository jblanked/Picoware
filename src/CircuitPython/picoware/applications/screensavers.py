_screensavers = None
_screensavers_index = 0
_app_loader = None


def start(view_manager) -> bool:
    """Start the screensavers app"""
    from picoware.gui.menu import Menu
    from picoware.system.app_loader import AppLoader

    if not view_manager.has_sd_card:
        view_manager.alert("Screensavers app requires an SD card.", False)
        return False

    # create screensavers folder if it doesn't exist
    view_manager.storage.mkdir("picoware/apps/screensavers")

    global _screensavers
    global _app_loader

    if _app_loader:
        del _app_loader
        _app_loader = None

    if _screensavers:
        del _screensavers
        _screensavers = None

    _screensavers = Menu(
        view_manager.draw,
        "Screensavers",
        0,
        view_manager.draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
        view_manager.foreground_color,
        2,
    )
    _app_loader = AppLoader(view_manager)

    for screensaver in _app_loader.list_available_apps("screensavers"):
        _screensavers.add_item(screensaver)

    _screensavers.set_selected(_screensavers_index)

    _screensavers.draw()
    return True


def run(view_manager) -> None:
    """Run the screensavers app."""
    from picoware.system.view import View
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_CENTER,
        BUTTON_RIGHT,
    )

    global _screensavers_index

    if not _screensavers:
        return

    input_manager = view_manager.input_manager
    button: int = input_manager.button

    if button in (BUTTON_UP, BUTTON_LEFT):
        input_manager.reset()
        _screensavers.scroll_up()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        input_manager.reset()
        _screensavers.scroll_down()
    elif button == BUTTON_BACK:
        _screensavers_index = 0
        input_manager.reset()
        view_manager.back()
    elif button == BUTTON_CENTER:
        input_manager.reset()
        _screensavers_index = _screensavers.selected_index

        # Get the selected screensaver name
        selected_screensaver = _screensavers.current_item

        if selected_screensaver and _app_loader:
            # Try to load the screensaver
            screensaver_module = _app_loader.load_app(
                selected_screensaver, "screensavers"
            )
            if screensaver_module is None:
                view_manager.alert(
                    f'Could not load screensaver "{selected_screensaver}".'
                )
                return
            from time import monotonic

            start_time = int(monotonic())

            # Create a view for the screensaver and switch to it
            screensaver_view_name = f"screensaver_{selected_screensaver}"

            # Check if view already exists
            if view_manager.get_view(screensaver_view_name) is None:
                screensaver_view = View(
                    screensaver_view_name,
                    screensaver_module.run,
                    screensaver_module.start,
                    screensaver_module.stop,
                )
                print(
                    f"[Screensavers]: Created view for app {selected_screensaver} after {int(monotonic()) - start_time} ms"
                )
                view_manager.add(screensaver_view)

            view_manager.switch_to(screensaver_view_name)
            print(
                f'[Screensavers]: Switched to view for app "{selected_screensaver}" after {int(monotonic()) - start_time} ms'
            )


def stop(view_manager) -> None:
    """Stop the screensavers app"""
    from gc import collect

    global _screensavers, _app_loader
    if _screensavers is not None:
        del _screensavers
        _screensavers = None
    if _app_loader is not None:
        _app_loader.cleanup_modules()
        del _app_loader
        _app_loader = None
    collect()
