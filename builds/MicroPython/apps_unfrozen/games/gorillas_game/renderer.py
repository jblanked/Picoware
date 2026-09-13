"""RAM-backed RGB332 compositing; only the completed frame touches the LCD.

FrameBuffer supplies native rectangle, ellipse and transparent sprite blits.
Keep the backing bytearrays alive alongside every FrameBuffer. In particular,
do not draw each decorative pixel run directly into the Pico's SPI PSRAM.
"""

from framebuf import FrameBuffer, GS8
from picoware.system.font import Font

TRANSPARENT = 0xE3


class Renderer:
    """Small native-blit surface with persistent art and terrain caches."""

    def __init__(self, draw):
        self.draw = draw
        self.width, self.height = int(draw.size.x), int(draw.size.y)
        self.data = bytearray(self.width * self.height)
        self.screen = FrameBuffer(self.data, self.width, self.height, GS8)
        self.surface = self.screen
        self.x = self.y = 0
        self.colors = {}
        self.sprites = {}
        self.terrain = {}
        self.glyphs = {}
        self.lights = {}
        self.labels = {}
        self.label_bytes = 0
        self.font = Font()
        self.font_id = draw.font
        self.font_width = self.font.get_width(self.font_id)
        self.font_height = self.font.get_height(self.font_id)
        self.advance = int(draw.font_size.x)
        self.palette_data = bytearray(2)
        self.palette = FrameBuffer(self.palette_data, 2, 1, GS8)

    def art(self, art, x, y, scale, palette, mirror=0, dissolve=0):
        """Rasterize each pose/palette once, then use a native keyed blit."""
        key = (id(art), scale, tuple(palette.items()), mirror)
        sprite = self.sprites.get(key) if not dissolve else None
        if sprite is None:
            width = int(max(mirror, max(c + n for c, r, n, p in art)) * scale)
            height = int((max(r for c, r, n, p in art) + 1) * scale)
            data = bytearray(width * height)
            surface = FrameBuffer(data, width, height, GS8)
            surface.fill(TRANSPARENT)
            for column, row, length, pixel in art:
                if dissolve and (column * 3 + row * 7) % 12 < dissolve:
                    continue
                offset = mirror - column - length if mirror else column
                left, top = int(offset * scale), int(row * scale)
                right, bottom = int((offset + length) * scale), int((row + 1) * scale)
                surface.fill_rect(left, top, right - left, bottom - top, self.color(palette[pixel]))
            sprite = (data, surface)
            if not dissolve:
                self.sprites[key] = sprite
        self.surface.blit(sprite[1], int(x) - self.x, int(y) - self.y, TRANSPARENT)

    def begin(self, color):
        """Begin a complete RAM frame, without clearing the LCD separately."""
        self.screen.fill(self.color(color))

    def blit(self, cached):
        """Composite one cached world-space rectangle, including blast holes."""
        x, y, data, surface = cached
        self.surface.blit(surface, x - self.x, y - self.y, TRANSPARENT)

    def capture(self, x, y, width, height):
        """Temporarily render existing facade code into a transparent tile."""
        data = bytearray(width * height)
        surface = FrameBuffer(data, width, height, GS8)
        surface.fill(TRANSPARENT)
        self.surface, self.x, self.y = surface, x, y
        return (x, y, data, surface)

    def circle(self, x, y, radius, color):
        self.surface.ellipse(int(x) - self.x, int(y) - self.y,
                             int(radius), int(radius), self.color(color), False)

    def color(self, color):
        """Match the Pico framebuffer's RGB565-to-RGB332 conversion."""
        result = self.colors.get(color)
        if result is None:
            result = ((color >> 8) & 0xE0) | ((color >> 6) & 0x1C) | ((color >> 3) & 3)
            # Reserve one otherwise unused magenta value as the sprite key.
            if result == TRANSPARENT:
                result = 0xE2
            self.colors[color] = result
        return result

    def end_capture(self, key, cached):
        self.release()
        self.terrain[key] = cached
        self.blit(cached)

    def fill_circle(self, x, y, radius, color):
        self.surface.ellipse(int(x) - self.x, int(y) - self.y,
                             int(radius), int(radius), self.color(color), True)

    def fill_rect(self, x, y, width, height, color):
        self.surface.fill_rect(x - self.x, y - self.y, width, height, self.color(color))

    def invalidate(self, key=None):
        """Discard only damaged tiles; a new round discards all of them."""
        if key is None:
            self.terrain.clear()
            self.lights.clear()
        else:
            self.terrain.pop(key, None)
            if key[0] == "building":
                self.lights.pop(key[1], None)

    def len(self, text):
        return len(text) * self.advance

    def present(self):
        """One native bulk transfer instead of thousands of PSRAM writes."""
        self.draw._bytearray(0, 0, self.width, self.height, self.data)
        self.draw.swap()

    def release(self):
        self.surface, self.x, self.y = self.screen, 0, 0

    def text(self, x, y, text, color):
        """Use the firmware's own font, caching native monochrome glyphs."""
        from framebuf import MONO_HLSB

        x, y = int(x) - self.x, int(y) - self.y
        key = (text, color)
        cached = self.labels.get(key)
        if cached is not None:
            self.surface.blit(cached[1], x, y, TRANSPARENT)
            return
        width = len(text) * self.advance
        size = width * self.font_height
        cache_label = width > 0 and self.label_bytes + size <= 12000
        if cache_label:
            data = bytearray(size)
            target = FrameBuffer(data, width, self.font_height, GS8)
            target.fill(TRANSPARENT)
            cursor, line = 0, 0
        else:
            target, cursor, line = self.surface, x, y
        self.palette_data[0], self.palette_data[1] = TRANSPARENT, self.color(color)
        for char in text:
            glyph = self.glyphs.get(char)
            if glyph is None:
                data = bytearray(self.font.get_character(self.font_id, ord(char)))
                glyph = (data, FrameBuffer(data, self.font_width, self.font_height,
                                          MONO_HLSB, (self.font_width + 7) & ~7))
                self.glyphs[char] = glyph
            target.blit(glyph[1], cursor, line, TRANSPARENT, self.palette)
            cursor += self.advance
        if cache_label:
            self.labels[key] = (data, target)
            self.label_bytes += size
            self.surface.blit(target, x, y, TRANSPARENT)
