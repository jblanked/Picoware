# VibesMP loading screen.

# ---- loading.py ----

from picoware.system.vector import Vector

class MusicLoader:
    """Branded loading screen with a rotating musical note."""
    def __init__(self, draw, text="", accent_color=None):
        self.draw = draw
        self.angle = 0
        self.center = Vector(draw.size.x // 2, draw.size.y // 2 - 10)
        self.current_text = text
        self.fg_color = getattr(draw, "foreground", 0xFFFF)
        self.bg_color = getattr(draw, "background", 0x0000)
        self.accent_color = accent_color if accent_color is not None else self.fg_color

    def set_text(self, text):
        self.current_text = text

    def animate(self, swap=True):
        self.draw.erase()
        from vibesmp_lib.ui_utils import draw_musical_note
        draw_musical_note(self.draw, self.center, self.angle, self.fg_color, self.accent_color)

        if self.current_text:
            tw = self.draw.len(self.current_text, 0)
            self.draw.text(Vector(self.center.x - tw // 2, self.center.y + 45), self.current_text, self.fg_color, 0)

        if swap:
            self.draw.swap()
        self.angle = (self.angle + 20) % 360

    def stop(self, swap=True):
        self.draw.erase()
        if swap:
            self.draw.swap()
