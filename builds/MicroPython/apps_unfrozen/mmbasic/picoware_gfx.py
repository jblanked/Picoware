"""
Graphics backend for the MMBasic interpreter.

Renders MMBasic graphics through the Picoware draw layer's C methods
(`_pixel`, `_line`, `_rectangle`, ...) with 24-bit colours converted to
16-bit 565. Includes a minimal turtle engine and treats FRAMEBUFFER as a
single double-buffered layer.
"""

import math

# Named colours for RGB(NAME) - 24-bit 0xRRGGBB values.
NAMED_COLORS = {
    "black": 0x000000,
    "white": 0xFFFFFF,
    "red": 0xFF0000,
    "green": 0x00FF00,
    "blue": 0x0000FF,
    "yellow": 0xFFFF00,
    "cyan": 0x00FFFF,
    "magenta": 0xFF00FF,
    "orange": 0xFF8000,
    "pink": 0xFF0080,
    "brown": 0xA52A2A,
    "grey": 0x808080,
    "gray": 0x808080,
    "darkgrey": 0x404040,
    "darkgray": 0x404040,
    "lightgrey": 0xC0C0C0,
    "lightgray": 0xC0C0C0,
    "purple": 0x800080,
    "myrtle": 0x21421E,
    "maroon": 0x800000,
    "navy": 0x000080,
    "teal": 0x008080,
    "olive": 0x808000,
    "silver": 0xC0C0C0,
    "lime": 0x00FF00,
    "aqua": 0x00FFFF,
    "fuchsia": 0xFF00FF,
    "gold": 0xFFD700,
    "violet": 0xEE82EE,
}


def rgb_to_565(color):
    """Convert a 24-bit 0xRRGGBB colour to a 16-bit 565 value."""
    color = int(color) & 0xFFFFFF
    r = (color >> 16) & 0xFF
    g = (color >> 8) & 0xFF
    b = color & 0xFF
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


