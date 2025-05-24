from microcontroller import reset, RunMode, on_next_reset
from supervisor import reload as sreload
from gc import mem_free, mem_alloc


class System:
    """Handle basic system operations."""

    def __init__(self):
        pass

    def bootloader_mode(self):
        """Enter the bootloader mode."""
        on_next_reset(RunMode.BOOTLOADER)
        reset()

    def free_heap(self):
        """Return the amount of free heap memory."""
        return mem_free()

    def hard_reset(self):
        """Reboot the system."""
        reset()

    def safe_mode(self):
        """Enter the safe mode."""
        on_next_reset(RunMode.SAFE_MODE)
        reset()

    def soft_reset(self):
        """Reboot the system without resetting the hardware."""
        sreload()

    def uf2_mode(self):
        """Enter the UF2 mode."""
        on_next_reset(RunMode.UF2)
        reset()

    def used_heap(self):
        """Return the total heap memory used."""
        return mem_alloc()
