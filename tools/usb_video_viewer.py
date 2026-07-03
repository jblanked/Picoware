#!/usr/bin/env python3
"""USB Video Viewer for Picoware.

Receives raw RGB332 framebuffer data over USB CDC serial and renders it
in a pygame window.

Usage:
    python tools/usb_video_viewer.py [--port PORT] [--scale N]
    python tools/usb_video_viewer.py --list

Requires pygame and pyserial (pip install pygame pyserial).
"""

import argparse
import struct
import sys
import time

try:
    import pygame
except ImportError:
    pygame = None

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None

USB_VIDEO_MAGIC = 0x50494356
USB_VIDEO_MAGIC_BYTES = struct.pack("<I", USB_VIDEO_MAGIC)
USB_VIDEO_HDR_SIZE = 10
USB_VIDEO_FORMAT_RGB332 = 0
USB_VIDEO_FORMAT_RGB565 = 1

# Pre-computed RGB332 to RGB888 lookup table
# RGB332-to-RGB888 lookup table, indexed by pixel byte
_RGB332_TO_RGB888 = bytes(
    v
    for r3 in range(8)
    for g3 in range(8)
    for b2 in range(4)
    for v in (
        ((r3 << 5) | (r3 << 2) | (r3 >> 1)),      # R
        ((g3 << 5) | (g3 << 2) | (g3 >> 1)),      # G
        ((b2 << 6) | (b2 << 4) | (b2 << 2) | b2),  # B
    )
)


def decode_frame(data, width, height, fmt):
    """Decode raw pixel data into a pygame-compatible bytes object.

    Returns a bytes object of length width*height*3 (RGB888 triples),
    or None on failure.
    """
    expected = width * height
    if fmt == USB_VIDEO_FORMAT_RGB332:
        if len(data) < expected:
            return None
        # Use lookup table: for each RGB332 byte, emit 3 RGB888 bytes
        out = bytearray(expected * 3)
        for i in range(expected):
            p = data[i]
            out[i * 3 + 0] = _RGB332_TO_RGB888[p * 3 + 0]
            out[i * 3 + 1] = _RGB332_TO_RGB888[p * 3 + 1]
            out[i * 3 + 2] = _RGB332_TO_RGB888[p * 3 + 2]
        return bytes(out)
    elif fmt == USB_VIDEO_FORMAT_RGB565:
        if len(data) < expected * 2:
            return None
        out = bytearray(expected * 3)
        for i in range(expected):
            p = data[i * 2] | (data[i * 2 + 1] << 8)
            r = ((p >> 11) & 0x1F) * 255 // 31
            g = ((p >> 5) & 0x3F) * 255 // 63
            b = (p & 0x1F) * 255 // 31
            out[i * 3 + 0] = r
            out[i * 3 + 1] = g
            out[i * 3 + 2] = b
        return bytes(out)
    return None


def list_ports():
    """Print available serial ports and exit."""
    if serial is None:
        print("pyserial not installed. Install it with: pip install pyserial")
        sys.exit(1)
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("No serial ports found.")
        sys.exit(1)
    print("Available serial ports:")
    for p in sorted(ports, key=lambda x: x.device):
        desc = p.description or "(no description)"
        print(f"  {p.device}  —  {desc}")
    sys.exit(0)


def find_picoware_port():
    """Try to auto-detect a Picoware device by USB vendor/product IDs."""
    if serial is None:
        return None
    for p in serial.tools.list_ports.comports():
        # RP2040/RP2350 CDC: vid=0x2E8A pid=0x0005 or 0x000a
        if p.vid == 0x2E8A and p.pid in (0x0005, 0x000A, 0x000C):
            return p.device
        # Fallback: any MicroPython CDC port
        if p.vid == 0x2E8A:
            return p.device
        if "MicroPython" in (p.description or ""):
            return p.device
        if "Board in FS mode" in (p.description or ""):
            return p.device
        if "Pico" in (p.product or ""):
            return p.device
    return None


