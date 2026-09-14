"""Build Gorillas art.bin offline: python tools/gorillas-assets.py [output.bin].

The original pixel art lives here, not in the game runtime. The GRL1 container
holds an offset/length directory followed by opaque RGB332 rectangle records.
Each record starts with a uint16 rectangle count; each rectangle is four uint16
values (x, y, width, height), then width*height raw pixels, all little-endian.
Transparent gaps are omitted, so the stock opaque Draw API preserves them.
"""

BANANA = (
    "......s.", ".....sy.", ".....yy.", "....yhy.",
    "...yhys.", ".syhys..", "syyys...", ".sss....",
)

CLOUD = (
    ".........hhhh...........",
    "........hhhhhh..........",
    "....hhhhhhhhhhhh........",
    "...hhhhhhhhhhhhhhhhh....",
    ".hhhhhhhhhhhhhhhhhhhh...",
    "hhhhhhhhhhhhhhhhhhhhhhh.",
    ".ssssssssssssssssssssss.",
    "...sssssssssssssssss....",
)

GORILLA = (
    ".......oooooo.......",
    "......offffffo......",
    ".....offhhhhffo.....",
    ".....ofhmmmmhfo.....",
    ".....ofmommomfo.....",
    ".....ofmmmmmmfo.....",
    "....offmssssmffo....",
    "...offfhmmmmhfffo...",
    "..offffhffffhffffo..",
    ".offffhhffffhhfffoo.",
    "offffhhmmmmmmhhfffo.",
    "offffhmmhhhhmmhfffo.",
    "offffhmmhhhhmmhfffo.",
    "offfohmmhhhhmmhofffo",
    "offfohmmmmmmmmhofffo",
    "ommmoofffffffoommmo",
    "ommmoffffffffommmmo",
    ".ooooffffffffooooo.",
    ".....offooffo.......",
    "....offfoofffo......",
    "...offffooffffo.....",
    "...ommmmoommmmo.....",
    "...ooooo..ooooo.....",
)

# Replace the hanging arm with the torso outline below the raised shoulder.
GORILLA_THROW = (
    ".ommmo.oooooo.......",
    ".ommmooffffffo......",
    ".offfoffhhhhffo.....",
    ".offfofhmmmmhfo.....",
    ".offfofmommomfo.....",
    ".offfofmmmmmmfo.....",
    ".offfofmssssmffo....",
    ".offfffhmmmmhfffo...",
    "..offffhffffhffffo..",
    "...offhhffffhhfffoo.",
) + tuple("....o" + row[5:] for row in GORILLA[10:18]) + GORILLA[18:]

GORILLA_SMALL = (
    "...oooo...", "..ohhhho..", "..hohhoh..", "..hmmmmh..",
    ".ohhmmhho.", "ohhmmmmhho", "ohhmmmmhho", "omohhhhomo",
    ".oohhhhoo.", "...h..h...", "..om..mo..",
)

GORILLA_DEAD = GORILLA_THROW[:3] + (
    ".offfofmomomomfo....",
    ".offfofmmoommfo.....",
    ".offfofmomomomfo....",
) + GORILLA_THROW[6:]

