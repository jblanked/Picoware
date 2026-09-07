"""Drawing coordinates for a keyboard dialog rotated counterclockwise."""


class KeyboardRotation:
    """Rotate dialog primitives without changing the display's global state."""

    def __init__(self, draw):
        from picoware.system.vector import Vector
        from picoware.system.font import Font

        self._draw = draw
        self.size = Vector(draw.size.y, draw.size.x)
        self._font = Font()
        self._tables = {}

    def __getattr__(self, name):
        return getattr(self._draw, name)

    def touch_point(self, x, y):
        """Map a physical touch back into the landscape dialog."""
        return self.size.x - 1 - y, x

    def _fill_rectangle(self, x, y, width, height, color):
        self._draw._fill_rectangle(y, self.size.x - x - width, height, width, color)

    def _line(self, x1, y1, x2, y2, color):
        self._draw._line(y1, self.size.x - 1 - x1, y2, self.size.x - 1 - x2, color)

    def _text(self, x, y, text, color, font_size=None):
        size = self._draw.font if font_size is None else font_size
        font = self._draw.get_font(size)
        if size not in self._tables:
            self._tables[size] = self._font.get_data(size)
        data = self._tables[size]
        row_bytes = (font.width + 7) // 8
        start_x = x
        for char in text:
            if char == "\n":
                x = start_x
                y += font.height
                continue
            code = ord(char)
            if not 32 <= code <= 126:
                code = ord("?")
            offset = (code - 32) * font.height * row_bytes
            for row in range(font.height):
                # Draw runs of set bits as vertical spans on the physical LCD.
                run = -1
                for col in range(font.width + 1):
                    on = col < font.width and data[offset + row * row_bytes + col // 8] & (0x80 >> (col % 8))
                    if on and run < 0:
                        run = col
                    elif not on and run >= 0:
                        self._fill_rectangle(x + run, y + row, col - run, 1, color)
                        run = -1
            x += font.width + font.spacing
