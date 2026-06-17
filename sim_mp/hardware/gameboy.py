import sim_runtime


class GameBoy:
    def __init__(self):
        """Initialize GameBoy emulator with direct-draw placeholder."""
        self.rom_path = ""
        self.save_state_path = None
        self.running = False
        self.frame = 0

    def __str__(self):
        """Return a readable representation."""
        return "GameBoy(rom_path={!r}, running={})".format(self.rom_path, self.running)

    def start(self, rom_path, save_state_path=None):
        """Load a ROM and start the emulator."""
        self.rom_path = rom_path
        self.save_state_path = save_state_path
        self.running = True
        self.frame = 0
        self._draw("GameBoy Emulator", "ROM: " + str(rom_path))
        return True

    def stop(self):
        """Stop the emulator."""
        self.running = False
        return None

    def run(self, button=-1):
        """Run one frame with the given button input."""
        if not self.running:
            return False
        self.frame += 1
        if self.frame % 6 == 0:
            self._draw("GameBoy Emulator", "Input: {}".format(button))
        return True

    def _draw(self, title, subtitle):
        lcd = getattr(sim_runtime, "_lcd", None)
        if lcd is None:
            return
        lcd._clear(0)
        lcd._rectangle(24, 16, 272, 240, 0x07E0)
        lcd._text(42, 36, title, 0xFFFF, 1)
        lcd._text(42, 58, subtitle[:32], 0xFFFF, 1)
        lcd._text(42, 88, "Simulator placeholder", 0xFFE0, 1)
        lcd._text(42, 108, "Use BACK to exit", 0xFFE0, 1)
        lcd.swap()
