import sim_runtime


class Ghouls:
    def __init__(self, user="", _credential="", sound_enabled=True):
        """Initialize a deterministic Ghouls simulator scene."""
        del _credential
        self.user = user
        self.sound_enabled = sound_enabled
        self.is_active = True
        self.frame = 0
        self.last_input = -1
        self.player_x = 5
        self.player_y = 5
        self.health = 100
        self.score = 0
        self.shots = 0
        self.map_name = "sim-arena"
        self.enemies = [(9, 4), (3, 8), (11, 9)]
        self._draw()

    def start(self, *args, **kwargs):
        """Start or restart the Ghouls engine."""
        self.is_active = True
        self.frame = 0
        self._draw()
        return True

    def stop(self):
        """Stop the Ghouls engine."""
        self.is_active = False
        return True

    def update_input(self, button):
        """Handle button input for the Ghouls engine."""
        self.last_input = button
        if button in (5, 0xB1, 27):
            self.is_active = False
        elif button == 0:
            self.player_y = max(0, self.player_y - 1)
        elif button == 1:
            self.player_y = min(11, self.player_y + 1)
        elif button == 2:
            self.player_x = min(15, self.player_x + 1)
        elif button == 3:
            self.player_x = max(0, self.player_x - 1)
        elif button in (4, 8):
            self.shots += 1
            if self.enemies:
                self.enemies.pop(0)
                self.score += 100
        return True

    def update_draw(self):
        """Advance and draw one simulator frame."""
        if not self.is_active:
            return False
        self.frame += 1
        if self.frame % 20 == 0 and self.enemies:
            self.health = max(0, self.health - 1)
            if self.health == 0:
                self.is_active = False
        if self.frame == 1 or self.frame % 6 == 0:
            self._draw()
        return True

    def snapshot(self):
        return {
            "active": self.is_active,
            "frame": self.frame,
            "last_input": self.last_input,
            "player": (self.player_x, self.player_y),
            "health": self.health,
            "score": self.score,
            "shots": self.shots,
            "enemies": len(self.enemies),
            "map": self.map_name,
        }

    def _draw(self):
        lcd = sim_runtime._lcd
        if lcd is None:
            return
        width = getattr(lcd, "width", 320)
        height = getattr(lcd, "height", 320)
        bg = 0x0841
        fg = 0xFFFF
        accent = 0xF800
        player = 0x07E0
        enemy = 0xF800
        try:
            lcd._clear(bg)
            lcd._rectangle(12, 12, width - 24, height - 24, fg)
            lcd._text(24, 28, "Ghouls Simulator", fg)
            lcd._text(24, 52, "Map: " + self.map_name, fg)
            lcd._text(24, 76, "User: " + str(self.user or "guest"), fg)
            lcd._text(24, 100, "HP " + str(self.health) + " Score " + str(self.score), fg)
            cell_w = max(8, (width - 64) // 16)
            cell_h = max(8, (height - 160) // 12)
            ox = 24
            oy = 132
            for ex, ey in self.enemies:
                lcd._rectangle(ox + ex * cell_w, oy + ey * cell_h, cell_w - 2, cell_h - 2, enemy)
            lcd._rectangle(
                ox + self.player_x * cell_w,
                oy + self.player_y * cell_h,
                cell_w - 2,
                cell_h - 2,
                player,
            )
            lcd._text(24, height - 36, "Back exits", accent)
            lcd.swap()
        except Exception:
            pass
