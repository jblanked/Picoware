import micropython
from picoware.system.colors import TFT_WHITE, TFT_BLACK
from picoware.system.vector import Vector


class Draw:
    """Class for drawing shapes and text on the display"""

    def __init__(self, foreground: int = TFT_WHITE, background: int = TFT_BLACK):
        from machine import Pin, SPI
        from picoware.system.drivers.ILI9341 import _ILI9341

        self.size = Vector(320, 320)
        self.display = _ILI9341(
            SPI(
                1,
                baudrate=25000000,
                sck=Pin(10),
                mosi=Pin(11),
                miso=Pin(12),
            ),
            cs=Pin(13),
            dc=Pin(14),
            rst=Pin(15),
            w=320,
            h=320,
            r=0,
        )
        self.background = background
        self.foreground = foreground
        self.display.set_color(foreground, background)

        self.framebuffer = None
        self.fb_data = None

        self.palette = self._create_rgb332_palette()

        self.text_background = background
        self.text_foreground = foreground
        self.use_background_text_color = False

        # Initialize the selected buffer system
        self._init_framebuffer()

        # clear the display
        self.display.fill_rectangle(0, 0, self.size.x, self.size.y, background)

    def _create_rgb332_palette(self):
        """Create an RGB332 to RGB565 palette conversion table"""
        palette = []
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
            rgb565 = ((r8 & 0xF8) << 8) | ((g8 & 0xFC) << 3) | (b8 >> 3)
            palette.append(rgb565)

        return palette

    def __del__(self):
        """Destructor to ensure cleanup on object deletion"""
        try:
            self.cleanup()
        except:
            pass

    def _draw_pixel_to_buffer(self, position: Vector, color: int):
        """Draw a pixel to the framebuffer"""
        if 0 <= position.x < self.size.x and 0 <= position.y < self.size.y:
            self.framebuffer.pixel(int(position.x), int(position.y), color)

    def _init_framebuffer(self):
        """Initialize framebuffer with correct color format"""
        from picoware.system.drivers.custom_framebuffer import CustomFrameBuffer
        import gc

        gc.collect()

        try:
            buffer_size = self.size.x * self.size.y * 2  # 2 bytes per pixel
            self.fb_data = bytearray(buffer_size)

            # Use custom framebuffer with byte order correction for all colors
            self.framebuffer = CustomFrameBuffer(
                self.fb_data,
                self.size.x,
                self.size.y,
            )

        except MemoryError:
            print("Failed to allocate framebuffer")
            self.framebuffer = None
            self.fb_data = None

    @micropython.native
    def circle(self, position: Vector, radius: int, color: int = TFT_WHITE):
        """Draw a circle"""
        cx, cy = int(position.x), int(position.y)
        x, y = 0, radius
        d = 3 - 2 * radius

        while x <= y:
            # Draw 8 symmetric points
            points = [
                (cx + x, cy + y),
                (cx - x, cy + y),
                (cx + x, cy - y),
                (cx - x, cy - y),
                (cx + y, cy + x),
                (cx - y, cy + x),
                (cx + y, cy - x),
                (cx - y, cy - x),
            ]

            for px, py in points:
                if 0 <= px < self.size.x and 0 <= py < self.size.y:
                    self._draw_pixel_to_buffer(Vector(px, py), color)

            if d < 0:
                d += 4 * x + 6
            else:
                d += 4 * (x - y) + 10
                y -= 1
            x += 1

    def clear(
        self,
        position: Vector = Vector(0, 0),
        size: Vector = Vector(320, 320),
        color=TFT_BLACK,
    ):
        """Fill a rectangular area with a color."""
        if position == Vector(0, 0) and size == Vector(320, 320):
            self.fill_screen(color)
        else:
            self.fill_rectangle(position, size, color)

    def cleanup(self):
        """Cleanup all allocated buffers and free memory"""
        import gc

        # Clean up framebuffer
        if self.framebuffer is not None:
            self.framebuffer = None
        if self.fb_data is not None:
            del self.fb_data
            self.fb_data = None

        # Clean up double buffers
        if self.palette is not None:
            del self.palette
            self.palette = None

        # Force garbage collection
        gc.collect()

    @micropython.native
    def color332(self, color: int) -> int:
        """Convert RGB565 to RGB332 color format"""
        return (
            ((color & 0xE000) >> 8) | ((color & 0x0700) >> 6) | ((color & 0x0018) >> 3)
        )

    def color565(self, r, g, b):
        """Convert RGB888 to RGB565 color format"""
        return self.display.color565(r, g, b)

    def erase(self):
        """Erase the display"""
        self.display.erase()

    @micropython.native
    def fill_circle(self, position: Vector, radius: int, color=TFT_WHITE):
        """Draw a filled circle on the display"""
        if radius <= 0:
            return

        x: int = 0
        y: int = radius
        d: int = 1 - radius

        while x <= y:
            # Draw horizontal lines to fill the circle
            # Draw lines for the main circle quadrants
            self.line(Vector(position.x - y, position.y + x), Vector(2 * y, 0), color)
            self.line(Vector(position.x - y, position.y - x), Vector(2 * y, 0), color)

            if x != y:
                self.line(
                    Vector(position.x - x, position.y + y), Vector(2 * x, 0), color
                )
                self.line(
                    Vector(position.x - x, position.y - y), Vector(2 * x, 0), color
                )

            if d < 0:
                d += 2 * x + 3
            else:
                d += 2 * (x - y) + 5
                y -= 1
            x += 1

    def fill_rectangle(self, position: Vector, size: Vector, color=TFT_WHITE):
        """Draw a filled rectangle on the display"""
        self.framebuffer.fill_rect(position.x, position.y, size.x, size.y, color)

    @micropython.native
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
        self.framebuffer.fill(color)

    def get_font_size(self) -> Vector:
        """Get the current font size"""
        return Vector(8, 8)

    @micropython.native
    def image(self, position: Vector, img):
        """Draw an image object to the back buffer"""
        for y in range(img.size.y):
            for x in range(img.size.x):
                color = img.get_pixel(x, y)
                self.pixel(Vector(position.x + x, position.y + y), color)

    @micropython.native
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

                # Process each row with direct buffer manipulation for speed
                fb_buffer = self.fb_data  # Access the underlying buffer directly
                fb_width = self.size.x

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

                    # Direct buffer manipulation
                    # Calculate starting position in framebuffer (2 bytes per pixel for RGB565)
                    fb_row_start = y * fb_width * 2
                    fb_pixel_start = fb_row_start + start_x * 2

                    # Create a temporary buffer for the converted row
                    row_buffer = bytearray(dst_width * 2)  # 2 bytes per pixel

                    # Convert the entire row at once
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

                            # Apply custom framebuffer color conversion (byte order swap)
                            converted_color = ((rgb565 & 0xFF) << 8) | (
                                (rgb565 >> 8) & 0xFF
                            )

                            # Store in row buffer
                            row_buffer[i * 2] = converted_color & 0xFF
                            row_buffer[i * 2 + 1] = (converted_color >> 8) & 0xFF

                    # Copy entire row at once
                    end_offset = fb_pixel_start + dst_width * 2
                    if end_offset <= len(fb_buffer):
                        fb_buffer[fb_pixel_start:end_offset] = row_buffer

        except (OSError, ValueError) as e:
            print(f"Error loading BMP: {e}")

    @micropython.native
    def image_bytearray(self, position: Vector, size: Vector, byte_data, palette=None):
        """Draw an image from 8-bit byte data (bytes or bytearray) with optional palette conversion"""
        if palette is None:
            palette = self.palette

        for y in range(size.y):
            for x in range(size.x):
                palette_index = byte_data[y * size.x + x]
                color = palette[palette_index] if palette_index < len(palette) else 0
                self.pixel(Vector(position.x + x, position.y + y), color)

    def line(self, position: Vector, size: Vector, color=TFT_WHITE):
        """Draw horizontal line"""
        self.framebuffer.hline(position.x, position.y, size.x, color)

    def line_custom(self, point_1: Vector, point_2: Vector, color=TFT_WHITE):
        """Draw line between two points"""
        self.framebuffer.line(point_1.x, point_1.y, point_2.x, point_2.y, color)

    def pixel(self, position: Vector, color=TFT_WHITE):
        """Draw a pixel"""
        self._draw_pixel_to_buffer(position, color)

    def rect(self, position: Vector, size: Vector, color=TFT_WHITE):
        """Draw a rectangle on the display"""
        if size.x <= 0 or size.y <= 0:
            return

        self.framebuffer.rect(position.x, position.y, size.x, size.y, color)

    def reset(self):
        """Reset the display"""
        self.display.reset()

    def scroll(self, up: bool = True, distance: int = 1):
        """Scroll the display up or down"""
        if up:
            self.display.scroll(distance)
        else:
            self.display.scroll(-distance)

    def set_background_color(self, color: int):
        """Set the background color"""
        self.background = color
        self.display.set_color(self.foreground, color)

    def set_color(
        self,
        foreground=TFT_WHITE,
        background=TFT_BLACK,
    ):
        """Set the foreground and background color of the display"""
        self.display.set_color(foreground, background)

    def set_foreground_color(self, color: int):
        """Set the foreground color"""
        self.foreground = color
        self.display.set_color(color, self.background)

    def swap(self):
        """Swap the front and back buffers"""
        self.display.blit_buffer(self.fb_data, 0, 0, self.size.x, self.size.y)

    def text(self, position: Vector, text: str, color=TFT_WHITE):
        """Draw text on the display"""
        self.framebuffer.text(text, position.x, position.y, color)
