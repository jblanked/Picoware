"""Image - Image structure for the game engine."""

import engine


class Image(engine.Image):
    """Store a native 2D image and its display size.

    Args:
        size (Vector): Image width and height.
        is_8bit (bool): Whether the image uses 8-bit graphics.
        data (bytes-like or None): Optional raw pixel data. Defaults to None.
        path (str): Optional file path for image data. Defaults to "".
        mask (bytes-like or None): Optional 1-bit transparency mask.
        psram_address (int or None): Optional PSRAM address for image data. Defaults to None.
        psram_mask_address (int or None): Optional PSRAM address for the image mask. Defaults to None.

    Pixel data, masks, and paths are copied into native-owned storage, so the
    original Python buffers and strings do not need to remain alive.

    Attributes:
        size (Vector): Image size in pixels. Writable.

    Methods:
        - set_size(size): Set the image size.
        - __del__(): Release the native image resources.
    """

    def __setattr__(self, name, value):
        """Set an image attribute, routing to the matching setter.

        Args:
            name (str): Attribute name to set.
            value (object): New value for the attribute.
        """
        if name == "size":
            self.set_size(value)
        else:
            super().__setattr__(name, value)
