# Picoware MicroPython Simulator

Run Picoware on your desktop. The simulator uses a native SDL2 window for
display and input, while Picoware itself runs inside MicroPython.

## Features

- Full Picoware UI with framebuffer and keyboard input
- Real network access via host DNS/TCP/TLS (or `--network offline` for fixtures)
- Audio playback for WAV/MP3 files and HTTP radio streams
- Simulated SD card at `sim_mp/sdcard` (auto-seeded on first run)
- Headless mode for automated testing (`--headless`)

## Installation

### macOS

```sh
brew install micropython sdl2
```

### Linux

```sh
# Debian / Ubuntu
sudo apt install micropython libsdl2-dev

# Fedora
sudo dnf install micropython SDL2-devel

# Arch
sudo pacman -S micropython sdl2
```

### Windows

Not supported. The simulator relies on Unix process spawning and file-pipe IPC
that have no direct equivalent on Windows. Use WSL2 or a Linux VM.

## Usage

Build the native helpers (SDL viewer, audio sidecars), then launch:

```sh
cd sim_mp
./build.sh
micropython run.py --viewer
```

### Keyboard shortcuts (viewer window)

| Shortcut | Action |
|---|---|
| `Ctrl+Q` | Quit |
| `Ctrl+D` | Toggle debug HUD |
| `Ctrl+S` | Save BMP screenshot |
| `Ctrl+M` | Toggle audio mute |
| `Ctrl+R` | Restart simulator |
| `Ctrl+Shift+R` | Reset SD card and restart |
| `Ctrl+1..4` | Change window scale |

### Common commands

```sh
cd sim_mp

# Interactive viewer (default scale 2x)
micropython run.py --viewer

# Launch directly into an app
micropython run.py --viewer --app Calculator

# Run headless for N frames (automation / CI)
micropython run.py --headless --frames 30

# Offline mode (no network, silent audio)
micropython run.py --viewer --network offline --audio silent

# Custom scale and speed
micropython run.py --viewer --scale 3 --fps 20

# Use a custom apps directory
micropython run.py --viewer --apps-source /path/to/apps
```

### Rebuilding

Native binaries are built automatically on first use. To rebuild manually:

```sh
cd sim_mp

./build.sh --force    # rebuild all
./build.sh --clean    # remove binaries
./build.sh viewer     # rebuild only the viewer
```

## Notes
- HTTP radio supports MP3 streams only.
- GameBoy and Ghouls show placeholder screens (full emulation is not included).

