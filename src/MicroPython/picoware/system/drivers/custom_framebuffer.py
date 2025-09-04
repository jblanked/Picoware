"""
Custom Framebuffer class for ST7789P display with BGR and inversion support
Based on https://github.com/easytarget/st7789-framebuffer/blob/main/st7789_purefb.py
but optimized for our specific hardware configuration.
"""

import framebuf
import micropython


class CustomFrameBuffer(framebuf.FrameBuffer):
    """
    Custom FrameBuffer that automatically handles BGR conversion and inversion
    to match ST7789P display configuration (MADCTL=0x48, INVON)
    """

    def __init__(self, buffer, width, height):
        """
        Initialize custom framebuffer with color conversion options

        Args:
            buffer: The buffer to use for framebuffer data
            width: Width of the framebuffer
            height: Height of the framebuffer
        """
        # Initialize parent class with RGB565 format
        super().__init__(buffer, width, height, framebuf.RGB565)

    @micropython.native
    def _convert_color(self, color):
        """Convert color with byte order fix for display compatibility"""
        return ((color & 0xFF) << 8) | ((color >> 8) & 0xFF)

    @micropython.native
    def _reverse_convert_color(self, color):
        """Reverse the byte order conversion for pixel reading"""
        return ((color & 0xFF) << 8) | ((color >> 8) & 0xFF)

    def fill(self, color):
        """Fill framebuffer with converted color"""
        super().fill(self._convert_color(color))

    def fill_rect(self, x, y, w, h, color):
        """Fill rectangle with converted color"""
        super().fill_rect(x, y, w, h, self._convert_color(color))

    def hline(self, x, y, w, color):
        """Draw horizontal line with converted color"""
        super().hline(x, y, w, self._convert_color(color))

    def line(self, x1, y1, x2, y2, color):
        """Draw line with converted color"""
        super().line(x1, y1, x2, y2, self._convert_color(color))

    def pixel(self, x, y, color=None):
        """Set or get pixel with color conversion"""
        if color is not None:
            super().pixel(x, y, self._convert_color(color))
        else:
            # When getting a pixel, we need to reverse the conversion
            raw_color = super().pixel(x, y)
            return self._reverse_convert_color(raw_color)

    def rect(self, x, y, w, h, color, fill=False):
        """Draw rectangle with converted color"""
        super().rect(x, y, w, h, self._convert_color(color), fill)

    def text(self, text, x, y, color):
        """Draw text with converted color"""
        super().text(text, x, y, self._convert_color(color))

    def vline(self, x, y, h, color):
        """Draw vertical line with converted color"""
        super().vline(x, y, h, self._convert_color(color))
