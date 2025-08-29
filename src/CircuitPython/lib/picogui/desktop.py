from gc import collect as free
from gc import mem_free
from .draw import Draw
from .vector import Vector
from picoware.system.color import COLOR_WHITE, COLOR_BLACK
from displayio import TileGrid, OnDiskBitmap


class Desktop:
    """A class to manage the desktop environment for the display."""

    def __init__(self, draw: Draw, text_color: int = COLOR_WHITE) -> None:
        self.display = draw
        self.text_color = text_color
        self.display.clear(Vector(0, 0), self.display.size, COLOR_BLACK)
        self.display.swap()

    def clear(self) -> None:
        """Clear the display with the background color."""
        self.display.clear(Vector(0, 0), self.display.size, COLOR_BLACK)
        self.display.swap()

    def draw(self) -> None:
        """Draw the desktop environment with a BMP image from disk."""
        self.draw_header()
        self.display.image_file_bmp_on_disk(Vector(0, 20), "/sd/desktop.bmp")
        self.display.swap()

    def draw_header(self) -> None:
        """Draw the header with the board name and Wi-Fi status."""
        # draw board name
        self.display.text(Vector(2, 5), self.display.board.name, self.text_color)
        # draw wifi icon
        self.display.image_file_bmp_on_disk(
            Vector(int(self.display.size.x - 21), 2),
            "/sd/wifi_on.bmp" if self.display.board.has_wifi else "/sd/wifi_off.bmp",
        )
