class System:
    """Handle basic system operations."""

    def __init__(self):
        pass

    @property
    def board_name(self):
        """Return the board name."""
        from os import uname

        system_info = uname()
        board_name = system_info.machine

        # remove everything after " with"
        board_name = board_name.split(" with")[0]
        return board_name

    @property
    def device_name(self):
        """Return the device name."""
        from os import uname

        system_info = uname()
        board_name = system_info.machine

        # remove everything after " with"
        name = board_name.split(" with")[0]

        if name == "Raspberry Pi Pico":
            return "PicoCalc - Pico"
        if name == "Raspberry Pi Pico W":
            return "PicoCalc - Pico W"
        if name == "Raspberry Pi Pico 2":
            return "PicoCalc - Pico 2"
        if name == "Raspberry Pi Pico 2 W":
            return "PicoCalc - Pico 2W"
        return name

    @property
    def has_wifi(self):
        """Return True if the device has WiFi capabilities."""
        from os import uname

        system_info = uname()

        return "W" in system_info.machine

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
        from picoware.system.psram import PSRAM

        psram = PSRAM()
        return psram.free_heap_size

    def hard_reset(self):
        """Reboot the system."""
        from machine import reset

        reset()

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
        from picoware.system.psram import PSRAM

        psram = PSRAM()
        return psram.total_heap_size

    def used_heap(self):
        """Return the total heap memory used."""
        from gc import mem_alloc

        return mem_alloc()

    def used_psram(self):
        """Return the total PSRAM memory used."""
        from picoware.system.psram import PSRAM

        psram = PSRAM()
        return psram.used_heap_size
