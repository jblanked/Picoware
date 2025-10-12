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
        _library.add_item("Applications")
        _library.add_item("Editor")
        _library.add_item("File Browser")
        _library.add_item("Games")
        _library.add_item("Screensavers")
        _library.add_item("System")
        if view_manager.get_wifi():
            _library.add_item("WiFi")
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
        input_manager.reset()
        _library.scroll_up()
    elif button == BUTTON_DOWN:
        input_manager.reset()
        _library.scroll_down()
    elif button in (BUTTON_BACK, BUTTON_LEFT):
        _library_index = 0
        input_manager.reset()
        view_manager.back()
    elif button in (BUTTON_CENTER, BUTTON_RIGHT):
        input_manager.reset()
        _library_index = _library.get_selected_index()

        app_map = {
            0: "Applications",
            1: "Editor",
            2: "File Browser",
            3: "Games",
            4: "Screensavers",
            5: "System",
            6: "WiFi",
        }

        if app_map.get(_library_index) == "System":
            from picoware.applications.system import system

            view_manager.add(View("system", system.run, system.start, system.stop))
            view_manager.switch_to("system")
        elif app_map.get(_library_index) == "WiFi":
            from picoware.applications.wifi import wifi

            view_manager.add(View("wifi", wifi.run, wifi.start, wifi.stop))
            view_manager.switch_to("wifi")
        elif app_map.get(_library_index) == "Screensavers":
            from picoware.applications import screensavers

            view_manager.add(
                View(
                    "screensavers",
                    screensavers.run,
                    screensavers.start,
                    screensavers.stop,
                )
            )
            view_manager.switch_to("screensavers")
        elif app_map.get(_library_index) == "Editor":
            from picoware.applications import editor

            view_manager.add(View("editor", editor.run, editor.start, editor.stop))
            view_manager.switch_to("editor")
        elif app_map.get(_library_index) == "Applications":
            from picoware.applications import applications

            view_manager.add(
                View(
                    "applications",
                    applications.run,
                    applications.start,
                    applications.stop,
                )
            )
            view_manager.switch_to("applications")
        elif app_map.get(_library_index) == "File Browser":
            from picoware.applications import file_browser

            view_manager.add(
                View(
                    "file_browser",
                    file_browser.run,
                    file_browser.start,
                    file_browser.stop,
                )
            )
            view_manager.switch_to("file_browser")
        elif app_map.get(_library_index) == "Games":
            from picoware.applications import games

            view_manager.add(View("games", games.run, games.start, games.stop))
            view_manager.switch_to("games")


def stop(view_manager) -> None:
    """Stop the app."""
    from gc import collect

    global _library
    if _library:
        del _library
        _library = None
    collect()
