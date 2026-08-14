# Picoware Desktop target

The Desktop target runs the existing Picoware simulator with a custom build of
MicroPython's Unix port. Picoware's portable C modules are compiled into that
interpreter, while the simulator continues to provide virtual display, input,
storage, network, Bluetooth, and audio hardware.

This avoids maintaining a separate Python translation of native module logic.
The hardware-independent `auto_complete`, `font`, `response`, and `vector`
modules are compiled directly. MMBasic uses the same C parser, runtime, and
interpreter as firmware; only its host callbacks are redirected to the
simulator's LCD and SD-card interfaces. Modules that model real hardware remain
Python simulator providers.

## Requirements

- A local MicroPython source checkout with the Unix port dependencies installed
- GNU Make and a C compiler
- SDL2 for the optional interactive simulator window

Set `MICROPYTHON_DIR` if the MicroPython checkout is not in one of the common
locations detected by the build script.

## Build

```sh
MICROPYTHON_DIR=/path/to/micropython sh tools/micropython-desktop.sh
```

Verify an existing build without rebuilding it:

```sh
sh tools/micropython-desktop.sh check
```

Remove the compiled Desktop interpreter and object files:

```sh
sh tools/micropython-desktop.sh clean
```

The reusable source alias under `/tmp` is intentionally retained and does not
need to be removed between builds.

## Run the simulator

Use the Desktop launcher in place of invoking a system `micropython` binary.
A launch without options opens the Desktop simulator window:

```sh
sh tools/run-micropython-desktop.sh
```

All normal simulator options remain available. The launcher selects the Desktop
board unless `--board` is provided explicitly. For example:

```sh
sh tools/run-micropython-desktop.sh --sim-check --audio silent --network offline
```

The direct `micropython simulator/run.py` workflow remains available for
development and hardware-shim testing, but it cannot import Desktop-native C
modules unless that `micropython` executable was built by the Desktop script.
