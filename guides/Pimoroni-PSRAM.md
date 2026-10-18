# Explicit Pimoroni PSRAM with an internal-SRAM Python heap

The Pimoroni Pico Plus 2 W has onboard QMI PSRAM in addition to the PicoCalc
motherboard's PIO PSRAM. This configuration keeps ordinary MicroPython objects
in internal SRAM and reserves onboard PSRAM for explicit `pimoram` allocations.
The motherboard framebuffer/allocator are unchanged and can be used concurrently.

## Build integration

Use `tools/micropython-picocalc-pimoroni-2w.sh`. It copies the new module and
runs `tools/prepare-pimoroni-psram.py` before cleaning or building. The preparation
tool checks/applies `tools/patches/rp2-sram-only-gc.patch` to the external
MicroPython checkout, accepts an already-patched checkout, and refuses unknown
source layouts. That branch only changes boards defining `PICOWARE_SRAM_ONLY_GC`.
Other RP2 board heap behavior is unchanged, even when sharing the checkout.

```bash
MICROPYTHON_DIR="$HOME/pico/micropython/ports/rp2" \
  bash tools/micropython-picocalc-pimoroni-2w.sh
```

For a custom build script, first run:

```bash
python3 tools/prepare-pimoroni-psram.py "$HOME/pico/micropython"
```

Then copy the `PicoCalc/pimoram` directory, board configuration and combined
module CMake file as the supplied script does. **Do not use an unpatched
MicroPython core:** ordinary GC allocations and explicit allocations must not
share onboard memory. The native module also checks the board configuration.
The patch adds a heap-selection branch, not PSRAM hardware initialization;
the Raspberry Pi SDK continues initializing the onboard chip.

This trades ordinary Python heap capacity for faster internal-SRAM access.
Applications which relied on several megabytes of automatic Python allocations
must use explicit storage or be adapted. The shared Picoware clock setting stays
unchanged at 210 MHz for Pimoroni; no display or motherboard PSRAM timing changes
are required by this contribution.

## Usage

The canonical high-level interface matches the existing import pattern:

```python
from picoware.system.pimoram import PSRAM

ram = PSRAM()
print(ram.is_ready(), ram.initialized)
print(ram.total_heap_size, ram.free_heap_size, ram.used_heap_size)

obj = ram.malloc(bytearray(b"hello"))
print(obj.value(), obj.addr(), obj.length())
obj[0] = 72
print(obj.value())                 # bytearray(b'Hello')
ram.write8(obj.addr() + 1, 65)
print(obj.value())                 # bytearray(b'HAllo')
obj.free()
```

For large storage, allocate without constructing a same-sized SRAM buffer:

```python
cache = ram.alloc(1024 * 1024)
addr = cache.addr()
ram.write(addr, b"cached data")
working = bytearray(11)
count = ram.read_into(addr, working)
print(count, working)
cache.free()
```

All original calls remain available:

```python
import pimoram
b = pimoram.alloc(65536)
b.write(0, b"hello")
print(b.read(0, 5), b.read8(0), b.size())
b.read_into(0, bytearray(5))
b.free()
```

The new native `pimoram.PSRAM()` also exposes the core address operations and
`alloc_object()`/`malloc()`. The Python wrapper adds the same convenience
properties, `from_file`, `memcpy`, and `memset` as the regular Picoware wrapper.

## API mapping

| API | Behavior |
|---|---|
| `is_ready()`, `initialized` | Onboard PSRAM availability |
| `size()` / `total_heap_size` | Physical chip size |
| `mem_free()` / `free_heap_size` | Available whole allocation pages |
| `used_heap_size` | Physical capacity minus free pages, including reserved prefix |
| `heap_start()` | First usable chip-relative byte offset |
| `get_next_free()` / `next_free_addr` | First free page; advisory, does not reserve it |
| `alloc(n)` | Existing native buffer, now also with `addr()` |
| `malloc(data)`, `alloc_object(data)` | Managed snapshot object |
| `read(addr, n)` | New bytes in SRAM, no 4 KB cap on this API |
| `write(addr, data)` | Copy a readable buffer into PSRAM |
| `read_into(addr, dst)` | Copy to writable buffer; returns number of bytes |
| `read8/16/32`, `write8/16/32` | Little-endian integer access; unaligned scalar access allowed |
| `fill(addr, value, n)` | Fill bytes |
| `copy(src, dst, n)` | Overlap-safe copy |
| `memcpy(dst, src, n)` | Wrapper alias with C-style destination-first order |
| `memset(addr, value, n)` | Wrapper alias for fill |
| `write32_bulk`, `read32_bulk` | Aligned address, transfers whole 32-bit words, returns bytes |
| `fill32(addr, value, words)` | Aligned address, count is words |
| `from_file(storage, addr, path, chunk_size=2048)` | Streams with Picoware storage API; closes on error |
| `test()` | Allocates/tests/releases one page; returns error count, zero on success |
| `collect()` | Runs MicroPython GC, returns 0 bytes moved; no compaction |

