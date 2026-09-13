"""Bounded bitmap preparation and drawing through Picoware's Draw driver.

There is no screen-sized application framebuffer. Small transparent assets are
prepared once, then submitted through Draw.image_bytearray_transparent().
FrameBuffer is used only while preparing a bounded sprite/tile, never to compose
the screen. The LCD driver owns the only display framebuffer.
"""

from framebuf import FrameBuffer, GS8
from picoware.system.font import Font
from picoware.system.vector import Vector

TRANSPARENT = 0xE3
CACHE_BYTES = 49152
# Leave room for actors and HUD labels even in a tall/dense city.
TERRAIN_BYTES = 32768
TILE_BYTES = 8192


class SpriteCache:
    """Prepare small reusable assets; render with the existing Draw/C driver."""

    def __init__(self, draw):
        if not hasattr(draw, "_bytearray_transparent"):
            raise RuntimeError("Gorillas requires firmware with Draw transparent bitmap support")
        self.draw = draw
        self.width, self.height = int(draw.size.x), int(draw.size.y)
        self.surface = None
        self.x = self.y = 0
        self.position = Vector(0, 0)
        self.size = Vector(0, 0)
        self.cached_bytes = 0
        self.terrain_bytes = 0
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

    def _pack(self, data, width, height):
        """Keep the source alive; transparency is processed by the C driver."""
        return (data, width, height)

    def _remember(self, table, key, packed):
        """Bound retained pixel data independently of the screen resolution."""
        if self.cached_bytes + len(packed[0]) <= CACHE_BYTES and len(table) < 96:
            table[key] = packed
            self.cached_bytes += len(packed[0])
            return True
        return False

    def _stamp(self, packed, x, y):
        self.position.x, self.position.y = x, y
        self.size.x, self.size.y = packed[1], packed[2]
        self.draw.image_bytearray_transparent(self.position, self.size, packed[0], TRANSPARENT)

    def art(self, art, x, y, scale, palette, mirror=0, dissolve=0):
        """Rasterize each pose/palette once, then use a native keyed blit."""
        key = (id(art), scale, tuple(palette.items()), mirror)
        sprite = self.sprites.get(key) if not dissolve else None
        if sprite is None:
            width = int(max(mirror, max(c + n for c, r, n, p in art)) * scale)
            height = int((max(r for c, r, n, p in art) + 1) * scale)
            if width * height > TILE_BYTES:
                raise ValueError("Gorillas sprite exceeds tile budget")
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
            sprite = self._pack(data, width, height)
            if not dissolve:
                self._remember(self.sprites, key, sprite)
        self._stamp(sprite, int(x), int(y))

    def begin(self, color):
        """Clear Picoware's own framebuffer, not an application buffer."""
        self.draw.fill_screen(color)

    def blit(self, cached):
        """Composite one cached world-space rectangle, including blast holes."""
        x, y, data, surface, packed, width, height = cached
        if packed is None:
            packed = self._pack(data, width, height)
            cached[4] = packed
        self._stamp(packed, x, y)

    def cache_lights(self, index, window, neon):
        size = sum(len(tile[2]) for tiles in (window, neon) for tile in tiles)
        if self.cached_bytes + size <= CACHE_BYTES:
            self.lights[index] = (window, neon)
            self.cached_bytes += size

    def capture(self, x, y, width, height):
        """Temporarily render existing facade code into a transparent tile."""
        if width * height > TILE_BYTES:
            # Large-screen facades use Draw directly, never a large allocation.
            self.release()
            return None
        data = bytearray(width * height)
        surface = FrameBuffer(data, width, height, GS8)
        surface.fill(TRANSPARENT)
        self.surface, self.x, self.y = surface, x, y
        return [x, y, data, surface, None, width, height]

    def circle(self, x, y, radius, color):
        self.position.x, self.position.y = int(x), int(y)
        self.draw.circle(self.position, int(radius), color)

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
        if cached is None:
            return
        cached[4] = self._pack(cached[2], cached[5], cached[6])
        size = len(cached[2])
        if self.cached_bytes + size <= CACHE_BYTES and self.terrain_bytes + size <= TERRAIN_BYTES:
            self.terrain[key] = cached
            self.cached_bytes += size
            self.terrain_bytes += size
        self.blit(cached)

    def fill_circle(self, x, y, radius, color):
        self.position.x, self.position.y = int(x), int(y)
        self.draw.fill_circle(self.position, int(radius), color)

    def fill_rect(self, x, y, width, height, color):
        if self.surface is not None:
            self.surface.fill_rect(x - self.x, y - self.y, width, height, self.color(color))
            return
        right, bottom = min(self.width, x + width), min(self.height, y + height)
        x, y = max(0, x), max(0, y)
        if right <= x or bottom <= y:
            return
        self.position.x, self.position.y = x, y
        self.size.x, self.size.y = right - x, bottom - y
        self.draw.fill_rectangle(self.position, self.size, color)

    def invalidate(self, key=None):
        """Discard only damaged tiles; a new round discards all of them."""
        if key is None:
            self.terrain.clear()
            self.lights.clear()
            self.sprites.clear()
            self.labels.clear()
            self.glyphs.clear()
            self.colors.clear()
            self.cached_bytes = 0
            self.terrain_bytes = 0
            self.label_bytes = 0
        else:
            cached = self.terrain.pop(key, None)
            if cached is not None:
                self.cached_bytes -= len(cached[2])
                self.terrain_bytes -= len(cached[2])
            if key[0] == "building":
                lights = self.lights.pop(key[1], None)
                if lights:
                    self.cached_bytes -= sum(len(tile[2]) for tiles in lights for tile in tiles)

    def len(self, text):
        return len(text) * self.advance

    def present(self):
        """Present Picoware's existing display buffer."""
        self.draw.swap()

    def release(self):
        self.surface, self.x, self.y = None, 0, 0

    def text(self, x, y, text, color):
        """Use the firmware's own font, caching native monochrome glyphs."""
        from framebuf import MONO_HLSB

        if not text:
            return
        x, y = int(x) - self.x, int(y) - self.y
        key = (text, color)
        cached = self.labels.get(key)
        if cached is not None and self.surface is None:
            self._stamp(cached, x, y)
            return
        width = len(text) * self.advance
        size = width * self.font_height
        if self.surface is None:
            if size > TILE_BYTES:
                raise ValueError("Gorillas label exceeds tile budget")
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
                glyph_data = bytearray(self.font.get_character(self.font_id, ord(char)))
                glyph = (glyph_data, FrameBuffer(glyph_data, self.font_width, self.font_height,
                                          MONO_HLSB, (self.font_width + 7) & ~7))
                self._remember(self.glyphs, char, glyph)
            target.blit(glyph[1], cursor, line, TRANSPARENT, self.palette)
            cursor += self.advance
        if self.surface is None:
            packed = self._pack(data, width, self.font_height)
            if self.label_bytes + size <= 8000 and self._remember(self.labels, key, packed):
                self.label_bytes += size
            self._stamp(packed, x, y)
