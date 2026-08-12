import lcd
from picoware.system.vector import Vector


class Draw(lcd.LCD):
    """Class for drawing shapes and text on the display.

    Methods:
        char(position, char, color=None, font_size=-1): Draw a single character
        circle(position, radius, color=None): Draw a circle outline
        clear(position=Vector(0, 0), size=Vector(320, 320), color=None): Fill a rectangular area with a color
        erase(): Clear the entire display
        fill_circle(position, radius, color=None): Draw a filled circle
        fill_rectangle(position, size, color=None): Draw a filled rectangle
        fill_round_rectangle(position, size, radius, color=None): Draw a filled rounded rectangle
        fill_screen(color=None): Fill the entire screen with a color
        fill_triangle(point1, point2, point3, color=None): Draw a filled triangle
        fill_triangle_alpha(point1, point2, point3, color=None, alpha=255): Draw a filled triangle with alpha blending
        get_font(font_size=0): Get the FontSize object for a given font size
        image(position, img): Draw an image object to the back buffer
        image_bmp(position, path, storage=None): Draw a 24-bit BMP image from a file path
        image_jpeg(position, path, storage=None): Draw a JPEG image from a file path
        image_jpeg_buffer(position, buf): Draw a JPEG image from bytes data in a buffer
        image_bytearray(position, size, byte_data, invert=False): Draw an image from 8-bit byte data (bytes or bytearray)
        image_bytearray_1bit(position, size, byte_data): Draw a 1-bit bitmap from packed byte_data (8 pixels per byte, row-aligned)
        image_bytearray_path(position, size, path, storage=None, seek=0, chunk_size=0, mount_vfs=True): Draw an image from an 8-bit bytearray file stored on disk
        len(text, font_size=0): Calculate the pixel width of a text string for a given font size
        line(position, size, color=None): Draw a horizontal line
        line_custom(point_1, point_2, color=None): Draw a line between two points
        pixel(position, color=None): Draw a single pixel
        psram(position, size, addr): Draw pixel data directly from PSRAM at the specified address and length
        rect(position, size, color=None): Draw a rectangle outline
        screenshot(file_path): Take a screenshot of the current display and save it to the specified file path (.bmp)
        set_brightness(level): Set the display brightness (0-100)
        set_mode(mode): Set the LCD mode (PSRAM or HEAP)
        set_scaling(scale_x, scale_y, scale_position=False): Set the LCD scaling parameters
        swap(): Update the display with the current framebuffer contents
        text(position, text, color=None, font_size=-1): Draw text on the display
        triangle(point1, point2, point3, color=None): Draw a triangle outline
    """

    def __init__(
        self,
        foreground: int = 0xFFFF,
        background: int = 0x0000,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        scale_position: bool = False,
    ) -> None:
        """Initialize the drawing context with colors and scaling.

        Args:
            foreground (int): The default color for drawing. Defaults to 0xFFFF.
            background (int): The default color for clearing. Defaults to 0x0000.
            scale_x (float): Horizontal scaling factor for drawing operations. Defaults to 1.0.
            scale_y (float): Vertical scaling factor for drawing operations. Defaults to 1.0.
            scale_position (bool): Whether to scale drawn element positions. Defaults to False.
        """
        super().__init__(scale_x, scale_y, scale_position)

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
        """Set the current background color.

        Args:
            color (int): The new background color.
        """
        self._background = color

    @property
    def font(self) -> int:
        """Get the default font size"""
        return self._font_default.size

    @font.setter
    def font(self, font_size: int):
        """Set the default font size.

        Args:
            font_size (int): The new default font size.
        """
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
        """Set the current foreground color.

        Args:
            color (int): The new foreground color.
        """
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
        """Set whether to use LVGL mode for drawing.

        Args:
            state (bool): True to enable LVGL mode.
        """
        self._use_lvgl = state

    def __del__(self):
        """Destructor to ensure cleanup on object deletion"""
        del self._size
        self._size = None
        del self._font_size
        self._font_size = None

    def char(self, position: Vector, char: str, color=None, font_size: int = -1):
        """Draw a single character on the display.

        Args:
            position (Vector): The position to draw the character.
            char (str): The character to draw.
            color (int): The color to use. Defaults to None (foreground).
            font_size (int): The font size to use. Defaults to -1 (default font).
        """
        _color = color if color is not None else self._foreground
        _font_size = font_size if font_size >= 0 else self._font_default.size
        self._char(position.x, position.y, char, _color, _font_size)

    def circle(self, position: Vector, radius: int, color: int = None):
        """Draw a circle outline.

        Args:
            position (Vector): The center position of the circle.
            radius (int): The radius of the circle.
            color (int): The color to use. Defaults to None (foreground).
        """
        _color = color if color is not None else self._foreground
        self._circle(position.x, position.y, radius, _color)

    def clear(
        self,
        position: Vector = Vector(0, 0),
        size: Vector = Vector(320, 320),
        color=None,
    ):
        """Fill a rectangular area with a color.

        Args:
            position (Vector): The top-left corner of the area. Defaults to Vector(0, 0).
            size (Vector): The size of the area. Defaults to Vector(320, 320).
            color (int): The fill color. Defaults to None (background).
        """
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
        """Draw a filled circle.

        Args:
            position (Vector): The center position of the circle.
            radius (int): The radius of the circle.
            color (int): The fill color. Defaults to None (foreground).
        """
        _color = color if color is not None else self._foreground
        self._fill_circle(position.x, position.y, radius, _color)

    def fill_rectangle(self, position: Vector, size: Vector, color=None):
        """Draw a filled rectangle.

        Args:
            position (Vector): The top-left corner of the rectangle.
            size (Vector): The size of the rectangle.
            color (int): The fill color. Defaults to None (foreground).
        """
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
        """Draw a filled rounded rectangle on the display.

        Args:
            position (Vector): The top-left corner of the rectangle.
            size (Vector): The size of the rectangle.
            radius (int): The corner radius.
            color (int): The fill color. Defaults to None (foreground).
        """
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
        """Fill the entire screen with a color.

        Args:
            color (int): The fill color. Defaults to None (background).
        """
        _color = color if color is not None else self._background
        self._clear(_color)

    def fill_triangle(self, point1: Vector, point2: Vector, point3: Vector, color=None):
        """Draw a filled triangle.

        Args:
            point1 (Vector): First vertex of the triangle.
            point2 (Vector): Second vertex of the triangle.
            point3 (Vector): Third vertex of the triangle.
            color (int): The fill color. Defaults to None (foreground).
        """
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

    def fill_triangle_alpha(
        self, point1: Vector, point2: Vector, point3: Vector, color=None, alpha: int = 255
    ):
        """Draw a filled triangle with alpha blending.

        Args:
            point1 (Vector): First vertex of the triangle.
            point2 (Vector): Second vertex of the triangle.
            point3 (Vector): Third vertex of the triangle.
            color (int): The fill color. Defaults to None (foreground).
            alpha (int): The alpha value for blending. Defaults to 255.
        """
        _color = color if color is not None else self._foreground
        self._fill_triangle_alpha(
            point1.x,
            point1.y,
            point2.x,
            point2.y,
            point3.x,
            point3.y,
            _color,
            alpha,
        )

    def get_font(self, font_size: int = 0):
        """Get the FontSize object for the specified font size.

        Args:
            font_size (int): The font size to look up. Defaults to 0.

        Returns:
            FontSize: The FontSize object for the given size.
        """
        from picoware.system.font import FontSize

        return FontSize(font_size)

    def image(self, position: Vector, img):
        """Draw an image object to the back buffer.

        Args:
            position (Vector): The top-left position to draw the image.
            img (Image): The image object to draw.
        """
        for y in range(img.size.y):
            for x in range(img.size.x):
                color = img.get_pixel(x, y)
                self._pixel(position.x + x, position.y + y, color)

    def image_bmp(self, position: Vector, path: str):
        """Draw a 24-bit BMP image.

        Args:
            position (Vector): The top-left position to draw the image.
            path (str): The path to the BMP file.
        """
        try:
            self._bmp(position.x, position.y, path)
        except Exception as e:
            print(f"Error loading BMP: {e}")

    def image_jpeg(self, position: Vector, path: str, storage=None) -> bool:
        """Draw a JPEG image from a file path.

        Args:
            position (Vector): The top-left position to draw the image.
            path (str): The path to the JPEG file.
            storage: Storage instance for file access. Defaults to None.

        Returns:
            bool: True on success, False on failure.
        """
        from picoware.gui.jpeg import JPEG

        try:
            jpeg = JPEG(screen_width=self._size.x, screen_height=self._size.y)
            return jpeg.draw(position.x, position.y, path, storage)
        except Exception as e:
            print(f"Error loading JPEG: {e}")
            return False

    def image_jpeg_buffer(self, position: Vector, buf) -> bool:
        """Draw a JPEG image from bytes data into a BytesIO buffer.

        Args:
            position (Vector): The top-left position to draw the image.
            buf: Bytes data containing the JPEG image.

        Returns:
            bool: True on success, False on failure.
        """
        from picoware.gui.jpeg import JPEG

        try:
            jpeg = JPEG(screen_width=self._size.x, screen_height=self._size.y)
            return jpeg.draw_buffer(position.x, position.y, buf)
        except Exception as e:
            print(f"Error loading JPEG from buffer: {e}")
            return False

    def image_bytearray(
        self, position: Vector, size: Vector, byte_data, invert: bool = False
    ):
        """Draw an image from 8-bit byte data (bytes or bytearray).

        Args:
            position (Vector): The top-left position to draw the image.
            size (Vector): The size of the image.
            byte_data: The pixel data as bytes or bytearray.
            invert (bool): Whether to invert the pixel values. Defaults to False.
        """
        self._bytearray(position.x, position.y, size.x, size.y, byte_data, invert)

    def image_bytearray_1bit(self, position: Vector, size: Vector, byte_data, invert: bool = False) -> None:
        """Draw a 1-bit bitmap from packed byte_data (8 pixels per byte, row-aligned).

        Args:
            position (Vector): The top-left position to draw the image.
            size (Vector): The size of the image.
            byte_data: Packed 1-bit pixel data.
            invert (bool): Whether to invert the pixel values. Defaults to False.
        """
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

        self._bytearray(position.x, position.y, size.x, size.y, unpacked, invert)

    def image_bytearray_path(
        self,
        position: Vector,
        size: Vector,
        path: str,
        storage=None,
        seek=0,
        chunk_size=0,
        invert=False,
    ):
        """Draw an image from an 8-bit bytearray file stored on disk.

        Args:
            position (Vector): The top-left position to draw the image.
            size (Vector): The size of the image.
            path (str): The path to the bytearray file.
            storage: Storage instance for file access. Defaults to None.
            seek (int): Byte offset to start reading from. Defaults to 0.
            chunk_size (int): Number of bytes to read per chunk. Defaults to 0 (read all).
            invert (bool): Whether to invert the pixel values. Defaults to False.
        """
        try:
            if storage:
                file = storage.file_open(path)
                if not file:
                    print(f"File not found: {path}")
                    return
                byte_array = storage.file_read(file, seek, chunk_size, decode=False)
                self._bytearray(position.x, position.y, size.x, size.y, byte_array, invert)
                storage.file_close(file)

        except Exception as e:
            print(f"Error loading bytearray image: {e}")

    def len(self, text: str, font_size: int = 0) -> int:
        """Calculate the pixel width of a text string for a given font size.

        Args:
            text (str): The text to measure.
            font_size (int): The font size to use. Defaults to 0.

        Returns:
            int: The pixel width of the text.
        """
        font = self.get_font(font_size)
        length = len(text)
        return length * (font.width + font.spacing)

    def line(self, position: Vector, size: Vector, color=None):
        """Draw horizontal line.

        Args:
            position (Vector): The starting position of the line.
            size (Vector): The size of the line.
            color (int): The line color. Defaults to None (foreground).
        """
        _color = color if color is not None else self._foreground
        self._line(position.x, position.y, size.x, size.y, _color)

    def line_custom(self, point_1: Vector, point_2: Vector, color=None):
        """Draw line between two points.

        Args:
            point_1 (Vector): The first point.
            point_2 (Vector): The second point.
            color (int): The line color. Defaults to None (foreground).
        """
        _color = color if color is not None else self._foreground
        self._line(
            point_1.x,
            point_1.y,
            point_2.x,
            point_2.y,
            _color,
        )

    def pixel(self, position: Vector, color=None):
        """Draw a pixel.

        Args:
            position (Vector): The position of the pixel.
            color (int): The pixel color. Defaults to None (foreground).
        """
        _color = color if color is not None else self._foreground
        self._pixel(position.x, position.y, _color)

    def psram(self, position: Vector, size: Vector, addr: int):
        """Draw pixel data directly from PSRAM at the specified address and length.

        Args:
            position (Vector): The top-left position to draw the data.
            size (Vector): The size of the image data.
            addr (int): The PSRAM address to read from.
        """
        self._psram(position.x, position.y, size.x, size.y, addr)

    def rect(self, position: Vector, size: Vector, color=None):
        """Draw a rectangle outline on the display.

        Args:
            position (Vector): The top-left corner of the rectangle.
            size (Vector): The size of the rectangle.
            color (int): The outline color. Defaults to None (foreground).
        """
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
        """Draw text on the display.

        Args:
            position (Vector): The position to draw the text.
            text (str): The text to draw.
            color (int): The text color. Defaults to None (foreground).
            font_size (int): The font size to use. Defaults to -1 (default font).
        """
        _color = color if color is not None else self._foreground
        _font_size = font_size if font_size >= 0 else self._font_default.size
        self._text(position.x, position.y, text, _color, _font_size)

    def triangle(self, point1: Vector, point2: Vector, point3: Vector, color=None):
        """Draw a triangle outline.

        Args:
            point1 (Vector): First vertex of the triangle.
            point2 (Vector): Second vertex of the triangle.
            point3 (Vector): Third vertex of the triangle.
            color (int): The outline color. Defaults to None (foreground).
        """
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
