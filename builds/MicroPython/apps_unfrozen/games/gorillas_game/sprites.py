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
        self.opaque_ui, self.opaque_terrain = (), ()
        self.terrain_unit = 1
        self.terrain_clip = None
        self.opaque_revision = 0
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
        self.art_access = [0] * len(self.art_cache)
        self.art_clock = 0
        self.art_scratch_index = -1
        self.art_entries = {}
        self.art_rectangles = {}
        self.art_rectangle_count = 0
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

    def _art_evict(self, page):
        """Recycle one cold page and its metadata without enlarging the cache."""
        for index in tuple(self.art_entries):
            if self.art_entries[index][0] == page:
                del self.art_entries[index]
                rectangles = self.art_rectangles.pop(index, ())
                self.art_rectangle_count -= len(rectangles)
        self.art_used -= self.art_offsets[page]
        self.art_offsets[page] = 0

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
            if kind == 1:
                self.draw._fill_circle(x + radius, y + radius, radius, value)
            else:
                self.draw._circle(x + radius, y + radius, radius, value)
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

    def _hidden(self, box):
        """Suppress damage only when every pixel is covered by later solids."""
        left, top, right, bottom = box
        for a, b, c, d in self.opaque_ui:
            if a <= left and b <= top and right <= c and bottom <= d:
                return True
        unit = self.terrain_unit
        for x, y, width, height, cols, rows, cells in self.opaque_terrain:
            if left < x or top < y or right > x + width or bottom > y + height:
                continue
            first, last = (left - x) // unit, (right - 1 - x) // unit
            solid = True
            for row in range((top - y) // unit, (bottom - 1 - y) // unit + 1):
                offset = row * cols
                for col in range(first, last + 1):
                    if not cells[offset + col]:
                        solid = False
                        break
                if not solid:
                    break
            if solid:
                return True
        return False

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
                if page < 0 and length <= len(self.art_cache[0]):
                    page = min(range(len(self.art_cache)), key=lambda candidate: self.art_access[candidate])
                    self._art_evict(page)
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
                    if self.art_scratch_index != index:
                        self.art_scratch_index = -1
                        self._read(self.art_source, offset, data)
                        self.art_scratch_index = index
            if cached is not None or page >= 0:
                self.art_clock += 1
                self.art_access[page] = self.art_clock
        cursor, calls = 2, 0
        a, b, c, d = self.clip
        image = self.draw._bytearray
        data_length = len(data)
        count = unpack_from('<H', data)[0]
        rectangles = self.art_rectangles.get(index)
        if (rectangles is None and index < EFFECT_BASE and index in self.art_entries
                and 0 < count <= 16 and self.art_rectangle_count + count <= 64
                and mem_free() > 65536):
            # Cache only a bounded amount of geometry for resident artwork.
            # Payloads stay in the existing pages; no additional pixel copies.
            rectangles = []
            for unused in range(count):
                px, py, w, h = unpack_from('<HHHH', data, cursor)
                cursor += 8
                end = cursor + w * h
                if not w or not h or end > data_length:
                    raise ValueError('Invalid sprite rectangle')
                rectangles.append((px, py, w, h, cursor, end))
                cursor = end
            if cursor != data_length:
                raise ValueError('Invalid sprite length')
            self.art_rectangles[index] = rectangles
            self.art_rectangle_count += count
            cursor = 2
        for unused in range(count):
            if rectangles is None:
                px, py, w, h = unpack_from('<HHHH', data, cursor)
                cursor += 8
                end = cursor + w * h
                if not w or not h or end > data_length:
                    raise ValueError('Invalid sprite rectangle')
            else:
                px, py, w, h, cursor, end = rectangles[unused]
            px += x
            py += y
            if px < c and px + w > a and py < d and py + h > b:
                left = a - px if px < a else 0
                top = b - py if py < b else 0
                right = c - px if px + w > c else w
                bottom = d - py if py + h > d else h
                # Clip before slicing; feed the existing bytearray API directly
                # from the record buffer, without a per-patch Python wrapper.
                if left == 0 and right == w:
                    image(px, py + top, w, bottom - top,
                          data[cursor + top * w:cursor + bottom * w])
                    calls += 1
                else:
                    for row in range(top, bottom):
                        offset = cursor + row * w
                        image(px + left, py + row, right - left, 1,
                              data[offset + left:offset + right])
                    calls += bottom - top
            cursor = end
        self.calls += calls
        self.frame_calls += calls
        if cursor != data_length:
            raise ValueError('Invalid sprite length')

    def _read(self, source, offset, data):
        source.seek(offset)
        if source.readinto(data) != len(data):
            raise ValueError('Truncated sprite')
        self.asset_reads += 1
        self.asset_bytes += len(data)

    def _watch(self, key, revision, boxes, background=False):
        self.seen.add(key)
        old = self.tracked.get(key)
        if background:
            # Unmoved clouds/stars need no repeated terrain scan. Damage and UI
            # changes invalidate this visibility decision even without motion.
            if old is not None and len(old) == 4 and old[0] == revision and old[2] == boxes and old[3] == self.opaque_revision:
                return
            visible = tuple(box for box in boxes if not self._hidden(box))
            current = (revision, visible, boxes, self.opaque_revision)
            boxes = visible
        else:
            current = (revision, boxes)
        if old is None or old[0] != revision or old[1] != boxes:
            if old is not None:
                for box in old[1]:
                    self._damage(box)
            for box in boxes:
                self._damage(box)
        if old != current:
            self.tracked[key] = current

    def art(self, art, x, y, scale, palette, mirror=0, dissolve=0):
        if dissolve >= 12:
            return
        index = variant(art, scale, palette, mirror, dissolve)
        w = 8 if art < 4 else (24 if art == 4 else (47 if art == 9 else (10 if art == 7 else 20)))
        h = 8 if art <= 4 else (7 if art == 9 else (11 if art == 7 else 23))
        x, y = int(x), int(y)
        self._emit((4, x, y, x + int(w * scale), y + int(h * scale), (index, x, y)))

    def begin(self, color, ui_boxes=(), terrain=(), terrain_unit=1):
        if ui_boxes != self.opaque_ui:
            self.opaque_revision += 1
        self.opaque_ui, self.opaque_terrain = ui_boxes, terrain
        self.terrain_unit = terrain_unit
        self.frame.clear()
        self.atoms.clear()
        self.seen.clear()
        self.frame_calls = 0
        if self.immediate:
            self.clip = (0, 0, self.width, self.height)
        self.fill_rect(0, 0, self.width, self.height, color)

    def blit(self, cached, background=False):
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
            self._watch(cached[2], cached[3], cached[1], background)

    def box(self, x, y, width, height, color):
        """Normalize scene geometry once and preserve terrain-hole clipping."""
        x, y = int(x), int(y)
        width, height = max(1, int(width)), max(1, int(height))
        clip = self.terrain_clip
        if clip is None:
            # Common path: no game helper, fill_rect or _emit dispatch.
            if self.surface is not None:
                self.surface.append((0, x, y, x + width, y + height, color))
            elif self.immediate:
                # Native LCD coordinates are unsigned. Clip before crossing
                # that boundary, including particles partly off screen.
                a, b, c, d = self.clip
                right, bottom = min(c, x + width), min(d, y + height)
                x, y = max(a, x), max(b, y)
                if x < right and y < bottom:
                    self.draw._fill_rectangle(x, y, right - x, bottom - y, color)
                    self.calls += 1
                    self.frame_calls += 1
            else:
                self.frame.append((0, x, y, x + width, y + height, color))
            return
        terrain, unit, intact = clip
        bx, by, bw, bh, cols, rows, cells = terrain
        rectangle = self.fill_rect
        # Rooftop props are drawn only when their supports survive.
        if y < by:
            top_height = min(height, by - y)
            rectangle(x, y, width, top_height, color)
            y += top_height
            height -= top_height
        end_x, end_y = min(x + width, bx + bw), min(y + height, by + bh)
        x, y = max(x, bx), max(y, by)
        if intact:
            if end_x > x and end_y > y:
                rectangle(x, y, end_x - x, end_y - y, color)
            return
        active = {}
        while y < end_y:
            current = {}
            row = (y - by) // unit
            bottom = min(end_y, by + (row + 1) * unit)
            xx = x
            while xx < end_x:
                col = (xx - bx) // unit
                solid = bool(cells[row * cols + col])
                right = min(end_x, bx + (col + 1) * unit)
                while right < end_x and bool(cells[row * cols + (right - bx) // unit]) == solid:
                    right = min(end_x, right + unit)
                if solid:
                    run = (xx, right)
                    current[run] = active.pop(run, y)
                xx = right
            for (left, right), top in active.items():
                rectangle(left, top, right - left, y - top, color)
            active = current
            y = bottom
        for (left, right), top in active.items():
            rectangle(left, top, right - left, y - top, color)

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
        key, revision, boxes, background = self.layer_info
        cached = self._metadata(self.surface, key, boxes)
        cached[3] = revision
        self.release()
        self.layer_info = None
        if self._admit(len(cached[0])):
            self.layers[key] = (revision, cached)
            self.command_count += len(cached[0])
        self.blit(cached, background)

    def fill_circle(self, x, y, radius, color):
        self._emit((1, x - radius, y - radius, x + radius + 1, y + radius + 1, color))

    def fill_rect(self, x, y, width, height, color):
        # Already-normalized solid spans: no command dispatcher per rectangle.
        if width > 0 and height > 0:
            if self.surface is not None:
                self.surface.append((0, x, y, x + width, y + height, color))
            elif self.immediate:
                a, b, c, d = self.clip
                right, bottom = min(c, x + width), min(d, y + height)
                x, y = max(a, x), max(b, y)
                if x < right and y < bottom:
                    self.draw._fill_rectangle(x, y, right - x, bottom - y, color)
                    self.calls += 1
                    self.frame_calls += 1
            else:
                self.frame.append((0, x, y, x + width, y + height, color))

    def invalidate(self, key=None, artwork=True):
        self.opaque_revision += 1
        if key is None:
            self.terrain.clear()
            self.lights.clear()
            self.layers.clear()
            self.tracked.clear()
            self.pending.clear()
            self.command_count = 0
            if artwork:
                self.art_entries.clear()
                self.art_rectangles.clear()
                self.art_rectangle_count = 0
                self.art_used = 0
                self.art_clock = 0
                self.art_scratch_index = -1
                for page in range(len(self.art_offsets)):
                    self.art_offsets[page] = 0
                    self.art_access[page] = 0
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
                self.blit(cached[1], background)
                return False
            self.layers.pop(key)
            self.command_count -= len(cached[1][0])
        self.layer_info = (key, revision, boxes, background)
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
        # Replay leaf commands directly into stock Draw. Avoid another Python
        # method dispatch for every rectangle in every cached building group.
        rectangle = self.draw._fill_rectangle
        circle, fill_circle = self.draw._circle, self.draw._fill_circle
        text, font = self.draw._text, self.draw.font
        packed = self._packed
        calls = 0
        for region in self.pending:
            self.clip = region
            a, b, c, d = region
            for group in self.frame:
                if group[1] >= c or group[3] <= a or group[2] >= d or group[4] <= b:
                    continue
                commands = group[5] if group[0] == 5 else (group,)
                for command in commands:
                    kind, x, y, right, bottom, value = command
                    if x >= c or right <= a or y >= d or bottom <= b:
                        continue
                    if kind == 0:
                        left, top = x if x > a else a, y if y > b else b
                        rectangle(left, top, (right if right < c else c) - left,
                                  (bottom if bottom < d else d) - top, value)
                    elif kind in (1, 2):
                        radius = (right - x - 1) // 2
                        if kind == 1:
                            fill_circle(x + radius, y + radius, radius, value)
                        else:
                            circle(x + radius, y + radius, radius, value)
                    elif kind == 3:
                        text(x, y, value[0], value[1], font)
                    elif kind == 4:
                        packed(value[0], value[1], value[2])
                        continue
                    else:
                        self._execute(command)
                        continue
                    calls += 1
        self.calls += calls
        self.frame_calls += calls
        if self.pending:
            self.draw.swap()
        self.pending.clear()
        self.max_calls = max(self.max_calls, self.frame_calls)

    def release(self):
        self.surface = None

    def set_terrain_clip(self, terrain, unit):
        # A drawing batch never mutates terrain. Recheck after every new batch,
        # including cache rebuilds after damage, not for every facade rectangle.
        self.terrain_clip = None if terrain is None else (terrain, unit, all(terrain[-1]))

    def text(self, x, y, text, color):
        self._emit((3, x, y, x + self.len(text), y + self.font_height, (text, color)))

    def watch(self, key, revision, box, background=False):
        if not self.immediate:
            self._watch(key, revision, (box,), background)
