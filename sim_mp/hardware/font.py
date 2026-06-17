class FontSize:
    def __init__(self, size=1):
        """Initialize a font size preset."""
        self.set_size(size)

    def set_size(self, size):
        """Apply a size preset (0-4), setting width, height, spacing."""
        object.__setattr__(self, "size", size)
        if size == 0:
            object.__setattr__(self, "width", 5)
            object.__setattr__(self, "height", 8)
            object.__setattr__(self, "spacing", 1)
        elif size == 2:
            object.__setattr__(self, "width", 11)
            object.__setattr__(self, "height", 16)
            object.__setattr__(self, "spacing", 0)
        elif size == 3:
            object.__setattr__(self, "width", 14)
            object.__setattr__(self, "height", 20)
            object.__setattr__(self, "spacing", 0)
        elif size == 4:
            object.__setattr__(self, "width", 17)
            object.__setattr__(self, "height", 24)
            object.__setattr__(self, "spacing", 0)
        else:
            object.__setattr__(self, "width", 7)
            object.__setattr__(self, "height", 12)
            object.__setattr__(self, "spacing", 0)


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

        return sim_font.glyph_rows(char)

    def get_data(self, font_size):
        """Return the raw bitmap font data."""
        import sim_font

        return sim_font.DATA
