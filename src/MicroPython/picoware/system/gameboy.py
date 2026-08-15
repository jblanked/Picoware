"""GameBoy - Game Boy emulator interface."""

import gameboy


class GameBoy(gameboy.GameBoy):
    """Class for the GameBoy app"""

    __slots__ = (
        "rom_path",
        "running",
    )
