from micropython import const
import font

FONT_XTRA_SMALL = const(0)  # Extra small
FONT_SMALL = const(1)  # Small
FONT_MEDIUM = const(2)  # Medium
FONT_LARGE = const(3)  # Large
FONT_XTRA_LARGE = const(4)  # Extra large


class Font(font.Font):
    """
    Font class

    Methods:
        - get_character(font_size: int, char: str) -> bytes: Get the bitmap data for a specific character at a given font size.
        - get_data(font_size: int) -> bytes: Get the bitmap data for the entire font at a given font size.
        - get_height(font_size: int) -> int: Get the height of the font at a given font size.
        - get_width(font_size: int) -> int: Get the width of the font at a given font size.
    """


class FontSize(font.FontSize):
    """
    FontSize class

    Properties:
        - height: int - The height of the font size.
        - size: int - The size identifier for the font size (e.g., FONT_XTRA_SMALL, FONT_SMALL, etc.).
        - width: int - The width of the font size.
    """
