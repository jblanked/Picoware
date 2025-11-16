class System:
    """Handle basic system operations."""

    def __init__(self):
        pass

    @property
    def board_id(self):
        """Return the board ID."""
        from picoware_boards import get_current_id

        return get_current_id()

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
    def has_psram(self):
        """Return True if the device has PSRAM capabilities."""
        from picoware_boards import has_psram, get_current_id

        board_id = get_current_id()
        return has_psram(board_id)

    @property
    def has_sd_card(self):
        """Return True if the device has an SD card slot."""
        from picoware_boards import has_sd_card, get_current_id

        board_id = get_current_id()
        return has_sd_card(board_id)

    @property
    def has_touch(self):
        """Return True if the device has touch capabilities."""
        from picoware_boards import get_current_id, has_touch

        board_id = get_current_id()
        return has_touch(board_id)

    @property
    def has_wifi(self):
        """Return True if the device has WiFi capabilities."""
        from picoware_boards import has_wifi, get_current_id

        board_id = get_current_id()
        return has_wifi(board_id)

    @property
    def is_circular(self):
        """Return True if the device has a circular display."""
        from picoware_boards import get_current_id, is_circular

        board_id = get_current_id()
        return is_circular(board_id)

    def bootloader_mode(self):
        """Enter the bootloader mode."""
        from machine import bootloader

        bootloader()

    def free_heap(self):
        """Return the amount of free heap memory."""
        from gc import mem_free

        return mem_free()

    def free_psram(self):
        """Return the amount of free PSRAM memory."""
        from picoware_boards import get_current_id, has_psram

        board_id = get_current_id()
        if not has_psram(board_id):
            # waveshare boards do not have PSRAM
            return 0

        from picoware.system.psram import PSRAM

        psram = PSRAM()
        return psram.free_heap_size

    def hard_reset(self):
        """Reboot the system."""
        from machine import reset

        reset()

    def shutdown_device(self, view_manager=None):
        """Shutdown the device."""
        from picoware_boards import get_current_id, has_psram

        board_id = get_current_id()
        if not has_psram(board_id):
            # waveshare boards do not have PSRAM
            return

        from picoware_southbridge import is_power_off_supported, write_power_off_delay

        if is_power_off_supported():

            if view_manager:
                from picoware.gui.alert import Alert

                draw = view_manager.get_draw()
                draw.clear()
                alert = Alert(
                    view_manager.get_draw(),
                    "The device will power off in 5 seconds...",
                    view_manager.get_foreground_color(),
                    view_manager.get_background_color(),
                )
                alert.draw("Warning")
                write_power_off_delay(0)

    def soft_reset(self):
        """Reboot the system without resetting the hardware."""
        from machine import soft_reset

        soft_reset()

    def total_heap(self):
        """Return the total heap memory size."""
        from gc import mem_free, mem_alloc

        return mem_free() + mem_alloc()

    def total_psram(self):
        """Return the total PSRAM memory size."""
        from picoware_boards import get_current_id, has_psram

        board_id = get_current_id()
        if not has_psram(board_id):
            # waveshare boards do not have PSRAM
            return 0

        from picoware.system.psram import PSRAM

        psram = PSRAM()
        return psram.total_heap_size

    def used_heap(self):
        """Return the total heap memory used."""
        from gc import mem_alloc

        return mem_alloc()

    def used_psram(self):
        """Return the total PSRAM memory used."""
        from picoware_boards import get_current_id, has_psram

        board_id = get_current_id()
        if not has_psram(board_id):
            # waveshare boards do not have PSRAM
            return 0

        from picoware.system.psram import PSRAM

        psram = PSRAM()
        return psram.used_heap_size
