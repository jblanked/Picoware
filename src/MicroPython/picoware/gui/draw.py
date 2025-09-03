from machine import Pin, SPI
from picoware.system.colors import TFT_WHITE, TFT_BLACK
from picoware.gui.image import Image
from picoware.system.vector import Vector
from picoware.system.drivers.ILI9341 import (
    _ILI9341,
    AdafruitGFX5x7Font,
    CMSansSerif2012,
    CMSansSerif201224,
    CMSansSerif201231,
)


class Font:
    """Enumeration of font types"""

    AdafruitGFX5x7Font = 0
    CMSansSerif2012 = 1
    CMSansSerif201224 = 2
    CMSansSerif201231 = 3


class Draw:
    """Class for drawing shapes and text on the display"""

    def __init__(self, foreground: int = TFT_WHITE, background: int = TFT_BLACK):
        self.size = Vector(320, 320)
        self.display = _ILI9341(
            SPI(
                1,
                baudrate=25000000,
                sck=Pin(10),
                mosi=Pin(11),
                miso=Pin(12),
            ),
            cs=Pin(13),
            dc=Pin(14),
            rst=Pin(15),
            w=320,
            h=320,
            r=0,
        )
        self.background = background
        self.foreground = foreground
        self.palette = self._create_rgb332_palette()
        self.display.set_color(foreground, background)
        self.display.fill_rectangle(0, 0, self.size.x, self.size.y, background)

    def clear(
        self,
        position: Vector = Vector(0, 0),
        size: Vector = Vector(320, 320),
        color=TFT_BLACK,
    ):
        """Fill a rectangular area on the display with a color."""
        self.display.fill_rectangle(position.x, position.y, size.x, size.y, color)

    def circle(self, position: Vector, radius: int, color=TFT_WHITE):
        """Draws a circle from a given position with a given radius using the midpoint circle algorithm"""
        x_pos: int = int(position.x)
        y_pos: int = int(position.y)
        x: int = radius - 1
        y: int = 0
        dx: int = 1
        dy: int = 1
        err: int = dx - (radius << 1)
        while x >= y:
            self.display.pixel(x_pos + x, y_pos + y, color)
            self.display.pixel(x_pos + y, y_pos + x, color)
            self.display.pixel(x_pos - y, y_pos + x, color)
            self.display.pixel(x_pos - x, y_pos + y, color)
            self.display.pixel(x_pos - x, y_pos - y, color)
            self.display.pixel(x_pos - y, y_pos - x, color)
            self.display.pixel(x_pos + y, y_pos - x, color)
            self.display.pixel(x_pos + x, y_pos - y, color)
            if err <= 0:
                y += 1
                err += dy
                dy += 2
            if err > 0:
                x -= 1
                dx += 2
                err += dx - (radius << 1)

    def color565(self, r, g, b):
        """Convert RGB888 to RGB565 color format"""
        return self.display.color565(r, g, b)

    def _create_rgb332_palette(self):
        """Create an RGB332 to RGB565 palette conversion table"""
        palette = []
        for i in range(256):
            # Extract RGB332 components
            r3 = (i >> 5) & 0x07  # 3 bits for red
            g3 = (i >> 2) & 0x07  # 3 bits for green
            b2 = i & 0x03  # 2 bits for blue

            # Convert to 8-bit RGB
            r8 = (r3 * 255) // 7  # Scale 3-bit to 8-bit
            g8 = (g3 * 255) // 7  # Scale 3-bit to 8-bit
            b8 = (b2 * 255) // 3  # Scale 2-bit to 8-bit

            # Convert to RGB565
            rgb565 = ((r8 & 0xF8) << 8) | ((g8 & 0xFC) << 3) | (b8 >> 3)
            palette.append(rgb565)

        return palette

    def erase(self):
        """Erase the display"""
        self.display.erase()

    def fill_circle(self, position: Vector, radius: int, color=TFT_WHITE):
        """Draw a filled circle on the display"""
        if radius <= 0:
            return

        x: int = 0
        y: int = radius
        d: int = 1 - radius

        while x <= y:
            # Draw horizontal lines to fill the circle
            # Draw lines for the main circle quadrants
            self.line(Vector(position.x - y, position.y + x), Vector(2 * y, 0), color)
            self.line(Vector(position.x - y, position.y - x), Vector(2 * y, 0), color)

            if x != y:
                self.line(
                    Vector(position.x - x, position.y + y), Vector(2 * x, 0), color
                )
                self.line(
                    Vector(position.x - x, position.y - y), Vector(2 * x, 0), color
                )

            if d < 0:
                d += 2 * x + 3
            else:
                d += 2 * (x - y) + 5
                y -= 1
            x += 1

    def fill_rectangle(self, position: Vector, size: Vector, color=TFT_WHITE):
        """Draw a filled rectangle on the display"""
        self.display.fill_rectangle(
            int(position.x), int(position.y), int(size.x), int(size.y), color
        )

    # this is really slow.. I'll optimize this later
    def fill_round_rectangle(
        self, position: Vector, size: Vector, radius: int, color=TFT_WHITE
    ):
        """Draw a filled rounded rectangle on the display"""
        if size.x <= 0 or size.y <= 0 or radius <= 0:
            return

        # Clip to screen bounds
        x: int = int(position.x)
        y: int = int(position.y)
        width: int = int(size.x)
        height: int = int(size.y)

        # Adjust for left and top boundaries
        if x < 0:
            width += x
            x = 0
        if y < 0:
            height += y
            y = 0

        # Adjust for right and bottom boundaries
        if x + width > self.size.x:
            width = self.size.x - x
        if y + height > self.size.y:
            height = self.size.y - y

        # Only draw if there's something to draw
        if width > 0 and height > 0:
            # Calculate effective radius considering clipping
            effective_radius: int = radius if radius < width / 2 else width / 2
            effective_radius: int = (
                effective_radius if effective_radius < height / 2 else height / 2
            )

            for py in range(y, y + height):
                for px in range(x, x + width):
                    # Check if the pixel is within the rounded corners
                    in_corner: bool = False
                    if px < x + effective_radius and py < y + effective_radius:
                        # Top-left corner
                        dx: int = px - (x + effective_radius)
                        dy: int = py - (y + effective_radius)
                        if dx * dx + dy * dy > effective_radius * effective_radius:
                            in_corner = True
                    elif (
                        px < x + effective_radius
                        and py >= y + height - effective_radius
                    ):
                        # Bottom-left corner
                        dx: int = px - (x + effective_radius)
                        dy: int = py - (y + height - effective_radius)
                        if dx * dx + dy * dy > effective_radius * effective_radius:
                            in_corner = True
                    elif (
                        px >= x + width - effective_radius and py < y + effective_radius
                    ):
                        # Top-right corner
                        dx: int = px - (x + width - effective_radius)
                        dy: int = py - (y + effective_radius)
                        if dx * dx + dy * dy > effective_radius * effective_radius:
                            in_corner = True
                    elif (
                        px >= x + width - effective_radius
                        and py >= y + height - effective_radius
                    ):
                        # Bottom-right corner
                        dx: int = px - (x + width - effective_radius)
                        dy: int = py - (y + height - effective_radius)
                        if dx * dx + dy * dy > effective_radius * effective_radius:
                            in_corner = True

                    if not in_corner:
                        self.display.pixel(px, py, color)

    def get_cursor(self) -> Vector:
        """Get the current cursor position"""
        return Vector(self.display._x, self.display._y)

    def get_font(self) -> Font:
        """Get the current font"""
        return self.display._font

    def get_font_size(self) -> Vector:
        """Get the current font size"""
        _font = self.display._font
        return Vector(_font.max_width, _font.height)

    def image(self, position: Vector, img: Image):
        """Draw an image on the display"""
        for y in range(img.size.y):
            for x in range(img.size.x):
                color = img.get_pixel(x, y)
                self.display.pixel(position.x + x, position.y + y, color)

    def image_bmp(self, position: Vector, path: str):
        """Draw a BMP image from the filesystem"""
        img = Image()
        img._load_bmp(path)
        self.image(position, img)

    def image_bytearray(self, position: Vector, size: Vector, byte_data, palette=None):
        """Draw an image from 8-bit byte data (bytes or bytearray) with optional palette conversion"""
        if palette is None:
            palette = self.palette

        for y in range(size.y):
            for x in range(size.x):
                palette_index = byte_data[y * size.x + x]
                color = palette[palette_index] if palette_index < len(palette) else 0
                self.display.pixel(position.x + x, position.y + y, color)

    def line(self, position: Vector, size: Vector, color=TFT_WHITE):
        """Draw a line on the display"""
        for i in range(size.x):
            current_x = int(position.x) + i
            if (
                current_x >= 0
                and current_x < self.size.x
                and position.y >= 0
                and position.y < self.size.y
            ):
                self.display.pixel(current_x, int(position.y), color)

    def line_custom(self, point_1: Vector, point_2: Vector, color=TFT_WHITE):
        """Draws a line using Bresenham's line algorithm"""
        x1: int = int(point_1.x)
        y1: int = int(point_1.y)
        x2: int = int(point_2.x)
        y2: int = int(point_2.y)

        dx: int = abs(x2 - x1)
        dy: int = abs(y2 - y1)
        sx: int = 1 if x1 < x2 else -1
        sy: int = 1 if y1 < y2 else -1
        err: int = dx - dy

        while True:
            # Draw pixel if within bounds
            if x1 >= 0 and x1 < self.size.x and y1 >= 0 and y1 < self.size.y:
                self.display.pixel(x1, y1, color)

            # Check if we've reached the end point
            if x1 == x2 and y1 == y2:
                break

            e2: int = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx

            if e2 < dx:
                err += dx
                y1 += sy

    def pixel(self, position: Vector, color=TFT_WHITE):
        """Draw a pixel on the display"""
        self.display.pixel(int(position.x), int(position.y), color)

    def print(self, text: str, font=Font.AdafruitGFX5x7Font):
        """Print text to the display"""
        self.set_font(font)
        self.display.print(text)

    def println(
        self,
        text: str,
        font=Font.AdafruitGFX5x7Font,
        clear: bool = False,
    ):
        """Print text to the display"""
        if clear:
            self.display.erase()
        self.set_font(font)
        self.display.print(f"{text}\n")

    def rect(self, position: Vector, size: Vector, color=TFT_WHITE):
        """Draw a rectangle on the display"""
        if size.x <= 0 or size.y <= 0:
            return

        # Top edge (horizontal line)
        self.line(position, Vector(size.x, 0), color)

        # Bottom edge (horizontal line)
        self.line(Vector(position.x, position.y + size.y - 1), Vector(size.x, 0), color)

        # Left edge (vertical line using individual pixels)
        for y in range(size.y):
            pixel_position = Vector(position.x, position.y + y)
            if (
                pixel_position.x >= 0
                and pixel_position.x < self.size.x
                and pixel_position.y >= 0
                and pixel_position.y < self.size.y
            ):
                self.pixel(pixel_position, color)

        # Right edge (vertical line using individual pixels)
        for y in range(size.y):
            pixel_position = Vector(position.x + size.x - 1, position.y + y)
            if (
                pixel_position.x >= 0
                and pixel_position.x < self.size.x
                and pixel_position.y >= 0
                and pixel_position.y < self.size.y
            ):
                self.pixel(pixel_position, color)

    def reset(self):
        """Reset the display"""
        self.display.reset()

    def set_color(
        self,
        foreground=TFT_WHITE,
        background=TFT_BLACK,
    ):
        """Set the foreground and background color of the display"""
        self.display.set_color(foreground, background)

    def set_cursor(self, position: Vector):
        """Set the cursor position for text printing"""
        self.display.set_pos(position.x, position.y)

    def set_font(self, font: int = Font.AdafruitGFX5x7Font):
        """Set the font for the display"""
        if font == Font.AdafruitGFX5x7Font:
            self.display.set_font(AdafruitGFX5x7Font)
        elif font == Font.CMSansSerif2012:
            self.display.set_font(CMSansSerif2012)
        elif font == Font.CMSansSerif201224:
            self.display.set_font(CMSansSerif201224)
        elif font == Font.CMSansSerif201231:
            self.display.set_font(CMSansSerif201231)

    def scroll(self, up: bool = True, distance: int = 1):
        """Scroll the display up or down"""
        if up:
            self.display.scroll(distance)
        else:
            self.display.scroll(-distance)

    def text(self, position: Vector, text: str, color=TFT_WHITE):
        """Draw text at a specific position"""
        self.display.set_pos(position.x, position.y)
        self.foreground = color
        self.display.set_color(color, self.background)
        self.display.print(text)