TITLE = {
    "A": (".###.", "##.##", "##.##", "#####", "##.##", "##.##", "##.##"),
    "G": (".####", "##...", "##...", "##.##", "##.##", "##.##", ".####"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "L": ("##...", "##...", "##...", "##...", "##...", "##...", "#####"),
    "O": (".###.", "##.##", "##.##", "##.##", "##.##", "##.##", ".###."),
    "R": ("####.", "##.##", "##.##", "####.", "##.##", "##.##", "##.##"),
    "S": (".####", "##...", "##...", ".###.", "...##", "...##", "####."),
}


def spans(pattern):
    """Compile transparent art to horizontal color runs outside rendering."""
    result = []
    for y, row in enumerate(pattern):
        x = 0
        while x < len(row):
            pixel = row[x]
            end = x + 1
            while end < len(row) and row[end] == pixel:
                end += 1
            if pixel != ".":
                result.append((x, y, end - x, pixel))
            x = end
    return tuple(result)


BANANA_FRAMES = []
_frame = BANANA
for _rotation in range(4):
    BANANA_FRAMES.append(spans(_frame))
    _frame = tuple("".join(row[x] for row in reversed(_frame)) for x in range(8))
BANANA_FRAMES = tuple(BANANA_FRAMES)
CLOUD_ART = spans(CLOUD)
GORILLA_ART = (spans(GORILLA), spans(GORILLA_THROW), spans(GORILLA_SMALL), spans(GORILLA_DEAD))
TITLE_ART = spans(tuple(".".join(TITLE[ch][row] for ch in "GORILLAS") for row in range(7)))


class Builder:
    """Host-only sprite baking and rectangle merging, never loaded on-device."""

    def build(self, output):
        import importlib.util
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location('gorillas_art_spec', root / 'builds/MicroPython/apps_unfrozen/games/gorillas_game/assets.py')
        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)
        records = []
        for art_index, (art, settings) in enumerate(zip(BANANA_FRAMES + (CLOUD_ART,) + GORILLA_ART + (TITLE_ART,), config.SPECS)):
            scales, channels, palettes, mirrors, phases = settings
            for scale in scales:
                for colors in palettes:
                    palette = dict(zip(channels, colors))
                    for mirrored in range(mirrors):
                        for dissolve in range(phases):
                            mirror = (10 if art is GORILLA_ART[2] else 20) if mirrored else 0
                            if config.variant(art_index, scale, palette, mirror, dissolve) != len(records):
                                raise ValueError('Asset directory and runtime index disagree')
                            records.append(self.encode(art, scale, palette, mirror, dissolve))
        if len(records) != config.EFFECT_BASE:
            raise ValueError('Effect index does not follow the sprite directory')
        result = self.container(records, b'GRL1')
        Path(output).write_bytes(result)
        print('Built', len(records), 'variants;', len(result), 'bytes:', output)
        for scale in range(6):
            frames = [self.effect(max(1, scale), scale == 0, age) for age in range(40)]
            target = Path(output).with_name('effects-{}.bin'.format(scale))
            result = self.container(frames, b'GFX1')
            target.write_bytes(result)
            print('Built', len(frames), 'effect frames;', len(result), 'bytes:', target)

    def circle(self, pixels, cx, cy, radius, color, filled=False):
        """Bake the same integer circle geometry as the stock LCD driver."""
        color = ((color >> 8) & 0xE0) | ((color >> 6) & 0x1C) | ((color >> 3) & 3)
        xv, yv, error = 0, radius, 3 - 2 * radius
        while xv <= yv:
            if filled:
                for x, y, width in ((cx-xv, cy+yv, 2*xv+1), (cx-xv, cy-yv, 2*xv+1),
                                    (cx-yv, cy+xv, 2*yv+1), (cx-yv, cy-xv, 2*yv+1)):
                    pixels[y][x:x+width] = bytes([color]) * width
            else:
                for x, y in ((cx+xv, cy+yv), (cx-xv, cy+yv), (cx+xv, cy-yv), (cx-xv, cy-yv),
                             (cx+yv, cy+xv), (cx-yv, cy+xv), (cx+yv, cy-xv), (cx-yv, cy-xv)):
                    pixels[y][x] = color
            if error < 0:
                error += 4 * xv + 6
            else:
                error += 4 * (xv - yv) + 10
                yv -= 1
            xv += 1

    def container(self, records, magic):
        from struct import pack

        offset, index = 8 + len(records) * 8, bytearray()
        for record in records:
            index.extend(pack('<II', offset, len(record)))
            offset += len(record)
        return magic + pack('<I', len(records)) + index + b''.join(records)

    def effect(self, scale, compact, age):
        """Bake fireball, shock ring and lingering smoke; debris stays dynamic."""
        from math import cos, pi, sin

        pixels = [bytearray(b'\xe3' * (64 * scale)) for row in range(72 * scale)]
        x, y = 32 * scale, 40 * scale
        if age < 13:
            self.circle(pixels, x, y, max(1, int((4 + age * 1.5) * scale)), 0xFFFF if compact else 0xFDEA)
        if age >= 10:
            for puff in range(5):
                px = x + int(sin(puff * 2.3) * (4 + age / 5) * scale)
                py = y - int((age - 10) * 0.6 * scale) + (puff % 2) * 3 * scale
                radius = max(1, int((3 + age / 9) * scale))
                color = 0xFFFF if compact else (0x52F0 if age < 24 else 0x39CD)
                self.circle(pixels, px, py, radius if age < 28 else max(1, radius - (age - 28) // 3), color, age < 28)
        if age < 22:
            radius = max(2, int((4 + min(age, 7) * 1.7 - max(0, age - 7) * 0.8) * scale))
            for lobe in range(6):
                angle = lobe * pi / 3 + age / 15
                px, py = x + int(cos(angle) * radius / 2), y + int(sin(angle) * radius / 2)
                self.circle(pixels, px, py, max(1, radius // 2), 0xFFFF if compact else (0xFBAE if age < 12 else 0xDAA6), True)
            self.circle(pixels, x, y, max(1, radius * 2 // 3), 0 if compact else 0xFDEA, True)
            if age < 9:
                self.circle(pixels, x, y, max(1, radius // 3), 0xFFFF if compact else 0xFF35, True)
        return self.pack(pixels)

    def encode(self, art, scale, palette, mirror, dissolve):

        width = int(max(mirror, max(x + length for x, y, length, symbol in art)) * scale)
        height = int((max(y for x, y, length, symbol in art) + 1) * scale)
        pixels = [bytearray(b'\xe3' * width) for row in range(height)]
        for x, y, length, symbol in art:
            if dissolve and (x * 3 + y * 7) % 12 < dissolve:
                continue
            left = mirror - x - length if mirror else x
            right = int((left + length) * scale)
            left = int(left * scale)
            color = palette[symbol]
            color = ((color >> 8) & 0xE0) | ((color >> 6) & 0x1C) | ((color >> 3) & 3)
            if color == 0xE3:
                color = 0xE2
            for row in range(int(y * scale), int((y + 1) * scale)):
                pixels[row][left:right] = bytes([color]) * (right - left)
        return self.pack(pixels)

    def pack(self, pixels):
        from struct import pack

        width = len(pixels[0])
        rectangles, active = [], {}
        for y, row in enumerate(pixels):
            current, x = {}, 0
            while x < width:
                if row[x] == 0xE3:
                    x += 1
                    continue
                end = x + 1
                while end < width and row[end] != 0xE3:
                    end += 1
                key = (x, end - x)
                rectangle = active.pop(key, None)
                if rectangle is None:
                    rectangle = [x, y, end - x, 0, bytearray()]
                    rectangles.append(rectangle)
                rectangle[3] += 1
                rectangle[4].extend(row[x:end])
                current[key] = rectangle
                x = end
            active = current
        result = bytearray(pack('<H', len(rectangles)))
        for x, y, width, height, data in rectangles:
            result.extend(pack('<HHHH', x, y, width, height))
            result.extend(data)
        return bytes(result)


if __name__ == '__main__':
    from pathlib import Path
    import sys

    output = sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / 'builds/MicroPython/apps_unfrozen/games/gorillas_game/art.bin'
    Builder().build(output)
