import sim_runtime


class Ghouls:
    def __init__(self, username="", password="", sound_enabled=True):
        """Initialize Ghouls engine with direct-draw placeholder."""
        self.username = username
        self.password = password
        self.sound_enabled = sound_enabled
        self.is_active = True
        self.frame = 0
        self.last_input = -1
        self._draw("Ghouls Simulator")

    def start(self, *args, **kwargs):
        """Start or restart the Ghouls engine."""
        self.is_active = True
        self._draw("Ghouls Simulator")
        return True

    def stop(self):
        """Stop the Ghouls engine."""
        self.is_active = False
        return True

    def update_input(self, button):
        """Handle button input for the Ghouls engine."""
        self.last_input = button
        if button in (0xB1, 8, 27):
            self.is_active = False
        return True

    def update_draw(self):
        """Draw placeholder frame to the LCD."""
        if not self.is_active:
            return False
        self.frame += 1
        if self.frame == 1 or self.frame % 12 == 0:
            self._draw("Ghouls Simulator")
        return True

    def _draw(self, title):
        lcd = sim_runtime._lcd
        if lcd is None:
            return
        width = getattr(lcd, "width", 320)
        height = getattr(lcd, "height", 320)
        bg = 0x0841
        fg = 0xFFFF
        accent = 0xF800
        try:
            lcd._clear(bg)
            lcd._rectangle(12, 12, width - 24, height - 24, fg)
            lcd._text(24, 28, title, fg)
            lcd._text(24, 52, "Native sidecar frame bridge", fg)
            lcd._text(24, 76, "User: " + str(self.username or "guest"), fg)
            lcd._text(24, 100, "Frame: " + str(self.frame), fg)
            lcd._text(24, height - 36, "Back exits", accent)
            lcd.swap()
        except Exception:
            pass
