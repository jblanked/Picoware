# Gorillas

Rooftop banana duels using Picoware's existing game engine and Draw API.

## Match rules

The first player to win three games wins the match, against the CPU or in
local two-player mode. Scores remain visible between games. A draw awards
neither player a point. After the explosion finishes, the next duel starts
automatically on a fresh skyline. A winner screen appears only at three wins,
saying "Player 1 wins", "Player 2 wins", or "CPU wins". On that screen, OK
starts a new match at 0-0. Starting from
the main menu also resets both scores. P1 starts each new match, then the
starting player alternates after every duel, including draws. The CPU still
starts each duel with its usual rough ranging shots.

Each duel places the gorillas on two distinct, clear rooftops on opposite
sides of the skyline. Player sides are randomized independently of who shoots
first; identities and scores do not swap. Both players begin with power 50.
The CPU then chooses its own shot settings. Destroying a gorilla's current
footing causes a fatal fall, even if masonry remains below it. Returning shots
and self-inflicted explosions can kill the shooter; if both gorillas die,
the duel is a draw.
After landing, a fallen gorilla lies sideways and blinks until the duel ends.

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
sky, scenery and HUD are drawn once from the first player's render callback,
after engine updates and collision dispatch. The callback remains active when
that gorilla loses, so menus and death/rematch screens still render. There is
no second scene draw after `run_async`. The app does not
sleep or request engine frame delays. Physics and visual animation use elapsed
33 ms ticks, including zero ticks when a frame arrives sooner, with bounded
catch-up after a slow frame.

RGB332 artwork is stored as sparse rectangles in `.bin` files; transparent gaps
are omitted. Records feed the stock bytearray API through exact-length views,
with clipped rows where needed. There is no runtime sprite rasterizer.

New duels invalidate scene commands but retain immutable artwork pages and
decoded sprite metadata. When the fixed page cache fills, a least-recently-used
page is recycled together with its metadata. Oversized records reuse the
existing scratch buffer when requested consecutively; cache storage does not
grow with the number of duels.

Terrain queries share horizontal buckets built with each skyline. Buckets
reference the live masonry cells, so destruction needs no duplicate collision
map or index rebuild. Sign-support checks query their owning building directly.

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

Background animation does not request a redraw when its complete bounds are
covered by a later opaque UI panel or solid terrain cells. Partially covered
objects remain conservative; crater holes and water-tank gaps are not opaque.
This uses the existing terrain cells, not another bitmap. Unchanged background
visibility is reused until the object moves or terrain/UI coverage changes.
Commands remain available for full redraws and newly exposed areas.

On colour displays the angle, power/bar, wind, turn indicator and footer have
independent cached revisions and tight repaint bounds. Adjusting angle no
longer invalidates both complete HUD panels. The result panel is separate;
compact displays retain the simple two-line HUD. Cache limits are unchanged.

Match state uses direct object attributes. Rectangle normalization and terrain
clipping live in the command renderer, without a separate game-level box
wrapper. A drawing batch checks whether its terrain is intact once; damaged
facades still clip against every surviving cell. Solid spans bypass the generic
command dispatcher. The cache remains bounded and still renders through stock
Draw; these changes do not add a framebuffer or change engine/firmware code.

Cached leaf commands replay directly into stock Draw with locally bound native
methods, avoiding a Python dispatch per rectangle. Sprite records are clipped
before taking payload views and call the bytearray method directly, without a
separate per-patch wrapper. Integer conversion happens at scene geometry
boundaries rather than again inside rectangle, circle and text submission.
The palette-blending math uses `picoware.system.decorator.native`; the current
helper compiles a calling wrapper, not the original function body, so it is
not treated as evidence of native math acceleration or a frame-rate guarantee.

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
