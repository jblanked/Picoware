"""Library - Central hub for all Picoware apps."""

_utilities = None
_utilities_index = 0


def start(view_manager) -> bool:
    """Start the app.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True on success.
    """
    from picoware.gui.menu import Menu

    global _utilities

    if _utilities is None:
        _utilities = Menu(
            view_manager.draw,
            "Utilities",
            0,
            view_manager.draw.size.y,
            view_manager.foreground_color,
            view_manager.background_color,
            view_manager.selected_color,
            view_manager.foreground_color,
            2,
        )
        _utilities.add_item("Email")
        _utilities.add_item("File Manager")
        _utilities.add_item("PicoIDE")
        _utilities.add_item("Python REPL")
        _utilities.add_item("Serial Terminal")
        _utilities.add_item("SSH Terminal")
        _utilities.set_selected(_utilities_index)

        _utilities.draw()
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

    if not _utilities:
        return

    global _utilities_index

    button: int = view_manager.button

    if button in (BUTTON_UP, BUTTON_LEFT):
        _utilities.scroll_up()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        _utilities.scroll_down()
    elif button == BUTTON_BACK:
        _utilities_index = 0
        view_manager.back()
    elif button == BUTTON_CENTER:
        _utilities_index = _utilities.selected_index

        if _utilities.current_item == "Email":
            from picoware.applications.utilities import email

            view_manager.add(
                View(
                    "email",
                    email.run,
                    email.start,
                    email.stop,
                )
            )
            view_manager.switch_to("email")
        elif _utilities.current_item == "File Manager":
            from picoware.applications.utilities import file_manager

            view_manager.add(
                View(
                    "file_manager",
                    file_manager.run,
                    file_manager.start,
                    file_manager.stop,
                )
            )
            view_manager.switch_to("file_manager")
        elif _utilities.current_item == "PicoIDE":
            from picoware.applications.utilities import pico_ide

            view_manager.add(
                View(
                    "ide", pico_ide.run, pico_ide.start, pico_ide.stop
                )
            )
            view_manager.switch_to("ide")
        elif _utilities.current_item == "Python REPL":
            from picoware.applications.utilities import repl

            view_manager.add(View("repl", repl.run, repl.start, repl.stop))
            view_manager.switch_to("repl")
        elif _utilities.current_item == "Serial Terminal":
            from picoware.applications.utilities import serial
            view_manager.add(View("serial", serial.run, serial.start, serial.stop))
            view_manager.switch_to("serial")
        elif _utilities.current_item == "SSH Terminal":
            from picoware.applications.utilities import ssh

            view_manager.add(View("ssh", ssh.run, ssh.start, ssh.stop))
            view_manager.switch_to("ssh")


def stop(view_manager) -> None:
    """Stop the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from gc import collect

    global _utilities
    if _utilities:
        del _utilities
        _utilities = None
    collect()
