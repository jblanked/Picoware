"""
bas-test.py - Run the Picoware MMBasic interpreter, all in one script.

Calls everything together:
    1. ViewManager  - the Picoware VM (real device hardware when present)
    2. AppLoader    - mounts the SD card and adds /picoware/apps to sys.path
    3. MMBasicEngine - the mmbasic parser + runtime + interpreter
    4. an embedded example .bas program, executed at the end (rendered to the
       real screen through picoware.gui.draw, PRINT output via PicowareConsole)

Run it on the device (PicoCalc / Thonny IDE):
    %Run bas-test.py

It degrades to a fake VM + FakeDraw when run on a host without the picoware
hardware modules (python3 or micropython), so you can sanity-check the wiring
off-device too:
    python3    tests/mmbasic/bas-test.py
    micropython tests/mmbasic/bas-test.py
"""

import sys

# ---------------------------------------------------------------------------
# 1) ViewManager + AppLoader (real device) or a fake VM (host fallback)
# ---------------------------------------------------------------------------
try:
    from picoware.system.view_manager import ViewManager
    from picoware.system.view import View  # noqa: F401  (used on-device)
    from picoware.system.app_loader import AppLoader
    _HAVE_PICOWARE = True
except ImportError:
    _HAVE_PICOWARE = False
    ViewManager = None
    AppLoader = None


class FakeVM:
    """Minimal host stand-in so bas-test runs without picoware hardware."""

    def __init__(self, draw):
        self.draw = draw
        self.foreground_color = 0xFFFF
        self.background_color = 0x0000
        self.selected_color = 0x001F
        self.storage = None

        class _IM:
            button = -1

            def reset(self):
                pass

            def button_to_char(self, b):
                return None

        self.input_manager = _IM()

    def log(self, message, level=-1):
        print("[vm.log] %s" % (message,))

    def back(self):
        pass


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
    """Records draw calls; has the same surface as picoware.gui.draw."""

    def __init__(self):
        self.size = FakeV(320, 240)
        self.font_size = FakeV(6, 8)
        self._background = 0
        self._font_default = FakeFont(8)
        self.total = 0

    def _rec(self, *a):
        self.total += 1

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

    def _clear(self, color):
        self._rec("_clear", color)

    def _swap(self):
        self._rec("_swap")

    def _text(self, x, y, text, color=None, font_size=-1):
        self._rec("_text", x, y, text, color)

    def text(self, pos, text, color=None, font_size=-1):
        self._rec("text", pos.x, pos.y, text, color)

    def pixel(self, pos, color=None):
        self._rec("pixel", pos.x, pos.y, color)

    def line_custom(self, p1, p2, color=None):
        self._rec("line_custom", p1.x, p1.y, p2.x, p2.y, color)

    def rect(self, pos, size, color=None):
        self._rec("rect", pos.x, pos.y, size.x, size.y, color)

    def fill_rectangle(self, pos, size, color=None):
        self._rec("fill_rectangle", pos.x, pos.y, size.x, size.y, color)

    def circle(self, pos, r, color=None):
        self._rec("circle", pos.x, pos.y, r, color)

    def fill_circle(self, pos, r, color=None):
        self._rec("fill_circle", pos.x, pos.y, r, color)

    def fill_triangle(self, p1, p2, p3, color=None):
        self._rec("fill_triangle", p1.x, p1.y, p2.x, p2.y, p3.x, p3.y, color)

    def erase(self):
        self._rec("erase")

    def fill_screen(self, color):
        self._rec("fill_screen", color)

    def swap(self):
        self._rec("swap")


class _CountingDraw:
    """Thin proxy around the real draw that counts every call.

    The device `Draw` (lcd.LCD) has no ``total`` attribute, so we count
    MMBasic graphics calls here instead.
    """

    def __init__(self, draw):
        self._draw = draw
        self.total = 0

    def __getattr__(self, name):
        attr = getattr(self._draw, name)
        if callable(attr):

            def _wrap(*a, **k):
                self.total += 1
                return attr(*a, **k)

            return _wrap
        return attr


# ---------------------------------------------------------------------------
# 2) Build the VM + AppLoader
# ---------------------------------------------------------------------------
if _HAVE_PICOWARE:
    import os
    vm = ViewManager()
    loader = AppLoader(vm)
    loader.load_module("/picoware/apps")
else:
    vm = FakeVM(FakeDraw())
    loader = None

# ---------------------------------------------------------------------------
# 3) The mmbasic_runtime interpreter classes
# ---------------------------------------------------------------------------
if not _HAVE_PICOWARE:
    import os
    _APPS = "/Users/user/Desktop/Picoware/builds/MicroPython/apps_unfrozen"
    if _APPS not in sys.path:
        sys.path.insert(0, _APPS)

