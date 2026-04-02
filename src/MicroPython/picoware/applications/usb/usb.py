"""USB Apps Menu - Central hub for all USB applications"""

_usb = None
_usb_index = 0


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.gui.menu import Menu

    # create usb folder
    view_manager.storage.mkdir("picoware/usb")

    global _usb

    if _usb is None:
        _usb = Menu(
            view_manager.draw,
            "USB",
            0,
            view_manager.draw.size.y,
            view_manager.foreground_color,
            view_manager.background_color,
            view_manager.selected_color,
            view_manager.foreground_color,
            2,
        )
        _usb.add_item("Keyboard")
        _usb.set_selected(_usb_index)

        _usb.draw()
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

    if not _usb:
        return

    global _usb_index

    input_manager = view_manager.input_manager
    button: int = input_manager.button

    if button in (BUTTON_UP, BUTTON_LEFT):
        input_manager.reset()
        _usb.scroll_up()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        input_manager.reset()
        _usb.scroll_down()
    elif button == BUTTON_BACK:
        _usb_index = 0
        input_manager.reset()
        view_manager.back()
    elif button == BUTTON_CENTER:
        input_manager.reset()
        _usb_index = _usb.selected_index

        if _usb_index == 0:
            # Keyboard
            from picoware.applications.usb import keyboard

            view_manager.add(
                View(
                    "usb_keyboard",
                    keyboard.run,
                    keyboard.start,
                    keyboard.stop,
                )
            )
            view_manager.switch_to("usb_keyboard")


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _usb
    if _usb is not None:
        del _usb
        _usb = None
    collect()
