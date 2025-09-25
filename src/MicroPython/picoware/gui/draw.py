import picoware_lcd
from picoware.system.colors import TFT_WHITE, TFT_BLACK
from picoware.system.vector import Vector


class Draw:
    """Class for drawing shapes and text on the display"""

    def __init__(self, foreground: int = TFT_WHITE, background: int = TFT_BLACK):
        self.size = Vector(320, 320)
        self.background = background
        self.foreground = foreground

        # Initialize native LCD extension
        picoware_lcd.init(background)

        # Create 8-bit framebuffer
        self.fb_data = bytearray(self.size.x * self.size.y)  # 1 byte per pixel

        # Create RGB332 palette
        self.palette = self._create_rgb332_palette()

        self.text_background = background
        self.text_foreground = foreground
        self.use_background_text_color = False

        # Clear the display and framebuffer
        picoware_lcd.clear_framebuffer(self.fb_data, self._rgb565_to_rgb332(background))

    def _create_rgb332_palette(self):
        """Create an RGB332 to RGB565 palette conversion table"""
        palette = bytearray(256 * 2)  # 256 colors × 2 bytes (RGB565)
        for i in range(256):
            # Extract RGB332 components
            r3 = (i >> 5) & 0x07  # 3 bits for red
            g3 = (i >> 2) & 0x07  # 3 bits for green
            b2 = i & 0x03  # 2 bits for blue

            # Convert to 8-bit RGB
            r8 = (r3 * 255) // 7  # Scale 3-bit to 8-bit
            g8 = (g3 * 255) // 7  # Scale 3-bit to 8-bit
            b8 = (b2 * 255) // 3  # Scale 2-bit to 8-bit

            # Convert to RGB565
            r565 = (r8 >> 3) & 0x1F
            g565 = (g8 >> 2) & 0x3F
            b565 = (b8 >> 3) & 0x1F
            rgb565 = (r565 << 11) | (g565 << 5) | b565

            # Store as little-endian bytes
            palette[i * 2] = rgb565 & 0xFF
            palette[i * 2 + 1] = (rgb565 >> 8) & 0xFF

        return palette

    def _rgb565_to_rgb332(self, rgb565):
        """Convert RGB565 color to RGB332 palette index"""
        r = (rgb565 >> 11) & 0x1F
        g = (rgb565 >> 5) & 0x3F
        b = rgb565 & 0x1F

        # Scale to RGB332
        r332 = (r * 7) // 31
        g332 = (g * 7) // 63
        b332 = (b * 3) // 31

        return (r332 << 5) | (g332 << 2) | b332

    def __del__(self):
        """Destructor to ensure cleanup on object deletion"""
        try:
            self.cleanup()
        except:
            pass

    def _draw_pixel_to_buffer(self, position: Vector, color: int):
        """Draw a pixel to the framebuffer"""
        picoware_lcd.draw_pixel(self.fb_data, int(position.x), int(position.y), color)

    def circle(self, position: Vector, radius: int, color: int = TFT_WHITE):
        """Draw a circle outline"""
        picoware_lcd.draw_circle(
            self.fb_data, int(position.x), int(position.y), radius, color
        )

    def clear(
        self,
        position: Vector = Vector(0, 0),
        size: Vector = Vector(320, 320),
        color=TFT_BLACK,
    ):
        """Fill a rectangular area with a color"""
        if position == Vector(0, 0) and size == Vector(320, 320):
            self.fill_screen(color)
        else:
            self.fill_rectangle(position, size, color)

    def cleanup(self):
        """Cleanup all allocated buffers and free memory"""
        import gc

        # Clean up framebuffer data
        if self.fb_data is not None:
            del self.fb_data
            self.fb_data = None

        # Clean up palette
        if self.palette is not None:
            del self.palette
            self.palette = None

        # Force garbage collection
        gc.collect()

    def color332(self, color: int) -> int:
        """Convert RGB565 to RGB332 color format"""
        return self._rgb565_to_rgb332(color)

    def color565(self, r, g, b):
        """Convert RGB888 to RGB565 color format"""
        return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

    def erase(self):
        """Erase the display by filling with background color"""
        self.fill_screen(self.background)

    def fill_circle(self, position: Vector, radius: int, color=TFT_WHITE):
        """Draw a filled circle"""
        picoware_lcd.fill_circle(
            self.fb_data, int(position.x), int(position.y), radius, color
        )

    def fill_rectangle(self, position: Vector, size: Vector, color=TFT_WHITE):
        """Draw a filled rectangle"""
        picoware_lcd.fill_rect(
            self.fb_data,
            int(position.x),
            int(position.y),
            int(size.x),
            int(size.y),
            color,
        )

    def fill_round_rectangle(
        self, position: Vector, size: Vector, radius: int, color=TFT_WHITE
    ):
        """Draw a filled rounded rectangle on the display"""
        if size.x <= 0 or size.y <= 0 or radius <= 0:
            return

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
        if x + width > self.size.x:
            width = self.size.x - x
        if y + height > self.size.y:
            height = self.size.y - y

        # Only draw if there's something to draw
        if width > 0 and height > 0:
            # Calculate effective radius considering clipping
            effective_radius: int = radius if radius < width / 2 else width / 2
            effective_radius: int = (
                effective_radius if effective_radius < height / 2 else height / 2
            )

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
                        self.pixel(Vector(px, py), color)

    def fill_screen(self, color=TFT_BLACK):
        """Fill the entire screen with a color"""
        picoware_lcd.clear_framebuffer(self.fb_data, self._rgb565_to_rgb332(color))

    def get_font_size(self) -> Vector:
        """Get the font size"""
        return Vector(picoware_lcd.CHAR_WIDTH, picoware_lcd.FONT_HEIGHT)

    def image(self, position: Vector, img):
        """Draw an image object to the back buffer"""
        for y in range(img.size.y):
            for x in range(img.size.x):
                color = img.get_pixel(x, y)
                self.pixel(Vector(position.x + x, position.y + y), color)

    def image_bmp(self, position: Vector, path: str):
        """Draw a 24-bit BMP image"""
        try:
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
                end_x = min(self.size.x, position.x + width)
                start_y = max(0, position.y)
                end_y = min(self.size.y, position.y + abs_height)

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
                            self.pixel(Vector(start_x + i, y), rgb565)

        except (OSError, ValueError) as e:
            print(f"Error loading BMP: {e}")

    def image_bytearray(self, position: Vector, size: Vector, byte_data):
        """Draw an image from 8-bit byte data (bytes or bytearray)"""
        x, y = int(position.x), int(position.y)
        width, height = int(size.x), int(size.y)

        # Clip to screen bounds
        src_x = max(0, -x)
        src_y = max(0, -y)
        dst_x = max(0, x)
        dst_y = max(0, y)
        copy_width = min(width - src_x, self.size.x - dst_x)
        copy_height = min(height - src_y, self.size.y - dst_y)

        if copy_width <= 0 or copy_height <= 0:
            return

        fb_view = memoryview(self.fb_data)
        data_view = memoryview(byte_data)

        # Copy line by line
        for row in range(copy_height):
            src_row_start = (src_y + row) * width + src_x
            dst_row_start = (dst_y + row) * self.size.x + dst_x

            # Direct memory copy for the row
            fb_view[dst_row_start : dst_row_start + copy_width] = data_view[
                src_row_start : src_row_start + copy_width
            ]

    def line(self, position: Vector, size: Vector, color=TFT_WHITE):
        """Draw horizontal line"""
        picoware_lcd.draw_line(
            self.fb_data, int(position.x), int(position.y), int(size.x), color
        )

    def line_custom(self, point_1: Vector, point_2: Vector, color=TFT_WHITE):
        """Draw line between two points"""
        picoware_lcd.draw_line_custom(
            self.fb_data,
            int(point_1.x),
            int(point_1.y),
            int(point_2.x),
            int(point_2.y),
            color,
        )

    def pixel(self, position: Vector, color=TFT_WHITE):
        """Draw a pixel"""
        picoware_lcd.draw_pixel(self.fb_data, int(position.x), int(position.y), color)

    def rect(self, position: Vector, size: Vector, color=TFT_WHITE):
        """Draw a rectangle outline on the display"""
        if size.x <= 0 or size.y <= 0:
            return

        x, y, w, h = int(position.x), int(position.y), int(size.x), int(size.y)
        picoware_lcd.draw_line(self.fb_data, x, y, w, color)  # Top
        picoware_lcd.draw_line(self.fb_data, x, y + h - 1, w, color)  # Bottom
        picoware_lcd.draw_line_custom(self.fb_data, x, y, x, y + h - 1, color)  # Left
        picoware_lcd.draw_line_custom(
            self.fb_data, x + w - 1, y, x + w - 1, y + h - 1, color
        )  # Right

    def reset(self):
        """Reset the display by clearing the framebuffer"""
        self.fill_screen(self.background)

    def set_background_color(self, color: int):
        """Set the background color"""
        self.background = color

    def set_color(
        self,
        foreground=TFT_WHITE,
        background=TFT_BLACK,
    ):
        """Set the foreground and background color of the display"""
        self.foreground = foreground
        self.background = background

    def set_foreground_color(self, color: int):
        """Set the foreground color"""
        self.foreground = color

    def swap(self):
        """
        Swap the front and back buffers - convert 8-bit framebuffer to display
        """
        picoware_lcd.blit_8bit_fullscreen(self.fb_data, self.palette)

    def text(self, position: Vector, text: str, color=TFT_WHITE):
        """Draw text on the display"""
        picoware_lcd.draw_text(
            self.fb_data, int(position.x), int(position.y), text, color
        )

    def text_char(self, position: Vector, char: str, color=TFT_WHITE):
        """Draw a single character on the display"""
        picoware_lcd.draw_char(
            self.fb_data, int(position.x), int(position.y), ord(char), color
        )
