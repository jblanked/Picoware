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

# Wire protocol constants 
USB_VIDEO_MAGIC = 0x50494356
USB_VIDEO_HDR_SIZE = 10
USB_VIDEO_FORMAT_RGB332 = 0
USB_VIDEO_FORMAT_RGB565 = 1

# Pre-computed RGB332 to RGB888 lookup table
# Index by RGB332 byte, yields 3 consecutive RGB888 bytes (R, G, B)
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


def rgb332_to_rgb888(pixel):
    """Convert a single RGB332 byte to (R, G, B) tuple."""
    r3 = (pixel >> 5) & 0x07
    g3 = (pixel >> 2) & 0x07
    b2 = pixel & 0x03
    r = (r3 * 255 + 3) // 7
    g = (g3 * 255 + 3) // 7
    b = (b2 * 255 + 1) // 3
    return r, g, b


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
    parser = argparse.ArgumentParser(description="Picoware USB Video Viewer")
    parser.add_argument("--port", "-p", default=None, help="USB serial port (e.g. /dev/ttyACM0)")
    parser.add_argument("--scale", "-s", type=int, default=2, help="Window scale factor (default: 2)")
    parser.add_argument("--list", "-l", action="store_true", help="List available serial ports")
    parser.add_argument("--baud", "-b", type=int, default=115200, help="Serial baud rate (default: 115200)")
    parser.add_argument("--fps", type=int, default=30, help="Target render FPS (default: 30)")
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
    ser = serial.Serial(port, args.baud, timeout=2)
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

        remaining = ser.in_waiting
        if remaining:
            buf.extend(ser.read(remaining))

        while len(buf) >= USB_VIDEO_HDR_SIZE:
            magic = struct.unpack_from("<I", buf, 0)[0]
            if magic != USB_VIDEO_MAGIC:
                buf.pop(0)
                continue

            w = struct.unpack_from("<H", buf, 4)[0]
            h = struct.unpack_from("<H", buf, 6)[0]
            fmt = buf[8]

            pixel_size = w * h if fmt == USB_VIDEO_FORMAT_RGB332 else w * h * 2
            frame_size = USB_VIDEO_HDR_SIZE + pixel_size

            if len(buf) < frame_size:
                break

            # Decode and render
            frame_data = decode_frame(buf[USB_VIDEO_HDR_SIZE:frame_size], w, h, fmt)
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

            buf = buf[frame_size:]

        clock.tick(args.fps)

    ser.close()
    pygame.quit()
    print(f"Disconnected. {frame_count} frames received.")


if __name__ == "__main__":
    main()
