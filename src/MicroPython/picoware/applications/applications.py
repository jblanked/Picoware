_applications = None
_applications_index = 0
_app_loader = None


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.gui.menu import Menu
    from picoware.system.app_loader import AppLoader

    # create apps folder if it doesn't exist
    view_manager.get_storage().mkdir("picoware/apps")

    global _applications
    global _applications_index
    global _app_loader

    if _app_loader:
        del _app_loader
        _app_loader = None

    if _applications:
        del _applications
        _applications = None

    _applications = Menu(
        view_manager.draw,
        "Applications",
        0,
        320,
        view_manager.get_foreground_color(),
        view_manager.get_background_color(),
        view_manager.get_selected_color(),
        view_manager.get_foreground_color(),
        2,
    )
    _app_loader = AppLoader(view_manager)

    for app in _app_loader.list_available_apps():
        _applications.add_item(app)

    _applications.set_selected(_applications_index)

    _applications.draw()
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

    global _applications_index, _app_loader

    if not _applications:
        return

    input_manager = view_manager.input_manager
    button: int = input_manager.get_last_button()

    if button == BUTTON_UP:
        input_manager.reset()
        _applications.scroll_up()
    elif button == BUTTON_DOWN:
        input_manager.reset()
        _applications.scroll_down()
    elif button in (BUTTON_BACK, BUTTON_LEFT):
        _applications_index = 0
        input_manager.reset()
        view_manager.back()
    elif button in (BUTTON_CENTER, BUTTON_RIGHT):
        input_manager.reset()
        _applications_index = _applications.get_selected_index()

        # Get the selected app name
        selected_app = _applications.get_current_item()

        if selected_app and _app_loader:
            # Try to load the app
            app_module = _app_loader.load_app(selected_app)
            if app_module:
                # Create a view for the app and switch to it
                app_view_name = f"app_{selected_app}"

                # Check if view already exists
                if view_manager.get_view(app_view_name) is None:
                    app_view = View(
                        app_view_name, app_module.run, app_module.start, app_module.stop
                    )
                    view_manager.add(app_view)

                view_manager.switch_to(app_view_name)


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _applications, _app_loader
    if _applications is not None:
        del _applications
        _applications = None
    if _app_loader is not None:
        _app_loader.cleanup_modules()
        del _app_loader
        _app_loader = None
    collect()
