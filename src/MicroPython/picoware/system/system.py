class System:
    """Handle basic system operations."""

    def __init__(self):
        pass

    def bootloader_mode(self):
        """Enter the bootloader mode."""
        import machine

        machine.bootloader()

    def free_heap(self):
        """Return the amount of free heap memory."""
        import gc

        return gc.mem_free()

    def hard_reset(self):
        """Reboot the system."""
        import machine

        machine.reset()

    def soft_reset(self):
        """Reboot the system without resetting the hardware."""
        import machine

        machine.soft_reset()

    def used_heap(self):
        """Return the total heap memory used."""
        import gc

        return gc.mem_alloc()
