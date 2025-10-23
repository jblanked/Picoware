_system = None
_system_index = 0


def start(view_manager) -> bool:
    """Start the app."""
    from picoware.gui.menu import Menu

    global _system
    if _system is None:
        _system = Menu(
            view_manager.draw,
            "System",
            0,
            320,
            view_manager.get_foreground_color(),
            view_manager.get_background_color(),
            view_manager.get_selected_color(),
            view_manager.get_foreground_color(),
            2,
        )
        _system.add_item("Settings")
        _system.add_item("About Picoware")
        _system.add_item("System Info")
        _system.add_item("Bootloader Mode")
        _system.add_item("Restart Device")
        _system.add_item("Shutdown Device")

        _system.set_selected(_system_index)

        _system.draw()
    return True


def run(view_manager) -> None:
    """Run the app."""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_CENTER,
        BUTTON_RIGHT,
    )

    global _system
    if not _system:
        return
    global _system_index

    input_manager = view_manager.input_manager
    button: int = input_manager.get_last_button()

    if button == BUTTON_UP:
        input_manager.reset()
        _system.scroll_up()
    elif button == BUTTON_DOWN:
        input_manager.reset()
        _system.scroll_down()
    elif button in (BUTTON_BACK, BUTTON_LEFT):

        input_manager.reset()
        view_manager.back()
        _system_index = 0
    elif button in (BUTTON_CENTER, BUTTON_RIGHT):
        input_manager.reset()
        _system_index = _system.get_selected_index()
        if _system_index == 0:
            from picoware.applications.system import settings
            from picoware.system.view import View

            view_manager.add(
                View("settings", settings.run, settings.start, settings.stop)
            )
            view_manager.switch_to("settings")
        elif _system_index == 1:
            from picoware.applications.system import about
            from picoware.system.view import View

            view_manager.add(View("about", about.run, about.start, about.stop))
            view_manager.switch_to("about")
        elif _system_index == 2:
            from picoware.applications.system import system_info
            from picoware.system.view import View

            view_manager.add(
                View(
                    "system_info", system_info.run, system_info.start, system_info.stop
                )
            )
            view_manager.switch_to("system_info")
        elif _system_index == 3:
            from picoware.system.system import System

            system = System()
            system.bootloader_mode()
        elif _system_index == 4:
            from picoware.system.system import System

            system = System()
            system.hard_reset()
        elif _system_index == 5:
            from picoware.system.system import System

            system = System()
            system.shutdown_device(view_manager)


def stop(view_manager) -> None:
    """Stop the app."""
    from gc import collect

    global _system
    if _system:
        del _system
        _system = None
    collect()
