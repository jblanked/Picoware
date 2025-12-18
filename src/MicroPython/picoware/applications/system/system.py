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
            view_manager.draw.size.y,
            view_manager.foreground_color,
            view_manager.background_color,
            view_manager.selected_color,
            view_manager.foreground_color,
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
    button: int = input_manager.button

    if button in (BUTTON_UP, BUTTON_LEFT):
        input_manager.reset()
        _system.scroll_up()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        input_manager.reset()
        _system.scroll_down()
    elif button == BUTTON_BACK:

        input_manager.reset()
        view_manager.back()
        _system_index = 0
    elif button == BUTTON_CENTER:
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

            from picoware.gui.choice import Choice
            from picoware.system.vector import Vector

            choice = Choice(
                view_manager.draw,
                Vector(0, 0),
                view_manager.draw.size,
                "Shutdown Device?",
                ["No", "Yes"],
                0,
                view_manager.foreground_color,
                view_manager.background_color,
            )
            choice.draw()

            while True:
                _button = input_manager.button
                if _button == BUTTON_LEFT:
                    input_manager.reset()
                    choice.scroll_up()
                elif _button == BUTTON_RIGHT:
                    input_manager.reset()
                    choice.scroll_down()
                elif _button == BUTTON_CENTER:
                    input_manager.reset()
                    if choice.state == 1:
                        del choice
                        choice = None
                        from picoware.system.system import System

                        system = System()
                        system.shutdown_device(view_manager)
                        break

                    del choice
                    choice = None
                    input_manager.reset()
                    view_manager.draw.clear()
                    _system.draw()
                    break
                elif _button == BUTTON_BACK:
                    del choice
                    choice = None
                    input_manager.reset()
                    view_manager.draw.clear()
                    _system.draw()
                    break


def stop(view_manager) -> None:
    """Stop the app."""
    from gc import collect

    global _system
    if _system:
        del _system
        _system = None
    collect()
