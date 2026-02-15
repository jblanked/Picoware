from picoware.system.colors import TFT_WHITE, TFT_BLACK
from picoware.system.vector import Vector
from picoware.system.boards import (
    BOARD_WAVESHARE_1_28_RP2350,
    BOARD_WAVESHARE_1_43_RP2350,
    BOARD_WAVESHARE_3_49_RP2350,
    BOARD_ID,
)

# Waveshare LCD imports
try:
    from waveshare_lcd import (
        get_font_size as waveshare_get_font_size,
        fill_screen as waveshare_fill_screen,
        draw_line,
        draw_rect as waveshare_draw_rect,
        blit as waveshare_blit,
        init,
        draw_circle,
        fill_circle,
        fill_rect,
        fill_round_rectangle,
        fill_triangle,
        draw_pixel,
        swap,
        draw_text,
        draw_char,
    )
except ImportError:
    pass

# PicoCalc LCD imports
try:
    from picoware_lcd import (
        deinit,
        init,
        clear_framebuffer,
        CHAR_WIDTH,
        FONT_HEIGHT,
        draw_circle,
        fill_circle,
        fill_rect,
        fill_round_rectangle,
        fill_triangle,
        draw_image_bytearray,
        draw_line,
        draw_line_custom,
        draw_pixel,
        swap,
        draw_text,
        draw_char,
        set_mode,
    )
except ImportError:
    pass


