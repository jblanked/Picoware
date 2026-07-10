# USB Streaming

Picoware can stream the device's framebuffer over USB CDC serial to a
computer. This is useful for recording, broadcasting, or viewing the
display on a larger screen.

## Setup

1. On your device, navigate to `Library` -> `Settings` -> `USB Stream`
   and toggle it on.
2. Connect a USB cable from the device to your computer.
3. Install dependencies on your computer:

```bash
pip install pygame pyserial
```

4. Run the viewer:

```bash
python tools/usb_video_viewer.py
```

The viewer auto-detects Picoware devices by USB vendor ID (0x2E8A).
It renders decoded frames in a window at 2x scale by default.

## Controls

| Key | Action |
|-----|--------|
| 1-4 | Set window scale |
| Esc / Q | Quit |

## Options

```
python tools/usb_video_viewer.py --list
python tools/usb_video_viewer.py --port /dev/ttyACM0 --scale 3
python tools/usb_video_viewer.py --baud 115200 --fps 30
```

| Flag | Default | Description |
|------|---------|-------------|
| `--port` / `-p` | auto | Serial port path |
| `--scale` / `-s` | 2 | Window scale factor |
| `--baud` / `-b` | 2000000 | Serial baud rate |
| `--fps` | 0 (uncapped) | Render frame cap |
| `--read-chunk` | 65536 | Max bytes per read |
| `--list` / `-l` | — | List available ports |

## Requirements

- Python 3.9+ with `pygame` and `pyserial` installed
  (`pip install pygame pyserial`)
- A virtual environment is recommended but not required
- Windows, macOS, or Linux
- Any Picoware-compatible board flashed with Picoware firmware

## Frame Format

Each frame is prefixed with a 10-byte header:

| Offset | Size | Field |
|--------|------|-------|
| 0 | 4 | Magic (0x50494356 = "PICV") |
| 4 | 2 | Width in pixels |
| 6 | 2 | Height in pixels |
| 8 | 1 | Pixel format (0=RGB332, 1=RGB565) |
| 9 | 1 | Reserved |

Pixel data follows immediately after the header. RGB332 uses 1 byte
per pixel (3-bit R, 3-bit G, 2-bit B). RGB565 uses 2 bytes per pixel
(5-bit R, 6-bit G, 5-bit B).