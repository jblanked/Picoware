from micropython import const

# Display constants
WIDTH = const(320)
HEIGHT = const(320)
BYTES_PER_PIXEL = const(1)  # RGB332
ROW_SIZE = const(WIDTH * BYTES_PER_PIXEL)  # 320 bytes per row
BUFFER_SIZE = const(WIDTH * HEIGHT * BYTES_PER_PIXEL)  # 102,400 bytes

# PSRAM buffer base address
FRAMEBUFFER_ADDR = const(0x400000)  # 4MB offset

# RGB332 color constants (matching picoware_lcd format)
BLACK = const(0x00)
WHITE = const(0xFF)
RED = const(0xE0)  # 0b11100000
GREEN = const(0x1C)  # 0b00011100
BLUE = const(0x03)  # 0b00000011
YELLOW = const(0xFC)  # 0b11111100 (red + green)
CYAN = const(0x1F)  # 0b00011111 (green + blue)
MAGENTA = const(0xE3)  # 0b11100011 (red + blue)


class PSRAMFramebuffer:
    """
    A full 320x320 RGB332 framebuffer stored in PSRAM.
    """

    def __init__(self, base_addr=FRAMEBUFFER_ADDR):
        from picoware_psram import is_ready, init

        self.base_addr = base_addr
        self.width = WIDTH
        self.height = HEIGHT
        self._row_buffer = bytearray(ROW_SIZE)  # Reusable row buffer for blitting

        # Ensure PSRAM is initialized
        if not is_ready():
            init()

    def clear(self, color=BLACK):
        """Clear the entire framebuffer with a color (RGB332)."""
        from picoware_psram import fill32

        # Use 32-bit fill
        # Pack four RGB332 pixels into one 32-bit value
        fill_value = (color << 24) | (color << 16) | (color << 8) | color

        # Calculate number of 32-bit words (BUFFER_SIZE / 4)
        word_count = BUFFER_SIZE // 4

        # Use 32-bit fill
        fill32(self.base_addr, fill_value, word_count)

    def pixel(self, x, y, color):
        """Set a single pixel (RGB332 color)."""
        from picoware_psram import write8

        if 0 <= x < self.width and 0 <= y < self.height:
            addr = self.base_addr + (y * ROW_SIZE) + x
            write8(addr, color)

    def get_pixel(self, x, y):
        """Get pixel color at (x, y)."""
        from picoware_psram import read8

        if 0 <= x < self.width and 0 <= y < self.height:
            addr = self.base_addr + (y * ROW_SIZE) + x
            return read8(addr)
        return 0

    def hline(self, x, y, length, color):
        """Draw a fast horizontal line using DMA."""
        from picoware_psram import write8, write32

        if y < 0 or y >= self.height:
            return

        # Clip to screen bounds
        if x < 0:
            length += x
            x = 0
        if x + length > self.width:
            length = self.width - x

        if length <= 0:
            return

        addr = self.base_addr + (y * ROW_SIZE) + x

        # Use 32-bit writes for aligned sections
        fill32 = (color << 24) | (color << 16) | (color << 8) | color

        # Handle unaligned start
        while length > 0 and (addr & 3):
            write8(addr, color)
            addr += 1
            length -= 1

        # 32-bit fill for aligned middle
        while length >= 4:
            write32(addr, fill32)
            addr += 4
            length -= 4

        # Handle remaining pixels
        while length > 0:
            write8(addr, color)
            addr += 1
            length -= 1

    def vline(self, x, y, length, color):
        """Draw a vertical line."""
        from picoware_psram import write8

        if x < 0 or x >= self.width:
            return

        # Clip to screen bounds
        if y < 0:
            length += y
            y = 0
        if y + length > self.height:
            length = self.height - y

        if length <= 0:
            return

        addr = self.base_addr + (y * ROW_SIZE) + x

        for _ in range(length):
            write8(addr, color)
            addr += ROW_SIZE

    def line(self, x0, y0, x1, y1, color):
        """Draw a line using Bresenham's algorithm."""
        # Fast path for horizontal lines
        if y0 == y1:
            if x0 > x1:
                x0, x1 = x1, x0
            self.hline(x0, y0, x1 - x0 + 1, color)
            return

        # Fast path for vertical lines
        if x0 == x1:
            if y0 > y1:
                y0, y1 = y1, y0
            self.vline(x0, y0, y1 - y0 + 1, color)
            return

        # Bresenham's line algorithm
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            self.pixel(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def rect(self, x, y, w, h, color):
        """Draw a rectangle outline."""
        self.hline(x, y, w, color)
        self.hline(x, y + h - 1, w, color)
        self.vline(x, y, h, color)
        self.vline(x + w - 1, y, h, color)

    def fill_rect(self, x, y, w, h, color):
        """Fill a rectangle."""
        # Clip bounds
        if x < 0:
            w += x
            x = 0
        if y < 0:
            h += y
            y = 0
        if x + w > self.width:
            w = self.width - x
        if y + h > self.height:
            h = self.height - y

        if w <= 0 or h <= 0:
            return

        # Draw each row using fast hline
        for row in range(h):
            self.hline(x, y + row, w, color)

    def circle(self, cx, cy, r, color):
        """Draw a circle outline using midpoint algorithm."""
        x = r
        y = 0
        err = 1 - r

        while x >= y:
            self.pixel(cx + x, cy + y, color)
            self.pixel(cx + y, cy + x, color)
            self.pixel(cx - y, cy + x, color)
            self.pixel(cx - x, cy + y, color)
            self.pixel(cx - x, cy - y, color)
            self.pixel(cx - y, cy - x, color)
            self.pixel(cx + y, cy - x, color)
            self.pixel(cx + x, cy - y, color)

            y += 1
            if err < 0:
                err += 2 * y + 1
            else:
                x -= 1
                err += 2 * (y - x) + 1

    def fill_circle(self, cx, cy, r, color):
        """Draw a filled circle using horizontal line spans."""
        x = r
        y = 0
        err = 1 - r

        while x >= y:
            # Draw horizontal lines for each row of the circle
            self.hline(cx - x, cy + y, 2 * x + 1, color)
            self.hline(cx - x, cy - y, 2 * x + 1, color)
            self.hline(cx - y, cy + x, 2 * y + 1, color)
            self.hline(cx - y, cy - x, 2 * y + 1, color)

            y += 1
            if err < 0:
                err += 2 * y + 1
            else:
                x -= 1
                err += 2 * (y - x) + 1

    def triangle(self, x0, y0, x1, y1, x2, y2, color):
        """Draw a triangle outline."""
        self.line(x0, y0, x1, y1, color)
        self.line(x1, y1, x2, y2, color)
        self.line(x2, y2, x0, y0, color)

    def read_row(self, y):
        """Read a single row from the framebuffer (for line-by-line rendering)."""
        from picoware_psram import read

        if 0 <= y < self.height:
            addr = self.base_addr + (y * ROW_SIZE)
            return read(addr, ROW_SIZE)
        return None

    def read_row_into(self, y, buffer):
        """Read a row directly into a provided buffer."""
        from picoware_psram import read_into

        if 0 <= y < self.height and len(buffer) >= ROW_SIZE:
            addr = self.base_addr + (y * ROW_SIZE)
            read_into(addr, buffer)
            return True
        return False

    def write_row(self, y, data):
        """Write a complete row to the framebuffer."""
        from picoware_psram import write

        if 0 <= y < self.height:
            addr = self.base_addr + (y * ROW_SIZE)
            write(addr, data[:ROW_SIZE])

    def blit_to_display(self, draw):
        """
        Render the PSRAM framebuffer to the display line-by-line.
        """
        from picoware.system.vector import Vector

        pos = Vector(0, 0)
        size = Vector(self.width, 1)

        for y in range(self.height):
            # Read row from PSRAM directly into buffer
            self.read_row_into(y, self._row_buffer)

            # blit
            pos.y = y
            draw.image_bytearray(pos, size, self._row_buffer)

    def blit_region_to_display(self, draw, x, y, w, h):
        """Blit only a specific region to the display."""
        from picoware.system.vector import Vector
        from picoware_psram import read_into

        # Clip bounds
        x = max(0, x)
        y = max(0, y)
        w = min(w, self.width - x)
        h = min(h, self.height - y)

        if w <= 0 or h <= 0:
            return

        pos = Vector(x, 0)
        size = Vector(w, 1)
        temp_buffer = bytearray(w)

        for row in range(y, y + h):
            # Read partial row from PSRAM
            addr = self.base_addr + (row * ROW_SIZE) + x
            read_into(addr, temp_buffer)

            # blit
            pos.y = row
            draw.image_bytearray(pos, size, temp_buffer)


_fb = None
_demo_state = 0
_frame_count = 0


def start(view_manager) -> bool:
    """Initialize the PSRAM framebuffer demo."""
    if not view_manager.has_psram:
        return False

    global _fb, _demo_state, _frame_count
    from picoware.system.vector import Vector

    draw = view_manager.get_draw()
    draw.fill_screen()
    draw.text(Vector(60, 150), "Initializing PSRAM Framebuffer...")
    draw.swap()

    _fb = PSRAMFramebuffer()
    _fb.clear(BLACK)

    _demo_state = 0
    _frame_count = 0

    # Draw initial demo
    _draw_demo()

    # Render to display
    _fb.blit_to_display(draw)

    # Show demo info
    draw.text(Vector(10, 10), "1: Radial Lines", WHITE)
    draw.text(Vector(10, 300), "ENTER: Next  BACK: Exit", WHITE)
    draw.swap()

    return True


def _draw_demo():
    """Draw demo graphics to the PSRAM framebuffer."""
    global _fb, _demo_state

    # RGB332 colors
    colors = [RED, GREEN, BLUE, YELLOW, CYAN, MAGENTA, WHITE]

    # Clear buffer
    _fb.clear(BLACK)

    if _demo_state == 0:
        # Demo 1: Lines radiating from center
        cx, cy = 160, 160
        import math

        for i in range(0, 360, 10):

            angle = math.radians(i)
            x = int(cx + 150 * math.cos(angle))
            y = int(cy + 150 * math.sin(angle))
            _fb.line(cx, cy, x, y, colors[i // 10 % len(colors)])

    elif _demo_state == 1:
        # Demo 2: Concentric circles
        for i, r in enumerate(range(10, 160, 15)):
            _fb.circle(160, 160, r, colors[i % len(colors)])

    elif _demo_state == 2:
        # Demo 3: Filled circles
        _fb.fill_circle(80, 80, 60, RED)
        _fb.fill_circle(240, 80, 60, GREEN)
        _fb.fill_circle(80, 240, 60, BLUE)
        _fb.fill_circle(240, 240, 60, YELLOW)
        _fb.fill_circle(160, 160, 50, WHITE)

    elif _demo_state == 3:
        # Demo 4: Rectangles
        for i in range(6):
            x = 20 + i * 15
            y = 20 + i * 15
            w = 280 - i * 30
            h = 280 - i * 30
            _fb.rect(x, y, w, h, colors[i])

    elif _demo_state == 4:
        # Demo 5: Filled rectangles with transparency effect
        _fb.fill_rect(40, 40, 120, 120, RED)
        _fb.fill_rect(100, 100, 120, 120, GREEN)
        _fb.fill_rect(160, 160, 120, 120, BLUE)

    elif _demo_state == 5:
        # Demo 6: Triangle pattern
        for i in range(6):
            offset = i * 25
            _fb.triangle(
                160,
                20 + offset,
                40 + offset,
                280 - offset,
                280 - offset,
                280 - offset,
                colors[i],
            )

    elif _demo_state == 6:
        # Demo 7: Grid pattern with alternating colors
        for y in range(0, 320, 20):
            for x in range(0, 320, 20):
                if (x // 20 + y // 20) % 2 == 0:
                    _fb.fill_rect(x, y, 18, 18, RED)
                else:
                    _fb.fill_rect(x, y, 18, 18, BLUE)

    elif _demo_state == 7:
        # Demo 8: Gradient bars (RGB332 gradients)
        for x in range(320):
            # Red gradient (3 bits = 8 levels)
            r = (x * 7) // 320
            color = r << 5
            _fb.vline(x, 0, 80, color)

            # Green gradient (3 bits = 8 levels)
            g = (x * 7) // 320
            color = g << 2
            _fb.vline(x, 80, 80, color)

            # Blue gradient (2 bits = 4 levels)
            b = (x * 3) // 320
            color = b
            _fb.vline(x, 160, 80, color)

            # Grayscale gradient
            gray = (x * 7) // 320
            color = (gray << 5) | (gray << 2) | (gray >> 1)
            _fb.vline(x, 240, 80, color)


def run(view_manager):
    """Handle input and update demo."""
    global _demo_state, _frame_count
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_CENTER,
    )
    from picoware.system.vector import Vector

    inp = view_manager.get_input_manager()
    draw = view_manager.get_draw()

    if inp.button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
        return

    if inp.button == BUTTON_CENTER:
        inp.reset()
        _demo_state = (_demo_state + 1) % 8
        _draw_demo()
        _fb.blit_to_display(draw)

        # Show demo info
        demo_names = [
            "1: Radial Lines",
            "2: Circles",
            "3: Filled Circles",
            "4: Rectangles",
            "5: Filled Rects",
            "6: Triangles",
            "7: Checkerboard",
            "8: Gradients",
        ]
        draw.text(Vector(10, 10), demo_names[_demo_state], WHITE)
        draw.text(Vector(10, 300), "ENTER: Next  BACK: Exit", WHITE)
        draw.swap()


def stop(view_manager):
    """Cleanup PSRAM framebuffer resources."""
    global _fb
    from gc import collect

    if _fb:
        del _fb
        _fb = None

    collect()
