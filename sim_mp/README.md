# Picoware MicroPython Simulator

This is the MicroPython-first simulator path for Picoware. Run it with the host
MicroPython executable, not CPython:

```sh
micropython sim_mp/run.py
```

The default mode is headless to avoid crashes in MicroPython's experimental
`ffi` path on systems where SDL2/display drivers are unstable. Use SDL
explicitly for an interactive window:

```sh
micropython sim_mp/run.py --viewer
```

`--viewer` runs Picoware under MicroPython and opens a separate native SDL2
viewer process. This is the recommended interactive mode. Close the SDL window
or press `Ctrl+Q` to stop both the viewer and the MicroPython simulator. Press
`Ctrl+D` to toggle the simulator HUD with current view, frame count, modes, and
recent input. The older direct MicroPython `ffi` SDL path is still available
for debugging:

```sh
micropython sim_mp/run.py --sdl
```

Viewer host shortcuts:

```text
Ctrl+Q         Quit viewer and simulator
Ctrl+D         Toggle debug HUD
Ctrl+L         Toggle simulator log overlay
Ctrl+S         Save a BMP screenshot to the simulated SD
Ctrl+M         Toggle simulator audio mute
Ctrl+R         Restart the simulator process
Ctrl+Shift+R   Reset the simulated SD and restart
Ctrl+1..4      Change viewer scale
```

Headless smoke tests:

```sh
micropython sim_mp/run.py --headless --frames 30
micropython sim_mp/run.py --headless --keys enter,down,up,escape --frames 80
micropython sim_mp/run.py --headless --open System --screenshot /tmp/system-mp.bmp --frames 10
micropython sim_mp/run.py --headless --app VibesMP --frames 240
micropython sim_mp/run.py --headless --game "Flappy Bird" --frames 120
micropython sim_mp/run.py --coverage games --headless --audio silent --network offline
```

Native simulator helper binaries are built through one script:

```sh
sh sim_mp/build.sh --check
sh sim_mp/build.sh
```

The script builds the SDL viewer, local audio sidecar, HTTP radio sidecar, and
GameBoy/Ghouls frame sidecar. It rebuilds helpers when their simulator C source
or native dependencies are newer than the binary. It also tracks Picoware audio
native review inputs such as `src/MicroPython/audio/audio.c` and `audio_mp.c`;
if those change, verify the simulator audio shim/sidecars and then refresh the
review baseline:

```sh
sh sim_mp/build.sh --update-baseline
```

Useful build script options and targets:

```sh
sh sim_mp/build.sh --force
sh sim_mp/build.sh --clean
sh sim_mp/build.sh viewer
sh sim_mp/build.sh audio
sh sim_mp/build.sh audio-player
sh sim_mp/build.sh radio-player
sh sim_mp/build.sh frame-sidecar
```

Run a compact simulator validation with:

```sh
sh sim_mp/build.sh && micropython sim_mp/run.py --sim-check
```

For day-to-day app work, use dev mode. It checks native helpers, starts the
viewer, and restarts the simulator when app, Picoware, or simulator shim files
change:

```sh
sh sim_mp/dev.sh --app VibesMP
sh sim_mp/dev.sh --game "Flappy Bird"
```

`--frames N` is an automation limit for headless runs. With `--viewer`, it
warms up the simulator but keeps the SDL viewer open for interactive use. Use
`--exit-after-frames N` when you intentionally want a viewer run to close.

Speed defaults are fast for headless automation and approximately real-time for
interactive viewer runs:

```sh
micropython sim_mp/run.py --viewer --speed real
micropython sim_mp/run.py --headless --speed fast --frames 120
micropython sim_mp/run.py --viewer --fps 20
```

Apps are loaded from unfrozen MicroPython sources by default:

```text
builds/MicroPython/apps_unfrozen
```

Override that source with:

```sh
micropython sim_mp/run.py --apps-source /path/to/apps_unfrozen
```

Open one app directly through the normal Applications menu path with:

```sh
micropython sim_mp/run.py --viewer --app VibesMP
```

Open nested games through the Games menu with:

```sh
micropython sim_mp/run.py --viewer --game "Flappy Bird"
```

Script printable input without spelling every key name:

```sh
micropython sim_mp/run.py --headless --open "Python REPL" --keys-text "print(1+1)" --keys enter --frames 120
```

