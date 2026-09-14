# Gorillas

Rooftop banana duels using Picoware's existing game engine and Draw API.

## Installation

Keep the launcher and package together in storage:

```text
picoware/apps/games/
    Gorillas.mpy                 # compiled from Gorillas.py
    gorillas_game/
        __init__.py
        assets.mpy
        game.mpy
        sprites.mpy
        art.bin
        effects-0.bin           # monochrome
        effects-1.bin           # colour, scale 1
        effects-2.bin           # colour, scale 2 (PicoCalc)
        effects-3.bin
        effects-4.bin
        effects-5.bin
```

The repository contains Python sources, not compiled application files.
The existing freeze/copy workflow compiles them and preserves binary assets.
Simulator memory tests should use compiled applications too. Keep the artwork
beside `sprites.py` or `sprites.mpy`; boards without SD need the same files in
their accessible filesystem.

No additional firmware rendering API is required.

## Rendering and memory

The engine manages entities, updates and collision callbacks. Rendering uses
the existing Draw rectangle, circle, text and bytearray calls, writing into
the LCD driver's existing display buffer. The game does not create a second
colour screen buffer, change LCD memory mode, or require engine-native layer
or framebuffer extensions.

Only four objects are engine entities: the banana, two gorillas, and a shared
city collision region. Buildings and obstacles are ordinary geometry records;
sky, scenery and HUD are drawn directly after engine updates. The app does not
sleep or request engine frame delays. Physics and visual animation use elapsed
33 ms ticks, including zero ticks when a frame arrives sooner, with bounded
catch-up after a slow frame.

RGB332 artwork is stored as sparse rectangles in `.bin` files; transparent gaps
are omitted. Records feed the stock bytearray API through exact-length views,
with clipped rows where needed. There is no runtime sprite rasterizer.

On larger heaps, unchanged geometry is cached and changed regions are replayed
in painter order. Old and new object bounds restore the background after motion
and destruction. Text and circle bounds expand repaint regions because those
stock primitives do not expose clipping. The stock LCD swap still transfers
the display: reducing drawing does not imply partial LCD transfers.

Cached command bounds and non-clippable text/circle references are computed
once. Cache admission does not change a scene object's visual revision. This
prevents a rejected cache entry from becoming an unnecessary redraw every
frame. When dirty regions exceed four, the pair with the smallest additional
area is merged instead of invalidating the entire screen. Trail dots share one
tracked group. Explosion bounds are read from the actual image records at
scene preparation, using a 320-byte bounds table and the existing scratch
buffer, so a small spark does not dirty the maximum-size explosion canvas.

Small displays and heaps with less than 192 KiB free when the renderer is
constructed use direct drawing without retained scene commands. This trades
rendering speed for memory headroom, not terrain accuracy. Limits are:

- At most 12 KiB of art caching, in separate 2 KiB pages; compact displays use
  one 512-byte page. Cache capacity is also reduced according to free memory.
- A reusable art scratch buffer of 4,629 bytes, or 1,127 on compact displays.
- One reusable explosion record buffer, sized during scene loading: 3,629 bytes
  for PicoCalc scale 2, up to 18,941 for the largest supported art scale.
- At most 1,024 retained drawing commands, reduced according to free memory,
  at most 48 cache groups, and at most four pending repaint regions. Admission
  also checks available heap before retaining a group. Small-heap direct
  drawing does not retain geometry between frames.
- Cosmetic scorch marks are capped at 24 rectangles per building. Destruction
  and collision cells are never discarded to satisfy that cosmetic limit.

Both artwork streams stay open across rematches and close on app exit. Static
art caches reset between rounds; explosion storage is reused at the same scale.
These limits are not a total game RAM budget: Python objects, transient drawing
commands, engine entities, filesystem buffers and code also consume memory.

Collision candidates come from the engine's entity overlap callbacks. The
banana exposes its movement bounds for that frame; callbacks check at most
four physics segments against player bounds or the city's surviving terrain cells.
Contacts inside crater holes are ignored, and the earliest real hit is resolved
after all callbacks, before rendering. This preserves thin-wall collisions
without a separate collision framebuffer. The same terrain cells support CPU
aiming and gorilla footing. Entity counts are fixed per scene; shots do not add
crater entities or retain a list of all previous blasts.

## Validation boundaries

Default simulator acceptance uses the Pico 2 W profile with a MicroPython heap
ceiling of 512 KiB, two-player shots controlled on both sides, repeated damage,
angle changes, rematches and exit/reopen. Low-heap tests are useful additional
stress checks, not proof that a particular physical board has that heap available.

The desktop LCD's host-backed display storage represents the driver's own
buffer. Python object sizes, firmware reservations and filesystem buffering
differ from hardware. CPU, SD and LCD bus timing are not cycle-accurately
emulated. Neither a simulator pass nor removal of the extra colour framebuffer
establishes compatibility or acceptable performance on every board.

## Artwork format

The offline-generated `GRL1` art and `GFX1` effect files contain little-endian
offset/length directories followed by RGB332 rectangle records. The game loads
these existing assets; no generator or development diagnostics run on-device.
