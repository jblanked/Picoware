from gc import collect as free
from gc import mem_free
from .draw import Draw
from .vector import Vector
from displayio import TileGrid, OnDiskBitmap


class Desktop:
    """A class to manage the desktop environment for the display."""

    def __init__(
        self, draw: Draw, text_color: int, background_color: int, sprite_file_path: str
    ) -> None:
        self.display = draw
        self.text_color = text_color
        self.background_color = background_color
        self.display.clear(Vector(0, 0), self.display.size, background_color)
        self.display.swap()
        self.board_name = self.display.board.name
        self.has_wifi = self.display.board.has_wifi
        self.tile_grid_main = None
        #
        try:
            bitmap = OnDiskBitmap(sprite_file_path)
            self.tile_grid_main = TileGrid(
                bitmap,
                pixel_shader=bitmap.pixel_shader,
                x=int(0),
                y=int(20),
            )
            del bitmap
            if draw.debug:
                print("Desktop bitmap loaded successfully.")
        except MemoryError as e:
            free()
            if draw.debug:
                print("MemoryError: Failed to load bitmap.")
                print(f"Free memory: {mem_free()} bytes")
            raise MemoryError(
                f"Failed to load bitmap. Memory free: {mem_free()} bytes"
            ) from e

        #
        bitmap = OnDiskBitmap(
            "/sd/wifi_on.bmp" if self.has_wifi else "/sd/wifi_off.bmp"
        )
        self.tile_grid_wifi = TileGrid(
            bitmap,
            pixel_shader=bitmap.pixel_shader,
            x=int(self.display.size.x - 21),
            y=int(2),
        )
        del bitmap

    def clear(self) -> None:
        """Clear the display with the background color."""
        self.display.clear(Vector(0, 0), self.display.size, self.background_color)
        self.display.swap()

    def draw(self) -> None:
        """Draw the desktop environment with a BMP image from disk."""
        self.display.clear(Vector(0, 0), self.display.size, self.background_color)
        self.draw_header()
        self.display.tile_grid(
            Vector(
                0,
                20,
            ),
            self.tile_grid_main,
        )
        self.display.swap()

    def draw_header(self) -> None:
        """Draw the header with the board name and Wi-Fi status."""
        # draw board name
        self.display.text(Vector(2, 5), self.board_name, self.text_color)
        # draw wifi icon
        self.display.tile_grid(
            Vector(
                self.display.size.x - 21,
                2,
            ),
            self.tile_grid_wifi,
        )