class PicowareGraphics:
    """Renders MMBasic graphics via the draw layer's C methods."""

    def __init__(self, draw, view_manager=None):
        """Bind the draw layer and capture screen, background and font."""
        self.draw = draw
        self.vm = view_manager
        self.cur_color = 0xFFFFFF
        self.pen_down = True
        self.tx = 0.0
        self.ty = 0.0
        self.thead = 0.0
        self._w = 320
        self._h = 240
        self._bg = 0
        self._fs = 8
        self.display_active = False
        if draw is not None:
            try:
                self._w = draw.size.x
                self._h = draw.size.y
            except Exception:
                pass
            try:
                self._bg = draw._background
            except Exception:
                pass
            try:
                self._fs = draw._font_default.size
            except Exception:
                pass

    def _c(self, color):
        """Return the 565 colour for an MMBasic colour."""
        if color is None:
            return rgb_to_565(self.cur_color)
        if isinstance(color, str):
            color = NAMED_COLORS.get(color.lower().strip(), 0xFFFFFF)
        return rgb_to_565(color)

    def cls(self, color=None):
        """Clear the screen with a colour, or the background."""
        if color is not None:
            self.draw._clear(self._c(color))
            return
        self.draw._clear(self._bg)

    def pixel(self, x, y, color=None):
        """Draw a single pixel."""
        self.draw._pixel(int(x), int(y), self._c(color))

    def line(self, x1, y1, x2, y2, thickness=1, color=None):
        """Draw a line, with optional thickness."""
        col = self._c(color)
        if thickness and int(thickness) > 1:
            self._thick_line(int(x1), int(y1), int(x2), int(y2),
                             int(thickness), col)
        else:
            self.draw._line(int(x1), int(y1), int(x2), int(y2), col)

    def box(self, x, y, w, h, thickness=1, outline=None, fill=None):
        """Draw a box outline and/or fill."""
        x, y, w, h = int(x), int(y), int(w), int(h)
        if fill is not None:
            self.draw._fill_rectangle(x, y, w, h, self._c(fill))
        if outline is not None:
            self.draw._rectangle(x, y, w, h, self._c(outline))
        elif fill is None:
            self.draw._rectangle(x, y, w, h, self._c(None))

    def circle(self, x, y, r, *extra):
        """Draw a circle, treating trailing args as outline/fill."""
        x, y, r = int(x), int(y), int(r)
        args = list(extra)
        outline = None
        fill = None
        while args:
            v = args.pop()
            if isinstance(v, bool):
                continue
            if fill is None:
                fill = v
            elif outline is None:
                outline = v
        if fill is not None and fill != 0:
            self.draw._fill_circle(x, y, r, self._c(fill))
        if outline is not None and outline != 0:
            self.draw._circle(x, y, r, self._c(outline))
        elif fill is None:
            self.draw._circle(x, y, r, self._c(None))

    def polygon(self, xs, ys, outline=None, fill=None):
        """Draw a polygon outline and/or fill from coordinate arrays."""
        pts = []
        n = min(len(xs), len(ys))
        for i in range(n):
            pts.append((int(xs[i]), int(ys[i])))
        if len(pts) < 3:
            return
        if fill is not None and fill != 0:
            col = self._c(fill)
            x1, y1 = pts[0]
            for i in range(1, len(pts) - 1):
                x2, y2 = pts[i]
                x3, y3 = pts[i + 1]
                self.draw._fill_triangle(x1, y1, x2, y2, x3, y3, col)
        if outline is not None and outline != 0:
            col = self._c(outline)
            for i in range(len(pts)):
                x1, y1 = pts[i]
                x2, y2 = pts[(i + 1) % len(pts)]
                self.draw._line(x1, y1, x2, y2, col)

    def color(self, color):
        """Set the current MMBasic colour."""
        if color is not None:
            self.cur_color = color

    def text(self, x, y, s):
        """Draw a string at the given position."""
        self.draw._text(int(x), int(y), str(s), self._c(None), self._fs)

    def framebuffer(self, sub, args):
        """Handle FRAMEBUFFER; the draw layer is already double-buffered."""
        sub = str(sub).lower()
        if sub == "create":
            self.display_active = True
            self.cls()
        elif sub == "write":
            self.display_active = True
        elif sub == "copy":
            # MMBasic's `FRAMEBUFFER COPY f,n` presents the completed frame.
            # Picoware already draws into a back buffer, so a swap is the
            # equivalent operation and avoids an unnecessary memory copy.
            self.display_active = True
            self.swap()
        elif sub == "close":
            self.display_active = False
        return True

    def swap(self):
        """Present the back buffer."""
        try:
            swap = getattr(self.draw, "swap", None)
            if swap is not None:
                swap()
            else:
                self.draw._swap()
        except Exception:
            pass

    def save_image(self, filename):
        """Save the framebuffer; unsupported on the device for now."""
        return True

    def turtle(self, sub, args):
        """Run a turtle command."""
        sub = str(sub).lower()
        if sub in ("reset", "home"):
            self.cls()
            self.pen_down = True
            self.tx = self._w / 2.0
            self.ty = self._h / 2.0
            self.thead = 0.0
        elif sub == "pen down":
            self.pen_down = True
        elif sub == "pen up":
            self.pen_down = False
        elif sub == "forward":
            self._turtle_step(float(args[0]) if args else 0)
        elif sub == "back":
            self._turtle_step(-(float(args[0]) if args else 0))
        elif sub == "right":
            self.thead = (self.thead + float(args[0])) % 360
        elif sub == "left":
            self.thead = (self.thead - float(args[0])) % 360
        elif sub in ("set xy", "setxy"):
            self.tx = float(args[0])
            self.ty = float(args[1])
        elif sub in ("set heading", "setheading", "heading"):
            self.thead = float(args[0]) % 360
        return True

    def _turtle_step(self, dist):
        """Move the turtle and draw if the pen is down."""
        rad = math.radians(self.thead)
        nx = self.tx + dist * math.cos(rad)
        ny = self.ty - dist * math.sin(rad)
        if self.pen_down:
            self.draw._line(int(self.tx), int(self.ty), int(nx), int(ny),
                            self._c(None))
        self.tx = nx
        self.ty = ny

    def _thick_line(self, x1, y1, x2, y2, thick, col):
        """Draw a thick line as a filled rectangle."""
        if x1 == x2:
            self.draw._fill_rectangle(x1 - thick // 2, min(y1, y2),
                                      thick, abs(y2 - y1) + 1, col)
        elif y1 == y2:
            self.draw._fill_rectangle(min(x1, x2), y1 - thick // 2,
                                      abs(x2 - x1) + 1, thick, col)
        else:
            self.draw._line(x1, y1, x2, y2, col)


class NullGraphics:
    """No-op graphics backend for host use."""

    def __init__(self, draw=None, view_manager=None):
        self.draw = draw
        self.display_active = False

    def cls(self):
        pass

    def pixel(self, *a):
        pass

    def line(self, *a):
        pass

    def box(self, *a):
        pass

    def circle(self, *a):
        pass

    def polygon(self, *a):
        pass

    def color(self, *a):
        pass

    def text(self, *a):
        pass

    def framebuffer(self, sub, args):
        sub = str(sub).lower()
        if sub in ("create", "write", "copy"):
            self.display_active = True
        elif sub == "close":
            self.display_active = False

    def swap(self):
        pass

    def save_image(self, *a):
        pass

    def turtle(self, *a):
        pass
