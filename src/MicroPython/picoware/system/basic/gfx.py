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

    __slots__ = (
        "draw",
        "vm",
        "cur_color",
        "pen_down",
        "tx",
        "ty",
        "thead",
        "_w",
        "_h",
        "_bg",
        "_fs",
        "display_active",
        "has_drawn",
    )

    def __init__(self, view_manager):
        """Bind the draw layer and capture screen, background and font."""
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
        self.has_drawn = False
        draw = view_manager.draw
        if draw is not None:
            self._w = draw.size.x
            self._h = draw.size.y
            self._bg = draw._background
            self._fs = draw._font_default.size

    def __del__(self):
        """Cleanup"""
        self.vm = None

    def present(self):
        """Present the back buffer so drawn graphics become visible."""
        if self.vm.draw is not None and self.has_drawn:
            self.vm.draw.swap()

    def _c(self, color):
        """Return the 565 colour for an MMBasic colour."""
        if color is None:
            return rgb_to_565(self.cur_color)
        if isinstance(color, str):
            color = NAMED_COLORS.get(color.lower().strip(), 0xFFFFFF)
        return rgb_to_565(color)

    def cls(self, color=None):
        """Clear the screen with a colour, or the background."""
        self.has_drawn = True
        if color is not None:
            self.vm.draw._clear(self._c(color))
            return
        self.vm.draw._clear(self._bg)

    def pixel(self, x, y, color=None):
        """Draw a single pixel."""
        self.has_drawn = True
        self.vm.draw._pixel(x, y, self._c(color))

    def line(self, x1, y1, x2, y2, thickness=1, color=None):
        """Draw a line, with optional thickness."""
        self.has_drawn = True
        col = self._c(color)
        if thickness and (thickness) > 1:
            self._thick_line(x1, y1, x2, y2,
                             (thickness), col)
        else:
            self.vm.draw._line((x1), (y1), (x2), (y2), col)

    def box(self, x, y, w, h, thickness=1, outline=None, fill=None):
        """Draw a box outline and/or fill."""
        self.has_drawn = True
        if fill is not None:
            self.vm.draw._fill_rectangle(x, y, w, h, self._c(fill))
        if outline is not None:
            self.vm.draw._rectangle(x, y, w, h, self._c(outline))
        elif fill is None:
            self.vm.draw._rectangle(x, y, w, h, self._c(None))

    def circle(self, x, y, r, *extra):
        """Draw a circle, treating trailing args as outline/fill."""
        self.has_drawn = True
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
            self.vm.draw._fill_circle(x, y, r, self._c(fill))
        if outline is not None and outline != 0:
            self.vm.draw._circle(x, y, r, self._c(outline))
        elif fill is None:
            self.vm.draw._circle(x, y, r, self._c(None))

    def polygon(self, xs, ys, outline=None, fill=None):
        """Draw a polygon outline and/or fill from coordinate arrays."""
        self.has_drawn = True
        pts = []
        n = min(len(xs), len(ys))
        for i in range(n):
            pts.append((xs[i], ys[i]))
        if len(pts) < 3:
            return
        if fill is not None and fill != 0:
            col = self._c(fill)
            x1, y1 = pts[0]
            for i in range(1, len(pts) - 1):
                x2, y2 = pts[i]
                x3, y3 = pts[i + 1]
                self.vm.draw._fill_triangle(x1, y1, x2, y2, x3, y3, col)
        if outline is not None and outline != 0:
            col = self._c(outline)
            for i in range(len(pts)):
                x1, y1 = pts[i]
                x2, y2 = pts[(i + 1) % len(pts)]
                self.vm.draw._line(x1, y1, x2, y2, col)

    def color(self, fg, bg=None):
        """Set the current MMBasic foreground (and optional background)."""
        if fg is not None:
            self.cur_color = fg
        if bg is not None:
            self._bg = bg

    def set_font_size(self, size):
        """MMBasic FONT n: 0-4 are font numbers; map to a pixel height."""
        sizes = {0: 8, 1: 8, 2: 12, 3: 16, 4: 20}
        try:
            self._fs = sizes.get(int(size), 8)
        except (TypeError, ValueError):
            self._fs = 8

    def text(self, x, y, s):
        """Draw a string at the given position."""
        self.has_drawn = True
        self.vm.draw._text(x, y, s, self._c(None), self._fs)

    def framebuffer(self, sub, args):
        """Handle FRAMEBUFFER; the draw layer is already double-buffered."""
        sub = str(sub).lower()
        if sub == "create":
            self.display_active = True
            self.has_drawn = True
            self.cls()
        elif sub == "write":
            self.display_active = True
            self.has_drawn = True
        elif sub == "copy":
            self.display_active = True
            self.has_drawn = True
            self.swap()
        elif sub == "close":
            self.display_active = False
        return True

    def swap(self):
        """Present the back buffer."""
        self.vm.draw.swap()

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
            self.vm.draw._line(self.tx, self.ty, nx, ny, self._c(None))
        self.tx = nx
        self.ty = ny

    def _thick_line(self, x1, y1, x2, y2, thick, col):
        """Draw a thick line as a filled rectangle."""
        if x1 == x2:
            self.vm.draw._fill_rectangle(x1 - thick // 2, min(y1, y2),
                                      thick, abs(y2 - y1) + 1, col)
        elif y1 == y2:
            self.vm.draw._fill_rectangle(min(x1, x2), y1 - thick // 2,
                                      abs(x2 - x1) + 1, thick, col)
        else:
            self.vm.draw._line(x1, y1, x2, y2, col)
