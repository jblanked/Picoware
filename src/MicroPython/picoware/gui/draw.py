import lcd
from picoware.system.vector import Vector


class Draw(lcd.LCD):
    """Class for drawing shapes and text on the display"""

    def __init__(self, foreground: int = 0xFFFF, background: int = 0x0000) -> None:
        super().__init__()

        from picoware.system.font import FontSize

        self._background = background
        self._foreground = foreground

        self._size = Vector(self.width, self.height)
        self._font_default = FontSize(self.FONT_DEFAULT)
        self._font_size = Vector(
            self._font_default.width + self._font_default.spacing,
            self._font_default.height,
        )

        self._use_lvgl = False

        # Clear the display and framebuffer
        self._clear(self._background)

    @property
    def background(self) -> int:
        """Get the current background color"""
        return self._background

    @background.setter
    def background(self, color: int):
        """Set the current background color"""
        self._background = color

    @property
    def font(self) -> int:
        """Get the default font size"""
        return self._font_default.size

    @font.setter
    def font(self, font_size: int):
        """Set the default font size"""
        from picoware.system.font import FontSize

        self._font_default = FontSize(font_size)
        self._font_size.x, self._font_size.y = (
            self._font_default.width + self._font_default.spacing,
            self._font_default.height,
        )

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

    def __del__(self):
        """Destructor to ensure cleanup on object deletion"""
        del self._size
        self._size = None
        del self._font_size
        self._font_size = None

    def char(self, position: Vector, char: str, color=None, font_size: int = -1):
        """Draw a single character on the display"""
        _color = color if color is not None else self._foreground
        _font_size = font_size if font_size >= 0 else self._font_default.size
        self._char(position.x, position.y, ord(char), _color, _font_size)

    def circle(self, position: Vector, radius: int, color: int = None):
        """Draw a circle outline"""
        _color = color if color is not None else self._foreground
        self._circle(position.x, position.y, radius, _color)

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

    def erase(self):
        """Erase the display by filling with background color"""
        self._clear(self._background)

    def fill_circle(self, position: Vector, radius: int, color=None):
        """Draw a filled circle"""
        _color = color if color is not None else self._foreground
        self._fill_circle(position.x, position.y, radius, _color)

    def fill_rectangle(self, position: Vector, size: Vector, color=None):
        """Draw a filled rectangle"""
        _color = color if color is not None else self._foreground
        self._fill_rectangle(
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

        self._fill_round_rectangle(
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
        self._clear(_color)

    def fill_triangle(self, point1: Vector, point2: Vector, point3: Vector, color=None):
        """Draw a filled triangle"""
        _color = color if color is not None else self._foreground
        self._fill_triangle(
            point1.x,
            point1.y,
            point2.x,
            point2.y,
            point3.x,
            point3.y,
            _color,
        )

    def get_font(self, font_size: int = 0):
        """Get the FontSize object for the specified font size"""
        from picoware.system.font import FontSize

        return FontSize(font_size)

    def image(self, position: Vector, img):
        """Draw an image object to the back buffer"""
        for y in range(img.size.y):
            for x in range(img.size.x):
                color = img.get_pixel(x, y)
                self._pixel(position.x + x, position.y + y, color)

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
                            self._pixel(start_x + i, y, rgb565)

            if storage:
                storage.unmount_vfs()

        except (OSError, ValueError) as e:
            print(f"Error loading BMP: {e}")

    def image_bytearray(
        self, position: Vector, size: Vector, byte_data, invert: bool = False
    ):
        """Draw an image from 8-bit byte data (bytes or bytearray)"""
        self._bytearray(position.x, position.y, size.x, size.y, byte_data)

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

        self._bytearray(position.x, position.y, size.x, size.y, unpacked)

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
                self._bytearray(position.x, position.y, size.x, size.y, byte_data)

            if storage and mount_vfs:
                storage.unmount_vfs()

        except (OSError, ValueError) as e:
            print(f"Error loading bytearray image: {e}")

    def len(self, text: str, font_size: int = 0) -> int:
        """Calculate the pixel width of a text string for a given font size"""
        font = self.get_font(font_size)
        length = len(text)
        return length * font.width

    def line(self, position: Vector, size: Vector, color=None):
        """Draw horizontal line"""
        _color = color if color is not None else self._foreground
        self._line(position.x, position.y, size.x, size.y, _color)

    def line_custom(self, point_1: Vector, point_2: Vector, color=None):
        """Draw line between two points"""
        _color = color if color is not None else self._foreground
        self._line(
            point_1.x,
            point_1.y,
            point_2.x,
            point_2.y,
            _color,
        )

    def pixel(self, position: Vector, color=None):
        """Draw a pixel"""
        _color = color if color is not None else self._foreground
        self._pixel(position.x, position.y, _color)

    def rect(self, position: Vector, size: Vector, color=None):
        """Draw a rectangle outline on the display"""
        if size.x <= 0 or size.y <= 0:
            return

        _color = color if color is not None else self._foreground
        self._rectangle(
            position.x,
            position.y,
            size.x,
            size.y,
            _color,
        )

    def text(self, position: Vector, text: str, color=None, font_size: int = -1):
        """Draw text on the display"""
        _color = color if color is not None else self._foreground
        _font_size = font_size if font_size >= 0 else self._font_default.size
        self._text(position.x, position.y, text, _color, _font_size)

    def triangle(self, point1: Vector, point2: Vector, point3: Vector, color=None):
        """Draw a triangle outline"""
        _color = color if color is not None else self._foreground
        self._triangle(
            point1.x,
            point1.y,
            point2.x,
            point2.y,
            point3.x,
            point3.y,
            _color,
        )
