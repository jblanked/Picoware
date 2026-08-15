"""Color constants for Picoware.

Attributes:
    TFT_WHITE (int): Color constant for white.
    TFT_BLACK (int): Color constant for black.
    TFT_BLUE (int): Color constant for blue.
    TFT_CYAN (int): Color constant for cyan.
    TFT_RED (int): Color constant for red.
    TFT_LIGHTGREY (int): Color constant for light grey.
    TFT_DARKGREY (int): Color constant for dark grey.
    TFT_GREEN (int): Color constant for green.
    TFT_DARKCYAN (int): Color constant for dark cyan.
    TFT_DARKGREEN (int): Color constant for dark green.
    TFT_SKYBLUE (int): Color constant for sky blue.
    TFT_VIOLET (int): Color constant for violet.
    TFT_BROWN (int): Color constant for brown.
    TFT_TRANSPARENT (int): Color constant for transparent.
    TFT_YELLOW (int): Color constant for yellow.
    TFT_ORANGE (int): Color constant for orange.
    TFT_PINK (int): Color constant for pink.
    TFT_MAGENTA (int): Color constant for magenta.
"""

from micropython import const

# https://doc-tft-espi.readthedocs.io/tft_espi/colors/

TFT_WHITE = const(0xFFFF)
TFT_BLACK = const(0x0000)
TFT_BLUE = const(0x001F)
TFT_CYAN = const(0x07FF)
TFT_RED = const(0xF800)
TFT_LIGHTGREY = const(0xD69A)
TFT_DARKGREY = const(0x7BEF)
TFT_GREEN = const(0x07E0)
TFT_DARKCYAN = const(0x03EF)
TFT_DARKGREEN = const(0x03E0)
TFT_SKYBLUE = const(0x867D)
TFT_VIOLET = const(0x915C)
TFT_BROWN = const(0x9A60)
TFT_TRANSPARENT = const(0x0120)
TFT_YELLOW = const(0xFFE0)
TFT_ORANGE = const(0xFDA0)
TFT_PINK = const(0xFE19)
TFT_MAGENTA = const(0xF81F)