def main():
    """Run the USB video viewer event loop.

    Opens a serial port, ingests framed video data, and renders decoded
    frames in a pygame window until the user exits.
    """
    parser = argparse.ArgumentParser(description="Picoware USB Video Viewer")
    parser.add_argument("--port", "-p", default=None, help="USB serial port (e.g. /dev/ttyACM0)")
    parser.add_argument("--scale", "-s", type=int, default=2, help="Window scale factor (default: 2)")
    parser.add_argument("--list", "-l", action="store_true", help="List available serial ports")
    parser.add_argument("--baud", "-b", type=int, default=2000000, help="Serial line coding (default: 2000000)")
    parser.add_argument("--fps", type=int, default=0, help="Render cap; 0 means uncapped")
    parser.add_argument("--read-chunk", type=int, default=65536, help="Max bytes to read per loop")
    args = parser.parse_args()

    if args.list:
        list_ports()

    if pygame is None:
        print("pygame is required. Install it with: pip install pygame")
        sys.exit(1)
    if serial is None:
        print("pyserial is required. Install it with: pip install pyserial")
        sys.exit(1)

    port = args.port or find_picoware_port()
    if not port:
        print("No Picoware device detected and no --port specified.")
        print("Use --list to see available ports.")
        sys.exit(1)

    print(f"Connecting to {port} at {args.baud} baud...")
    ser = serial.Serial(port, args.baud, timeout=0)
    ser.reset_input_buffer()
    print("Connected. Waiting for frames...")

    frame_count = 0
    last_fps_time = time.monotonic()
    fps_counter = 0
    current_fps = 0
    width, height = 320, 320 

    pygame.init()
    clock = pygame.time.Clock()
    scale = max(1, args.scale)
    window = pygame.display.set_mode((width * scale, height * scale))
    pygame.display.set_caption(f"Picoware USB Video — {port}")
    font = pygame.font.SysFont("monospace", 14)
    surface = pygame.Surface((width, height))
    running = True

    buf = bytearray()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    running = False
                elif event.key == pygame.K_1:
                    scale = 1
                    window = pygame.display.set_mode((width * scale, height * scale))
                elif event.key == pygame.K_2:
                    scale = 2
                    window = pygame.display.set_mode((width * scale, height * scale))
                elif event.key == pygame.K_3:
                    scale = 3
                    window = pygame.display.set_mode((width * scale, height * scale))
                elif event.key == pygame.K_4:
                    scale = 4
                    window = pygame.display.set_mode((width * scale, height * scale))

        chunk = ser.read(max(1, args.read_chunk))
        if chunk:
            buf.extend(chunk)
        elif args.fps <= 0:
            time.sleep(0.001)

        while True:
            if len(buf) < USB_VIDEO_HDR_SIZE:
                break

            start = buf.find(USB_VIDEO_MAGIC_BYTES)
            if start < 0:
                keep = len(USB_VIDEO_MAGIC_BYTES) - 1
                if len(buf) > keep:
                    del buf[:-keep]
                break
            if start > 0:
                del buf[:start]
            if len(buf) < USB_VIDEO_HDR_SIZE:
                break

            w = struct.unpack_from("<H", buf, 4)[0]
            h = struct.unpack_from("<H", buf, 6)[0]
            fmt = buf[8]

            if w == 0 or h == 0 or w > 1024 or h > 1024:
                del buf[0]
                continue

            pixel_size = w * h if fmt == USB_VIDEO_FORMAT_RGB332 else w * h * 2
            frame_size = USB_VIDEO_HDR_SIZE + pixel_size
            if len(buf) < frame_size:
                break

            frame_data = decode_frame(memoryview(buf)[USB_VIDEO_HDR_SIZE:frame_size], w, h, fmt)
            if frame_data:
                if w != width or h != height:
                    width, height = w, h
                    surface = pygame.Surface((width, height))
                    window = pygame.display.set_mode((width * scale, height * scale))

                img = pygame.image.frombuffer(frame_data, (width, height), "RGB")
                surface.blit(img, (0, 0))
                scaled = pygame.transform.scale(surface, (width * scale, height * scale))
                window.blit(scaled, (0, 0))

                fps_counter += 1
                now = time.monotonic()
                if now - last_fps_time >= 1.0:
                    current_fps = fps_counter
                    fps_counter = 0
                    last_fps_time = now
                frame_count += 1
                hud = font.render(f"Frame {frame_count}  {current_fps} FPS  {width}x{height}", True, (200, 200, 200))
                window.blit(hud, (6, 6))

                pygame.display.flip()

            del buf[:frame_size]

        if args.fps > 0:
            clock.tick(args.fps)

    ser.close()
    pygame.quit()
    print(f"Disconnected. {frame_count} frames received.")


if __name__ == "__main__":
    main()
