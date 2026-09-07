class FontSize:
    def __init__(self, size=1):
        """Initialize a font size preset."""
        self.set_size(size)

    def set_size(self, size):
        """Apply a size preset (0-4), setting width, height, spacing."""
        object.__setattr__(self, "size", size)
        from sim_font import METRICS

        width, height, spacing = METRICS[size if 0 <= size < 5 else 0]
        object.__setattr__(self, "width", width)
        object.__setattr__(self, "height", height)
        object.__setattr__(self, "spacing", spacing)


class Font:
    def get_width(self, font_size):
        """Return glyph width for a given font size."""
        return FontSize(font_size).width

    def get_height(self, font_size):
        """Return glyph height for a given font size."""
        return FontSize(font_size).height

    def get_spacing(self, font_size):
        """Return inter-glyph spacing for a given font size."""
        return FontSize(font_size).spacing

    def get_character(self, font_size, char):
        """Return the bitmap rows for a character at a given size."""
        import sim_font

        return sim_font.glyph_rows(chr(char), font_size)

    def get_data(self, font_size):
        """Return the raw bitmap font data."""
        import sim_font

        width, height, _ = sim_font.METRICS[font_size if 0 <= font_size < 5 else 0]
        return sim_font.font_data(font_size)[:((width + 7) // 8) * height * 95]
