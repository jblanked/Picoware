"""ESP Flasher Utility App for Picoware."""
from picoware.gui.file_browser import FileBrowser, FILE_BROWSER_SELECTOR

def _flash(view_manager, firmware_path: str, chip: str = "esp32s2") -> bool:
    """Flash the ESP32 with the given firmware file."""
    from picoware.system.drivers.espflasher import ESPFlasher
    from picoware.system.boards import BOARD_FLIPPER_ZERO, BOARD_HAS_PICOCALC
    from machine import Pin

    s = view_manager.storage

    _prefix = s.vfs_prefix
    path = firmware_path
    if not firmware_path.startswith(_prefix):
        path = f"{_prefix}{firmware_path}"

    esp = None
    reset = None
    gpio0 = None
    success = False
    _id = view_manager.board_id
    try:
        if _id == BOARD_FLIPPER_ZERO:
            reset = Pin(Pin.cpu.B2, Pin.OUT) # on devboard, its the 6th pin from the left (RTS/EN)
            gpio0 = Pin(Pin.cpu.C3, Pin.OUT) # on devboard, its the 7th pin from the left (DTR/BOOT)
        elif BOARD_HAS_PICOCALC == 1:
            raise ValueError(f"Unsupported board ID: {_id}\nThis is not supported for PicoCalc.")
        else:
            raise ValueError(f"Unsupported board ID: {_id}\nContact JBlanked to add support for this board.")

        esp = ESPFlasher(reset, gpio0, view_manager.uart, chip=chip)

        # Enter bootloader download mode, at 115200
        attempts = 10
        esp.bootloader(attempts)

        # change to higher/lower baudrate
        esp.set_baudrate(460800)

        # Must call this first before any flash functions.
        esp.flash_attach()

        # Read flash size
        size = esp.flash_read_size()

        # Configure flash parameters.
        esp.flash_config(size)

        # Write firmware image from internal storage.
        esp.flash_write_file(path, blksize=0x400, progress_interval=128)

        # Resets the ESP32 chip.
        esp.reboot()

        success = True

    except Exception as e:
        view_manager.log(f"Flashing failed: {e}")
        success = False
    finally:
        if esp is not None:
            del esp
            esp = None
        if reset is not None:
            del reset
            reset = None
        if gpio0 is not None:
            del gpio0
            gpio0 = None
    return success

_file_browser = None


def start(view_manager) -> bool:
    """Start the app"""
    global _file_browser
    
    _file_browser = FileBrowser(
        view_manager,
        mode=FILE_BROWSER_SELECTOR,
    )
    return _file_browser is not None


def run(view_manager) -> None:
    """Run the app"""
    global _file_browser

    if not _file_browser.run():
        if _file_browser.mode == FileBrowser.MODE_SELECT:
            selected_path = _file_browser.path
            success = _flash(view_manager, selected_path)
            msg = (
                f"Flashed {selected_path} successfully"
                if success
                else f"Flashing {selected_path} failed"
            )
            view_manager.alert(msg, back=True)
        else:
            view_manager.back()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _file_browser
    if _file_browser is not None:
        del _file_browser
        _file_browser = None
    collect()