"""Disk-backed artwork and native RGB332 framebuffer rendering.

The app retains drawing commands and small, prebuilt RGB332 sprites. The engine
composes those commands into one native surface and transfers it in one bulk
LCD operation.
"""

from struct import unpack
from .assets import EFFECT_BASE, EFFECT_RECORD_BYTES, variant
from picoware.engine.engine import FrameBuffer2D, Layer2D

CACHE_BYTES = 32768
COMMAND_LIMIT = 2048
LAYER_POOL_SIZE = 48


class SpriteCache:
    """Cache artwork and compose native layers in painter order."""

    def __init__(self, draw):
        self.draw = draw
        self.game = None
        self.width, self.height = int(draw.size.x), int(draw.size.y)
        # These are the inherited C-backed Draw methods, not a separate LCD
        # implementation. Avoid repeated Vector setters and wrapper dispatch.
        self._native_image = draw._bytearray
        self._native_rect = draw._fill_rectangle
        self._native_circle = draw._circle
        self._native_fill_circle = draw._fill_circle
        self._native_text = draw._text
        self.font_id = draw.font
        self.advance, self.font_height = int(draw.font_size.x), int(draw.font_size.y)
        self.path = __file__.rsplit('/', 1)[0] + '/art.bin'
        # A firmware VFS handle includes a 16 KiB read buffer. Allocate once
        # before scene fragmentation, then reuse it for every pose and HUD.
        self.art_source = open(self.path, 'rb')
        self.effect_skip = memoryview(bytearray(512))
        self.sprites, self.terrain, self.lights = {}, {}, {}
        self.cached_bytes = self.command_count = 0
        self.surface = None
        self.native_segments = []
        self.native_pool = []
        self.native_order = []
        self.native_segment = None
        self.native_translate = hasattr(Layer2D, 'translate')
        self.native_layer = None
        self.native_layer_keys = [None] * LAYER_POOL_SIZE
        self.native_layer_pool = [None] * LAYER_POOL_SIZE
        self.native_layer_pool_count = 0
        self.native_packed = hasattr(Layer2D, 'image_packed')
        self.prepared_effect_layer = None
        if self.native_packed and hasattr(Layer2D, 'reserve_packed'):
            self.prepared_effect_layer = Layer2D()
            if hasattr(Layer2D, 'reserve_commands'):
                self.prepared_effect_layer.reserve_commands(32)
            self.prepared_effect_layer.reserve_packed(EFFECT_RECORD_BYTES)
        self.native_capture = None
        self.native_framebuffer = FrameBuffer2D(self.width, self.height)
        self.frame, self.groups = [], {}
        self.clip = (0, 0, self.width, self.height)
        self.last_regions, self.last_area = 0, 0
        self.covers, self.ui_boxes = [], ()
        self.covers_dirty = self.full_redraw = True
        self.layers, self.tracked, self.seen = {}, {}, set()
        self.layer_commands = self.layer_info = None
        self.pending, self.serial = [], 0
        self.effect_data = None
        self.effect_source = self.effect_directory = None
        self.effect_variant = self.effect_next = self.effect_position = 0

    def _cached_command_count(self, cached):
        commands = cached[4]
        return commands if isinstance(commands, int) else len(commands)

    def _close_effect(self):
        if self.effect_source is not None:
            self.effect_source.close()
            self.effect_source = None
        self.effect_directory = None

    def _cover(self, covers, box):
        x, y, right, bottom = box
        if (right - x) * (bottom - y) < 64:
            return
        for a, b, c, d in covers:
            if a <= x and b <= y and c >= right and d >= bottom:
                return
        covers[:] = [old for old in covers if not (x <= old[0] and y <= old[1] and right >= old[2] and bottom >= old[3])]
        covers.append(box)

    def _damage(self, regions, box):
        left, top = max(0, box[0]), max(0, box[1])
        right, bottom = min(self.width, box[2]), min(self.height, box[3])
        if left >= right or top >= bottom:
            return
        # Merge intersecting rectangles until the union is stable. Disjoint
        # regions cannot overwrite one another during back-to-front replay.
        index = 0
        while index < len(regions):
            a, b, c, d = regions[index]
            if left <= c and right >= a and top <= d and bottom >= b:
                left, top, right, bottom = min(left, a), min(top, b), max(right, c), max(bottom, d)
                regions.pop(index)
                index = 0
            else:
                index += 1
        regions.append((left, top, right, bottom))

    def _draw_patch(self, x, y, width, height, data):
        a, b, c, d = self.clip
        left, top = max(0, a - x), max(0, b - y)
        right, bottom = min(width, c - x), min(height, d - y)
        if left >= right or top >= bottom:
            return
        if left == 0 and right == width:
            pixels = data if top == 0 and bottom == height else memoryview(data)[top * width:bottom * width]
            self._native_image(x + left, y + top, right - left, bottom - top, pixels)
        else:
            # Stock Draw has no source stride. Exact slices also prevent the
            # binding from mistaking RGB332 data for RGB565.
            pixels = memoryview(data)
            for row in range(top, bottom):
                self._native_image(x + left, y + row, right - left, 1, pixels[row * width + left:row * width + right])

    def _emit(self, command):
        if command[0] == 5:
            self.frame.append(command)
            self._reuse_native_segment()
            return
        if self.surface is not None:
            if self.game is not None:
                self.surface = 1
            else:
                self.surface.append(command)
        elif self.layer_commands is not None:
            if self.game is not None:
                self.layer_commands = 1
            else:
                self.layer_commands.append(command)
        else:
            if self.game is None:
                self.frame.append(command)
        self._record_native(command)

    def _execute(self, command):
        kind, x, y, right, bottom, payload = command
        a, b, c, d = self.clip
        if x >= c or y >= d or right <= a or bottom <= b:
            return
        if kind == 0:
            left, top = max(a, x), max(b, y)
            self._native_rect(left, top, min(c, right) - left, min(d, bottom) - top, payload)
        elif kind in (1, 2):
            radius = (right - x - 1) // 2
            if kind == 1:
                self._native_fill_circle(x + radius, y + radius, radius, payload)
            else:
                self._native_circle(x + radius, y + radius, radius, payload)
        elif kind == 3:
            self._native_text(x, y, payload[0], payload[1], self.font_id)
        elif kind == 4:
            return
        else:
            cached = self.groups[payload]
            native = cached[11] if len(cached) > 11 else None
            if native is not None and self.game is not None:
                native.render(self.game, a, b, c, d)
                return
            for child in cached[4]:
                if child[1] < c and child[2] < d and child[3] > a and child[4] > b:
                    self._execute(child)

    def _expand(self, regions, commands):
        """Stock text/circle calls lack clipping: include their whole bounds."""
        for command in commands:
            kind, x, y, right, bottom, payload = command
            if kind == 5:
                self._expand(regions, self.groups[payload][6])
            elif kind in (1, 2, 3):
                for a, b, c, d in regions:
                    if x < c and right > a and y < d and bottom > b:
                        if x < a or y < b or right > c or bottom > d:
                            self._damage(regions, (x, y, right, bottom))
                        break

    def _load(self, index):
        if index >= EFFECT_BASE:
            record = self._read_effect(index)
            length = len(record)
        else:
            length = self._seek_art(index)
            record = self.art_source.read(length)
        if len(record) != length:
            raise ValueError('Truncated Gorillas art.bin')
        count = unpack('<H', record[:2])[0]
        cursor, size, patches = 2, 0, []
        for unused in range(count):
            if cursor + 8 > length:
                raise ValueError('Truncated Gorillas rectangle')
            x, y, width, height = unpack('<HHHH', record[cursor:cursor + 8])
            cursor += 8
            pixels = record[cursor:cursor + width * height]
            if not width or not height or len(pixels) != width * height:
                raise ValueError('Truncated Gorillas sprite')
            patches.append((x, y, width, height, pixels))
            cursor += width * height
            size += len(pixels)
        if cursor != length:
            raise ValueError('Invalid Gorillas sprite length')
        if index >= EFFECT_BASE:
            if self.effect_data is not None:
                self.cached_bytes -= self.effect_data[2]
            if self.cached_bytes + size > CACHE_BYTES:
                self.sprites.clear()
                self.cached_bytes = 0
            self.effect_data = (index, patches, size)
            self.cached_bytes += size
        elif self.cached_bytes + size <= CACHE_BYTES and len(self.sprites) < 96:
            self.sprites[index] = patches
            self.cached_bytes += size
        return patches

    def _load_packed(self, index, target, x, y):
        """Let the engine own the SD record; do not decode Python patch lists."""
        if index >= EFFECT_BASE:
            self._read_effect(index, target, x, y)
            return
        length = self._seek_art(index)
        target.image_packed(x, y, self.art_source, length)

    def _read_effect(self, index, target=None, x=0, y=0):
        """Read animation sequentially: FAT seek restarts its cluster walk."""
        variant, frame = (index - EFFECT_BASE) // 40, (index - EFFECT_BASE) % 40
        if not 0 <= variant <= 5:
            raise ValueError('Invalid Gorillas effect variant')
        if self.effect_source is None or variant != self.effect_variant:
            self._close_effect()
            path = self.path.rsplit('/', 1)[0] + '/effects-{}.bin'.format(variant)
            self.effect_source = open(path, 'rb')
            if self.effect_source.read(8) != b'GFX1\x28\x00\x00\x00':
                raise ValueError('Invalid Gorillas effect file')
            self.effect_directory = self.effect_source.read(320)
            if len(self.effect_directory) != 320:
                raise ValueError('Truncated Gorillas effect directory')
            self.effect_variant, self.effect_next, self.effect_position = variant, 0, 328
        elif frame < self.effect_next:
            # Rewind within the small animation file without reopening its path.
            self.effect_source.seek(328)
            self.effect_next, self.effect_position = 0, 328
        record = None
        while self.effect_next <= frame:
            start = self.effect_next * 8
            offset, length = unpack('<II', self.effect_directory[start:start + 8])
            if offset != self.effect_position or not 2 <= length <= 32768:
                raise ValueError('Invalid Gorillas effect bounds')
            if self.effect_next == frame and target is not None and target is not False:
                try:
                    target.image_packed(x, y, self.effect_source, length)
                except Exception:
                    # A short read may have advanced the stream. Reopen next time.
                    self._close_effect()
                    raise
            elif self.effect_next == frame and target is None:
                record = self.effect_source.read(length)
                if len(record) != length:
                    raise ValueError('Truncated Gorillas effect frame')
            else:
                remaining = length
                while remaining:
                    buffer = self.effect_skip if remaining >= 512 else self.effect_skip[:remaining]
                    count = self.effect_source.readinto(buffer)
                    if not count:
                        raise ValueError('Truncated Gorillas skipped frame')
                    remaining -= count
            self.effect_next += 1
            self.effect_position += length
        return record

    def _record_native(self, command):
        """Record primitive work in C++ so present() has no Python draw loop."""
        if self.surface is not None:
            target = self.native_capture
        elif self.layer_commands is not None:
            target = self.native_layer
        else:
            if self.game is not None and self.native_segment is None:
                self._reuse_native_segment()
                self.native_segment = self.native_segments[-1]
                self.native_order.append(self.native_segment)
            target = self.native_segment if self.game is not None else self.native_segments[-1]
        if target is None:
            return
        kind, x, y, right, bottom, payload = command
        if kind == 0:
            target.fill_rect(x, y, right - x, bottom - y, payload)
        elif kind in (1, 2):
            radius = (right - x - 1) // 2
            if kind == 1:
                target.fill_circle(x + radius, y + radius, radius, payload)
            else:
                target.circle(x + radius, y + radius, radius, payload)
        elif kind == 3:
            target.text(x, y, payload[0], payload[1], self.font_id)
        elif kind == 4:
            if isinstance(payload, tuple):
                index, origin_x, origin_y = payload
            else:
                index, origin_x, origin_y = payload, x, y
            if self.native_packed:
                self._load_packed(index, target, origin_x, origin_y)
                return
            patches = self.effect_data[1] if self.effect_data is not None and self.effect_data[0] == index else self.sprites.get(index)
            if patches is None:
                patches = self._load(index)
            for dx, dy, width, height, pixels in patches:
                # art.bin and effects-*.bin contain opaque rectangles; use the
                # native row-copy path instead of checking every pixel for the
                # transparent sentinel.
                target.image_opaque(origin_x + dx, origin_y + dy, width, height, pixels)

    def _regions(self):
        # Retire objects that disappeared (projectile, death pose, old HUD).
        for key in tuple(self.tracked):
            if key not in self.seen:
                revision, boxes, background = self.tracked.pop(key)
                self._restore(boxes, background)
                self.layers.pop(key, None)
        regions, self.pending = self.pending, []
        if self.full_redraw:
            regions = [(0, 0, self.width, self.height)]
            self.full_redraw = False
        while regions:
            before = tuple(regions)
            self._expand(regions, self.frame)
            if tuple(regions) == before:
                break
        return regions

    def _restore(self, boxes, background):
        for box in boxes:
            hidden = False
            if background:
                x, y, right, bottom = box
                for a, b, c, d in self.ui_boxes:
                    if a <= x and b <= y and c >= right and d >= bottom:
                        hidden = True
                        break
                if not hidden:
                    for a, b, c, d in self.covers:
                        if a <= x and b <= y and c >= right and d >= bottom:
                            hidden = True
                            break
            if not hidden:
                self._damage(self.pending, box)

    def _retire_cached(self, cached, key=None):
        native = cached[11]
        if key is None and len(cached) > 12:
            key = cached[12]
        cached[11] = None
        self._retire_native(native, key)

    def _retire_lights(self, lights):
        for group in lights:
            for cached in group:
                self._retire_cached(cached)

    def _retire_native(self, native, key=None):
        if native is None:
            return
        native.clear()
        if key == 'explosion' and self.prepared_effect_layer is None:
            self.prepared_effect_layer = native
        elif key is not None and self.native_layer_pool_count < LAYER_POOL_SIZE:
            self.native_layer_keys[self.native_layer_pool_count] = key
            self.native_layer_pool[self.native_layer_pool_count] = native
            self.native_layer_pool_count += 1

    def _reuse_native_segment(self):
        if self.native_pool:
            segment = self.native_pool.pop()
            segment.clear()
        else:
            segment = Layer2D()
        self.native_segments.append(segment)

    def _seek_art(self, index):
        """Position the retained stream at one validated sprite record."""
        source = self.art_source
        source.seek(0)
        magic, count = unpack('<4sI', source.read(8))
        if magic != b'GRL1' or not 0 <= index < count <= 1024:
            raise ValueError('Invalid Gorillas art.bin index')
        source.seek(8 + index * 8)
        offset, length = unpack('<II', source.read(8))
        if offset < 8 + count * 8 or not 2 <= length <= 32768:
            raise ValueError('Invalid Gorillas sprite bounds')
        source.seek(offset)
        return length

    def _take_native_layer(self, key=None):
        index = 0
        while index < self.native_layer_pool_count:
            if self.native_layer_keys[index] == key:
                self.native_layer_pool_count -= 1
                native = self.native_layer_pool[index]
                self.native_layer_keys[index] = self.native_layer_keys[self.native_layer_pool_count]
                self.native_layer_pool[index] = self.native_layer_pool[self.native_layer_pool_count]
                self.native_layer_keys[self.native_layer_pool_count] = None
                self.native_layer_pool[self.native_layer_pool_count] = None
                return native
            index += 1
        return Layer2D()

    def _watch(self, key, revision, boxes, background):
        """The game supplies each object's revision and old/new repaint areas."""
        if self.game is not None:
            return
        self.seen.add(key)
        current = (revision, boxes, background)
        old = self.tracked.get(key)
        if old != current:
            if old is not None:
                self._restore(old[1], old[2])
            self._restore(boxes, background)
            self.tracked[key] = current

    def art(self, art, x, y, scale, palette, mirror=0, dissolve=0):
        if dissolve >= 12:
            return
        index = variant(art, scale, palette, mirror, dissolve)
        width = 8 if art < 4 else (24 if art == 4 else (47 if art == 9 else (10 if art == 7 else 20)))
        height = 8 if art <= 4 else (7 if art == 9 else (11 if art == 7 else 23))
        x, y = int(x), int(y)
        self._emit((4, x, y, x + int(width * scale), y + int(height * scale), index))

    def begin(self, color, ui_boxes=()):
        self.frame, self.groups = [], {}
        self.native_pool.extend(self.native_segments)
        self.native_segments = []
        self.native_order = []
        self.native_segment = None
        self.seen.clear()
        if self.game is not None:
            self.native_framebuffer.clear(color)
            return
        self._reuse_native_segment()
        self.ui_boxes = ui_boxes
        if self.covers_dirty:
            self.covers = []
            for key, cached in self.terrain.items():
                if key[0] in ('building', 'obstacle') and cached[5] is not None:
                    for box in cached[5]:
                        self._cover(self.covers, box)
            self.covers_dirty = False
        self.fill_rect(0, 0, self.width, self.height, color)

    def blit(self, cached):
        if self.game is not None:
            if cached[4]:
                if cached[7] is not None:
                    self.seen.add(cached[7])
                self.native_order.append(cached[11])
                self.native_segment = None
            return
        x, y, width, height, commands = cached[:5]
        if not commands:
            return
        if cached[5] is None:
            covers, atoms = [], []
            for command in commands:
                if command[0] == 0:
                    self._cover(covers, command[1:5])
                elif command[0] in (1, 2, 3):
                    atoms.append(command)
            cached[5], cached[6] = covers, atoms
        key = id(cached)
        self.groups[key] = cached
        if cached[7] is not None:
            boxes = cached[9] if cached[9] is not None else ((x, y, x + width, y + height),)
            self._watch(cached[7], cached[8], boxes, cached[10])
        self._emit((5, x, y, x + width, y + height, key))

    def cache_lights(self, index, window, neon):
        for tiles, name in ((window, 'window'), (neon, 'neon')):
            for tile in tiles:
                tile[7] = (name, index)
        count = sum(self._cached_command_count(tile) for tile in window + neon)
        if self.command_count + count <= COMMAND_LIMIT:
            self.lights[index] = (window, neon)
            self.command_count += count

    def capture(self, x, y, width, height, key=None):
        """Record geometry only; no bitmap allocation or pixel rasterization."""
        self.surface = 0 if self.game is not None else []
        self.native_capture = self._take_native_layer(key)
        self.serial += 1
        return [x, y, width, height, self.surface, None, None, None, self.serial, None, False, self.native_capture, key]

    def circle(self, x, y, radius, color):
        x, y, radius = int(x), int(y), int(radius)
        self._emit((2, x - radius, y - radius, x + radius + 1, y + radius + 1, color))

    def close(self):
        self._close_effect()
        if self.art_source is not None:
            self.art_source.close()
            self.art_source = None

    def effect(self, x, y, scale, compact, age):
        index = EFFECT_BASE + (0 if compact else scale) * 40 + min(39, max(0, age))
        x, y = int(x) - 32 * scale, int(y) - 40 * scale
        if self.native_packed:
            self._emit((4, x, y, x + 64 * scale, y + 80 * scale, (index, x, y)))
            return
        patches = self.effect_data[1] if self.effect_data is not None and self.effect_data[0] == index else self._load(index)
        if patches:
            left, top = min(p[0] for p in patches), min(p[1] for p in patches)
            right, bottom = max(p[0] + p[2] for p in patches), max(p[1] + p[3] for p in patches)
            self._emit((4, x + left, y + top, x + right, y + bottom, (index, x, y)))

    def end_capture(self, key, cached):
        if self.game is not None:
            cached[4] = self.surface
        self.release()
        cached[7] = key
        count = self._cached_command_count(cached)
        if self.command_count + count <= COMMAND_LIMIT:
            self.terrain[key] = cached
            self.command_count += count
        if key[0] in ('building', 'obstacle'):
            self.covers_dirty = True
        self.blit(cached)

    def end_layer(self):
        key, revision, boxes, background, position = self.layer_info
        commands = self.layer_commands
        native = self.native_layer
        self.layer_commands = self.layer_info = None
        self.native_layer = None
        if not commands:
            self._retire_native(native, key)
            return
        if self.game is not None:
            x = y = right = bottom = 0
        else:
            x, y = min(c[1] for c in commands), min(c[2] for c in commands)
            right, bottom = max(c[3] for c in commands), max(c[4] for c in commands)
        self.serial += 1
        cached = [x, y, right - x, bottom - y, commands, None, None,
                  key, self.serial, boxes, background, native]
        self.layers[key] = (revision, cached, position)
        self.blit(cached)

    def fill_circle(self, x, y, radius, color):
        x, y, radius = int(x), int(y), int(radius)
        self._emit((1, x - radius, y - radius, x + radius + 1, y + radius + 1, color))

    def fill_rect(self, x, y, width, height, color):
        x, y, width, height = int(x), int(y), int(width), int(height)
        if width > 0 and height > 0:
            self._emit((0, x, y, x + width, y + height, color))

    def invalidate(self, key=None):
        self.covers_dirty = True
        if key is None:
            # Keep both SD handles across rounds. prepare_effect() rewinds the
            # effect stream; close() releases the handles when leaving the app.
            for cached in self.terrain.values():
                self._retire_cached(cached)
            for lights in self.lights.values():
                self._retire_lights(lights)
            for layer_key, layer in self.layers.items():
                self._retire_cached(layer[1], layer_key)
            self.terrain.clear()
            self.lights.clear()
            self.sprites.clear()
            self.effect_data = None
            self.cached_bytes = self.command_count = 0
            self.layers.clear()
            self.tracked.clear()
            self.pending.clear()
            self.full_redraw = True
        else:
            lights = self.lights.pop(key[1], ()) if key[0] == 'building' else ()
            if lights:
                self.command_count -= sum(self._cached_command_count(tile) for group in lights for tile in group)
                self._retire_lights(lights)
            cached = self.terrain.pop(key, None)
            if cached is not None:
                self.command_count -= self._cached_command_count(cached)
                self._retire_cached(cached)

    def layer(self, key, revision, boxes=None, background=False, position=None):
        """Reuse unchanged game objects without rebuilding their draw commands."""
        if position is not None and (self.game is None or not self.native_translate):
            revision = (revision, position)
            position = None
        cached = self.layers.get(key)
        if cached is not None and cached[0] == revision and (cached[2] is None) == (position is None):
            if position is not None and cached[2] != position:
                dx, dy = position[0] - cached[2][0], position[1] - cached[2][1]
                # A layer already queued this frame must retain its placement.
                if key in self.seen:
                    cached = None
                else:
                    cached[1][11].translate(dx, dy)
                    cached[1][0] += dx
                    cached[1][1] += dy
                    cached = (revision, cached[1], position)
                    self.layers[key] = cached
            if cached is not None:
                self.blit(cached[1])
                return False
        self.layer_info = (key, revision, boxes, background, position)
        self.layer_commands = 0 if self.game is not None else []
        if cached is not None and key not in self.seen:
            self.native_layer = cached[1][11]
            self.native_layer.clear()
        elif key == 'explosion' and self.prepared_effect_layer is not None:
            self.native_layer = self.prepared_effect_layer
            self.prepared_effect_layer = None
        else:
            self.native_layer = self._take_native_layer(key)
        return True

    def len(self, text):
        return len(text) * self.advance

    def prepare_effect(self, scale, compact):
        """Open/prime animation during round loading, not the first impact."""
        index = EFFECT_BASE + (0 if compact else scale) * 40
        if self.native_packed:
            self._read_effect(index, False)
        else:
            self._load(index)

    def present(self):
        if self.game is not None:
            # The native surface is deliberately full-screen: this preserves
            # painter order while avoiding one LCD transaction per primitive.
            self.last_regions = 1
            self.last_area = self.width * self.height
            for key in tuple(self.layers):
                if key not in self.seen:
                    retired = self.layers.pop(key)
                    self._retire_cached(retired[1], key)
            for native in self.native_order:
                self.native_framebuffer.render(native)
            self.native_framebuffer.present(self.game)
            return
        regions = self._regions()
        self.last_regions = len(regions)
        self.last_area = sum((c - a) * (d - b) for a, b, c, d in regions)
        for region in regions:
            self.clip = region
            a, b, c, d = region
            segment = 0
            for command in self.frame:
                if command[0] == 5:
                    if self.game is not None:
                        self.native_segments[segment].render(self.game, a, b, c, d)
                    if command[1] < c and command[2] < d and command[3] > a and command[4] > b:
                        self._execute(command)
                    segment += 1
            if self.game is not None:
                self.native_segments[segment].render(self.game, a, b, c, d)
        if regions:
            # The stock API still transfers the display; only drawing is local.
            self.draw.swap()

    def release(self):
        self.surface = None
        self.native_capture = None

    def text(self, x, y, text, color):
        x, y = int(x), int(y)
        self._emit((3, x, y, x + self.len(text), y + self.font_height, (text, color)))

    def watch(self, key, revision, box, background=False):
        if self.game is None:
            self._watch(key, revision, (box,), background)
