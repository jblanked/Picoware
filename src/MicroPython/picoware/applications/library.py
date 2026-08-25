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
        _library.add_item("Agent")
        _library.add_item("Applications")
        _library.add_item("App Store")
        _library.add_item("Bluetooth")
        _library.add_item("Email")
        _library.add_item("File Manager")
        _library.add_item("FlipSocial")
        _library.add_item("GameBoy Emulator")
        _library.add_item("Games")
        _library.add_item("MMBasic")
        _library.add_item("Python Editor")
        _library.add_item("Python REPL")
        _library.add_item("Screensavers")
        _library.add_item("Scripts")
        _library.add_item("System")
        _library.add_item("Text Editor")
        _library.add_item("USB")
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

        app_map = {
            0: "Agent",
            1: "Applications",
            2: "App Store",
            3: "Bluetooth",
            4: "Email",
            5: "File Manager",
            6: "FlipSocial",
            7: "GameBoy Emulator",
            8: "Games",
            9: "MMBasic",
            10: "Python Editor",
            11: "Python REPL",
            12: "Screensavers",
            13: "Scripts",
            14: "System",
            15: "Text Editor",
            16: "USB",
            17: "WiFi",
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
            from picoware.applications import python_editor

            view_manager.add(
                View(
                    "editor", python_editor.run, python_editor.start, python_editor.stop
                )
            )
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
        elif app_map.get(_library_index) == "GameBoy Emulator":
            from picoware.applications import gameboy

            view_manager.add(
                View(
                    "gameboy",
                    gameboy.run,
                    gameboy.start,
                    gameboy.stop,
                )
            )
            view_manager.switch_to("gameboy")
        elif app_map.get(_library_index) == "USB":
            from picoware.applications.usb import usb

            view_manager.add(
                View(
                    "usb",
                    usb.run,
                    usb.start,
                    usb.stop,
                )
            )
            view_manager.switch_to("usb")
        elif app_map.get(_library_index) == "Python REPL":
            from picoware.applications import repl

            view_manager.add(View("repl", repl.run, repl.start, repl.stop))
            view_manager.switch_to("repl")
        elif app_map.get(_library_index) == "Text Editor":
            from picoware.applications import text_editor

            view_manager.add(
                View(
                    "text_editor",
                    text_editor.run,
                    text_editor.start,
                    text_editor.stop,
                )
            )
            view_manager.switch_to("text_editor")
        elif app_map.get(_library_index) == "Agent":
            from picoware.applications import agent

            view_manager.add(View("agent", agent.run, agent.start, agent.stop))
            view_manager.switch_to("agent")
        elif app_map.get(_library_index) == "Scripts":
            from picoware.applications import scripts

            view_manager.add(
                View(
                    "scripts",
                    scripts.run,
                    scripts.start,
                    scripts.stop,
                )
            )
            view_manager.switch_to("scripts")
        elif app_map.get(_library_index) == "Email":
            from picoware.applications import email

            view_manager.add(
                View(
                    "email",
                    email.run,
                    email.start,
                    email.stop,
                )
            )
            view_manager.switch_to("email")
        elif app_map.get(_library_index) == "MMBasic":
            from picoware.applications import mmbasic

            view_manager.add(
                View(
                    "mmbasic",
                    mmbasic.run,
                    mmbasic.start,
                    mmbasic.stop,
                )
            )
            view_manager.switch_to("mmbasic")
        elif app_map.get(_library_index) == "FlipSocial":
            from picoware.applications import FlipSocial

            view_manager.add(
                View(
                    "flipsocial",
                    FlipSocial.run,
                    FlipSocial.start,
                    FlipSocial.stop,
                )
            )
            view_manager.switch_to("flipsocial")


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
