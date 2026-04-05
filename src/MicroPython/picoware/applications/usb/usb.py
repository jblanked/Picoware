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
        _usb.add_item("Media Keys")
        _usb.add_item("Numpad")
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

    button: int = view_manager.button

    if button in (BUTTON_UP, BUTTON_LEFT):
        _usb.scroll_up()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        _usb.scroll_down()
    elif button == BUTTON_BACK:
        _usb_index = 0
        view_manager.back()
    elif button == BUTTON_CENTER:
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
        elif _usb_index == 1:
            # Media Keys
            from picoware.applications.usb import media_keys

            view_manager.add(
                View(
                    "usb_media_keys",
                    media_keys.run,
                    media_keys.start,
                    media_keys.stop,
                )
            )
            view_manager.switch_to("usb_media_keys")
        elif _usb_index == 2:
            # Numpad
            from picoware.applications.usb import numpad

            view_manager.add(
                View(
                    "usb_numpad",
                    numpad.run,
                    numpad.start,
                    numpad.stop,
                )
            )
            view_manager.switch_to("usb_numpad")


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _usb
    if _usb is not None:
        del _usb
        _usb = None
    collect()
