_usb = None
_initialized = False
_key_map = None


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.system.usb import USBMedia
    from picoware.system.buttons import (
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_RIGHT,
        BUTTON_CENTER,
        BUTTON_0,
    )

    view_manager.alert(
        "USB Media Keys is about to start.. make sure you have a USB cable connected before clicking `Back`"
    )
    global _usb, _initialized, _key_map
    _usb = USBMedia(manufacturer="MicroPython", product="Pico Media", serial="000002")
    view_manager.draw.erase()
    d = view_manager.draw
    fg = view_manager.foreground_color
    d._text(10, 10, "Media Keys", fg)
    d._text(10, 30, "Up: Vol+    Down: Vol-", fg)
    d._text(10, 45, "Left: Prev  Right: Next", fg)
    d._text(10, 60, "Center: Play/Pause", fg)
    d._text(10, 75, "0: Mute", fg)
    d.swap()
    _key_map = {
        BUTTON_CENTER: USBMedia.USAGE_PLAY_PAUSE,
        BUTTON_UP: USBMedia.USAGE_VOL_UP,
        BUTTON_DOWN: USBMedia.USAGE_VOL_DOWN,
        BUTTON_LEFT: USBMedia.USAGE_PREV_TRACK,
        BUTTON_RIGHT: USBMedia.USAGE_NEXT_TRACK,
        BUTTON_0: USBMedia.USAGE_MUTE,
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

    if button in _key_map:
        _usb.press(_key_map[button])
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
