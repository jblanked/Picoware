import math
import utime
from picoware.system.vector import Vector
from grocery_lib.ui_utils import C_BG, C_TEXT, C_ACCENT

class CartLoader:
    """Branded loading screen with a rotating grocery shopping cart."""
    def __init__(self, draw, text=""):
        self.draw = draw
        self.angle = 0
        self.center = Vector(draw.size.x // 2, draw.size.y // 2)
        self.current_text = text
        
    def set_text(self, text):
        self.current_text = text
        
    def _rotate(self, x, y, angle):
        rad = (angle * 3.14159) / 180.0
        nx = x * math.cos(rad) - y * math.sin(rad)
        ny = x * math.sin(rad) + y * math.cos(rad)
        return int(nx), int(ny)

    def draw_cart(self, angle):
        # Cart segments relative to 0,0
        segments = [
            ((-15, -10), (15, -10)), # Top bar
            ((-15, -10), (-10, 10)), # Back wall
            ((15, -10), (10, 10)),   # Front wall
            ((-10, 10), (10, 10)),   # Bottom
            ((-15, -10), (-22, -14)),# Handle
            ((-22, -14), (-22, -8))  # Handle grip
        ]
        
        for p1, p2 in segments:
            x1, y1 = self._rotate(p1[0], p1[1], angle)
            x2, y2 = self._rotate(p2[0], p2[1], angle)
            self.draw.line(self.center + Vector(x1, y1), self.center + Vector(x2, y2), C_TEXT)
            
        # Wheels
        wheels = [(-8, 14), (8, 14)]
        for wx, wy in wheels:
            rx, ry = self._rotate(wx, wy, angle)
            self.draw.fill_rectangle(self.center + Vector(rx-1, ry-1), Vector(3, 3), C_ACCENT)

    def animate(self, swap=True):
        self.draw.erase()
        self.draw_cart(self.angle)
        
        if self.current_text:
            tw = self.draw.len(self.current_text, 0)
            self.draw.text(Vector(self.center.x - tw // 2, self.center.y + 40), self.current_text, C_TEXT, 0)
        
        if swap:
            self.draw.swap()
        self.angle = (self.angle + 20) % 360

    def stop(self):
        self.draw.erase()
        self.draw.swap()
