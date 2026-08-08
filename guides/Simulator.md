# Picoware MicroPython Simulator
Run Picoware on your desktop. The simulator uses a native SDL2 window for display and input, while Picoware itself runs inside MicroPython.

## Features
- Full Picoware UI with framebuffer and keyboard input
- Scripted/viewer touch input for supported touch-board profiles
- Real network access via host DNS/TCP/TLS (or `--network offline` for fixtures)
- Audio playback for WAV/MP3 files and HTTP MP3 radio streams
- Simulated SD card at `simulator/sdcard` (auto-seeded on first run)
- Headless mode for automated testing (`--headless`)

## Installation

### macOS

```sh
brew install micropython sdl2 ffmpeg
```

### Linux

```sh
# Debian / Ubuntu
sudo apt install micropython libsdl2-dev ffmpeg

# Fedora
sudo dnf install micropython SDL2-devel ffmpeg

# Arch
sudo pacman -S micropython sdl2 ffmpeg
```

### Windows

Not supported. The simulator relies on Unix process spawning and file-pipe IPC
that have no direct equivalent on Windows. Use WSL2 or a Linux VM.

## Usage

Build the native helpers (SDL viewer, audio sidecars), then launch:

```sh
cd simulator
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
| Left mouse click | Send a touch point to touch-board profiles |

### Common commands

```sh
cd simulator

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

# Run as a touch board
micropython run.py --viewer --board waveshare-1.43-rp2350

# Capture a screenshot at exit
micropython run.py --headless --frames 120 --screenshot /tmp/picoware.bmp

# Record simulator framebuffer frames
micropython run.py --viewer --record /tmp/picoware.frames
```

Useful board names include `picocalc-pico2w`, `waveshare-1.28-rp2350`,
`waveshare-1.43-rp2350`, `waveshare-1.69-rp2350`, `waveshare-3.49-rp2350`,
`crowpanel-10.1`, and `cardputer`.

### Game Boy controls

The simulator runs Game Boy ROMs through the native Walnut-CGB helper when it
is available, with a placeholder fallback if the helper cannot build or start.
Firmware/PicoCalc controls still work, and the simulator also accepts a
QWERTY-friendly keymap:

| Key | Game Boy button |
|---|---|
| Arrow keys | D-pad |
| `X` or `]` | A |
| `Z` or `[` | B |
| `Enter` or `=` | Start |
| `Space` or `-` | Select |

### Script input

Simulator scripts support queued key/text input plus simulator state changes:

```text
app Calculator
keys down,enter
text hello
touch 440 200
gesture 6 160 160
battery 42
```

`touch X Y [GESTURE]` and left-clicks in the viewer update the simulated touch
controller. `battery N` sets the battery percentage reported by simulator board
shims.

`wait`, `sleep`, or `frames` in a script delays later queued input. This is useful
when launching directly into an app and waiting for lazy imports or loading
screens before sending keys.

### Rebuilding

Native binaries are built automatically on first use. To rebuild manually:

```sh
cd simulator

./build.sh --force    # rebuild all
./build.sh --clean    # remove binaries
./build.sh --check    # report missing/stale binaries without rebuilding
./build.sh viewer     # rebuild only the viewer
./build.sh audio      # rebuild local audio and radio helpers
./build.sh audio-player
./build.sh radio-player
./build.sh jpeg
./build.sh gameboy    # rebuild only the Game Boy helper
```