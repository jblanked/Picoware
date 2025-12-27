import sys

try:
    from PIL import Image
except ImportError:
    raise ImportError(
        "Pillow library is required to run this module. Please install it via 'pip install Pillow'."
    )


def color(r, g, b):
    """
    color(r, g, b) returns a 16-bit integer color code for the ST7789 display.
    It converts 24-bit RGB to 16-bit RGB565 and swaps the LSB and MSB bytes.
    """
    # Convert 24-bit RGB to 16-bit RGB565
    r5 = (r & 0b11111000) >> 3
    g6 = (g & 0b11111100) >> 2
    b5 = (b & 0b11111000) >> 3
    rgb565 = (r5 << 11) | (g6 << 5) | b5

    # Swap LSB and MSB bytes before sending to the screen
    lsb = rgb565 & 0xFF
    msb = (rgb565 >> 8) & 0xFF

    return (lsb << 8) | msb


def color8(r, g, b):
    """
    Convert 24-bit RGB color to an 8-bit color value using a 3-3-2 format:
      - 3 bits for red (0-7)
      - 3 bits for green (0-7)
      - 2 bits for blue (0-3)
    The conversion is done by:
        r3 = r >> 5
        g3 = g >> 5
        b2 = b >> 6
    and then combining them as: (r3 << 5) | (g3 << 2) | b2
    """
    r3 = r >> 5  # 8 -> 3 bits
    g3 = g >> 5  # 8 -> 3 bits
    b2 = b >> 6  # 8 -> 2 bits
    return (r3 << 5) | (g3 << 2) | b2


