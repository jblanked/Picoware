"""Bounded stock-Draw command cache and dirty-region renderer.

Artwork remains in SD .bin files. Small fixed buffers feed the existing LCD
bytearray API; there is no second screen surface and no native engine extension.
The only frame-sized object is the display driver's own buffer.
"""

from struct import pack_into, unpack_from
from gc import mem_free
from .assets import EFFECT_BASE, variant

CACHE_BYTES = 12288
CACHE_PAGE_BYTES = 2048
COMMAND_LIMIT = 1024
GROUP_LIMIT = 48
REGION_LIMIT = 4


class SpriteCache:
    def __init__(self, draw):
        self.draw = draw
        self.width, self.height = int(draw.size.x), int(draw.size.y)
        compact = self.width < 180 or self.height < 120
        # Small heaps favour direct drawing over retaining hundreds of Python
        # command objects. This changes rendering cost, never collision detail.
        self.immediate = compact or mem_free() < 192 * 1024
        self.command_limit = 128 if compact else min(COMMAND_LIMIT, max(128, mem_free() // 256))
        self.advance, self.font_height = int(draw.font_size.x), int(draw.font_size.y)
        self.terrain, self.lights, self.layers = {}, {}, {}
        self.frame, self.pending = [], []
        self.atoms = []
        self.tracked, self.seen = {}, set()
        self.surface = self.layer_info = None
        self.serial = self.command_count = 0
        self.full_redraw = True
        self.clip = (0, 0, self.width, self.height)
        self.path = __file__.rsplit('/', 1)[0]
        self.art_source = open(self.path + '/art.bin', 'rb')
        header = self.art_source.read(8)
        if header[:4] != b'GRL1':
            raise ValueError('Invalid art header')
        count = unpack_from('<I', header, 4)[0]
        if not 0 < count <= 1024:
            raise ValueError('Invalid art count')
        self.art_count = count
        self.art_directory = None if compact else self.art_source.read(count * 8)
        self.art_index_buffer = memoryview(bytearray(8))
        if self.art_directory is not None and len(self.art_directory) != count * 8:
            raise ValueError('Truncated art directory')
        self.art_buffer = memoryview(bytearray(1127 if compact else 4629))
        page_bytes = 512 if compact else CACHE_PAGE_BYTES
        cache_bytes = page_bytes if compact else min(CACHE_BYTES, max(CACHE_PAGE_BYTES,
                              (mem_free() // 16 // CACHE_PAGE_BYTES) * CACHE_PAGE_BYTES))
        # Separate small pages avoid needing a fresh contiguous cache block
        # when reopening the app after a long session.
        self.art_cache = tuple(memoryview(bytearray(page_bytes))
                               for unused in range(cache_bytes // page_bytes))
        self.art_offsets = [0] * len(self.art_cache)
        self.art_entries = {}
        self.art_used = 0
        self.effect_buffer = None
        self.effect_bounds = bytearray(320)
        self.effect_index = -1
        self.effect_source = self.effect_directory = None
        self.effect_variant = None
        self.calls = self.asset_reads = self.asset_bytes = 0
        self.frame_calls = self.max_calls = self.last_area = self.last_regions = 0

    def _admit(self, count):
        return self.command_count + count <= self.command_limit and (
            len(self.terrain) + len(self.lights) + len(self.layers) < GROUP_LIMIT
            and mem_free() > 32768 + count * 128)

    def _art_record(self, index):
        if not 0 <= index < self.art_count:
            raise ValueError('Invalid art index')
        if self.art_directory is not None:
            return unpack_from('<II', self.art_directory, index * 8)
        self.art_source.seek(8 + index * 8)
        if self.art_source.readinto(self.art_index_buffer) != 8:
            raise ValueError('Truncated art directory')
        return unpack_from('<II', self.art_index_buffer)

    def _damage(self, box):
        left, top = max(0, box[0]), max(0, box[1])
        right, bottom = min(self.width, box[2]), min(self.height, box[3])
        if left >= right or top >= bottom:
            return
        index = 0
        while index < len(self.pending):
            a, b, c, d = self.pending[index]
            if left <= c and right >= a and top <= d and bottom >= b:
                left, top = min(left, a), min(top, b)
                right, bottom = max(right, c), max(bottom, d)
                self.pending.pop(index)
                index = 0
            else:
                index += 1
        self.pending.append((left, top, right, bottom))
        if len(self.pending) > REGION_LIMIT:
            # Merge the cheapest pair instead of repainting the entire display.
            best, pair = self.width * self.height * 2, (0, 1)
            for first in range(len(self.pending) - 1):
                a, b, c, d = self.pending[first]
                area = (c - a) * (d - b)
                for second in range(first + 1, len(self.pending)):
                    x, y, r, s = self.pending[second]
                    extra = (max(c, r) - min(a, x)) * (max(d, s) - min(b, y)) - area - (r - x) * (s - y)
                    if extra < best:
                        best, pair = extra, (first, second)
            a, b, c, d = self.pending.pop(pair[1])
            x, y, r, s = self.pending.pop(pair[0])
            self._damage((min(a, x), min(b, y), max(c, r), max(d, s)))

    def _emit(self, command):
        if self.surface is not None:
            self.surface.append(command)
        elif self.immediate:
            self._execute(command)
        else:
            self.frame.append(command)
            if command[0] in (1, 2, 3):
                self.atoms.append(command)

    def _execute(self, command):
        kind, x, y, right, bottom, value = command
        a, b, c, d = self.clip
        if x >= c or y >= d or right <= a or bottom <= b:
            return
        if kind == 0:
            left, top = max(a, x), max(b, y)
            self.draw._fill_rectangle(left, top, min(c, right) - left,
                                      min(d, bottom) - top, value)
        elif kind in (1, 2):
            radius = (right - x - 1) // 2
            method = self.draw._fill_circle if kind == 1 else self.draw._circle
            method(x + radius, y + radius, radius, value)
        elif kind == 3:
            self.draw._text(x, y, value[0], value[1], self.draw.font)
        elif kind == 4:
            self._packed(value[0], value[1], value[2])
            return
        else:
            for child in value:
                if child[1] < c and child[3] > a and child[2] < d and child[4] > b:
                    self._execute(child)
            return
        self.calls += 1
        self.frame_calls += 1

    def _expand(self):
        # Stock text/circles cannot be clipped. Repaint their entire bounds and
        # then every overlapping later object, preserving painter order.
        changed = True
        while changed:
            before = tuple(self.pending)
            for command in self.atoms:
                x, y, right, bottom = command[1:5]
                for a, b, c, d in self.pending:
                    if x < c and right > a and y < d and bottom > b:
                        if x < a or y < b or right > c or bottom > d:
                            self._damage((x, y, right, bottom))
                        break
            changed = tuple(self.pending) != before

    def _metadata(self, commands, key, boxes=None):
        if boxes is None:
            boxes = ((min(c[1] for c in commands), min(c[2] for c in commands),
                      max(c[3] for c in commands), max(c[4] for c in commands)),) if commands else ()
        self.serial += 1
        return [commands, boxes, key, self.serial]

    def _packed(self, index, x, y):
        if index >= EFFECT_BASE:
            frame = (index - EFFECT_BASE) % 40
            offset, length = unpack_from('<II', self.effect_directory, frame * 8)
            if length < 2 or length > len(self.effect_buffer):
                raise ValueError('Invalid effect size')
            data = self.effect_buffer[:length]
            if self.effect_index != index:
                self._read(self.effect_source, offset, data)
                self.effect_index = index
        else:
            cached = self.art_entries.get(index)
            if cached is not None:
                page, start, length = cached
                data = self.art_cache[page][start:start + length]
            else:
                offset, length = self._art_record(index)
                page = -1
                if len(self.art_entries) < 64:
                    for candidate, used in enumerate(self.art_offsets):
                        if used + length <= len(self.art_cache[candidate]):
                            page = candidate
                            break
                if page >= 0:
                    start = self.art_offsets[page]
                    data = self.art_cache[page][start:start + length]
                    self._read(self.art_source, offset, data)
                    self.art_entries[index] = (page, start, length)
                    self.art_offsets[page] += length
                    self.art_used += length
                else:
                    if length > len(self.art_buffer):
                        raise ValueError('Art exceeds small scratch buffer')
                    data = self.art_buffer[:length]
                    self._read(self.art_source, offset, data)
        cursor = 2
        for unused in range(unpack_from('<H', data)[0]):
            px, py, w, h = unpack_from('<HHHH', data, cursor)
            cursor += 8
            if not w or not h or cursor + w * h > len(data):
                raise ValueError('Invalid sprite rectangle')
            self._patch(x + px, y + py, w, h, data[cursor:cursor + w * h])
            cursor += w * h
        if cursor != len(data):
            raise ValueError('Invalid sprite length')

    def _patch(self, x, y, w, h, data):
        a, b, c, d = self.clip
        left, top = max(0, a - x), max(0, b - y)
        right, bottom = min(w, c - x), min(h, d - y)
        if left >= right or top >= bottom:
            return
        if left == 0 and right == w:
            self.draw._bytearray(x, y + top, w, bottom - top, data[top * w:bottom * w])
            count = 1
        else:
            for row in range(top, bottom):
                self.draw._bytearray(x + left, y + row, right - left, 1,
                                     data[row * w + left:row * w + right])
            count = bottom - top
        self.calls += count
        self.frame_calls += count

    def _read(self, source, offset, data):
        source.seek(offset)
        if source.readinto(data) != len(data):
            raise ValueError('Truncated sprite')
        self.asset_reads += 1
        self.asset_bytes += len(data)

    def _watch(self, key, revision, boxes):
        self.seen.add(key)
        current = (revision, boxes)
        old = self.tracked.get(key)
        if old != current:
            if old is not None:
                for box in old[1]:
                    self._damage(box)
            for box in boxes:
                self._damage(box)
            self.tracked[key] = current

    def art(self, art, x, y, scale, palette, mirror=0, dissolve=0):
        if dissolve >= 12:
            return
        index = variant(art, scale, palette, mirror, dissolve)
        w = 8 if art < 4 else (24 if art == 4 else (47 if art == 9 else (10 if art == 7 else 20)))
        h = 8 if art <= 4 else (7 if art == 9 else (11 if art == 7 else 23))
        x, y = int(x), int(y)
        self._emit((4, x, y, x + int(w * scale), y + int(h * scale), (index, x, y)))

    def begin(self, color, ui_boxes=()):
        self.frame.clear()
        self.atoms.clear()
        self.seen.clear()
        self.frame_calls = 0
        if self.immediate:
            self.clip = (0, 0, self.width, self.height)
        self.fill_rect(0, 0, self.width, self.height, color)

    def blit(self, cached):
        if self.immediate:
            for command in cached[0]:
                self._execute(command)
            return
        if cached[0]:
            # Geometry bounds and non-clippable commands never change within a
            # cached group. Compute them once, not once per frame.
            if len(cached) == 4:
                commands = cached[0]
                cached.append((5, min(c[1] for c in commands), min(c[2] for c in commands),
                               max(c[3] for c in commands), max(c[4] for c in commands), commands))
                cached.append(tuple(c for c in commands if c[0] in (1, 2, 3)))
            self.frame.append(cached[4])
            self.atoms.extend(cached[5])
        if cached[2] is not None:
            self._watch(cached[2], cached[3], cached[1])

    def cache_lights(self, index, window, neon):
        if self.immediate:
            return
        for tiles, name in ((window, 'window'), (neon, 'neon')):
            for tile in tiles:
                tile[2] = (name, index)
        count = sum(len(tile[0]) for tile in window + neon)
        if self._admit(count):
            self.lights[index] = (window, neon)
            self.command_count += count

    def capture(self, x, y, width, height, key=None):
        if self.immediate and (key is None or key[0] not in ('window', 'neon')):
            self.surface = None
            return [(), (), None, 0]
        self.surface = []
        return self._metadata(self.surface, None, ((x, y, x + width, y + height),))

    def circle(self, x, y, radius, color):
        x, y, radius = int(x), int(y), int(radius)
        self._emit((2, x - radius, y - radius, x + radius + 1, y + radius + 1, color))

    def close(self):
        if self.art_source is not None:
            self.art_source.close()
            self.art_source = None
        if self.effect_source is not None:
            self.effect_source.close()
            self.effect_source = None

    def effect(self, x, y, scale, compact, age):
        index = EFFECT_BASE + (0 if compact else scale) * 40 + min(39, max(0, age))
        x, y = int(x) - 32 * scale, int(y) - 40 * scale
        left, top, right, bottom = unpack_from('<HHHH', self.effect_bounds, (index - EFFECT_BASE) % 40 * 8)
        self._emit((4, x + left, y + top, x + right, y + bottom, (index, x, y)))

    def end_capture(self, key, cached):
        self.release()
        cached[2] = key
        # Cache admission must not make unchanged scenery appear to move.
        # Explicit invalidation removes its tracked revision when damaged.
        cached[3] = 0
        if not self.immediate and self._admit(len(cached[0])):
            self.terrain[key] = cached
            self.command_count += len(cached[0])
        self.blit(cached)

    def end_layer(self):
        if self.immediate:
            return
        key, revision, boxes = self.layer_info
        cached = self._metadata(self.surface, key, boxes)
        cached[3] = revision
        self.release()
        self.layer_info = None
        if self._admit(len(cached[0])):
            self.layers[key] = (revision, cached)
            self.command_count += len(cached[0])
        self.blit(cached)

    def fill_circle(self, x, y, radius, color):
        x, y, radius = int(x), int(y), int(radius)
        self._emit((1, x - radius, y - radius, x + radius + 1, y + radius + 1, color))

    def fill_rect(self, x, y, width, height, color):
        x, y, width, height = int(x), int(y), int(width), int(height)
        if width > 0 and height > 0:
            self._emit((0, x, y, x + width, y + height, color))

    def invalidate(self, key=None):
        if key is None:
            self.terrain.clear()
            self.lights.clear()
            self.layers.clear()
            self.tracked.clear()
            self.pending.clear()
            self.command_count = 0
            self.art_entries.clear()
            self.art_used = 0
            for page in range(len(self.art_offsets)):
                self.art_offsets[page] = 0
            self.full_redraw = True
        else:
            tracked = self.tracked.pop(key, None)
            if tracked is not None:
                for box in tracked[1]:
                    self._damage(box)
            cached = self.terrain.pop(key, None)
            if cached is not None:
                self.command_count -= len(cached[0])
            if key[0] == 'building':
                lights = self.lights.pop(key[1], ())
                self.command_count -= sum(len(t[0]) for group in lights for t in group)

    def layer(self, key, revision, boxes=None, background=False, position=None):
        if self.immediate:
            return True
        if position is not None:
            revision = (revision, position)
        cached = self.layers.get(key)
        if cached is not None:
            if cached[0] == revision:
                self.blit(cached[1])
                return False
            self.layers.pop(key)
            self.command_count -= len(cached[1][0])
        self.layer_info = (key, revision, boxes)
        self.surface = []
        return True

    def len(self, text):
        return len(text) * self.advance

    def prepare_effect(self, scale, compact):
        selected = 0 if compact else scale
        self.effect_index = -1
        if not 0 <= selected <= 5:
            raise ValueError('Invalid effect scale')
        if self.effect_source is not None and selected == self.effect_variant:
            return
        if self.effect_source is not None:
            self.effect_source.close()
        self.effect_source = open(self.path + '/effects-{}.bin'.format(selected), 'rb')
        if self.effect_source.read(8) != b'GFX1\x28\x00\x00\x00':
            raise ValueError('Invalid effect header')
        self.effect_directory = self.effect_source.read(320)
        if len(self.effect_directory) != 320:
            raise ValueError('Truncated effect directory')
        length = max(unpack_from('<II', self.effect_directory, frame * 8)[1] for frame in range(40))
        if not 2 <= length <= 18941:
            raise ValueError('Invalid effect record size')
        # One animation frame, allocated while loading the scene and reused
        # across shots/rematches. PicoCalc scale 2 needs 3,629 bytes, not 100 KiB.
        self.effect_buffer = memoryview(bytearray(length))
        # Retain bounds, not forty image payloads. Tight bounds prevent a tiny
        # spark from invalidating the whole maximum-size explosion canvas.
        for frame in range(40):
            offset, size = unpack_from('<II', self.effect_directory, frame * 8)
            data = self.effect_buffer[:size]
            self._read(self.effect_source, offset, data)
            cursor, left, top, right, bottom = 2, 65535, 65535, 0, 0
            for unused in range(unpack_from('<H', data)[0]):
                x, y, w, h = unpack_from('<HHHH', data, cursor)
                cursor += 8 + w * h
                left, top = min(left, x), min(top, y)
                right, bottom = max(right, x + w), max(bottom, y + h)
            if cursor != size:
                raise ValueError('Invalid effect record')
            if right == 0 or bottom == 0:
                left = top = 0
            pack_into('<HHHH', self.effect_bounds, frame * 8, left, top, right, bottom)
        self.effect_variant = selected

    def present(self):
        if self.immediate:
            self.draw.swap()
            self.max_calls = max(self.max_calls, self.frame_calls)
            return
        for key in tuple(self.tracked):
            if key not in self.seen:
                for box in self.tracked.pop(key)[1]:
                    self._damage(box)
                cached = self.layers.pop(key, None)
                if cached is not None:
                    self.command_count -= len(cached[1][0])
        if self.full_redraw:
            self.pending[:] = [(0, 0, self.width, self.height)]
            self.full_redraw = False
        else:
            self._expand()
        self.last_regions = len(self.pending)
        self.last_area = sum((c - a) * (d - b) for a, b, c, d in self.pending)
        for region in self.pending:
            self.clip = region
            a, b, c, d = region
            for command in self.frame:
                if command[1] < c and command[3] > a and command[2] < d and command[4] > b:
                    self._execute(command)
        if self.pending:
            self.draw.swap()
        self.pending.clear()
        self.max_calls = max(self.max_calls, self.frame_calls)

    def release(self):
        self.surface = None

    def text(self, x, y, text, color):
        x, y = int(x), int(y)
        self._emit((3, x, y, x + self.len(text), y + self.font_height, (text, color)))

    def watch(self, key, revision, box, background=False):
        if not self.immediate:
            self._watch(key, revision, (box,))