## Important compatibility details

- This targets Pimoroni onboard QMI PSRAM, never the PicoCalc motherboard memory.
  Addresses are **chip-relative offsets**, not physical memory pointers. An
  address from one PSRAM API must not be passed to the other.
- The linker-reserved prefix and extra guard page remain protected. With the
  uploaded configuration, the first usable offset is 4096 and baseline free
  memory is 8,384,512 bytes.
- Allocation rounds up to 4096 bytes. Even tiny/empty objects consume one page;
  this is intended for buffers and resource caches, not millions of scalars.
- Raw address methods validate against the usable chip range, not individual
  allocation ownership. Retain the allocation object and respect its length.
  Never use an address after its owner is freed. `get_next_free()` alone does not
  reserve memory and does not report the size of a contiguous run.
- `collect()` never relocates live data, and `free()` never moves neighboring
  objects. Contiguous allocation can fail despite sufficient fragmented free
  capacity. This differs from the motherboard allocator's compaction.
- `PSRAM.read()` and managed `.value()` reconstruct data in internal SRAM. Large
  values can raise MemoryError. Use `read_into()` and small reusable buffers.
  The old native `Buffer.read()` retains its original 4096-byte limit.
- Managed objects support strings, bytes, bytearray, signed 32-bit integers,
  32-bit floats, bool, None, and nested lists/tuples/string-key dictionaries.
  Container encoding is private to this module, not the motherboard serializer.
  `.length()` returns payload bytes, not logical container item count. `len()`
  uses logical length. Cycles and nesting beyond 16 levels are rejected.
- Managed values are snapshots. Bytearray integer item assignment writes back;
  dict/list mutation through the wrapper is not supported. Basic arithmetic,
  equality, indexing and callable forwarding are supplied; this is not a full
  transparent replacement for every Python operator or native Python type.
- Callable objects keep a GC-visible reference to the actual function in SRAM.
  Code/closures are not migrated into PSRAM and this does not save function RAM.
- Explicit `.free()` is supported. Otherwise the existing native buffer
  finalizer releases pages when the owning Python object becomes unreachable.
  New PSRAM handles neither reset allocation state nor deinitialize the chip.
- No buffer-protocol exposure or new cross-core synchronization is introduced.

## Tests

On the PicoCalc, run `tests/pimoram.py` through a USB REPL after flashing. It
only writes allocations it owns. `tests/pimoram_stress.py` is an optional test
which temporarily consumes all currently free onboard PSRAM; run it with other
apps stopped. Check ordinary menus and Gorillas afterward.

For a desktop C-module test, use an upstream MicroPython checkout with its usual
Unix build prerequisites and submodules. The host-only shim replaces the SDK
PSRAM API with 8 MiB of aligned process memory. It is never linked into firmware.

```bash
PICOWARE_DIR="$(pwd)"
make -C "$MICROPYTHON_ROOT/ports/unix" -j4 \
  USER_C_MODULES="$PICOWARE_DIR/tests/pimoram_host" \
  MICROPY_PY_FFI=0 MICROPY_PY_SSL=0 MICROPY_PY_BTREE=0
MICROPYPATH="$PICOWARE_DIR/src/MicroPython" \
  "$MICROPYTHON_ROOT/ports/unix/build-standard/micropython" \
  -X heapsize=128K "$PICOWARE_DIR/tests/pimoram.py"
MICROPYPATH="$PICOWARE_DIR/src/MicroPython" \
  "$MICROPYTHON_ROOT/ports/unix/build-standard/micropython" \
  -X heapsize=128K "$PICOWARE_DIR/tests/pimoram_stress.py"
python3 tests/test_pimoram_build.py
```

Desktop checks validate native code integration, allocation ownership, bounds,
GC cleanup, snapshots, raw operations, build-patch idempotence and portable UI.
They do not establish QMI timing, LCD behavior, cross-core safety, or performance
on physical hardware.

## Hardware observations supplied with this contribution

Jeff's custom firmware performed substantially better in Gorillas after moving
ordinary allocations from onboard PSRAM to SRAM, including at 210 MHz. This is
a qualitative observation, not a controlled before/after FPS benchmark. The
legacy allocator passed a 4 MiB write/read integrity test and a 2 MiB synthetic
sprite-cache demonstration. Later API and System Information updates were
reported working on the custom 220 MHz build; individual on-device test-suite
output has not been supplied.

The clean build integration and cross-board UI handling added for this PR still
need a full RP2350 build and device verification. Keep this as a draft until those
checks are complete. Tested dependency baseline: MicroPython
`f668077be205dc0fe39ee831df5d8fc19db9ea9d`. Host tests used MicroPython
`9a3a0c0d5ea946a4a1b6ff0e3f3087c8adbcac01`.
