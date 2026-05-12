import gameboy


class GameBoy(gameboy.GameBoy):
    """Class for the GameBoy app"""

    __slots__ = (
        "rom_path",
        "running",
    )