When `--open`, `--app`, or `--game` is used, scripted text/keys are delayed
until after the target view has had time to open. `--assert-text TEXT` fails
the run if rendered text never contains `TEXT`; `--wait-view NAME` fails the run
if the named view is never reached.

Simple script files can queue navigation and input:

```text
open Python REPL
text 1+1
keys enter
```

Run them with:

```sh
micropython sim_mp/run.py --headless --script repl.script --assert-text 2 --frames 240
```

Record viewer input to a replayable script:

```sh
micropython sim_mp/run.py --viewer --record /tmp/repl.script --open "Python REPL"
micropython sim_mp/run.py --headless --script /tmp/repl.script --assert-text 2 --frames 240
```

Reset and seed the simulator SD card:

```sh
micropython sim_mp/run.py --reset-sd --sd /tmp/picoware-sim-sd --sd-profile clean --headless --frames 1
micropython sim_mp/run.py --reset-sd --sd /tmp/picoware-sim-sd --sd-profile media --headless --frames 1
micropython sim_mp/run.py --reset-sd --sd /tmp/picoware-sim-sd --sd-profile network-fixtures --headless --frames 1
```

Print current simulator module coverage:

```sh
micropython sim_mp/run.py --capabilities
```

The simulator places `sim_mp/hardware` before `src/MicroPython` on `sys.path`,
so Picoware imports MicroPython-compatible simulator modules for hardware APIs.

Features currently covered:

- PicoCalc board profile and feature flags
- RGB565 LCD framebuffer with BMP screenshots, uncompressed BMP decode, PSRAM
  RGB565 blits, and a bitmap ASCII font renderer
- Recommended SDL2 display/input backend through `--viewer`
- Optional direct SDL2 backend via MicroPython `ffi`, enabled with `--sdl`
- Headless fallback when SDL cannot initialize
- PicoCalc keyboard queue and scripted key playback
- Simulated SD card mapped to `sim_mp/sdcard` or `--sd PATH`
- `.py` app discovery/loading from `builds/MicroPython/apps_unfrozen`, overlaid
  onto `/picoware/apps`
- Cooperative simulator-safe Python Editor and Python REPL paths. The REPL
  captures `print`, expression results, exceptions, multiline prompts, and
  prompt-protected editing.
- `network.WLAN`, `socket`/`usocket`, `ssl`, and `tls` wrappers. Real network is
  the default and uses host DNS/TCP/TLS. `--network offline` prevents outbound
  sockets and uses simulator fixtures/stubs instead.
- Virtual BLE scan/connect/GATT/UART behavior with paired-device persistence.
- Simulated `machine.Pin`, `PWM`, `UART`, `I2S`, and `USBDevice` state.
- UART/I2S/USB activity logs under the simulated SD card for tests.
- Offline WebSocket handshake/echo fixture for WebSocket app testing.
- JPEG display through a host `djpeg` sidecar when available, falling back to a
  visible placeholder if decode fails.
- SDL/minimp3 local MP3/WAV playback sidecar when `--audio real` is used in a
  non-headless run. `audio.py` controls the sidecar through command/status
  files for stop, pause, resume, seek, volume, position, and duration.
- SDL/minimp3 HTTP radio sidecar for VibesMP streams. The sidecar reads the URL
  through host `curl`, decodes MP3 frames incrementally, and queues PCM into SDL.
- Silent audio model for deterministic tests and headless runs. HTTP radio
  URLs use the same app-visible state.
- Engine 2D callback/collision support with basic 3D sprite/wall projection for
  simulator-visible testing.
- Native RGB565 frame/input sidecar shell for GameBoy and Ghouls. These sidecars
  exercise process startup, input transport, frame transfer, and LCD blitting.
- No-crash shell for UF2 flashing.

Limitations:

- `.mpy` apps are not the simulator path. Use unfrozen `.py` sources instead.
- HTTP radio playback currently supports MP3 streams. Non-MP3 stream formats
  remain unsupported unless another decoder sidecar is added.
- GameBoy and Ghouls sidecars are frame/input shells, not full emulator/game
  ports yet. They establish the host process contract for future real ports.
- Free Roam is not part of the current simulator acceptance set because it
  depends on online account/server behavior.
- VT now matches the Picoware driver render signature, but it is still a minimal
  terminal renderer rather than a complete terminal emulator.
- Cycle-accurate hardware timing/electrical behavior is out of scope; the goal
  is API-compatible app-development behavior.
