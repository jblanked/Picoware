_usb = None
_initialized = False


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.system.usb_keyboard import USBKeyboard

    view_manager.alert(
        "USB Keyboard is about to start.. make sure you have a usb cable connected before clicking `Back`"
    )
    global _usb, _initialized
    _usb = USBKeyboard(
        manufacturer="MicroPython", product="Pico Keyboard", serial="000001"
    )
    view_manager.draw.erase()
    view_manager.draw._text(10, 40, "Press any key...", view_manager.foreground_color)
    view_manager.draw.swap()
    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK

    global _usb, _initialized

    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()

    if not _usb:
        return

    if not _initialized:
        _usb.init()
        _initialized = True

    if button != -1:
        _usb.type_string(inp.button_to_char(button))
        inp.reset()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _usb, _initialized
    if _usb is not None:
        del _usb
        _usb = None
    _initialized = False

    collect()
