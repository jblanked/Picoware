"""Library - Central hub for all Picoware apps."""

_library = None
_library_index = 0


def start(view_manager) -> bool:
    """Start the app.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True on success.
    """
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
        _library.add_item("Bluetooth")
        _library.add_item("Infrared")
        _library.add_item("Settings")
        _library.add_item("System")
        _library.add_item("USB")
        _library.add_item("Utilities")
        _library.add_item("WiFi")
        _library.set_selected(_library_index)

        _library.draw()
    return True


def run(view_manager) -> None:
    """Run the app.

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

    if not _library:
        return

    global _library_index

    button: int = view_manager.button

    if button in (BUTTON_UP, BUTTON_LEFT):
        _library.scroll_up()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        _library.scroll_down()
    elif button == BUTTON_BACK:
        _library_index = 0
        view_manager.back()
    elif button == BUTTON_CENTER:
        _library_index = _library.selected_index

        if _library.current_item == "Applications":
            from picoware.applications.applications import applications

            view_manager.add(
                View(
                    "applications",
                    applications.run,
                    applications.start,
                    applications.stop,
                )
            )
            view_manager.switch_to("applications")
        elif _library.current_item == "Bluetooth":
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
        elif _library.current_item == "Infrared":
            from picoware.applications import ir

            view_manager.add(View("ir",ir.run,ir.start,ir.stop))
            view_manager.switch_to("ir")
        elif _library.current_item == "Settings":
            from picoware.applications import settings

            view_manager.add(
                View("settings", settings.run, settings.start, settings.stop)
            )
            view_manager.switch_to("settings")
        elif _library.current_item == "System":
            from picoware.applications.system import system

            view_manager.add(View("system", system.run, system.start, system.stop))
            view_manager.switch_to("system")
        elif _library.current_item == "USB":
            from picoware.applications.usb import usb

            view_manager.add(View( "usb",usb.run,usb.start,usb.stop))
            view_manager.switch_to("usb")
        elif _library.current_item == "Utilities":
            from picoware.applications.utilities import utilities

            view_manager.add(View("utilities", utilities.run, utilities.start, utilities.stop))
            view_manager.switch_to("utilities")
        elif _library.current_item == "WiFi":
            from picoware.applications.wifi import wifi

            view_manager.add(View("wifi", wifi.run, wifi.start, wifi.stop))
            view_manager.switch_to("wifi")
        


def stop(view_manager) -> None:
    """Stop the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from gc import collect

    global _library
    if _library:
        del _library
        _library = None
    collect()
