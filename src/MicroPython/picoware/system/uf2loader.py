import uf2loader as _uf2


class UF2Loader:
    """Flash UF2 firmware files to the device."""
    def flash(self, filename: str) -> None:
        """Flash a UF2 firmware file to the device.

        Args:
            filename (str): The path to the UF2 file to be flashed.
        """
        try:
            _uf2.flash_uf2(filename)
        except Exception as e:
            print(f"Error flashing UF2 file: {e}")