def png2fb(file_obj):
    """
    Convert an image to a framebuffer (RGB565, 2 bytes/pixel).

    Args:
        file_obj: A file-like object (the uploaded PNG).

    Returns:
        A bytearray of the converted framebuffer in RGB565.

    Raises:
        ValueError: If the image is in an unsupported pixel mode.
    """
    inputImage = Image.open(file_obj)

    # Convert image to RGB if necessary:
    if inputImage.mode == "RGB":
        pass
    elif inputImage.mode == "RGBA":
        inputImage = inputImage.convert("RGB")
    elif inputImage.mode in ("L", "LA", "P"):
        inputImage = inputImage.convert("RGB")
    else:
        raise ValueError(
            f"Not supported pixel mode ({inputImage.mode}): Supports only RGB/RGBA/L/LA/P"
        )

    pixelsIn = inputImage.tobytes()
    pixelSize = 3  # 3 bytes per pixel (R, G, B)
    pixelsOut = bytearray((len(pixelsIn) // pixelSize) * 2)

    for i in range(0, len(pixelsIn), pixelSize):
        r = pixelsIn[i]
        g = pixelsIn[i + 1]
        b = pixelsIn[i + 2]
        c = color(r, g, b)
        lsb = c & 0xFF
        msb = (c >> 8) & 0xFF
        index = (i // pixelSize) * 2
        pixelsOut[index] = lsb
        pixelsOut[index + 1] = msb

    return pixelsOut


def png2fb8(file_obj):
    """
    Convert an image to a framebuffer (8-bit, 1 byte/pixel) using a 3-3-2 color format.

    Args:
        file_obj: A file-like object (the uploaded PNG).

    Returns:
        A bytearray of the converted framebuffer in 8-bit (3-3-2 format).

    Raises:
        ValueError: If the image is in an unsupported pixel mode.
    """
    inputImage = Image.open(file_obj)

    # Convert image to RGB if necessary:
    if inputImage.mode == "RGB":
        pass
    elif inputImage.mode == "RGBA":
        inputImage = inputImage.convert("RGB")
    elif inputImage.mode in ("L", "LA", "P"):
        inputImage = inputImage.convert("RGB")
    else:
        raise ValueError(
            f"Not supported pixel mode ({inputImage.mode}): Supports only RGB/RGBA/L/LA/P"
        )

    pixelsIn = inputImage.tobytes()
    pixelSize = 3  # 3 bytes per pixel (R, G, B)
    pixelsOut = bytearray(len(pixelsIn) // pixelSize)

    for i in range(0, len(pixelsIn), pixelSize):
        r = pixelsIn[i]
        g = pixelsIn[i + 1]
        b = pixelsIn[i + 2]
        index = i // pixelSize
        pixelsOut[index] = color8(r, g, b)

    return pixelsOut


def png2bin(file_obj, save_path, bit_depth=16):
    """
    Convert an image to raw pixel data and save it to a binary file.

    Args:
        file_obj: A file-like object (the uploaded PNG).
        save_path: Path to save the BIN file.
        bit_depth: Bit depth for conversion (16 for RGB565, 8 for 3-3-2 format).

    Returns:
        The path to the saved BIN file.
    """
    if bit_depth == 8:
        pixel_data = png2fb8(file_obj)
    else:
        pixel_data = png2fb(file_obj)

    with open(save_path, "wb") as f:
        f.write(pixel_data)

    return save_path


# command line usage
if __name__ == "__main__":
    import os
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert PNG images to raw pixel data (.bin files)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  png2fb.py image.png              - Convert single PNG to RGB565 .bin
  png2fb.py folder/                - Convert all PNGs in folder to RGB565 .bin files
  png2fb.py image.png --8bit       - Convert to 8-bit (3-3-2 format) .bin
  png2fb.py folder/ --8bit         - Convert all PNGs to 8-bit .bin files
        """,
    )
    parser.add_argument("input", help="Input PNG file or folder containing PNG files")
    parser.add_argument(
        "--8bit",
        action="store_true",
        dest="eight_bit",
        help="Use 8-bit color (3-3-2 format) instead of 16-bit RGB565",
    )

    args = parser.parse_args()
    input_path = args.input
    bit_depth = 8 if args.eight_bit else 16

    # Check if input is a file or directory
    if os.path.isfile(input_path):
        # Single file conversion
        if not input_path.lower().endswith(".png"):
            print(f"Error: {input_path} is not a PNG file")
            sys.exit(1)

        # Generate output BIN filename in same directory
        output_bin = os.path.splitext(input_path)[0] + ".bin"

        with open(input_path, "rb") as f_in:
            png2bin(f_in, output_bin, bit_depth=bit_depth)

        bit_mode = "8-bit (3-3-2)" if bit_depth == 8 else "16-bit (RGB565)"
        print(f"Converted {input_path} to {output_bin} ({bit_mode})")

    elif os.path.isdir(input_path):
        # Folder conversion - pack all PNGs into a single .bin file
        png_files = sorted(
            [f for f in os.listdir(input_path) if f.lower().endswith(".png")]
        )

        if not png_files:
            print(f"No PNG files found in {input_path}")
            sys.exit(1)

        # Prepare output file
        output_bin = os.path.join(input_path, "packed_frames.bin")

        # Collect all pixel data
        all_pixel_data = bytearray()
        frame_info = []
        converted_count = 0

        for png_file in png_files:
            input_png = os.path.join(input_path, png_file)

            try:
                with open(input_png, "rb") as f_in:
                    if bit_depth == 8:
                        pixel_data = png2fb8(f_in)
                    else:
                        pixel_data = png2fb(f_in)

                    offset = len(all_pixel_data)
                    size = len(pixel_data)
                    all_pixel_data.extend(pixel_data)

                    frame_info.append(
                        {"file": png_file, "offset": offset, "size": size}
                    )

                    converted_count += 1
                    print(
                        f"Frame {converted_count}: {png_file} - offset: {offset}, size: {size} bytes"
                    )
            except Exception as e:
                print(f"Error converting {png_file}: {e}")

        # Write packed binary file
        with open(output_bin, "wb") as f:
            f.write(all_pixel_data)

        bit_mode = "8-bit (3-3-2)" if bit_depth == 8 else "16-bit (RGB565)"
        print(f"\nPacked {converted_count} frames into {output_bin} ({bit_mode})")
        print(f"Total size: {len(all_pixel_data)} bytes")

    else:
        print(f"Error: {input_path} is not a valid file or directory")
        sys.exit(1)
