# Gorillas

Rooftop banana duels using Picoware's game engine and the existing Draw API.

## Installation

Keep the launcher and package together on the SD card:

```text
picoware/apps/games/
    Gorillas.mpy                 # compiled from ../Gorillas.py
    gorillas_game/
        __init__.py
        assets.mpy
        game.mpy
        sprites.mpy
        art.bin
        effects-0.bin           # monochrome effects
        effects-1.bin           # color effects, scale 1
        effects-2.bin           # color effects, scale 2 (PicoCalc)
        effects-3.bin           # color effects, scale 3
        effects-4.bin           # color effects, scale 4
        effects-5.bin           # color effects, scale 5
```

The simulator uses the corresponding `.py` sources. `art.bin` is required in
both cases; keep it and the effect files next to `sprites.py` or `sprites.mpy`. The existing
`tools/freeze-all.sh` copy/compile workflow preserves non-Python assets.
The native renderer requires the engine's `FrameBuffer2D`, `Layer2D`, and
`Layer2D.image_opaque` APIs. `Layer2D.translate` is optional: older engines
rebuild moving cloud layers while retaining the other rendering optimizations.
`Layer2D.image_packed` enables the low-allocation SD loader. Older engines keep
the Python patch-decoder fallback, which has substantially higher memory costs.

## Rendering

Sprites, cloud silhouettes, banana rotations, death poses, explosions and smoke
are baked offline into RGB332 rectangles. Transparent gaps are omitted rather than
painted over the background. With `image_packed`, the engine reads each selected
record directly from the open SD stream into one owned allocation and retains
it as one `Layer2D` command. It parses rectangle spans during native rendering;
there are no Python patch lists or additional per-rectangle pixel copies.
The existing asset files and their formats are unchanged. The engine composes them into
its RGB332 `FrameBuffer2D` and presents through the existing Draw/LCD path.

Only the effect file for the current scale is opened and primed during round
loading, not on the first impact. Its frames are read
sequentially (including skipped animation frames), avoiding repeated FAT seeks.
Both artwork and effect streams are retained across rematches and closed on
app exit. This avoids reopening the firmware's 16 KiB buffered SD handles in a
fragmented heap. Skipped frames use a reusable 512-byte buffer with `readinto`.

The engine owns scene entities, updates and collision callbacks. Unchanged
actor and HUD layers reuse their drawing commands. Moving clouds translate
cached native commands without reallocating their pixel payloads when the
engine supports translation. Stars rebuild only when their twinkle changes.
Gorilla bodies are cached separately from aiming markers, so marker movement
and angle adjustments do not reload body artwork. Changed layers reuse command storage; layers that
disappear are retired. Native composition clears the surface once and submits
only populated layers/segments in painter order, retaining the sky behind
moving objects and blast holes. It does not calculate unused repaint regions.
The entire surface is composed and transferred each frame.

The engine owns a 100 KiB display surface at 320 by 320 pixels. There is no
Python display framebuffer or runtime sprite rasterizer in the app.
Packed reads are limited to 32 KiB **per record**, not per game. The PicoCalc
scale-2 explosion's largest record is 3,629 bytes; up to 139 rectangles now use
one native command. Record allocations are released with their layer commands;
command-array capacity is reused. Packed records are not kept in a second
Python sprite cache. This does not promise allocation-free animation.
The older decoder's Python payload cache remains limited to 32 KiB, including
the current explosion. Native storage, command capacity and Python metadata
are additional in either path; neither limit is a total game RAM cap.
The separate one-bit terrain collision map in `game.py` uses 12.5 KiB at
320 by 320 pixels. The Pico 2 W version has passed controlled shooting tests and
user gameplay acceptance; this is not a guarantee for other boards or long runs.

Simulator validation must use the Pico 2 W profile and disclose unsupported
resource limits. The desktop launcher defaults to a 512 KiB heap ceiling and
does not automatically enlarge smaller heaps. The desktop-only LCD GRAM is
host-backed; normal unscaled colour transfers no longer copy a whole frame
into Python bytes. Game buffers and caches remain inside the bounded heap.
Desktop object sizes, source-loaded code and missing firmware reservations
still prevent a direct equivalence with device RAM. CPU, SD and LCD timings
are not emulated. See `guides/Simulator.md` for the desktop runtime.

The app does not change LCD memory modes. Internal-RAM mode is a separate
benchmark option, not the default: its driver-owned 100 KiB allocation and
PSRAM lifecycle tradeoffs require explicit consideration.

## Rebuilding artwork

From the repository root, with host Python:

```sh
python tools/gorillas-assets.py
```

This regenerates `art.bin` and all six `effects-*.bin` files. The original pixel
patterns and effect geometry are in that generator; palette/scale/pose indexing
is in `assets.py`. The deterministic `GRL1` art and `GFX1` effect files contain little-endian
offset/length directory and raw RGB332 rectangle records, not a full-screen
bitmap. No asset-generation code runs on the device.
