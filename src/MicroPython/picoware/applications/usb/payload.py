"""USB Payload - Execute payload over USB."""
from micropython import const
from picoware.system.decorator import storage_required

STATE_BROWSER = const(0)
STATE_PAYLOAD = const(1)

_usb = None
_ducky = None
_state = STATE_BROWSER
_browser = None
_path = None

@storage_required
def start(view_manager) -> bool:
    """Start the app and warn before initializing USB.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.

    Returns:
        bool: True if the app started.
    """
    from picoware.gui.file_browser import FileBrowser
    from picoware.system.ducky import Ducky
    from picoware.system.usb import USBKeyboard
    global _usb, _ducky, _browser, _state
    try:
        _usb = USBKeyboard(
            manufacturer="MicroPython", product="Picoware Keyboard", serial="000001"
        )
        _ducky = Ducky(_usb, storage=view_manager.storage)
        _usb.init()
        _browser = FileBrowser(view_manager, start_directory="picoware/usb", allowed_extensions=["txt", "duck"])
        _state = STATE_BROWSER
        return _browser.run()
    except Exception as e:
        view_manager.alert(f"Failed to initialize USB payload: {e}")
        return False


def run(view_manager) -> None:
    """Run the app and send typed characters over USB.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
    global _state, _path
    from picoware.system.buttons import BUTTON_BACK

    button = view_manager.button

    if button == BUTTON_BACK or not _usb or not _ducky:
        view_manager.back()
        return

    if _state == STATE_BROWSER:
        continue_browsing = _browser.run()

        if not continue_browsing:
            if not _browser.path:
                view_manager.back()
                return
            # User selected a file or exited
            _path = _browser.path
            _state = STATE_PAYLOAD
            return

    elif _state == STATE_PAYLOAD:
        _ducky.exec(_path)
        _state = STATE_BROWSER
        _path = None
        return


def stop(view_manager) -> None:
    """Stop the app and clean up.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
    from gc import collect

    global _usb, _ducky
    if _usb is not None:
        del _usb
        _usb = None
    if _ducky is not None:
        del _ducky
        _ducky = None

    collect()
