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
cd tools
bash micropython-desktop.sh # build
bash run-micropython-desktop.sh # run
```

### Pico 2 W memory checks

The launcher defaults to `--board picocalc-pico2w` and a **512 KiB
MicroPython heap ceiling**. A smaller `PICOWARE_DESKTOP_HEAP_SIZE` is preserved;
the runtime no longer silently grows the heap to 16 MiB. Selecting Pico 2 W
with `--keep-interpreter` rejects an oversized heap.

Use `sh tools/run-micropython-desktop.sh` for the bounded interactive path.
The desktop build freezes the simulator runner, hardware shims and Picoware
Python libraries into its executable, analogous to firmware-resident code.
The launcher gives these frozen modules import priority and rebuilds when their
Python sources change. SD apps and assets are **not frozen**: application
bytecode, state, native surfaces and image records still consume the heap.
Directly executing `micropython simulator/run.py` remains a source-loaded path
and is not an equivalent memory test. Source SD apps also need compilation RAM;
`--apps-source` may point to a separately compiled `.mpy` payload for comparison.

This is an upper-bound memory stress test, **not full Pico 2 W emulation**.
Firmware/static/stack/network reservations leave less application RAM on the
device. Conversely, 64-bit desktop objects and remaining Python hardware-shim
state can use more RAM than 32-bit firmware/native drivers. `--speed pico2w`
provides frame pacing; it does not emulate CPU instruction speed, SD latency,
LCD bus throughput, or firmware memory reservations. A pass or failure is not
by itself proof of hardware performance or memory fit.

The native desktop display uses one shared, process-lifetime host GRAM arena
(1,228,800 bytes reserved for the largest supported display; 204,800 active
bytes for PicoCalc RGB565). Only its small Python view is charged to the
MicroPython heap. Every LCD wrapper addresses the same simulated controller.
This exception is display-only: the game's native RGB332 surface, command
arrays, image payloads and Python caches still consume the bounded heap.
It is not an exemption for any buffer allocated by actual firmware.

Unscaled colour transfers write directly into that GRAM without a temporary
full-frame Python bytes object. Scaled/monochrome fallback keeps the original
full-image conversion for correct sampling; custom test adapters without a
native target receive owned chunks of at most 4,096 bytes. There is still only
one display swap per frame.

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
