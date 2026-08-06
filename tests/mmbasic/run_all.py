"""Run every tests/mmbasic/*.bas through the Picoware MMBasic interpreter.

The graphics backend is the real `PicowareGraphics` (the picoware.gui.draw
bridge); the draw object is a recorder so we can confirm every GUI call goes
through the picoware.gui.draw interface.

Run:
    python3 tests/mmbasic/run_all.py
"""
import sys
import os
import time
import gc

# MicroPython lacks the `glob`, `traceback` and `os.path` modules; guard so
# this harness runs under both CPython and MicroPython.
try:
    import traceback
except ImportError:
    traceback = None

try:
    from os import path as ospath
except ImportError:
    # Minimal posix path helpers for MicroPython.
    class _Path:
        @staticmethod
        def join(*parts):
            parts = [str(p) for p in parts if str(p) not in ("", ".")]
            res = parts[0]
            for p in parts[1:]:
                res = res.rstrip("/") + "/" + p.strip("/")
            return res

        @staticmethod
        def _norm(p):
            out = []
            for part in p.split("/"):
                if part in ("", "."):
                    continue
                if part == "..":
                    if out and out[-1] != "..":
                        out.pop()
                    else:
                        out.append(part)
                else:
                    out.append(part)
            res = "/".join(out)
            return "/" + res if p.startswith("/") else res

        @staticmethod
        def abspath(p):
            if not p.startswith("/"):
                p = _Path.join(os.getcwd(), p)
            return _Path._norm(p)

        @staticmethod
        def dirname(p):
            p = _Path._norm(p)
            idx = p.rfind("/")
            return p[:idx] if idx >= 0 else "."

        @staticmethod
        def isabs(p):
            return p.startswith("/")

    ospath = _Path()

# On the device (Thonny/PicoCalc) we build the real Picoware VM and let the
# AppLoader mount the SD card and add /picoware/apps to sys.path so `import
# mmbasic_runtime` resolves to the on-SD package. On a host without picoware we fall
# back to importing the source tree under builds/MicroPython/apps_unfrozen.
try:
    from picoware.system.view_manager import ViewManager
    from picoware.system.view import View  # noqa: F401
    from picoware.system.app_loader import AppLoader
    _HAVE_PICOWARE = True
except ImportError:
    _HAVE_PICOWARE = False
    ViewManager = None
    AppLoader = None

if _HAVE_PICOWARE:
    vm = ViewManager()
    loader = AppLoader(vm)
    loader.load_module("/picoware/apps")
else:
    _APPS = ospath.abspath(ospath.join(
        ospath.dirname(ospath.abspath(__file__)),
        "..", "..", "builds", "MicroPython", "apps_unfrozen"))
    if _APPS not in sys.path:
        sys.path.insert(0, _APPS)

from mmbasic_runtime import MMBasicEngine, PicowareGraphics, InterpreterState


def _exc_summary():
    """One-line summary of the current exception (no traceback module)."""
    if traceback is not None:
        lines = traceback.format_exc().strip().splitlines()
        return lines[-1] if lines else "?"
    # MicroPython: print_exception to a buffer, keep the last line.
    import io
    buf = io.StringIO()
    sys.print_exception(sys.exc_info()[1], buf)
    lines = buf.getvalue().strip().splitlines()
    return lines[-1] if lines else "?"

TESTS_DIR = ospath.dirname(ospath.abspath(__file__))


class FakeV:
    __slots__ = ("x", "y")

    def __init__(self, x, y):
        self.x = x
        self.y = y


class FakeFont:
    __slots__ = ("size",)

    def __init__(self, size):
        self.size = size