class Draw:
    """Class for drawing shapes and text on the display"""

    def __init__(
        self, foreground: int = TFT_WHITE, background: int = TFT_BLACK, mode: int = 0
    ) -> None:
        self._current_board_id = BOARD_ID

        self._background = background
        self._foreground = foreground

        self._size = Vector(0, 0)
        self._font_size = Vector(0, 0)

        self._use_lvgl = False

        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            self._size.x, self._size.y = 240, 240

            # Initialize native LCD extension
            init(True)
            self._font_size.x, self._font_size.y = waveshare_get_font_size()

        elif self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            self._size.x, self._size.y = 466, 466

            # Initialize native LCD extension
            init()
            self._font_size.x, self._font_size.y = waveshare_get_font_size()

        elif self._current_board_id == BOARD_WAVESHARE_3_49_RP2350:
            self._size.x, self._size.y = 172, 640

            # Initialize native LCD extension
            init()
            self._font_size.x, self._font_size.y = waveshare_get_font_size()

        else:  # PicoCalc
            self._size.x, self._size.y = 320, 320

            # Initialize native LCD extension
            init(background, mode)

            self._font_size.x = CHAR_WIDTH
            self._font_size.y = FONT_HEIGHT

            # Clear the display and framebuffer
            clear_framebuffer(self._rgb565_to_rgb332(background))

    @property
    def background(self) -> int:
        """Get the current background color"""
        return self._background

    @background.setter
    def background(self, color: int):
        """Set the current background color"""
        self._background = color

    @property
    def board_id(self) -> int:
        """Get the current board ID"""
        return self._current_board_id

    @property
    def font_size(self) -> Vector:
        """Get the font size"""
        return self._font_size

    @property
    def foreground(self) -> int:
        """Get the current foreground color"""
        return self._foreground

    @foreground.setter
    def foreground(self, color: int):
        """Set the current foreground color"""
        self._foreground = color

    @property
    def size(self) -> Vector:
        """Get the size of the display"""
        return self._size

    @property
    def use_lvgl(self) -> bool:
        """Get whether LVGL mode is enabled"""
        return self._use_lvgl

    @use_lvgl.setter
    def use_lvgl(self, state: bool):
        """Set whether to use LVGL mode for drawing"""
        self._use_lvgl = state

    def _rgb565_to_rgb332(self, rgb565):
        """Convert RGB565 color to RGB332 palette index"""
        return (
            ((rgb565 & 0xE000) >> 8)
            | ((rgb565 & 0x0700) >> 6)
            | ((rgb565 & 0x0018) >> 3)
        )

    def __del__(self):
        """Destructor to ensure cleanup on object deletion"""
        del self._size
        self._size = None
        del self._font_size
        self._font_size = None

        if BOARD_ID not in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            deinit()

    def char(self, position: Vector, char: str, color=None):
        """Draw a single character on the display"""
        _color = color if color is not None else self._foreground
        draw_char(position.x, position.y, ord(char), _color)

    def circle(self, position: Vector, radius: int, color: int = None):
        """Draw a circle outline"""
        _color = color if color is not None else self._foreground
        draw_circle(position.x, position.y, radius, _color)

    def clear(
        self,
        position: Vector = Vector(0, 0),
        size: Vector = Vector(320, 320),
        color=None,
    ):
        """Fill a rectangular area with a color"""
        _color = color if color is not None else self._background
        if (
            position.x == 0
            and position.y == 0
            and size.x >= self._size.x
            and size.y >= self._size.y
        ):
            self.fill_screen(_color)
        else:
            self.fill_rectangle(position, size, _color)

    def color332(self, color: int) -> int:
        """Convert RGB565 to RGB332 color format"""
        return self._rgb565_to_rgb332(color)

    def color565(self, r, g, b):
        """Convert RGB888 to RGB565 color format"""
        return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

    def erase(self):
        """Erase the display by filling with background color"""
        self.fill_screen(self._background)

    def fill_circle(self, position: Vector, radius: int, color=None):
        """Draw a filled circle"""
        _color = color if color is not None else self._foreground
        fill_circle(position.x, position.y, radius, _color)

    def fill_rectangle(self, position: Vector, size: Vector, color=None):
        """Draw a filled rectangle"""
        _color = color if color is not None else self._foreground
        fill_rect(
            position.x,
            position.y,
            size.x,
            size.y,
            _color,
        )

    def fill_round_rectangle(
        self, position: Vector, size: Vector, radius: int, color=None
    ):
        """Draw a filled rounded rectangle on the display"""
        if size.x <= 0 or size.y <= 0 or radius <= 0:
            return

        _color = color if color is not None else self._foreground

        fill_round_rectangle(
            position.x,
            position.y,
            size.x,
            size.y,
            radius,
            _color,
        )

    def fill_screen(self, color=None):
        """Fill the entire screen with a color"""
        _color = color if color is not None else self._background
        if self._current_board_id in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            waveshare_fill_screen(_color)
        else:
            clear_framebuffer(self._rgb565_to_rgb332(_color))

    def fill_triangle(self, point1: Vector, point2: Vector, point3: Vector, color=None):
        """Draw a filled triangle"""
        _color = color if color is not None else self._foreground
        fill_triangle(
            point1.x,
            point1.y,
            point2.x,
            point2.y,
            point3.x,
            point3.y,
            _color,
        )

    def image(self, position: Vector, img):
        """Draw an image object to the back buffer"""
        for y in range(img.size.y):
            for x in range(img.size.x):
                color = img.get_pixel(x, y)
                draw_pixel(position.x + x, position.y + y, color)

    def image_bmp(self, position: Vector, path: str, storage=None):
        """Draw a 24-bit BMP image"""
        try:
            if storage:
                storage.mount_vfs()
                if not path.startswith("sd") and not path.startswith("/sd"):
                    path = "/sd/" + path.lstrip("/")

            with open(path, "rb") as f:
                # Read BMP file header
                if f.read(2) != b"BM":
                    print("Not a BMP file")
                    return

                # Read file size and reserved fields
                _ = f.read(8)  # file size (4) + reserved (4)
                data_offset = int.from_bytes(f.read(4), "little")

                # Read DIB header
                _ = int.from_bytes(f.read(4), "little")  # dib_header_size
                width_bytes = f.read(4)
                height_bytes = f.read(4)

                # Convert bytes to signed integers manually
                width = int.from_bytes(width_bytes, "little")
                if width >= 0x80000000:
                    width = width - 0x100000000

                height = int.from_bytes(height_bytes, "little")
                if height >= 0x80000000:
                    height = height - 0x100000000

                # Read rest of header
                _ = int.from_bytes(f.read(2), "little")  # planes
                bits_per_pixel = int.from_bytes(f.read(2), "little")

                if bits_per_pixel != 24:
                    print(f"Expected 24-bit BMP, got {bits_per_pixel}-bit")
                    return

                # Go to pixel data
                f.seek(data_offset, 0)

                # Handle BMP orientation
                bottom_up = height > 0
                abs_height = abs(height)

                # For 24-bit BMPs: 3 bytes per pixel (BGR format)
                row_bytes = width * 3
                padding = (4 - (row_bytes % 4)) % 4

                # Calculate clipping boundaries once
                start_x = max(0, position.x)
                end_x = min(self._size.x, position.x + width)
                start_y = max(0, position.y)
                end_y = min(self._size.y, position.y + abs_height)

                if start_x >= end_x or start_y >= end_y:
                    return  # Completely clipped

                # Calculate source clipping
                src_start_x = max(0, -position.x)
                dst_width = end_x - start_x
                # Process each row with fast direct buffer writes
                for row in range(abs_height):
                    row_data = f.read(row_bytes)
                    if len(row_data) < row_bytes:
                        break

                    if padding > 0:
                        f.read(padding)

                    # Calculate y position
                    if bottom_up:
                        y = position.y + (abs_height - 1 - row)
                    else:
                        y = position.y + row

                    # Skip rows outside visible area
                    if y < start_y or y >= end_y:
                        continue

                    # For 8-bit framebuffer, convert each pixel and draw directly
                    for i in range(dst_width):
                        src_idx = src_start_x + i
                        pixel_offset = src_idx * 3

                        if pixel_offset + 2 < len(row_data):
                            # Read BGR pixel data
                            b = row_data[pixel_offset]
                            g = row_data[pixel_offset + 1]
                            r = row_data[pixel_offset + 2]

                            # Convert BGR888 to RGB565
                            rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

                            # Draw pixel using the framebuffer's conversion
                            draw_pixel(start_x + i, y, rgb565)

            if storage:
                storage.unmount_vfs()

        except (OSError, ValueError) as e:
            print(f"Error loading BMP: {e}")

    def image_bytearray(
        self, position: Vector, size: Vector, byte_data, invert: bool = False
    ):
        """Draw an image from 8-bit byte data (bytes or bytearray)"""
        if self._current_board_id in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            waveshare_blit(
                position.x,
                position.y,
                size.x,
                size.y,
                byte_data,
                # invert,
            )
        else:
            draw_image_bytearray(
                position.x,
                position.y,
                size.x,
                size.y,
                byte_data,
                invert,
            )

    def image_bytearray_1bit(self, position: Vector, size: Vector, byte_data) -> None:
        """Draw a 1-bit bitmap from packed byte_data (8 pixels per byte, row-aligned)"""
        width, height = size.x, size.y
        bytes_per_row = (width + 7) // 8  # Each row is padded to byte boundary

        # Unpack bits to 8-bit pixel values
        unpacked = bytearray(width * height)

        for y in range(height):
            row_start_byte = y * bytes_per_row
            for x in range(width):
                byte_offset = x // 8
                bit_position = 7 - (x % 8)  # MSB first
                byte_index = row_start_byte + byte_offset
                if byte_index < len(byte_data):
                    bit_value = (byte_data[byte_index] >> bit_position) & 1
                    if bit_value:  # Only write if bit is 1
                        unpacked[y * width + x] = 255

        self.image_bytearray(position, size, unpacked)

    def image_bytearray_path(
        self,
        position: Vector,
        size: Vector,
        path: str,
        storage=None,
        seek=0,
        chunk_size=0,
        mount_vfs=True,
    ):
        """Draw an image from an 8-bit bytearray file stored on disk"""
        try:
            if storage and mount_vfs:
                storage.mount_vfs()
                if not path.startswith("sd") and not path.startswith("/sd"):
                    path = "/sd/" + path.lstrip("/")

            with open(path, "rb") as f:
                if seek:
                    f.seek(seek, 0)
                if chunk_size:
                    byte_data = f.read(chunk_size)
                else:
                    byte_data = f.read()
                self.image_bytearray(position, size, byte_data)

            if storage and mount_vfs:
                storage.unmount_vfs()

        except (OSError, ValueError) as e:
            print(f"Error loading bytearray image: {e}")

    def line(self, position: Vector, size: Vector, color=None):
        """Draw horizontal line"""
        _color = color if color is not None else self._foreground
        if self._current_board_id in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            draw_line(position.x, position.y, size.x, size.y, _color)
        else:
            draw_line(position.x, position.y, size.x, _color)

    def line_custom(self, point_1: Vector, point_2: Vector, color=None):
        """Draw line between two points"""
        _color = color if color is not None else self._foreground
        if self._current_board_id in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            draw_line(
                point_1.x,
                point_1.y,
                point_2.x,
                point_2.y,
                _color,
            )
        else:
            draw_line_custom(
                point_1.x,
                point_1.y,
                point_2.x,
                point_2.y,
                _color,
            )

    def pixel(self, position: Vector, color=None):
        """Draw a pixel"""
        _color = color if color is not None else self._foreground
        draw_pixel(position.x, position.y, _color)

    def rect(self, position: Vector, size: Vector, color=None):
        """Draw a rectangle outline on the display"""
        if size.x <= 0 or size.y <= 0:
            return

        _color = color if color is not None else self._foreground

        if self._current_board_id in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            waveshare_draw_rect(
                position.x,
                position.y,
                size.x,
                size.y,
                _color,
            )
        else:
            x, y, w, h = position.x, position.y, size.x, size.y
            draw_line(x, y, w, _color)  # Top
            draw_line(x, y + h - 1, w, _color)  # Bottom
            draw_line_custom(x, y, x, y + h - 1, _color)  # Left
            draw_line_custom(x + w - 1, y, x + w - 1, y + h - 1, _color)  # Right

    def reset(self):
        """Reset the display by clearing the framebuffer"""
        self.fill_screen(self._background)

    def swap(self):
        """
        Swap the front and back buffers - convert 8-bit framebuffer to display
        """
        swap()

    def set_mode(self, mode: int) -> None:
        """
        Set the LCD framebuffer mode

        0 = PSRAM mode
        1 = HEAP mode
        """
        if BOARD_ID not in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            # MODE_PSRAM = 0, MODE_HEAP = 1
            set_mode(mode)

    def text(self, position: Vector, text: str, color=None):
        """Draw text on the display"""
        _color = color if color is not None else self._foreground
        draw_text(position.x, position.y, text, _color)

    def triangle(self, point1: Vector, point2: Vector, point3: Vector, color=None):
        """Draw a triangle outline"""
        _color = color if color is not None else self._foreground
        self.line_custom(point1, point2, _color)
        self.line_custom(point2, point3, _color)
        self.line_custom(point3, point1, _color)
