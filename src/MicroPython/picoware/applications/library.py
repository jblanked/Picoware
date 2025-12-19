_library = None
_library_index = 0


def start(view_manager) -> bool:
    """Start the app."""
    from picoware.gui.menu import Menu

    global _library

    if _library is None:
        _library = Menu(
            view_manager.draw,
            "Library",
            0,
            view_manager.draw.size.y,
            view_manager.foreground_color,
            view_manager.background_color,
            view_manager.selected_color,
            view_manager.foreground_color,
            2,
        )
        _library.add_item("Applications")
        _library.add_item("App Store")
        _library.add_item("Bluetooth")
        _library.add_item("File Manager")
        _library.add_item("Games")
        _library.add_item("Python Editor")
        _library.add_item("Screensavers")
        _library.add_item("System")
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

    if not _library:
        return

    global _library_index

    input_manager = view_manager.input_manager
    button: int = input_manager.button

    if button in (BUTTON_UP, BUTTON_LEFT):
        input_manager.reset()
        _library.scroll_up()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        input_manager.reset()
        _library.scroll_down()
    elif button == BUTTON_BACK:
        _library_index = 0
        input_manager.reset()
        view_manager.back()
    elif button == BUTTON_CENTER:
        input_manager.reset()
        _library_index = _library.selected_index

        app_map = {
            0: "Applications",
            1: "App Store",
            2: "Bluetooth",
            3: "File Manager",
            4: "Games",
            5: "Python Editor",
            6: "Screensavers",
            7: "System",
            8: "WiFi",
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
        elif app_map.get(_library_index) == "Python Editor":
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
        elif app_map.get(_library_index) == "File Manager":
            from picoware.applications import file_manager

            view_manager.add(
                View(
                    "file_manager",
                    file_manager.run,
                    file_manager.start,
                    file_manager.stop,
                )
            )
            view_manager.switch_to("file_manager")
        elif app_map.get(_library_index) == "Games":
            from picoware.applications import games

            view_manager.add(View("games", games.run, games.start, games.stop))
            view_manager.switch_to("games")
        elif app_map.get(_library_index) == "App Store":
            from picoware.applications import app_store

            view_manager.add(
                View(
                    "app_store",
                    app_store.run,
                    app_store.start,
                    app_store.stop,
                )
            )
            view_manager.switch_to("app_store")
        elif app_map.get(_library_index) == "Bluetooth":
            from picoware.applications.bluetooth import bluetooth

            view_manager.add(
                View(
                    "bluetooth",
                    bluetooth.run,
                    bluetooth.start,
                    bluetooth.stop,
                )
            )
            view_manager.switch_to("bluetooth")


def stop(view_manager) -> None:
    """Stop the app."""
    from gc import collect

    global _library
    if _library:
        del _library
        _library = None
    collect()
