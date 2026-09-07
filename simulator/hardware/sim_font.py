"""Firmware bitmap fonts loaded lazily for the host simulator."""

METRICS = ((5, 8, 1), (7, 12, 1), (11, 16, 1), (14, 20, 0), (17, 24, 0))
_TABLES = {}


def font_data(size):
    """Read the original row-padded C table, keeping one cached copy per size."""
    size = size if 0 <= size < len(METRICS) else 0
    if size not in _TABLES:
        height = METRICS[size][1]
        path = __file__.rsplit("/", 1)[0] + "/../../src/MicroPython/font/font%d.c" % height
        data = bytearray()
        in_table = False
        with open(path) as source:
            for line in source:
                if "const uint8_t Font" in line:
                    in_table = True
                elif in_table:
                    if "};" in line:
                        break
                    for value in line.split("//", 1)[0].split(","):
                        value = value.strip()
                        if value.startswith("0x"):
                            data.append(int(value, 16))
        width, height, _ = METRICS[size]
        if len(data) < ((width + 7) // 8) * height * 95:
            raise ValueError("Incomplete firmware font table: " + path)
        _TABLES[size] = bytes(data)
    return _TABLES[size]


def glyph_rows(char, size=0):
    """Return one glyph, including the byte padding at the end of each row."""
    size = size if 0 <= size < len(METRICS) else 0
    code = ord(char[0]) if char else 32
    if not 32 <= code <= 126:
        code = ord("?")
    width, height, _ = METRICS[size]
    stride = ((width + 7) // 8) * height
    start = (code - 32) * stride
    return font_data(size)[start:start + stride]
