"""Full-colour helper for FlipWorld.

The panel stores an 8-bit RGB332 framebuffer and is displayed inverted (see the C
`esp_lcd_panel_invert_color(..., true)`), and `image_bytearray`'s 8-bit path is a raw
memcpy with no transparency. So we pre-build a coloured RGB332 buffer per sprite ONCE:
each ink pixel (mask 0x00) becomes the inverted RGB332 of the wanted colour, and each
transparent pixel (mask 0xFF) stays 0xFF (framebuffer 0xFF -> panel black -> the game's
black background, i.e. transparent). Blitting the cached buffer is then free.
"""

# transparent framebuffer byte: 0xFF -> panel black -> matches the world background
_TRANSPARENT = 0xFF


def to332(c565):
    """RGB565 -> RGB332 (same packing the native lcd_color565_to_332 uses)."""
    return ((c565 & 0xE000) >> 8) | ((c565 & 0x0700) >> 6) | ((c565 & 0x0018) >> 3)


def ink_byte(c565):
    """Framebuffer byte that displays as colour c565 once the panel inverts it."""
    return (~to332(c565)) & 0xFF


def colorize(mask, c565):
    """Return a coloured RGB332 buffer for an 8-bit mask (0x00 ink / 0xFF clear).

    Masks only contain 0x00 (ink) and 0xFF (clear), so a single native replace recolours
    every ink pixel and leaves the transparent 0xFF bytes untouched.
    """
    return mask.replace(b"\x00", bytes([ink_byte(c565)]))


# ── World palette (RGB565, matches the Arduino build's ink colours) ────────────
COL_TREE = 0x0480    # deep foliage green (tree/plant)
COL_FLOWER = 0xF81F  # magenta bloom
COL_HOUSE = 0xB483   # warm timber
COL_FENCE = 0x9340   # wood brown
COL_ROCK = 0x8410    # stone grey
COL_WATER = 0x041F   # water blue
COL_ICE = 0xE77F     # pale ice
COL_MAN = 0x24BF     # blue-tunic NPC
COL_WOMAN = 0xFD5A   # rose-tunic NPC
COL_ENEMY = 0xF800   # red foe
COL_NPC = 0x2FE0     # friendly green NPC
COL_PLAYER = 0x001F  # pure blue hero (stays distinct from cyan water in RGB332)
COL_CHAR = 0x5982    # charred brown (burnt scenery)

# icon id -> colour (ids come from general.ICON_ID_*)
ICON_COLOR = {
    0: COL_HOUSE,
    1: COL_TREE,
    2: COL_TREE,
    3: COL_FENCE,
    4: COL_FLOWER,
    5: COL_ROCK,
    6: COL_ROCK,
    7: COL_ROCK,
    8: COL_WATER,
    9: COL_ICE,
    10: COL_WATER,
    11: COL_WATER,
    12: COL_FENCE,
    13: COL_FENCE,
    14: COL_MAN,
    15: COL_WOMAN,
}