import mmbasic_runtime
from mmbasic_runtime import (
    MMBasicEngine,
    PicowareConsole,
    PicowareGraphics,
    InterpreterState,
)

# The console renders through the *real* vm.draw; the MMBasic graphics go
# through the counting wrapper so we can report how many draw calls ran.
counting_draw = _CountingDraw(vm.draw)
console = PicowareConsole(vm)
console.footer = "BAS-TEST"
gfx = PicowareGraphics(counting_draw, vm)

# --- which mmbasic_runtime is actually loaded? ------------------------------
try:
    print("mmbasic_runtime loaded from:", mmbasic_runtime.__file__)
except Exception:
    print("mmbasic_runtime loaded from: (no __file__ - frozen/builtin?)")
try:
    # Note: .mpy files are the frozen (compiled) current source, which is the
    # normal on-device layout - not stale.
    _pkg_dir = mmbasic_runtime.__file__.rsplit("/", 1)[0]
    _items = list(os.listdir(_pkg_dir))
    _n_mpy = 0
    _n_py = 0
    for _f in _items:
        if _f.endswith(".mpy"):
            _n_mpy += 1
        elif _f.endswith(".py"):
            _n_py += 1
    print("mmbasic_runtime pkg: %d .py files, %d .mpy files" % (_n_py, _n_mpy))
except Exception as _e:
    print("(could not inspect mmbasic_runtime dir: %r)" % (_e,))


def run_bas(label, src, max_ticks=500):
    """Parse + run an embedded BASIC program through the real engine."""
    engine = MMBasicEngine(console=console, gfx=gfx)
    try:
        engine.load(src)          # mmbasic_runtime class does the parsing here
    except Exception as e:
        print("PARSE FAIL [%s]: %r" % (label, e))
        if "recursion" in str(e).lower():
            print("  HINT: the loaded mmbasic_runtime is stale (check the path above).")
            print("  Delete ALL *.mpy under /sd/picoware/apps/mmbasic_runtime/, then")
            print("  copy builds/MicroPython/apps_unfrozen/mmbasic_runtime/ (.py) and")
            print("  MMBasic.py to /sd/picoware/apps/. Re-run.")
        return "parse-error"
    interp = engine.interpreter
    interp.start()
    counting_draw.total = 0
    state = None
    for _ in range(max_ticks):
        state = interp.tick(300)
        if state.status != "running":
            break
    if state is None:
        state = InterpreterState("stopped", "no-tick")
    console.render()
    print("RESULT [%s]: status=%s  msg=%r  draws=%d" % (
        label, state.status, state.message, counting_draw.total))
    return state.status


# ---------------------------------------------------------------------------
# 4) Example .bas programs (embedded so no SD file is required)
# ---------------------------------------------------------------------------
HELLO_BAS = """
CLS
PRINT "Hello from MMBasic on Picoware!"
PRINT "2 + 3 * 4 = "; 2 + 3 * 4
FOR i = 1 TO 3
  PRINT "loop"; i
NEXT i
PRINT "goodbye"
END
"""

GRAPHICS_BAS = """
CLS RGB(BLACK)
COLOR RGB(WHITE)
BOX 10, 10, 60, 40, 2, RGB(RED), RGB(BLUE)
LINE 10, 100, 310, 100, 2, RGB(GREEN)
CIRCLE 160, 150, 40, 0, 1, RGB(YELLOW)
PIXEL 160, 150, RGB(WHITE)
DIM px(5), py(5)
FOR i = 0 TO 4
  px(i) = 100 + i * 20
  py(i) = 80 + (i AND 1) * 30
NEXT i
POLYGON 5, px(), py(), RGB(WHITE), RGB(MAGENTA)
TURTLE RESET
TURTLE PEN DOWN
TURTLE FORWARD 40
TURTLE RIGHT 90
TURTLE FORWARD 40
PRINT "graphics done"
END
"""

