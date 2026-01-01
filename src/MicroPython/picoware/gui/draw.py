from picoware.system.colors import TFT_WHITE, TFT_BLACK
from picoware.system.vector import Vector
from picoware.system.boards import (
    BOARD_WAVESHARE_1_28_RP2350,
    BOARD_WAVESHARE_1_43_RP2350,
    BOARD_WAVESHARE_3_49_RP2350,
)


class Draw:
    """Class for drawing shapes and text on the display"""

    def __init__(self, foreground: int = TFT_WHITE, background: int = TFT_BLACK):
        from picoware_boards import BOARD_ID

        self._current_board_id = BOARD_ID

        self._background = background
        self._foreground = foreground

        self._size = Vector(0, 0)
        self._font_size = Vector(0, 0)
        self.palette = None

        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            self._size = Vector(240, 240)

            from waveshare_lcd import init, get_font_size

            # Initialize native LCD extension
            init(True)
            self._font_size.x, self._font_size.y = get_font_size()

        elif self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            self._size = Vector(466, 466)

            from waveshare_lcd import init, get_font_size

            # Initialize native LCD extension
            init()
            self._font_size.x, self._font_size.y = get_font_size()

        elif self._current_board_id == BOARD_WAVESHARE_3_49_RP2350:
            self._size = Vector(172, 640)

            from waveshare_lcd import init, get_font_size

            # Initialize native LCD extension
            init()
            self._font_size.x, self._font_size.y = get_font_size()

        else:  # PicoCalc
            self._size = Vector(320, 320)

            from picoware_lcd import init, clear_framebuffer, CHAR_WIDTH, FONT_HEIGHT

            # Initialize native LCD extension
            init(background)

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

    def _rgb565_to_rgb332(self, rgb565):
        """Convert RGB565 color to RGB332 palette index"""
        return (
            ((rgb565 & 0xE000) >> 8)
            | ((rgb565 & 0x0700) >> 6)
            | ((rgb565 & 0x0018) >> 3)
        )

    def __del__(self):
        """Destructor to ensure cleanup on object deletion"""
        try:
            self.cleanup()
        except Exception:
            pass

    def circle(self, position: Vector, radius: int, color: int = None):
        """Draw a circle outline"""
        _color = color if color is not None else self._foreground
        if self._current_board_id in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            from waveshare_lcd import draw_circle

            draw_circle(int(position.x), int(position.y), radius, _color)
        else:
            from picoware_lcd import draw_circle

            draw_circle(int(position.x), int(position.y), radius, _color)

    def clear(
        self,
        position: Vector = Vector(0, 0),
        size: Vector = Vector(320, 320),
        color=None,
    ):
        """Fill a rectangular area with a color"""
        _color = color if color is not None else self._background
        if position == Vector(0, 0) and size == Vector(320, 320):
            self.fill_screen(_color)
        else:
            self.fill_rectangle(position, size, _color)

    def cleanup(self):
        """Cleanup all allocated buffers and free memory"""
        from gc import collect

        # Clean up palette
        if self.palette is not None:
            del self.palette
            self.palette = None

        del self._size
        self._size = None

        # Force garbage collection
        collect()

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
        if self._current_board_id in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            from waveshare_lcd import fill_circle

            fill_circle(int(position.x), int(position.y), radius, _color)
        else:
            from picoware_lcd import fill_circle

            fill_circle(int(position.x), int(position.y), radius, _color)

    def fill_rectangle(self, position: Vector, size: Vector, color=None):
        """Draw a filled rectangle"""
        _color = color if color is not None else self._foreground
        if self._current_board_id in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            from waveshare_lcd import fill_rect

            fill_rect(
                int(position.x),
                int(position.y),
                int(size.x),
                int(size.y),
                _color,
            )
        else:
            from picoware_lcd import fill_rect

            fill_rect(
                int(position.x),
                int(position.y),
                int(size.x),
                int(size.y),
                _color,
            )

    def fill_round_rectangle(
        self, position: Vector, size: Vector, radius: int, color=None
    ):
        """Draw a filled rounded rectangle on the display"""
        if size.x <= 0 or size.y <= 0 or radius <= 0:
            return

        _color = color if color is not None else self._foreground

        # Clip to screen bounds
        x: int = int(position.x)
        y: int = int(position.y)
        width: int = int(size.x)
        height: int = int(size.y)

        # Adjust for left and top boundaries
        if x < 0:
            width += x
            x = 0
        if y < 0:
            height += y
            y = 0

        # Adjust for right and bottom boundaries
        if x + width > self._size.x:
            width = self._size.x - x
        if y + height > self._size.y:
            height = self._size.y - y

        # Only draw if there's something to draw
        if width > 0 and height > 0:
            # Calculate effective radius considering clipping
            effective_radius: int = radius if radius < width / 2 else width / 2
            effective_radius: int = (
                effective_radius if effective_radius < height / 2 else height / 2
            )
            pix_vec = Vector(0, 0)
            for py in range(y, y + height):
                for px in range(x, x + width):
                    # Check if the pixel is within the rounded corners
                    in_corner: bool = False
                    if px < x + effective_radius and py < y + effective_radius:
                        # Top-left corner
                        dx: int = px - (x + effective_radius)
                        dy: int = py - (y + effective_radius)
                        if dx * dx + dy * dy > effective_radius * effective_radius:
                            in_corner = True
                    elif (
                        px < x + effective_radius
                        and py >= y + height - effective_radius
                    ):
                        # Bottom-left corner
                        dx: int = px - (x + effective_radius)
                        dy: int = py - (y + height - effective_radius)
                        if dx * dx + dy * dy > effective_radius * effective_radius:
                            in_corner = True
                    elif (
                        px >= x + width - effective_radius and py < y + effective_radius
                    ):
                        # Top-right corner
                        dx: int = px - (x + width - effective_radius)
                        dy: int = py - (y + effective_radius)
                        if dx * dx + dy * dy > effective_radius * effective_radius:
                            in_corner = True
                    elif (
                        px >= x + width - effective_radius
                        and py >= y + height - effective_radius
                    ):
                        # Bottom-right corner
                        dx: int = px - (x + width - effective_radius)
                        dy: int = py - (y + height - effective_radius)
                        if dx * dx + dy * dy > effective_radius * effective_radius:
                            in_corner = True

                    if not in_corner:
                        pix_vec.x = px
                        pix_vec.y = py
                        self.pixel(pix_vec, _color)

    def fill_screen(self, color=None):
        """Fill the entire screen with a color"""
        _color = color if color is not None else self._background
        if self._current_board_id in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            from waveshare_lcd import fill_screen

            fill_screen(_color)
        else:
            from picoware_lcd import clear_framebuffer

            clear_framebuffer(self._rgb565_to_rgb332(_color))

    def fill_triangle(self, point1: Vector, point2: Vector, point3: Vector, color=None):
        """Draw a filled triangle"""
        _color = color if color is not None else self._foreground
        if self._current_board_id in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            from waveshare_lcd import fill_triangle

            fill_triangle(
                int(point1.x),
                int(point1.y),
                int(point2.x),
                int(point2.y),
                int(point3.x),
                int(point3.y),
                _color,
            )
        else:
            from picoware_lcd import fill_triangle

            fill_triangle(
                int(point1.x),
                int(point1.y),
                int(point2.x),
                int(point2.y),
                int(point3.x),
                int(point3.y),
                _color,
            )

    def image(self, position: Vector, img):
        """Draw an image object to the back buffer"""
        image_vec = Vector(0, 0)
        for y in range(img.size.y):
            for x in range(img.size.x):
                color = img.get_pixel(x, y)
                image_vec.x = position.x + x
                image_vec.y = position.y + y
                self.pixel(image_vec, color)

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
                image_vec = Vector(0, 0)
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
                            image_vec.x = start_x + i
                            image_vec.y = y
                            self.pixel(image_vec, rgb565)

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
            from waveshare_lcd import blit

            blit(
                int(position.x),
                int(position.y),
                int(size.x),
                int(size.y),
                byte_data,
                # invert,
            )
        else:
            from picoware_lcd import draw_image_bytearray

            draw_image_bytearray(
                int(position.x),
                int(position.y),
                int(size.x),
                int(size.y),
                byte_data,
                invert,
            )

    def image_bytearray_1bit(self, position: Vector, size: Vector, byte_data) -> None:
        """Draw a 1-bit bitmap from packed byte_data (8 pixels per byte, row-aligned)"""
        width, height = int(size.x), int(size.y)
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
            from waveshare_lcd import draw_line

            draw_line(
                int(position.x), int(position.y), int(size.x), int(size.y), _color
            )
        else:
            from picoware_lcd import draw_line

            draw_line(int(position.x), int(position.y), int(size.x), _color)

    def line_custom(self, point_1: Vector, point_2: Vector, color=None):
        """Draw line between two points"""
        _color = color if color is not None else self._foreground
        if self._current_board_id in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            from waveshare_lcd import draw_line

            draw_line(
                int(point_1.x),
                int(point_1.y),
                int(point_2.x),
                int(point_2.y),
                _color,
            )
        else:
            from picoware_lcd import draw_line_custom

            draw_line_custom(
                int(point_1.x),
                int(point_1.y),
                int(point_2.x),
                int(point_2.y),
                _color,
            )

    def pixel(self, position: Vector, color=None):
        """Draw a pixel"""
        _color = color if color is not None else self._foreground
        if self._current_board_id in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            from waveshare_lcd import draw_pixel

            draw_pixel(int(position.x), int(position.y), _color)
        else:
            from picoware_lcd import draw_pixel

            draw_pixel(int(position.x), int(position.y), _color)

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
            from waveshare_lcd import draw_rect

            draw_rect(
                int(position.x),
                int(position.y),
                int(size.x),
                int(size.y),
                _color,
            )
        else:
            from picoware_lcd import draw_line, draw_line_custom

            x, y, w, h = int(position.x), int(position.y), int(size.x), int(size.y)
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
        if self._current_board_id in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            from waveshare_lcd import swap

            swap()
        else:
            from picoware_lcd import swap

            swap()

    def text(self, position: Vector, text: str, color=None):
        """Draw text on the display"""
        _color = color if color is not None else self._foreground
        if self._current_board_id in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            from waveshare_lcd import draw_text

            draw_text(int(position.x), int(position.y), text, _color)
        else:
            from picoware_lcd import draw_text

            draw_text(int(position.x), int(position.y), text, _color)

    def text_char(self, position: Vector, char: str, color=None):
        """Draw a single character on the display"""
        _color = color if color is not None else self._foreground
        if self._current_board_id in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            from waveshare_lcd import draw_char

            draw_char(int(position.x), int(position.y), ord(char), _color)
        else:
            from picoware_lcd import draw_char

            draw_char(int(position.x), int(position.y), ord(char), _color)

    def triangle(self, point1: Vector, point2: Vector, point3: Vector, color=None):
        """Draw a triangle outline"""
        _color = color if color is not None else self._foreground
        self.line_custom(point1, point2, _color)
        self.line_custom(point2, point3, _color)
        self.line_custom(point3, point1, _color)
