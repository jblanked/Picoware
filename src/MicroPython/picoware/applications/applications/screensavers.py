"""Screensavers - Collection of screensaver animations."""

from picoware.system.decorator import storage_required

_screensavers = None
_screensavers_index = 0
_app_loader = None


@storage_required
def start(view_manager) -> bool:
    """Start the screensavers app.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True on success.
    """
    from picoware.gui.menu import Menu

    # create screensavers folder if it doesn't exist
    view_manager.storage.mkdir("picoware/apps/screensavers")

    global _screensavers
    global _app_loader

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
    _app_loader = view_manager.app_loader

    for screensaver in _app_loader.list_available_apps("screensavers"):
        _screensavers.add_item(screensaver)

    _screensavers.set_selected(_screensavers_index)

    _screensavers.draw()
    return True


def run(view_manager) -> None:
    """Run the screensavers app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
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

    button: int = view_manager.button

    if button in (BUTTON_UP, BUTTON_LEFT):
        _screensavers.scroll_up()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        _screensavers.scroll_down()
    elif button == BUTTON_BACK:
        _screensavers_index = 0
        view_manager.back()
    elif button == BUTTON_CENTER:
        _screensavers_index = _screensavers.selected_index

        # Get the selected screensaver name
        selected_screensaver = _screensavers.current_item

        if selected_screensaver and not view_manager.create_view(
            "picoware/apps/screensavers/%s" % selected_screensaver
        ):
            view_manager.alert("Failed to load: %s" % selected_screensaver)
            _screensavers.draw()


def stop(view_manager) -> None:
    """Stop the screensavers app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from gc import collect

    global _screensavers
    if _screensavers is not None:
        del _screensavers
        _screensavers = None
    if _app_loader is not None:
        _app_loader.cleanup_modules()
    collect()