# The comprehensive example program, executed at the end of the script.
EXAMPLE_BAS = """
'Spheres raytrace
CLS
Dim pal(256)
pal(0)=RGB(0,0,0)
pal(1)=RGB(0,0,128)
pal(2)=RGB(8,128,8)
pal(3)=RGB(0,128,128)
pal(4)=RGB(128,0,0)
pal(5)=RGB(128,0,128)
pal(6)=RGB(128,64,32)
pal(7)=RGB(168,168,168)
pal(8)=RGB(128,128,128)
pal(9)=RGB(84,84,252)
pal(10)=RGB(42,252,42)
pal(11)=RGB(0,220,220)
pal(12)=RGB(255,0,0)
pal(13)=RGB(255,84,255)
pal(14)=RGB(255,255,0)
pal(15)=RGB(255,255,255)

pal(16)=RGB(255,255,255)
pal(32)=RGB(0,192,255)
pal(255)=RGB(0,0,192)
rainbow(16,32)
rainbow(32,255)


Read spheres
Dim c(spheres,3),r(spheres)
Dim q(spheres),cl(5)
scrw=320
scrh=320' or 200
w=scrw/2
h=scrh/2
s=0
cl(1)=6
cl(2)=1
cl(3)=cl(1)+8
cl(4)=cl(2)+8
For k=1 To spheres
Read c1,c2,c3,rr
c(k,1)=c1
c(k,2)=c2
c(k,3)=c3
r(k)=rr
q(k)=rr*rr
Next k

Data 6
Data -0.3,-0.8,3,0.6

Data 0.9,-1.4,3.5,0.35
Data 0.7,-0.45,2.5,0.4
Data -0.5,-0.3,1.5,0.15
Data 1.0,-0.2,1.5,0.1
Data -0.1,-0.2,1.25,0.2

For i=1 To scrh
For j=0 To scrw-1
x=0.3
y=-0.5
z=0
ba=3
dx=j-w
dy=h-i
dz=scrh/480*600
dd=dx*dx+dy*dy+dz*dz

recurs:
n=0-(y>=0 Or dy<=0)
If n=0 Then s=0-y/dy

For k=1 To spheres
px=c(k,1)-x
py=c(k,2)-y
pz=c(k,3)-z
pp=px*px+py*py+pz*pz
sc=px*dx+py*dy+pz*dz
If sc<=0 Then GoTo contk
bb=sc*sc/dd
aa=q(k)-pp+bb
If aa<=0 Then GoTo contk
sc=(Sqr(bb)-Sqr(aa))/Sqr(dd)
If (sc<s) Or (n<0) Then n=k:s=sc
contk:
Next k

If n<0 Then
c_=Int(16+(dy*dy/dd)*240)
Color pal(c_)
Pixel j,scrh-i
GoTo contj
EndIf
dx=dx*s
dy=dy*s
dz=dz*s
dd=dd*s*s
x=x+dx
y=y+dy
z=z+dz
If n<>0 Then
nx=x-c(n,1)
ny=y-c(n,2)
nz=z-c(n,3)
nn=nx*nx+ny*ny+nz*nz
l=2*(dx*nx+dy*ny+dz*nz)/nn
dx=dx-nx*l
dy=dy-ny*l
dz=dz-nz*l
GoTo recurs
EndIf

For k=1 To spheres
u=c(k,1)-x
v=c(k,3)-z
If u*u+v*v<=q(k) Then
ba=1
Exit For
EndIf
Next k
'If (x Mod 1+(x<0)>0.5)=(z Mod 1+(z<0)>0.5) Then
If (x-Int(x)>0.5)=(z-Int(z)>0.5) Then
 ik=cl(ba)
 Else
 ik=cl(ba+1)
 EndIf
  Color pal(ik)
Pixel j,scrh-i
EndIf
contj:
Next j
Next i


Sub rainbow(startidx,stopidx)
r0=(pal(startidx)>>16) And 255
r1=(pal(stopidx)>>16) And 255

g0=(pal(startidx)>>8) And 255
g1=(pal(stopidx)>>8) And 255

b0=pal(startidx) And 255
b1=pal(stopidx) And 255

For i=startidx+1 To stopidx-1
a=1-(stopidx-i)/(stopidx-startidx)
r_=Int(r0*(1-a)+r1*a)
g_=Int(g0*(1-a)+g1*a)
b_=Int(b0*(1-a)+b1*a)
pal(i)=RGB(r_,g_,b_)
Next i
End Sub
"""

# ---------------------------------------------------------------------------
# Run everything: quick checks, then the example program at the end.
# ---------------------------------------------------------------------------
def _mem_free():
    try:
        import gc

        return gc.mem_free()
    except Exception:
        return 0


print("bas-test: picoware=%s  screen=%dx%d  mem_free=%d" % (
    "real" if _HAVE_PICOWARE else "fake",
    vm.draw.size.x, vm.draw.size.y, _mem_free()))

print("--- quick parse checks ---")
print("parse 1:", run_bas("hello", HELLO_BAS, max_ticks=200))
print("parse 2:", run_bas("graphics", GRAPHICS_BAS, max_ticks=200))

print("--- example program (executed at the end) ---")
status = run_bas("example", EXAMPLE_BAS, max_ticks=500)
if status == "running":
    # The ray tracer is a long-running program (320x320 pixels); reaching
    # "running" after 500 ticks means it parsed and started executing fine.
    print("bas-test done: loaded + running (long program, still going)")
else:
    print("bas-test done:", status)
