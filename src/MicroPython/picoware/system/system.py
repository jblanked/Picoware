class System:
    """Handle basic system operations."""

    def __init__(self):
        from picoware_boards import BOARD_ID

        self._board_id = BOARD_ID

    @property
    def board_id(self) -> int:
        """Return the board ID."""
        return self._board_id

    @property
    def board_name(self):
        """Return the board name."""
        from picoware_boards import get_device_name

        return get_device_name()

    @property
    def device_name(self):
        """Return the device name."""
        from picoware_boards import get_current_name

        return get_current_name()

    @property
    def free_psram(self):
        """Return the amount of free PSRAM memory."""
        from picoware_boards import BOARD_HAS_PSRAM

        if BOARD_HAS_PSRAM == 0:
            return 0

        from picoware.system.psram import PSRAM

        psram = PSRAM()
        return psram.free_heap_size

    @property
    def free_heap(self) -> int:
        """Return the amount of free heap memory."""
        from gc import mem_free

        return mem_free()

    @property
    def has_psram(self) -> bool:
        """Return True if the device has PSRAM capabilities."""
        from picoware_boards import BOARD_HAS_PSRAM

        return BOARD_HAS_PSRAM == 1

    @property
    def has_sd_card(self) -> bool:
        """Return True if the device has an SD card slot."""
        from picoware_boards import BOARD_HAS_SD

        return BOARD_HAS_SD == 1

    @property
    def has_touch(self):
        """Return True if the device has touch capabilities."""
        from picoware_boards import BOARD_HAS_TOUCH

        return BOARD_HAS_TOUCH == 1

    @property
    def has_wifi(self):
        """Return True if the device has WiFi capabilities."""
        from picoware_boards import BOARD_HAS_WIFI

        return BOARD_HAS_WIFI == 1

    @property
    def is_circular(self):
        """Return True if the device has a circular display."""
        from picoware_boards import is_circular

        return is_circular(self._board_id)

    @property
    def free_flash(self):
        """Return the free flash memory size."""
        from os import statvfs

        stat = statvfs("/")
        free = stat[0] * stat[3]

        return free

    @property
    def total_flash(self):
        """Return the total flash memory size."""
        from os import statvfs

        stat = statvfs("/")
        size = stat[1] * stat[2]

        return size

    @property
    def used_flash(self):
        """Return the used flash memory size."""
        from os import statvfs

        stat = statvfs("/")
        size = stat[1] * stat[2]
        free = stat[0] * stat[3]
        used = size - free

        return used

    @property
    def total_heap(self):
        """Return the total heap memory size."""
        from gc import mem_free, mem_alloc

        return mem_free() + mem_alloc()

    @property
    def total_psram(self):
        """Return the total PSRAM memory size."""
        from picoware_boards import BOARD_HAS_PSRAM

        if BOARD_HAS_PSRAM == 0:
            return 0

        from picoware.system.psram import PSRAM

        psram = PSRAM()
        return psram.total_heap_size

    @property
    def used_heap(self):
        """Return the total heap memory used."""
        from gc import mem_alloc

        return mem_alloc()

    @property
    def used_psram(self):
        """Return the total PSRAM memory used."""
        from picoware_boards import BOARD_HAS_PSRAM

        if BOARD_HAS_PSRAM == 0:
            return 0

        from picoware.system.psram import PSRAM

        psram = PSRAM()
        return psram.used_heap_size

    @property
    def version(self) -> str:
        """Return the Picoware version."""
        return "1.6.1"

    def bootloader_mode(self):
        """Enter the bootloader mode."""
        from machine import bootloader

        bootloader()

    def hard_reset(self):
        """Reboot the system."""
        from machine import reset

        reset()

    def shutdown_device(self, view_manager=None):
        """Shutdown the device."""
        from picoware_boards import BOARD_HAS_PSRAM

        if BOARD_HAS_PSRAM == 0:
            return

        from picoware_southbridge import is_power_off_supported, write_power_off_delay

        if is_power_off_supported():
            if view_manager:
                view_manager.alert("This device will power off in 5 seconds...")
                write_power_off_delay(0)

    def soft_reset(self):
        """Reboot the system without resetting the hardware."""
        from machine import soft_reset

        soft_reset()