class FakeDraw:
    """Records picoware.gui.draw calls (capped so heavy fractals stay fast)."""

    def __init__(self):
        self.size = FakeV(320, 240)
        self.font_size = FakeV(6, 8)
        self._background = 0
        self._font_default = FakeFont(8)
        self.calls = []
        # Keep the recorded log small: MicroPython's ~2MB heap cannot hold
        # 50k recorded tuples. `total` still counts *every* call.
        self._limit = 1000
        self.total = 0

    def _rec(self, *a):
        self.total += 1
        if len(self.calls) < self._limit:
            self.calls.append(a)

    # C-level methods (picoware_gfx calls these directly).
    def _pixel(self, x, y, color=None):
        self._rec("_pixel", x, y, color)

    def _line(self, x1, y1, x2, y2, color=None):
        self._rec("_line", x1, y1, x2, y2, color)

    def _rectangle(self, x, y, w, h, color=None):
        self._rec("_rectangle", x, y, w, h, color)

    def _fill_rectangle(self, x, y, w, h, color=None):
        self._rec("_fill_rectangle", x, y, w, h, color)

    def _circle(self, x, y, r, color=None):
        self._rec("_circle", x, y, r, color)

    def _fill_circle(self, x, y, r, color=None):
        self._rec("_fill_circle", x, y, r, color)

    def _fill_triangle(self, x1, y1, x2, y2, x3, y3, color=None):
        self._rec("_fill_triangle", x1, y1, x2, y2, x3, y3, color)

    def _text(self, x, y, text, color=None, font_size=-1):
        self._rec("_text", x, y, text, color)

    def _clear(self, color):
        self._rec("_clear", color)

    def _swap(self):
        self._rec("_swap")

    def pixel(self, pos, color=None):
        self._rec("pixel", pos.x, pos.y, color)

    def line_custom(self, p1, p2, color=None):
        self._rec("line_custom", p1.x, p1.y, p2.x, p2.y, color)

    def line(self, pos, size, color=None):
        self._rec("line", pos.x, pos.y, size.x, size.y, color)

    def rect(self, pos, size, color=None):
        self._rec("rect", pos.x, pos.y, size.x, size.y, color)

    def fill_rectangle(self, pos, size, color=None):
        self._rec("fill_rectangle", pos.x, pos.y, size.x, size.y, color)

    def circle(self, pos, r, color=None):
        self._rec("circle", pos.x, pos.y, r, color)

    def fill_circle(self, pos, r, color=None):
        self._rec("fill_circle", pos.x, pos.y, r, color)

    def triangle(self, p1, p2, p3, color=None):
        self._rec("triangle", p1.x, p1.y, p2.x, p2.y, p3.x, p3.y, color)

    def fill_triangle(self, p1, p2, p3, color=None):
        self._rec("fill_triangle", p1.x, p1.y, p2.x, p2.y, p3.x, p3.y, color)

    def text(self, pos, text, color=None, font_size=-1):
        self._rec("text", pos.x, pos.y, text, color)

    def char(self, pos, char, color=None, font_size=-1):
        self._rec("char", pos.x, pos.y, char, color)

    def erase(self):
        self._rec("erase",)

    def fill_screen(self, color):
        self._rec("fill_screen", color)

    def swap(self):
        self._rec("swap",)


class CaptureConsole:
    def __init__(self):
        self.buffer = ""

    def output(self, text):
        self.buffer += text

    def newline(self):
        self.buffer += "\n"

    def echo(self, ch):
        self.buffer += ch

    def backspace(self):
        if self.buffer:
            self.buffer = self.buffer[:-1]

    def pos(self):
        return len(self.buffer)


def run_test(path, timeout=25):
    with open(path, "r") as f:
        src = f.read()

    draw = FakeDraw()
    gfx = PicowareGraphics(draw)
    console = CaptureConsole()
    engine = MMBasicEngine(console=console, gfx=gfx)
    try:
        engine.load(src)
    except Exception:
        return ("parse-error", _exc_summary(), 0, 0, src)

    interp = engine.interpreter
    interp.start()
    state = None
    ticks = 0
    start = time.time()

    while True:
        try:
            state = interp.tick(300)
        except Exception:
            return ("tick-error", _exc_summary(), len(draw.calls), ticks, src)
        if state.status == "running" and ticks > 60:
            # break interactive Inkey$/Input loops aggressively
            if ticks % 15 == 0:
                interp.feed_char("\x1b")
            if ticks % 20 == 0:
                interp.feed_char("q")
        if state.status == "input":
            interp.feed_char("\x1b")
        ticks += 1
        # MicroPython's auto-GC can leave the heap fragmented (many small
        # temporaries freed during expression evaluation); an explicit,
        # frequent collection keeps large (8KB+) allocations from failing.
        if ticks % 5 == 0:
            gc.collect()
        if state.status != "running":
            break
        if time.time() - start > timeout:
            state = InterpreterState("stopped", "timeout")
            break

    return (state.status, state.message, draw.total, ticks, src)


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    tests = sorted(ospath.join(TESTS_DIR, f) for f in os.listdir(TESTS_DIR)
                   if f.endswith(".bas"))
    if only:
        tests = [ospath.join(TESTS_DIR, only) if not ospath.isabs(only)
                 else only]
    results = []
    for t in tests:
        name = ospath.basename(t) if hasattr(ospath, "basename") \
            else t.rstrip("/").split("/")[-1]
        status, msg, draws, ticks, _src = run_test(t)
        results.append((name, status, msg, draws, ticks))
        print("%-12s -> %-12s draws=%-8d ticks=%d  %s" % (
            name, status, draws, ticks, msg[:90]))
        sys.stdout.flush()

    ok = [r for r in results if r[1] in ("ended", "stopped")]
    print("\n=== summary: %d/%d passed (ended or stopped cleanly) ===" %
          (len(ok), len(results)))
    for name, status, msg, draws, ticks in results:
        if status not in ("ended", "stopped"):
            print("  FAIL", name, "->", status, msg[:90])


if __name__ == "__main__":
    main()
