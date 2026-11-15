"""Custom - External Picoware applications."""

from picoware.system.decorator import storage_required

_applications = None
_applications_index = 0
_app_loader = None


@storage_required
def start(view_manager) -> bool:
    """Start the app.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True on success.
    """
    from picoware.gui.menu import Menu

    # create apps folder if it doesn't exist
    view_manager.storage.mkdir("picoware/apps")

    global _applications
    global _app_loader

    if _applications:
        del _applications
        _applications = None

    _applications = Menu(
        view_manager.draw,
        "Custom",
        0,
        view_manager.draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
        view_manager.foreground_color,
        2,
    )
    _app_loader = view_manager.app_loader

    for app in _app_loader.list_available_apps():
        _applications.add_item(app)

    _applications.set_selected(_applications_index)

    _applications.draw()
    return True


def run(view_manager) -> None:
    """Run the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_CENTER,
        BUTTON_RIGHT,
    )

    global _applications_index

    if not _applications:
        return

    button: int = view_manager.button

    if button in (BUTTON_UP, BUTTON_LEFT):
        _applications.scroll_up()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        _applications.scroll_down()
    elif button == BUTTON_BACK:
        _applications_index = 0
        view_manager.back()
    elif button == BUTTON_CENTER:
        _applications_index = _applications.selected_index

        # Get the selected app name
        selected_app = _applications.current_item

        if selected_app and not view_manager.create_view(
            "picoware/apps/%s" % selected_app
        ):
            view_manager.alert("Failed to load: %s" % selected_app)
            _applications.draw()


def stop(view_manager) -> None:
    """Stop the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from gc import collect

    global _applications
    if _applications is not None:
        del _applications
        _applications = None
    if _app_loader is not None:
        _app_loader.cleanup_modules()
    collect()
