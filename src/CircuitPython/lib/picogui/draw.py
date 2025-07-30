import board
from gc import collect as free
from terminalio import FONT
from displayio import (
    Bitmap,
    Group,
    OnDiskBitmap,
    Palette,
    TileGrid,
    release_displays,
)  # https://circuitpython.org/libraries - add to the /lib folder

from adafruit_display_text.bitmap_label import (
    Label,
)  # https://circuitpython.org/libraries - add to the /lib folder

from adafruit_imageload import (
    load as load_image,
)  # https://circuitpython.org/libraries - add to the /lib folder

from picoware.system.boards import (
    Board,
    BOARD_TYPE_VGM,
    BOARD_TYPE_PICO_CALC,
    BOARD_TYPE_JBLANKED,
)

from .vector import Vector
from .image import Image


TFT_WHITE = 0xFFFFFF
TFT_BLACK = 0x000000


class Draw:
    """A memory-optimized class for drawing on a display using the CircuitPython displayio library."""

    def __init__(
        self,
        board_type: Board,
        palette_count: int = 2,
        auto_swap: bool = False,
        debug: bool = False,
    ):
        """Initialize the display with the specified board type.

        Args:
            board_type: The board configuration to use
            palette_count: Number of colors in the palette
            auto_swap: Whether display updates should be automatic (False = manual control with swap())
        """

        # Free up any existing displays and force garbage collection
        release_displays()
        free()

        self.board = board_type
        self.size = Vector(board_type.width, board_type.height)
        self.is_ready = False
        self.debug = debug

        # Text object pool for reuse
        self.text_objects = []
        self.current_text_index = 0
        self.frame_buffer = None
        self.fb_display = None
        self.display = None
        self.title_grid = None

        # Initialize a minimal palette to save memory
        self.palette = Palette(palette_count)
        self.palette[0] = TFT_BLACK
        self.palette[1] = TFT_WHITE
        self.palette_count = palette_count

        # Create minimal display groups
        self.bg_group = Group()
        self.text_group = Group()
        self.group = Group()
        self.group.append(self.bg_group)
        self.group.append(self.text_group)

        self.spi = None

        if board_type.board_type == BOARD_TYPE_VGM:
            try:
                from picodvi import Framebuffer
                from framebufferio import FramebufferDisplay

                self.frame_buffer = Framebuffer(
                    320,
                    240,
                    clk_dp=board.GP9,
                    clk_dn=board.GP8,
                    red_dp=board.GP15,
                    red_dn=board.GP14,
                    green_dp=board.GP13,
                    green_dn=board.GP12,
                    blue_dp=board.GP11,
                    blue_dn=board.GP10,
                    color_depth=8,
                )
                self.fb_display = FramebufferDisplay(
                    self.frame_buffer, auto_refresh=auto_swap
                )
                free()
                if self.debug:
                    print("[Draw:__init__]: Framebuffer initialized successfully.")
            except ImportError as e:
                raise ImportError(
                    f"Not available on Raspberry Pi Pico W. Import error occurred: {e}"
                ) from e
            except MemoryError:
                free()
                if self.debug:
                    print("[Draw:__init__]: Failed to allocate memory for framebuffer.")

            try:
                self.display = Bitmap(self.size.x, self.size.y, self.palette_count)
                self.title_grid = TileGrid(self.display, pixel_shader=self.palette)
                self.bg_group.append(self.title_grid)
                self.fb_display.root_group = self.group
                self.is_ready = True
                if self.debug:
                    print("[Draw:__init__]: Display initialized successfully.")
            except MemoryError:
                free()
                if self.debug:
                    print(
                        "[Draw:__init__]: Failed to allocate memory for display bitmap."
                    )
                raise MemoryError(
                    "Not enough memory to allocate display bitmap."
                ) from None

        elif board_type.board_type == BOARD_TYPE_JBLANKED:
            try:
                from fourwire import FourWire
                from adafruit_ili9341 import ILI9341
                from busio import SPI
                import digitalio

                self.spi = SPI(clock=board.GP6, MOSI=board.GP7, MISO=board.GP4)
                if not self.spi.try_lock():
                    print("Failed to lock SPI bus")
                    return
                self.spi.configure(baudrate=40000000)
                self.spi.unlock()
                tft_cs = board.GP5
                tft_dc = board.GP11
                display_bus = FourWire(
                    self.spi, command=tft_dc, chip_select=tft_cs, reset=board.GP10
                )
                self.fb_display = ILI9341(
                    display_bus, width=320, height=240, rotation=180
                )
                self.display = Bitmap(self.size.x, self.size.y, self.palette_count)
                self.title_grid = TileGrid(self.display, pixel_shader=self.palette)
                self.bg_group.append(self.title_grid)
                self.fb_display.root_group = self.group
                self.is_ready = True
                free()
                if self.debug:
                    print("[Draw:__init__]: Display initialized successfully.")
            except MemoryError:
                free()
                if self.debug:
                    print(
                        "[Draw:__init__]: Failed to allocate memory for display bitmap."
                    )
            except Exception as e:
                digitalio.DigitalInOut(board.GP6).deinit()
                free()
                if self.debug:
                    print(f"[Draw:__init__]: Error initializing display: {e}")
                raise e
        elif board_type.board_type == BOARD_TYPE_PICO_CALC:
            try:
                from fourwire import FourWire
                from adafruit_ili9341 import ILI9341
                from busio import SPI
                import digitalio

                self.spi = SPI(clock=board.GP10, MOSI=board.GP11, MISO=board.GP12)
                if not self.spi.try_lock():
                    print("Failed to lock SPI bus")
                    return
                self.spi.configure(baudrate=40000000)
                self.spi.unlock()

                tft_cs = board.GP13
                tft_dc = board.GP14
                display_bus = FourWire(
                    self.spi, command=tft_dc, chip_select=tft_cs, reset=board.GP15
                )
                self.fb_display = ILI9341(
                    display_bus, width=320, height=320, rotation=270
                )
                self.display = Bitmap(self.size.x, self.size.y, self.palette_count)
                self.title_grid = TileGrid(self.display, pixel_shader=self.palette)
                self.bg_group.append(self.title_grid)
                self.fb_display.root_group = self.group
                self.is_ready = True
                free()
                if self.debug:
                    print("[Draw:__init__]: Display initialized successfully.")
            except MemoryError:
                free()
                if self.debug:
                    print(
                        "[Draw:__init__]: Failed to allocate memory for display bitmap."
                    )
            except Exception as e:
                digitalio.DigitalInOut(board.GP10).deinit()
                free()
                if self.debug:
                    print(f"[Draw:__init__]: Error initializing display: {e}")
                raise e
        free()

    def _color_to_palette_index(self, color: int) -> int:
        """Map a color to the nearest palette index using a more memory-efficient approach."""
        if not self.is_ready:
            if self.debug:
                print("[Draw:_color_to_palette_index]: Display not ready.")
            return 0

        # Direct palette match
        if 0 <= color < self.palette_count:
            return color

        # Direct color match
        for i in range(self.palette_count):
            if self.palette[i] == color:
                return i

        # Calculate RGB components
        if color <= 0xFF:
            r_in = g_in = b_in = color
        else:
            # Extract RGB components from color value
            r_in = (color >> 16) & 0xFF
            g_in = (color >> 8) & 0xFF
            b_in = color & 0xFF

        # Find best match
        best_i = 0
        best_dist = float("inf")
        for i in range(self.palette_count):
            pal = self.palette[i]
            r_p = (pal >> 16) & 0xFF
            g_p = (pal >> 8) & 0xFF
            b_p = pal & 0xFF
            # Use Manhattan distance instead of squared distance to save computation
            dist = abs(r_in - r_p) + abs(g_in - g_p) + abs(b_in - b_p)
            if dist < best_dist:
                best_dist = dist
                best_i = i

        del best_dist
        return best_i

    def char(self, position: Vector, ch: str, color: int):
        """Print a character at the specified position with a memory-efficient approach."""
        if not self.is_ready:
            if self.debug:
                print("[Draw:char]: Display not ready.")
            return

        # Use text method for single characters
        self.text(position, ch, color)

    def clear(self, position: Vector, size: Vector, color: int = TFT_BLACK):
        """Clear a rectangular area with a color, optimized for speed and memory."""
        if not self.is_ready or not self.display:
            if self.debug:
                print("[Draw:clear]: Display not ready.")
            return

        pidx = self._color_to_palette_index(color)

        # Special case for full screen clear
        if (position.x, position.y) == (0, 0) and (size.x, size.y) == (
            self.size.x,
            self.size.y,
        ):
            self.display.fill(pidx)
            return

        # Ensure we're within bounds to avoid unnecessary checks in the loops
        x_start = max(0, position.x)
        y_start = max(0, position.y)
        x_end = min(self.size.x, position.x + size.x)
        y_end = min(self.size.y, position.y + size.y)

        # Direct memory access for better performance
        for y in range(y_start, y_end):
            for x in range(x_start, x_end):
                self.display[int(x), int(y)] = pidx

        del x_start, y_start, x_end, y_end

    def clear_text_objects(self, should_collect: bool = True):
        """Remove all text objects from the text_group to free up memory."""
        if not self.text_objects or not self.text_group:
            return
        # Hide all current text objects by setting empty text
        for text_obj in self.text_objects:
            if hasattr(text_obj, "text"):
                text_obj.text = ""

        # Reset counter for reuse
        self.current_text_index = 0

        # Remove all objects from text_group
        while len(self.text_group) > 0:
            self.text_group.pop()

        # Force garbage collection
        if should_collect:
            free()

    def deinit(self):
        """Deinitialize the display and free up resources."""
        # Clear references to release memory
        self.text_objects = []
        self.text_group = None
        self.bg_group = None
        self.group = None
        self.title_grid = None
        if self.display:
            self.display.deinit()
            self.display = None

        if hasattr(self, "frame_buffer") and self.frame_buffer:
            self.frame_buffer.deinit()
            self.frame_buffer = None

        if self.spi:
            self.spi.deinit()

        release_displays()
        free()

    def fill(self, color: int):
        """Fill the display with a color, optimized for memory usage."""
        if not self.is_ready or not self.display:
            if self.debug:
                print("[Draw:fill]: Display not ready.")
            return

        pidx = self._color_to_palette_index(color)
        self.display.fill(pidx)

    def get_cursor(self) -> Vector:
        """Get the current cursor position (which is at the end of the last text)."""
        if not self.is_ready or len(self.text_group) == 0:
            if self.debug:
                print("[Draw:get_cursor]: Display not ready or no text group.")
            return Vector(0, 0)

        last_text = self.text_group[-1]
        return Vector(last_text.x + last_text.width, last_text.y)

    def image(self, position: Vector, img: Image):
        """Draw an image at the specified position."""
        if not self.is_ready:
            if self.debug:
                print("[Draw:image]: Display not ready.")
            return

        self.image_bytearray(position, img._raw, img.size.x)

    def image_file_bmp(self, position: Vector, filename: str):
        """Draw a bitmap from a file at the specified position."""
        if not self.is_ready:
            if self.debug:
                print("[Draw:image_file_bmp]: Display not ready.")
            return

        try:
            bitmap, palette = load_image(filename, bitmap=Bitmap, palette=Palette)
            tile_grid = TileGrid(
                bitmap,
                pixel_shader=palette,
                x=int(position.x),
                y=int(position.y),
            )
            self.text_group.append(tile_grid)
            return True
        except ValueError as e:
            print(f"Error loading bitmap from file: {e}")
            return False
        except MemoryError as e:
            print(f"{e}")
            return self.image_file_bmp_on_disk(position, filename)

    def image_file_bmp_on_disk(self, position: Vector, filename: str) -> bool:
        """Draw a bitmap from a file at the specified position."""
        if not self.is_ready:
            if self.debug:
                print("[Draw:image_file_bmp_on_disk]: Display not ready.")
            return False

        try:
            bitmap = OnDiskBitmap(filename)
            tile_grid = TileGrid(
                bitmap,
                pixel_shader=bitmap.pixel_shader,
                x=int(position.x),
                y=int(position.y),
            )
            self.text_group.append(tile_grid)
            return True
        except ValueError as e:
            print(f"Error loading bitmap from file: {e}")
            return False
        except MemoryError as e:
            print(f"Not enough memory: {e}")
            return False

    def image_bytearray(self, position: Vector, byte_array: bytearray, img_width: int):
        """Draw a byte array into the bitmap, optimized for memory usage."""
        if not self.is_ready or not self.display:
            if self.debug:
                print("[Draw:image_bytearray]: Display not ready.")
            return

        # derive height from length
        total_pixels = len(byte_array) // 2
        img_height = total_pixels // img_width

        # Pre-calculate bounds to avoid checks in the inner loop
        x_max = min(self.size.x, position.x + img_width)
        y_max = min(self.size.y, position.y + img_height)

        for row in range(img_height):
            y = position.y + row
            if y >= y_max or y < 0:
                continue

            for col in range(img_width):
                x = position.x + col
                if x >= x_max or x < 0:
                    continue

                idx = row * img_width + col
                if idx * 2 + 1 < len(byte_array):
                    color = (byte_array[2 * idx] << 8) | byte_array[2 * idx + 1]
                    pidx = self._color_to_palette_index(color)
                    self.display[int(x), int(y)] = pidx

    def line(self, position: Vector, size: Vector, color: int):
        """Draw a line from (x1, y1) to (x2, y2) with the specified color."""
        if not self.is_ready or not self.display:
            if self.debug:
                print("[Draw:line]: Display not ready.")
            return

        pidx = self._color_to_palette_index(color)
        x1, y1 = int(position.x), int(position.y)
        x2, y2 = int(size.x), int(size.y)

        # Bresenham's line algorithm, with bounds checking outside the loop
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        while True:
            if 0 <= x1 < self.size.x and 0 <= y1 < self.size.y:
                self.display[int(x1), int(y1)] = pidx

            if x1 == x2 and y1 == y2:
                break

            e2 = err * 2
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy

    def pixel(self, position: Vector, color: int):
        """Set the pixel at (x, y) to the specified color."""
        if not self.is_ready or not self.display:
            if self.debug:
                print("[Draw:pixel]: Display not ready.")
            return

        x, y = int(position.x), int(position.y)
        if 0 <= x < self.size.x and 0 <= y < self.size.y:
            pidx = self._color_to_palette_index(color)
            self.display[int(x), int(y)] = pidx

    def rect(self, position: Vector, size: Vector, color: int):
        """Draw a rectangle at (x, y) with width w and height h."""
        if not self.is_ready:
            if self.debug:
                print("[Draw:rect]: Display not ready.")
            return

        # Draw four lines efficiently
        x, y = int(position.x), int(position.y)
        w, h = int(size.x), int(size.y)

        # Use direct line drawing for better memory usage
        self.line(Vector(x, y), Vector(x + w - 1, y), color)  # Top line
        self.line(
            Vector(x, y + h - 1), Vector(x + w - 1, y + h - 1), color
        )  # Bottom line
        self.line(Vector(x, y), Vector(x, y + h - 1), color)  # Left line
        self.line(
            Vector(x + w - 1, y), Vector(x + w - 1, y + h - 1), color
        )  # Right line

    def rect_fill(self, position: Vector, size: Vector, color: int):
        """Fill a rectangle with a color."""
        if not self.is_ready or not self.display:
            if self.debug:
                print("[Draw:rect_fill]: Display not ready.")
            return

        pidx = self._color_to_palette_index(color)

        # Pre-calculate bounds to avoid checks in the inner loop
        x_start = max(0, position.x)
        y_start = max(0, position.y)
        x_end = min(self.size.x, position.x + size.x)
        y_end = min(self.size.y, position.y + size.y)

        # Direct memory access for better performance
        for y in range(y_start, y_end):
            for x in range(x_start, x_end):
                self.display[int(x), int(y)] = pidx

    def set_palette(self, index: int, color: int):
        """Set the color of a palette index."""
        if not self.is_ready:
            if self.debug:
                print("[Draw:set_palette]: Display not ready.")
            return

        if 0 <= index < self.palette_count:
            self.palette[index] = color

    def swap(self):
        """
        Swaps the display buffers to show the next frame while optimizing memory usage.
        """
        if not self.is_ready:
            if self.debug:
                print("[Draw:swap]: Display not ready.")
            return

        self.fb_display.refresh()  # update the display immediately.

    def text(
        self,
        position: Vector,
        text: str,
        color: int = 0xFFFFFF,
        font: int = 1,
        spacing: float = 1.00,  # default is 1.25 actually
    ):
        """Print a string at the specified position, with memory reuse."""
        if not self.is_ready or not self.text_group:
            if self.debug:
                print("[Draw:text]: Display not ready or text group not initialized.")
            return

        # Reuse existing text object if available
        if self.current_text_index < len(self.text_objects):
            text_obj = self.text_objects[self.current_text_index]
            # Update existing text object properties
            text_obj.text = text
            text_obj.color = color
            text_obj.x = int(position.x)
            text_obj.y = int(position.y)

        else:
            # search if any of the text from the label matches the text
            found = False
            for txt in self.text_objects:
                if txt.text == text:
                    txt.x = int(position.x)
                    txt.y = int(position.y)
                    found = True
                    break
            if not found:
                # Create new text object only if needed
                text_obj = Label(
                    FONT,
                    text=text,
                    color=color,
                    x=int(position.x),
                    y=int(position.y),
                    scale=font,
                    line_spacing=spacing,
                )

                # Add to our pool and the display group
                self.text_objects.append(text_obj)
                self.text_group.append(text_obj)

                # Increment index for next use
                self.current_text_index += 1

                # Force garbage collection after creating a new object
                free()

    def text_multi(
        self,
        position: Vector,
        text: str,
        color: int = 0xFFFFFF,
        font: int = 1,
        spacing: float = 1.00,  # default is 1.25 actually
    ):
        """Print a string at the specified position, with memory reuse and multi-line support."""
        if not self.is_ready:
            if self.debug:
                print("[Draw:text_multi]: Display not ready.")
            return

        # If text contains newlines, split and render each line separately
        if "\n" in text:
            lines = text.split("\n")
            line_height = FONT.get_glyph(ord("M")).height * font

            # Add spacing between lines
            line_spacing = int(line_height * spacing)

            # Process each line separately
            current_y = position.y
            for line in lines:
                if line.strip():  # Skip empty lines but preserve spacing
                    # Try to find an existing text object with the same content
                    text_obj = None

                    # First try to reuse an existing object from the pool
                    if self.current_text_index < len(self.text_objects):
                        text_obj = self.text_objects[self.current_text_index]
                        # Update properties
                        text_obj.text = line
                        text_obj.color = color
                        text_obj.x = int(position.x)
                        text_obj.y = int(current_y)

                        # Make sure it's in the text_group
                        if text_obj not in self.text_group:
                            self.text_group.append(text_obj)

                        self.current_text_index += 1
                    else:
                        # Search if there's any existing label with this text
                        for idx, txt in enumerate(self.text_objects):
                            if txt.text == line and txt not in self.text_group:
                                txt.x = int(position.x)
                                txt.y = int(current_y)
                                txt.color = color
                                self.text_group.append(txt)
                                text_obj = txt
                                break

                        # If no existing object found, create a new one
                        if text_obj is None:
                            text_obj = Label(
                                FONT,
                                text=line,
                                color=color,
                                x=int(position.x),
                                y=int(current_y),
                                scale=font,
                                line_spacing=spacing,
                            )
                            self.text_objects.append(text_obj)
                            self.text_group.append(text_obj)
                            self.current_text_index = len(self.text_objects)

                            # Force garbage collection after creating a new object
                            free()

                current_y += line_spacing
            return

        # Handle single line text
        text_obj = None

        # Try to reuse an existing object first
        if self.current_text_index < len(self.text_objects):
            text_obj = self.text_objects[self.current_text_index]
            # Update existing text object properties
            text_obj.text = text
            text_obj.color = color
            text_obj.x = int(position.x)
            text_obj.y = int(position.y)

            # Make sure it's in the text_group
            if text_obj not in self.text_group:
                self.text_group.append(text_obj)

            self.current_text_index += 1
        else:
            # Search if there's any existing label with this text
            for idx, txt in enumerate(self.text_objects):
                if txt.text == text and txt not in self.text_group:
                    txt.x = int(position.x)
                    txt.y = int(position.y)
                    txt.color = color
                    self.text_group.append(txt)
                    text_obj = txt
                    break

            # If no existing object found, create a new one
            if text_obj is None:
                text_obj = Label(
                    FONT,
                    text=text,
                    color=color,
                    x=int(position.x),
                    y=int(position.y),
                    scale=font,
                    line_spacing=spacing,
                )
                self.text_objects.append(text_obj)
                self.text_group.append(text_obj)
                self.current_text_index = len(self.text_objects)

                # Force garbage collection after creating a new object
                free()

    def tile_grid(self, position: Vector, tile_grid: TileGrid):
        """Add a TileGrid to the display at the specified position."""
        if not self.is_ready or not self.text_group:
            if self.debug:
                print(
                    "[Draw:tile_grid]: Display not ready or text group not initialized."
                )
            return
        if tile_grid not in self.text_group:
            tile_grid.x = int(position.x)
            tile_grid.y = int(position.y)
            self.text_group.append(tile_grid)
        else:
            # find the tile_grid then change the position
            for txt in self.text_objects:
                if txt == tile_grid:
                    txt.x = int(position.x)
                    txt.y = int(position.y)
                    break
