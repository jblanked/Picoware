import uf2loader as _uf2


class UF2Loader:
    """UF2Loader class for flashing UF2 firmware files to devices."""

    def __init__(self) -> None:
        pass

    def flash(self, filename: str) -> None:
        """
        Flash a UF2 firmware file to the device.

        Args:
            filename (str): The path to the UF2 file to be flashed.

        Returns:
            None
        """
        try:
            _uf2.flash_uf2(filename)
        except Exception as e:
            print(f"Error flashing UF2 file: {e}")
