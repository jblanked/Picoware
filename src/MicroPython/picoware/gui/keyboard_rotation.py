"""Drawing coordinates for a keyboard dialog rotated counterclockwise."""


class KeyboardRotation:
    """Rotate dialog primitives without changing the display's global state."""

    def __init__(self, draw):
        """Wrap a landscape display draw object for rotated drawing.

        Args:
            draw: The display draw object whose coordinates are rotated.
        """
        from picoware.system.vector import Vector
        from picoware.system.font import Font

        self._draw = draw
        self.size = Vector(draw.size.y, draw.size.x)
        self._font = Font()
        self._tables = {}

    def __getattr__(self, name):
        """Forward unknown attributes to the wrapped draw object.

        Args:
            name: The attribute name to look up on the wrapped draw object.
        """
        return getattr(self._draw, name)

    def scale_x(self, value, screen_width=320):
        """Scale horizontal spacing along the rotated display width.

        Args:
            value: The horizontal spacing value to scale.
            screen_width: The reference width of the rotated display.
        """
        return self._draw.scale_y(value, screen_width)

    def scale_y(self, value, screen_height=320):
        """Scale vertical spacing along the rotated display height.

        Args:
            value: The vertical spacing value to scale.
            screen_height: The reference height of the rotated display.
        """
        return self._draw.scale_x(value, screen_height)

    def touch_point(self, x, y):
        """Map a physical touch back into the landscape dialog.

        Args:
            x: The horizontal coordinate of the physical touch.
            y: The vertical coordinate of the physical touch.

        Returns:
            The (x, y) coordinates in the rotated dialog space.
        """
        return self.size.x - 1 - y, x

    def _fill_rectangle(self, x, y, width, height, color):
        """Draw a filled rectangle using rotated coordinates.

        Args:
            x: The horizontal coordinate of the top-left corner.
            y: The vertical coordinate of the top-left corner.
            width: The rectangle width.
            height: The rectangle height.
            color: The color to fill the rectangle with.
        """
        self._draw._fill_rectangle(y, self.size.x - x - width, height, width, color)

    def _rectangle(self, x, y, width, height, color):
        """Draw a rectangle outline using rotated coordinates.

        Args:
            x: The horizontal coordinate of the top-left corner.
            y: The vertical coordinate of the top-left corner.
            width: The rectangle width.
            height: The rectangle height.
            color: The color of the outline.
        """
        self._draw._rectangle(
            y, self.size.x - 1 - x - width, height, width, color,
        )

    def _line(self, x1, y1, x2, y2, color):
        """Draw a line using rotated coordinates.

        Args:
            x1: The horizontal coordinate of the start point.
            y1: The vertical coordinate of the start point.
            x2: The horizontal coordinate of the end point.
            y2: The vertical coordinate of the end point.
            color: The color of the line.
        """
        self._draw._line(y1, self.size.x - 1 - x1, y2, self.size.x - 1 - x2, color)

    def _text(self, x, y, text, color, font_size=None):
        """Draw text using rotated coordinates.

        Args:
            x: The horizontal coordinate of the text origin.
            y: The vertical coordinate of the text origin.
            text: The text string to draw, with newlines wrapping to the origin.
            color: The color of the text.
            font_size: The font size, or None to use the current draw font.
        """
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
