"""Index of prebuilt RGB332 artwork in art.bin; no runtime sprite rasterizer."""

BANANA_FRAMES = (0, 1, 2, 3)
CLOUD_ART = 4
EFFECT_BASE = 409
EFFECT_RECORD_BYTES = 3629
GORILLA_ART = (5, 6, 7, 8)
GORILLA_FALLEN_ART = (10, 11)
TITLE_ART = 9
_BASES = (0, 10, 20, 30, 40, 50, 70, 90, 138, 378, 387, 407)

_BANANA = ((1, 2, 3, 4, 5), "syh", ((0xA365, 0xFDEA, 0xFF35), (0xFFFF,) * 3), 1, 1)
_NORMAL = ((0x1085, 0x49CA, 0x8B51, 0xE534, 0x3928), (0x1085, 0x71E9, 0xBBAE, 0xE534, 0x3928))
_FLASH = (0xFFFF, 0xFFFF, 0xFFFF, 0xFFFF, 0)
_SCALES = (1, 1.5, 2.25, 3, 3.75)
SPECS = (
    _BANANA, _BANANA, _BANANA, _BANANA,
    ((1, 2), "hs", ((0xDEDC, 0xA475), (0xFFFF, 0xAE1B), (0xAD15, 0x83B2), (0x4A70, 0x294A), (0xFFFF, 0)), 1, 1),
    (_SCALES, "ofhms", _NORMAL, 2, 1),
    (_SCALES, "ofhms", _NORMAL, 2, 1),
    ((1,), "ofhms", ((0, 0xFFFF, 0xFFFF, 0xFFFF, 0), _FLASH), 2, 12),
    (_SCALES, "ofhms", (_FLASH, (0x1085, 0x296A, 0x52F0, 0xACD4, 0x1085)), 2, 12),
    ((1, 2, 3), "#", ((0xFF35,), (0x91E9,), (0xFFFF,)), 1, 1),
    (_SCALES, "ofhms", _NORMAL, 2, 1),
    ((1,), "ofhms", ((0, 0xFFFF, 0xFFFF, 0xFFFF, 0),), 2, 1),
)


def variant(art, scale, palette, mirror, dissolve):
    """Locate a prebuilt palette/scale/pose without creating pixel data."""
    scales, channels, palettes, mirrors, phases = SPECS[art]
    colors = tuple(palette[channel] for channel in channels)
    return _BASES[art] + (((scales.index(scale) * len(palettes) + palettes.index(colors)) * mirrors + bool(mirror)) * phases + dissolve)

# Raw RGB332 loading assets: filename, width, height.
LOADING_LOGO = ("loading-logo.bin", 78, 72)
LOADING_LOGO_COMPACT = ("loading-logo-compact.bin", 52, 48)
LOADING_SCENE = ("loading-scene.bin", 320, 320)
LOADING_SCENE_SPRING = ("loading-scene-spring.bin", 320, 320)
LOADING_SCENE_SUMMER = ("loading-scene-summer.bin", 320, 320)
LOADING_SCENE_FALL = ("loading-scene-fall.bin", 320, 320)
LOADING_SCENE_WINTER = ("loading-scene-winter.bin", 320, 320)
