_usb = None
_initialized = False
_key_map = None


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.system.usb import USBKeyboard
    from picoware.system.buttons import (
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_RIGHT,
        BUTTON_CENTER,
        BUTTON_0,
        BUTTON_1,
        BUTTON_2,
        BUTTON_3,
        BUTTON_4,
        BUTTON_5,
        BUTTON_6,
        BUTTON_7,
        BUTTON_8,
        BUTTON_9,
    )

    view_manager.alert(
        "USB Numpad is about to start.. make sure you have a USB cable connected before clicking `Back`"
    )
    global _usb, _initialized, _key_map
    _usb = USBKeyboard(
        manufacturer="MicroPython", product="Picoware Numpad", serial="000003"
    )
    view_manager.draw.erase()
    d = view_manager.draw
    fg = view_manager.foreground_color
    d._text(10, 10, "Numpad", fg)
    d._text(10, 30, "0-9: Numpad digits", fg)
    d._text(10, 45, "Up: +    Down: -", fg)
    d._text(10, 60, "Left: *  Right: /", fg)
    d._text(10, 75, "Center: Enter", fg)
    d.swap()
    _key_map = {
        BUTTON_0: 0x62,
        BUTTON_1: 0x59,
        BUTTON_2: 0x5A,
        BUTTON_3: 0x5B,
        BUTTON_4: 0x5C,
        BUTTON_5: 0x5D,
        BUTTON_6: 0x5E,
        BUTTON_7: 0x5F,
        BUTTON_8: 0x60,
        BUTTON_9: 0x61,
        BUTTON_UP: 0x57,
        BUTTON_DOWN: 0x56,
        BUTTON_LEFT: 0x55,
        BUTTON_RIGHT: 0x54,
        BUTTON_CENTER: 0x58,
    }
    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK

    global _initialized

    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
        return

    if not _usb:
        return

    if not _initialized:
        _usb.init()
        _initialized = True

    if button != -1:
        if button in _key_map:
            _usb.press(0, _key_map[button])
        inp.reset()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _usb, _initialized, _key_map
    if _usb is not None:
        del _usb
        _usb = None
    _initialized = False
    _key_map = None

    collect()
