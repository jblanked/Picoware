# picoware/apps/Graph3D.py
# 3D Graphing Calculator & Plotter for PicoCalc / Picoware
# z = f(x, y) — menu GUI, presets, orbit, height-shaded mesh.

from micropython import const
from math import sin, cos, sqrt, exp, log, log10, tan, pi, e, floor, ceil
from math import asin, acos, atan, atan2, sinh, cosh, tanh, isnan, isinf
import math
from gc import collect

from picoware.system.font import FONT_SMALL, FONT_MEDIUM
from picoware.system.buttons import (
    BUTTON_BACK,
    BUTTON_LEFT,
    BUTTON_RIGHT,
    BUTTON_UP,
    BUTTON_DOWN,
    BUTTON_CENTER,
    BUTTON_START,
    BUTTON_PLUS,
    BUTTON_MINUS,
    BUTTON_EQUAL,
    BUTTON_A,
    BUTTON_H,
    BUTTON_R,
    BUTTON_W,
    BUTTON_S,
    BUTTON_G,
    BUTTON_Z,
    BUTTON_SPACE,
    BUTTON_QUESTION,
    BUTTON_P,
    BUTTON_C,
    BUTTON_BACKSPACE,
)

ST_MENU = const(0)
ST_PRESETS = const(1)
ST_INPUT = const(2)
ST_PLOT = const(3)
ST_HELP = const(4)
ST_SETTINGS = const(5)
ST_ERROR = const(6)
ST_SAVED = const(7)
ST_INPUT2 = const(8)
ST_SLICE = const(9)

C_BG = const(0x0862)
C_PLOT = const(0x0841)
C_PANEL = const(0x10A4)
C_FRAME = const(0x3C9A)
C_ACCENT = const(0x07FF)
C_AMBER = const(0xFD20)
C_TITLE = const(0xFFFF)
C_MUTED = const(0x7BEF)
C_DIM = const(0x4208)
C_OK = const(0x07E8)
C_ERR = const(0xF800)
C_AXIS_X = const(0xF800)
C_AXIS_Y = const(0x07E0)
C_AXIS_Z = const(0x051F)
C_WIRE = const(0x1CE7)
C_SEL = const(0x0292)

HEAD_H = const(22)
FOOT_H = const(34)

RANGES = (2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0)
GRIDS = (8, 10, 12)
DIR_APP = "picoware/settings/graph3d"
FILE_SAVED = "picoware/settings/graph3d/saved.txt"
C_WIRE2 = const(0xA11E)
C_LINE2 = const(0xFC9F)

PRESETS = (
    ("Wave", "0.6*sin(x)*cos(y)"),
    ("Paraboloid", "0.12*(x*x+y*y)"),
    ("Saddle", "0.12*(x*x-y*y)"),
    ("Ripple", "sin(sqrt(x*x+y*y))"),
    ("Sombrero", "sin(sqrt(x*x+y*y)+0.001)/(sqrt(x*x+y*y)+0.4)"),
    ("Hyperbolic", "0.18*x*y"),
    ("Gaussian", "1.6*exp(-(x*x+y*y)/3)"),
    ("Twin peaks", "1.4*(exp(-((x-2)**2+y*y)/2)+exp(-((x+2)**2+y*y)/2))"),
    ("Bowl", "-0.1*(x*x+y*y)"),
    ("Checker", "0.5*sin(2*x)*sin(2*y)"),
    ("Helix bowl", "0.15*(x*x+y*y)+0.4*sin(3*atan2(y,x))"),
    ("Volcano", "1.2*exp(-(x*x+y*y)/4)-0.6*exp(-(x*x+y*y)/0.6)"),
)

_SAFE = {
    "abs": abs,
    "min": min,
    "max": max,
    "pow": pow,
    "round": round,
    "int": int,
    "float": float,
    "sin": sin,
    "cos": cos,
    "tan": tan,
    "asin": asin,
    "acos": acos,
    "atan": atan,
    "atan2": atan2,
    "log": log,
    "log10": log10,
    "exp": exp,
    "sqrt": sqrt,
    "pi": pi,
    "e": e,
    "floor": floor,
    "ceil": ceil,
    "sinh": sinh,
    "cosh": cosh,
    "tanh": tanh,
    "math": math,
}

_state = ST_MENU
_menu = None
_preset_menu = None
_help_box = None
_dirty = True
_error_msg = ""
_expr = "0.6*sin(x)*cos(y)"
_expr2 = ""
_range = 4.0
_grid_n = 12
_style = 1
_auto = False
_pitch = 0.55
_yaw = 0.70
_zoom = 1.0
_zmin = 0.0
_zmax = 1.0
_zscale = 1.0
_zs = None
_zs2 = None
_need_eval = True
_saved_menu = None
_saved = []
_slice_axis = 0
_slice_idx = 0
_toast = ""
_storage = None
_sw = 320
_sh = 320
_cx = 160
_cy = 150
_focal = 220.0
_cam = 9.0
_px0 = 0
_py0 = 0
_px1 = 320
_py1 = 320
_set_row = 0
_hint_flash = 0


def _rgb565(r, g, b):
    if r < 0:
        r = 0
    elif r > 255:
        r = 255
    if g < 0:
        g = 0
    elif g > 255:
        g = 255
    if b < 0:
        b = 0
    elif b > 255:
        b = 255
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def _heat(t):
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    stops = (
        (0.00, 18, 28, 130),
        (0.22, 0, 170, 210),
        (0.42, 16, 200, 70),
        (0.62, 220, 210, 16),
        (0.82, 236, 110, 8),
        (1.00, 220, 28, 36),
    )
    for i in range(len(stops) - 1):
        t0, r0, g0, b0 = stops[i]
        t1, r1, g1, b1 = stops[i + 1]
        if t <= t1:
            u = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return (
                int(r0 + (r1 - r0) * u),
                int(g0 + (g1 - g0) * u),
                int(b0 + (b1 - b0) * u),
            )
    return (220, 28, 36)


def _shade_color(t, shade, cool=False):
    if cool:
        r, g, b = _cool(t)
    else:
        r, g, b = _heat(t)
    r = int(r * shade)
    g = int(g * shade)
    b = int(b * shade)
    return _rgb565(r, g, b)


def _cool(t):
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    stops = (
        (0.00, 20, 16, 80),
        (0.30, 80, 20, 180),
        (0.55, 200, 40, 160),
        (0.80, 240, 140, 200),
        (1.00, 255, 220, 240),
    )
    for i in range(len(stops) - 1):
        t0, r0, g0, b0 = stops[i]
        t1, r1, g1, b1 = stops[i + 1]
        if t <= t1:
            u = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return (
                int(r0 + (r1 - r0) * u),
                int(g0 + (g1 - g0) * u),
                int(b0 + (b1 - b0) * u),
            )
    return (255, 220, 240)


def _clean_expr(s):
    s = (s or "").strip()
    s = s.replace("^", "**")
    s = s.replace("×", "*")
    s = s.replace("÷", "/")
    low = s.lower()
    if low.startswith("z="):
        s = s[2:]
    elif low.startswith("f="):
        s = s[2:]
    return s.strip()


def _short_expr(n=22):
    s = _clean_expr(_expr)
    if len(s) <= n:
        return s
    return s[: n - 2] + ".."


def _cycle(seq, cur, step):
    idx = 0
    best = 1e9
    for i, v in enumerate(seq):
        d = abs(v - cur)
        if d < best:
            best = d
            idx = i
    return seq[(idx + step) % len(seq)]


def _sample_expr(expr):
    expr = _clean_expr(expr)
    if not expr:
        return None, 0.0, 1.0, "Type an equation first."
    try:
        code = compile(expr, "<z>", "eval")
    except Exception as ex:
        return None, 0.0, 1.0, str(ex)[:48]

    n = _grid_n
    r = _range
    step = (2.0 * r) / (n - 1) if n > 1 else 1.0
    zs = []
    zmin = 1e30
    zmax = -1e30
    env = dict(_SAFE)
    ok_any = False
    for j in range(n):
        y = -r + j * step
        row = []
        env["y"] = y
        for i in range(n):
            x = -r + i * step
            env["x"] = x
            env["r"] = sqrt(x * x + y * y)
            z = None
            try:
                v = eval(code, {"__builtins__": {}}, env)
                if isinstance(v, (int, float)) and not isnan(v) and not isinf(v):
                    z = float(v)
                    if z < zmin:
                        zmin = z
                    if z > zmax:
                        zmax = z
                    ok_any = True
            except Exception:
                z = None
            row.append(z)
        zs.append(row)
    if not ok_any:
        return None, 0.0, 1.0, "No real values. Check x, y, domain."
    if zmax - zmin < 1e-9:
        zmax = zmin + 1.0
    return zs, zmin, zmax, ""


def _eval_grid():
    global _zs, _zs2, _zmin, _zmax, _zscale, _need_eval, _error_msg
    zs, zmin, zmax, err = _sample_expr(_expr)
    if zs is None:
        _error_msg = err
        return False
    zs2 = None
    if _clean_expr(_expr2):
        zs2, zmin2, zmax2, err2 = _sample_expr(_expr2)
        if zs2 is None:
            _error_msg = "g(x,y): " + err2
            return False
        if zmin2 < zmin:
            zmin = zmin2
        if zmax2 > zmax:
            zmax = zmax2
    if zmax - zmin < 1e-9:
        zmax = zmin + 1.0
    _zs = zs
    _zs2 = zs2
    _zmin = zmin
    _zmax = zmax
    _zscale = (_range * 0.72) / (zmax - zmin)
    _need_eval = False
    _error_msg = ""
    collect()
    return True


def _ensure_dir(storage):
    if not storage:
        return False
    try:
        if not storage.exists(DIR_APP):
            storage.mkdir(DIR_APP)
        return True
    except Exception:
        return False


def _load_saved(storage):
    global _saved
    _saved = []
    if not storage:
        return
    try:
        if storage.exists(FILE_SAVED):
            raw = storage.read(FILE_SAVED, "r")
            if raw:
                for line in str(raw).split("\n"):
                    line = line.strip()
                    if line:
                        _saved.append(line)
    except Exception:
        _saved = []


def _write_saved(storage):
    if not storage or not _ensure_dir(storage):
        return False
    try:
        return storage.write(FILE_SAVED, "\n".join(_saved) + "\n", "w")
    except Exception:
        return False


def _pack_entry():
    a = _clean_expr(_expr)
    b = _clean_expr(_expr2)
    if b:
        return a + " | " + b
    return a


def _unpack_entry(line):
    if " | " in line:
        a, b = line.split(" | ", 1)
        return a.strip(), b.strip()
    return line.strip(), ""


def _next_shot_path(storage):
    if not _ensure_dir(storage):
        return None
    n = 1
    while n < 100:
        path = "picoware/settings/graph3d/shot{:02d}.bmp".format(n)
        try:
            if not storage.exists(path):
                return path
        except Exception:
            return path
        n += 1
    return "picoware/settings/graph3d/shot99.bmp"


def _xform(x, y_up, z_depth):
    cy = cos(_yaw)
    sy = sin(_yaw)
    x1 = x * cy - z_depth * sy
    z1 = x * sy + z_depth * cy
    cp = cos(_pitch)
    sp = sin(_pitch)
    y2 = y_up * cp - z1 * sp
    z2 = y_up * sp + z1 * cp
    zc = _cam - z2
    if zc < 0.45:
        return None
    s = (_focal * _zoom) / zc
    sx = int(_cx + x1 * s)
    sy = int(_cy - y2 * s)
    return (sx, sy, zc, x1, y2, z2)


def _pt_ok(p):
    if p is None:
        return False
    if p[0] < _px0 - 40 or p[0] > _px1 + 40:
        return False
    if p[1] < _py0 - 40 or p[1] > _py1 + 40:
        return False
    return True


def _outcode(x, y):
    c = 0
    if x < _px0:
        c |= 1
    elif x > _px1:
        c |= 2
    if y < _py0:
        c |= 4
    elif y > _py1:
        c |= 8
    return c


def _clip_line(draw, a, b, color):
    if a is None or b is None:
        return
    x0 = a[0]
    y0 = a[1]
    x1 = b[0]
    y1 = b[1]
    c0 = _outcode(x0, y0)
    c1 = _outcode(x1, y1)
    xmin = _px0
    xmax = _px1
    ymin = _py0
    ymax = _py1
    while True:
        if not (c0 | c1):
            draw._line(x0, y0, x1, y1, color)
            return
        if c0 & c1:
            return
        c = c0 if c0 else c1
        if c & 8:
            x = x0 + (x1 - x0) * (ymax - y0) / (y1 - y0) if y1 != y0 else x0
            y = ymax
        elif c & 4:
            x = x0 + (x1 - x0) * (ymin - y0) / (y1 - y0) if y1 != y0 else x0
            y = ymin
        elif c & 2:
            y = y0 + (y1 - y0) * (xmax - x0) / (x1 - x0) if x1 != x0 else y0
            x = xmax
        else:
            y = y0 + (y1 - y0) * (xmin - x0) / (x1 - x0) if x1 != x0 else y0
            x = xmin
        if c == c0:
            x0, y0 = x, y
            c0 = _outcode(x0, y0)
        else:
            x1, y1 = x, y
            c1 = _outcode(x1, y1)


def _tri_in_plot(p0, p1, p2):
    cx = (p0[0] + p1[0] + p2[0]) / 3.0
    cy = (p0[1] + p1[1] + p2[1]) / 3.0
    return (_px0 - 4) <= cx <= (_px1 + 4) and (_py0 - 4) <= cy <= (_py1 + 4)


def _area2(p0, p1, p2):
    return (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p2[0] - p0[0]) * (p1[1] - p0[1])


def _face_shade(p0, p1, p2):
    ux = p1[3] - p0[3]
    uy = p1[4] - p0[4]
    uz = p1[5] - p0[5]
    vx = p2[3] - p0[3]
    vy = p2[4] - p0[4]
    vz = p2[5] - p0[5]
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    ln = sqrt(nx * nx + ny * ny + nz * nz)
    if ln < 1e-8:
        return 0.55
    nd = (nx * 0.35 + ny * 0.82 + nz * 0.25) / ln
    if nd < 0.0:
        nd = -nd
    return 0.38 + 0.62 * nd


def _layout(draw):
    global _sw, _sh, _cx, _cy, _focal, _cam, _px0, _py0, _px1, _py1
    _sw = int(draw.size.x)
    _sh = int(draw.size.y)
    _px0 = 6
    _py0 = HEAD_H + 2
    _px1 = _sw - 7
    _py1 = _sh - FOOT_H - 2
    _cx = (_px0 + _px1) // 2
    _cy = (_py0 + _py1) // 2 + 4
    short = min(_px1 - _px0, _py1 - _py0)
    _focal = short * 0.78
    _cam = 7.6 + _range * 0.22


def _paint_chrome(draw, subtitle, footer1, footer2):
    draw._fill_rectangle(0, 0, _sw, HEAD_H, C_PANEL)
    draw._fill_rectangle(0, 0, _sw, 2, C_ACCENT)
    draw._text(draw.scale_x(6), draw.scale_y(5), "GRAPH 3D", C_ACCENT, FONT_SMALL)
    if subtitle:
        draw._text(draw.scale_x(82), draw.scale_y(5), subtitle, C_TITLE, FONT_SMALL)

    fy = _sh - FOOT_H
    draw._fill_rectangle(0, fy, _sw, FOOT_H, C_PANEL)
    draw._fill_rectangle(0, fy, _sw, 1, C_FRAME)
    if footer1:
        draw._text(draw.scale_x(6), fy + draw.scale_y(4), footer1, C_ACCENT, FONT_SMALL)
    if footer2:
        draw._text(draw.scale_x(6), fy + draw.scale_y(18), footer2, C_MUTED, FONT_SMALL)


def _draw_gizmo(draw):
    """Small XYZ triad in the plot's top-left — not through the mesh."""
    ox = _px0 + 20
    oy = _py0 + 20
    L = 16
    cy = cos(_yaw)
    sy = sin(_yaw)
    cp = cos(_pitch)
    sp = sin(_pitch)

    def tip(x, yup, zd):
        x1 = x * cy - zd * sy
        z1 = x * sy + zd * cy
        y2 = yup * cp - z1 * sp
        return ox + int(x1 * L), oy - int(y2 * L)

    axes = (
        (tip(1, 0, 0), C_AXIS_X, "X"),
        (tip(0, 0, 1), C_AXIS_Y, "Y"),
        (tip(0, 1, 0), C_AXIS_Z, "Z"),
    )
    for (tx, ty), col, ch in axes:
        draw._line(ox, oy, tx, ty, col)
        lx = tx + 2
        ly = ty - 4
        if _px0 <= lx <= _px1 - 6 and _py0 <= ly <= _py1 - 6:
            draw._text(lx, ly, ch, col, FONT_SMALL)


def _draw_plot(draw):
    global _toast
    draw.fill_screen(C_BG)
    draw._fill_rectangle(
        _px0, _py0,
        _px1 - _px0 + 1, _py1 - _py0 + 1,
        C_PLOT,
    )

    if _zs is None:
        draw._text(draw.scale_x(24),_sh // 2, "No surface", C_ERR, FONT_MEDIUM)
        _paint_chrome(draw, "empty", "BACK  menu", "ENTER  type equation")
        draw.swap()
        return

    n = _grid_n
    r = _range
    step = (2.0 * r) / (n - 1) if n > 1 else 1.0
    zspan = _zmax - _zmin
    if zspan < 1e-9:
        zspan = 1.0

    def _project_zs(zs):
        pts = []
        for j in range(n):
            yw = -r + j * step
            row = []
            for i in range(n):
                xw = -r + i * step
                zraw = zs[j][i]
                if zraw is None:
                    row.append(None)
                else:
                    yup = (zraw - _zmin) * _zscale
                    p = _xform(xw, yup, yw)
                    row.append(p if _pt_ok(p) else None)
            pts.append(row)
        return pts

    def _add_faces(faces, pts, zs, cool):
        for j in range(n - 1):
            for i in range(n - 1):
                p00 = pts[j][i]
                p10 = pts[j][i + 1]
                p01 = pts[j + 1][i]
                p11 = pts[j + 1][i + 1]
                zc = zs[j][i]
                if zc is None:
                    zc = _zmin
                t = (zc - _zmin) / zspan

                def _push(a, b, c):
                    if a is None or b is None or c is None:
                        return
                    if abs(_area2(a, b, c)) < 2:
                        return
                    if not _tri_in_plot(a, b, c):
                        return
                    depth = a[2] + b[2] + c[2]
                    faces.append((depth, t, a, b, c, cool))

                _push(p00, p10, p01)
                _push(p10, p11, p01)

    def _draw_wires(pts, zs, cool):
        if _style == 0:
            for j in range(n):
                for i in range(n - 1):
                    a = pts[j][i]
                    b = pts[j][i + 1]
                    if a and b:
                        zc = zs[j][i]
                        tt = 0.5 if zc is None else (zc - _zmin) / zspan
                        _clip_line(draw, a, b, _shade_color(tt, 1.0, cool))
            for j in range(n - 1):
                for i in range(n):
                    a = pts[j][i]
                    b = pts[j + 1][i]
                    if a and b:
                        zc = zs[j][i]
                        tt = 0.5 if zc is None else (zc - _zmin) / zspan
                        _clip_line(draw, a, b, _shade_color(tt, 1.0, cool))
        else:
            wcol = C_WIRE2 if cool else C_WIRE
            for j in range(n):
                for i in range(n - 1):
                    _clip_line(draw, pts[j][i], pts[j][i + 1], wcol)
            for j in range(n - 1):
                for i in range(n):
                    _clip_line(draw, pts[j][i], pts[j + 1][i], wcol)

    pts1 = _project_zs(_zs)
    pts2 = _project_zs(_zs2) if _zs2 is not None else None
    faces = []
    _add_faces(faces, pts1, _zs, False)
    if pts2 is not None:
        _add_faces(faces, pts2, _zs2, True)
    faces.sort(key=lambda f: f[0], reverse=True)

    if _style == 1:
        for depth, t, a, b, c, cool in faces:
            col = _shade_color(t, _face_shade(a, b, c), cool)
            draw._fill_triangle(
                a[0], a[1],
                b[0], b[1],
                c[0], c[1],
                col,
            )

    _draw_wires(pts1, _zs, False)
    if pts2 is not None:
        _draw_wires(pts2, _zs2, True)

    _draw_gizmo(draw)
    draw._rectangle(
        _px0, _py0,
        _px1 - _px0, _py1 - _py0,
        C_FRAME,
    )

    sty = "SOLID" if _style == 1 else "WIRE"
    spin = "SPIN" if _auto else "HOLD"
    two = "+g" if _zs2 is not None else ""
    sub = "z=" + _short_expr(20)
    if _toast:
        sub = _toast
    f1 = "R{:.0f}  {}x{}  {}{}  {}".format(_range, n, n, sty, two, spin)
    f2 = "C slice  P shot  ENTER edit  BACK menu"
    _paint_chrome(draw, sub, f1, f2)
    draw.swap()
    if _toast:
        _toast = ""


def _draw_error(draw):
    draw.fill_screen(C_BG)
    draw._fill_rectangle(draw.scale_x(14), draw.scale_y(70), _sw - draw.scale_x(28), draw.scale_y(132), C_PANEL)
    draw._rectangle(draw.scale_x(14), draw.scale_y(70), _sw - draw.scale_x(28), draw.scale_y(132), C_ERR)
    draw._text(draw.scale_x(26), draw.scale_y(84), "Could not plot", C_ERR, FONT_MEDIUM)
    msg = _error_msg or "Unknown error"
    if len(msg) > 34:
        draw._text(draw.scale_x(26), draw.scale_y(114), msg[:34], C_TITLE, FONT_SMALL)
        draw._text(draw.scale_x(26), draw.scale_y(128), msg[34:68], C_TITLE, FONT_SMALL)
    else:
        draw._text(draw.scale_x(26), draw.scale_y(114), msg, C_TITLE, FONT_SMALL)
    draw._text(draw.scale_x(26), draw.scale_y(156), "ENTER  fix equation", C_ACCENT, FONT_SMALL)
    draw._text(draw.scale_x(26), draw.scale_y(172), "BACK   main menu", C_MUTED, FONT_SMALL)
    _paint_chrome(draw, "error", "ENTER  edit", "BACK  menu")
    draw.swap()


def _draw_settings(draw):
    draw.fill_screen(C_BG)
    rows = (
        ("Range", "{:.1f} to {:.1f}".format(-_range, _range)),
        ("Grid", "{} x {}".format(_grid_n, _grid_n)),
        ("Style", "Solid + wire" if _style == 1 else "Wireframe"),
        ("Auto spin", "On" if _auto else "Off"),
        ("Reset camera", "pitch / yaw / zoom"),
        ("Done", "back to menu"),
    )
    y = HEAD_H + draw.scale_y(16) 
    draw._text(draw.scale_x(16), y, "UP/DOWN select   LEFT/RIGHT change", C_MUTED, FONT_SMALL)
    y += draw.scale_y(22)
    for i, (lab, val) in enumerate(rows):
        sel = i == _set_row
        if sel:
            draw._fill_rectangle(draw.scale_x(10), y - draw.scale_y(3), _sw - draw.scale_x(20), draw.scale_y(22), C_SEL)
        col = C_TITLE if sel else C_MUTED
        vcol = C_AMBER if sel else C_ACCENT
        draw._text(draw.scale_x(18), y, lab, col, FONT_SMALL)
        draw._text(draw.scale_x(150), y, val, vcol, FONT_SMALL)
        if sel and i < 4:
            draw._text(_sw - draw.scale_x(28), y, "<>", C_AMBER, FONT_SMALL)
        y += draw.scale_y(24)
    _paint_chrome(
        draw,
        "settings",
        "LEFT/RIGHT  adjust selected row",
        "ENTER  activate     BACK  menu",
    )
    draw.swap()


def _kill_menu(obj_name):
    global _menu, _preset_menu, _help_box, _saved_menu
    if obj_name == "menu" and _menu:
        del _menu
        _menu = None
    elif obj_name == "preset" and _preset_menu:
        del _preset_menu
        _preset_menu = None
    elif obj_name == "help" and _help_box:
        del _help_box
        _help_box = None
    elif obj_name == "saved" and _saved_menu:
        del _saved_menu
        _saved_menu = None


def _make_saved(view_manager):
    global _saved_menu
    from picoware.gui.menu import Menu

    _kill_menu("saved")
    _load_saved(_storage)
    draw = view_manager.draw
    _saved_menu = Menu(
        draw,
        "Saved   ENTER load   DEL drop",
        0,
        draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
        view_manager.foreground_color,
    )
    _saved_menu.add_item("Save current plot")
    if _saved:
        for line in _saved:
            shown = line if len(line) <= 28 else line[:26] + ".."
            _saved_menu.add_item(shown)
    else:
        _saved_menu.add_item("(empty)")
    _saved_menu.set_selected(0)


def _make_menu(view_manager):
    global _menu
    from picoware.gui.menu import Menu

    _kill_menu("menu")
    draw = view_manager.draw
    _menu = Menu(
        draw,
        "3D Graphing Calculator",
        0,
        draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
        view_manager.foreground_color,
    )
    g2 = _clean_expr(_expr2)
    _menu.add_item("Plot   z=" + _short_expr(16))
    _menu.add_item("Type z = f(x,y)")
    if g2:
        gs = g2 if len(g2) <= 14 else g2[:12] + ".."
        _menu.add_item("Second surface  g=" + gs)
    else:
        _menu.add_item("Second surface  (off)")
    _menu.add_item("Choose a preset")
    _menu.add_item("Saved list")
    _menu.add_item("Settings")
    _menu.add_item("Help")
    _menu.add_item("Quit")
    _menu.set_selected(0)


def _make_presets(view_manager):
    global _preset_menu
    from picoware.gui.menu import Menu

    _kill_menu("preset")
    draw = view_manager.draw
    _preset_menu = Menu(
        draw,
        "Presets   ENTER plots",
        0,
        draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
        view_manager.foreground_color,
    )
    for name, expr in PRESETS:
        _preset_menu.add_item(name + "  " + expr)
    _preset_menu.set_selected(0)


def _make_help(view_manager):
    global _help_box
    from picoware.gui.textbox import TextBox

    _kill_menu("help")
    draw = view_manager.draw
    _help_box = TextBox(
        draw,
        0,
        draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
    )
    _help_box.set_text(
        "GRAPH 3D\n"
        "Plot z = f(x, y) as a surface.\n"
        "\n"
        "MAIN MENU\n"
        "  Plot      draw current equation\n"
        "  Type      keyboard editor\n"
        "  Preset    12 ready surfaces\n"
        "  Settings  range, grid, style\n"
        "\n"
        "ON THE PLOT\n"
        "  Arrows    rotate\n"
        "  +  -      zoom\n"
        "  ENTER     edit equation\n"
        "  BACK      menu\n"
        "  C         2D slice\n"
        "  P         screenshot to SD\n"
        "  A         auto-spin on/off\n"
        "  W / S     wire / solid\n"
        "  G         grid 8 / 10 / 12\n"
        "  Z         next XY range\n"
        "  R         reset camera\n"
        "  ? or H    this help\n"
        "\n"
        "EQUATIONS\n"
        "  Use x and y.  r is radius.\n"
        "  ^ is allowed (becomes **).\n"
        "  sin cos tan exp log sqrt\n"
        "  abs min max pow atan2 pi e\n"
        "\n"
        "  0.6*sin(x)*cos(y)\n"
        "  0.12*(x*x-y*y)\n"
        "  sin(sqrt(x*x+y*y))\n"
        "\n"
        "TIPS\n"
        "  Grid 10-12 is the sweet spot.\n"
        "  Wire mode is faster.\n"
        "  Solid uses height + lighting.\n"
        "  Two surfaces: f heat, g pink.\n"
        "  Saved list stores f | g.\n"
        "  Tiny XYZ gizmo is top-left.\n"
        "  Shots: picoware/settings/graph3d/\n"
        "\n"
        "BACK returns to the menu."
    )


def _begin_input(view_manager, second=False):
    kb = view_manager.keyboard
    view_manager.input_manager.reset()
    kb.reset()
    if second:
        kb.title = "g(x,y)  empty clears"
        kb.response = _clean_expr(_expr2)
    else:
        kb.title = "z = f(x, y)   ENTER plots"
        kb.response = _clean_expr(_expr)
    kb.run(force=True)


def _draw_slice(draw):
    draw.fill_screen(C_BG)
    draw._fill_rectangle(
       _px0, _py0,
       _px1 - _px0 + 1, _py1 - _py0 + 1,
        C_PLOT,
    )
    if _zs is None:
        _paint_chrome(draw, "slice", "no data", "BACK  3D")
        draw.swap()
        return

    n = _grid_n
    r = _range
    step = (2.0 * r) / (n - 1) if n > 1 else 1.0
    idx = _slice_idx
    idx = max(idx, 0)
    idx = min(idx, n - 1)
    zspan = _zmax - _zmin
    if zspan < 1e-9:
        zspan = 1.0

    left = _px0 + draw.scale_x(18)
    right = _px1 - draw.scale_x(8)
    top = _py0 + draw.scale_y(8)
    bot = _py1 - draw.scale_y(10)
    draw._line(left, top, left, bot, C_FRAME)
    draw._line(left, bot, right, bot, C_FRAME)
    # zero line
    if _zmin < 0.0 < _zmax:
        zy = int(bot - (0.0 - _zmin) / zspan * (bot - top))
        draw._line(left, zy, right, zy, C_DIM)

    def _poly(zs, color):
        last = None
        for i in range(n):
            if _slice_axis == 0:
                z = zs[idx][i]
            else:
                z = zs[i][idx]
            if z is None:
                last = None
                continue
            t = i / float(n - 1) if n > 1 else 0.0
            px = int(left + t * (right - left))
            py = int(bot - (z - _zmin) / zspan * (bot - top))
            if last is not None:
                draw._line(last[0], last[1], px, py, color)
            last = (px, py)

    _poly(_zs, C_ACCENT)
    if _zs2 is not None:
        _poly(_zs2, C_LINE2)

    if _slice_axis == 0:
        val = -r + idx * step
        title = "slice  y={:.2f}".format(val)
    else:
        val = -r + idx * step
        title = "slice  x={:.2f}".format(val)
    f1 = "LEFT/RIGHT  move cut"
    f2 = "C  other axis    BACK  3D"
    _paint_chrome(draw, title, f1, f2)
    draw.swap()


def _take_shot(view_manager):
    global _toast, _dirty
    storage = view_manager.storage
    path = _next_shot_path(storage)
    if not path:
        _toast = "shot failed (SD?)"
        _dirty = True
        return
    try:
        view_manager.draw.screenshot(path)
        _toast = "saved " + path.split("/")[-1]
    except Exception:
        _toast = "screenshot failed"
    _dirty = True


def _goto_plot(view_manager):
    global _state, _dirty, _need_eval, _slice_idx, _toast
    draw = view_manager.draw
    _layout(draw)
    draw.fill_screen(C_BG)
    _paint_chrome(draw, "working", "Sampling f(x,y)...", "")
    draw._text(draw.scale_x(28), _sh // 2 - draw.scale_y(8), "Sampling surface...", C_ACCENT, FONT_MEDIUM)
    draw.swap()
    if _need_eval or _zs is None:
        if not _eval_grid():
            _state = ST_ERROR
            _dirty = True
            return
    _slice_idx = _grid_n // 2
    _toast = ""
    _state = ST_PLOT
    _dirty = True


def _apply_setting(step):
    global _range, _grid_n, _style, _auto, _need_eval
    global _pitch, _yaw, _zoom
    row = _set_row
    if row == 0:
        _range = _cycle(RANGES, _range, step)
        _need_eval = True
    elif row == 1:
        _grid_n = int(_cycle(GRIDS, float(_grid_n), step))
        _need_eval = True
    elif row == 2:
        _style = 0 if _style == 1 else 1
    elif row == 3:
        _auto = not _auto
    elif row == 4:
        _pitch = 0.55
        _yaw = 0.70
        _zoom = 1.0
        _auto = False
    return True


def start(view_manager) -> bool:
    global _state, _dirty, _need_eval, _auto, _zs, _zs2
    global _pitch, _yaw, _zoom, _set_row, _hint_flash
    global _menu, _preset_menu, _help_box, _saved_menu
    global _storage, _grid_n, _toast

    _storage = view_manager.storage
    if _grid_n not in GRIDS:
        _grid_n = 12
    _layout(view_manager.draw)
    _state = ST_MENU
    _menu = None
    _preset_menu = None
    _help_box = None
    _saved_menu = None
    _dirty = True
    _need_eval = True
    _auto = False
    _zs = None
    _zs2 = None
    _pitch = 0.55
    _yaw = 0.70
    _zoom = 1.0
    _set_row = 0
    _hint_flash = 0
    _toast = ""
    view_manager.input_manager.reset()
    _ensure_dir(_storage)
    _load_saved(_storage)
    _make_menu(view_manager)
    return True


def run(view_manager) -> None:
    global _state, _dirty, _expr, _expr2, _need_eval, _zs2
    global _pitch, _yaw, _zoom, _auto, _style
    global _range, _grid_n, _set_row, _slice_axis, _slice_idx, _toast

    inp = view_manager.input_manager
    button = inp.button
    draw = view_manager.draw

    if _state == ST_MENU:
        if _menu is None:
            _make_menu(view_manager)
        if button == BUTTON_UP:
            inp.reset()
            _menu.scroll_up()
        elif button == BUTTON_DOWN:
            inp.reset()
            _menu.scroll_down()
        elif button == BUTTON_BACK:
            inp.reset()
            view_manager.back()
        elif button == BUTTON_CENTER:
            inp.reset()
            idx = _menu.selected_index
            if idx == 0:
                _goto_plot(view_manager)
            elif idx == 1:
                _state = ST_INPUT
                _begin_input(view_manager, False)
            elif idx == 2:
                _state = ST_INPUT2
                _begin_input(view_manager, True)
            elif idx == 3:
                _state = ST_PRESETS
                _make_presets(view_manager)
            elif idx == 4:
                _state = ST_SAVED
                _make_saved(view_manager)
            elif idx == 5:
                _state = ST_SETTINGS
                _set_row = 0
                _dirty = True
            elif idx == 6:
                _state = ST_HELP
                _make_help(view_manager)
            elif idx == 7:
                view_manager.back()

    elif _state == ST_PRESETS:
        if _preset_menu is None:
            _make_presets(view_manager)
        if button == BUTTON_UP:
            inp.reset()
            _preset_menu.scroll_up()
        elif button == BUTTON_DOWN:
            inp.reset()
            _preset_menu.scroll_down()
        elif button == BUTTON_BACK:
            inp.reset()
            _kill_menu("preset")
            _state = ST_MENU
            _make_menu(view_manager)
        elif button == BUTTON_CENTER:
            inp.reset()
            idx = _preset_menu.selected_index
            if 0 <= idx < len(PRESETS):
                _expr = PRESETS[idx][1]
                _need_eval = True
                _kill_menu("preset")
                _goto_plot(view_manager)

    elif _state == ST_SAVED:
        if _saved_menu is None:
            _make_saved(view_manager)
        if button == BUTTON_UP:
            inp.reset()
            _saved_menu.scroll_up()
        elif button == BUTTON_DOWN:
            inp.reset()
            _saved_menu.scroll_down()
        elif button == BUTTON_BACK:
            inp.reset()
            _kill_menu("saved")
            _state = ST_MENU
            _make_menu(view_manager)
        elif button == BUTTON_BACKSPACE:
            inp.reset()
            idx = _saved_menu.selected_index
            if idx >= 1 and idx - 1 < len(_saved):
                _saved.pop(idx - 1)
                _write_saved(_storage)
                _make_saved(view_manager)
        elif button == BUTTON_CENTER:
            inp.reset()
            idx = _saved_menu.selected_index
            if idx == 0:
                entry = _pack_entry()
                if entry and entry not in _saved:
                    _saved.insert(0, entry)
                    _write_saved(_storage)
                _make_saved(view_manager)
            elif idx >= 1 and idx - 1 < len(_saved):
                _expr, _expr2 = _unpack_entry(_saved[idx - 1])
                _need_eval = True
                _kill_menu("saved")
                _goto_plot(view_manager)

    elif _state == ST_SETTINGS:
        if button == BUTTON_UP:
            inp.reset()
            _set_row = (_set_row - 1) % 6
            _dirty = True
        elif button == BUTTON_DOWN:
            inp.reset()
            _set_row = (_set_row + 1) % 6
            _dirty = True
        elif button == BUTTON_LEFT:
            inp.reset()
            if _set_row <= 3:
                _apply_setting(-1)
            _dirty = True
        elif button == BUTTON_RIGHT:
            inp.reset()
            if _set_row <= 3:
                _apply_setting(1)
            _dirty = True
        elif button == BUTTON_CENTER:
            inp.reset()
            if _set_row == 4:
                _apply_setting(0)
                _dirty = True
            elif _set_row == 5:
                _state = ST_MENU
                _make_menu(view_manager)
                return
            else:
                _apply_setting(1)
                _dirty = True
        elif button == BUTTON_BACK:
            inp.reset()
            _state = ST_MENU
            _make_menu(view_manager)
            return
        if _dirty:
            _draw_settings(draw)
            _dirty = False

    elif _state == ST_HELP:
        if _help_box is None:
            _make_help(view_manager)
        if button in (BUTTON_BACK,):
            inp.reset()
            _kill_menu("help")
            _state = ST_MENU
            _make_menu(view_manager)
        elif button == BUTTON_UP:
            inp.reset()
            _help_box.scroll_up()
        elif button == BUTTON_DOWN:
            inp.reset()
            _help_box.scroll_down()

    elif _state == ST_INPUT:
        kb = view_manager.keyboard
        if button == BUTTON_BACK:
            inp.reset()
            kb.reset()
            _state = ST_MENU
            _make_menu(view_manager)
        elif not kb.run():
            inp.reset()
            kb.reset()
            _state = ST_MENU
            _make_menu(view_manager)
        elif kb.is_finished:
            result = (kb.response or "").strip()
            kb.reset()
            inp.reset()
            if result:
                _expr = result
                _need_eval = True
                _goto_plot(view_manager)
            else:
                _state = ST_MENU
                _make_menu(view_manager)

    elif _state == ST_INPUT2:
        kb = view_manager.keyboard
        if button == BUTTON_BACK:
            inp.reset()
            kb.reset()
            _state = ST_MENU
            _make_menu(view_manager)
        elif not kb.run():
            inp.reset()
            kb.reset()
            _state = ST_MENU
            _make_menu(view_manager)
        elif kb.is_finished:
            result = (kb.response or "").strip()
            kb.reset()
            inp.reset()
            _expr2 = result
            _need_eval = True
            if result:
                _goto_plot(view_manager)
            else:
                _zs2 = None
                _state = ST_MENU
                _make_menu(view_manager)

    elif _state == ST_ERROR:
        if _dirty:
            _draw_error(draw)
            _dirty = False
        if button == BUTTON_BACK:
            inp.reset()
            _state = ST_MENU
            _make_menu(view_manager)
        elif button == BUTTON_CENTER:
            inp.reset()
            _state = ST_INPUT
            _begin_input(view_manager, False)

    elif _state == ST_SLICE:
        n = _grid_n
        if button == BUTTON_BACK:
            inp.reset()
            _state = ST_PLOT
            _dirty = True
        elif button == BUTTON_C:
            inp.reset()
            _slice_axis = 1 - _slice_axis
            _dirty = True
        elif button == BUTTON_LEFT:
            inp.reset()
            _slice_idx -= 1
            if _slice_idx < 0:
                _slice_idx = 0
            _dirty = True
        elif button == BUTTON_RIGHT:
            inp.reset()
            _slice_idx += 1
            if _slice_idx > n - 1:
                _slice_idx = n - 1
            _dirty = True
        elif button == BUTTON_P:
            inp.reset()
            _take_shot(view_manager)
        if _dirty:
            _layout(draw)
            _draw_slice(draw)
            _dirty = False

    elif _state == ST_PLOT:
        moved = False
        if button == BUTTON_BACK:
            inp.reset()
            _auto = False
            _state = ST_MENU
            _make_menu(view_manager)
            return
        if button == BUTTON_LEFT:
            inp.reset()
            _yaw -= 0.16
            moved = True
        elif button == BUTTON_RIGHT:
            inp.reset()
            _yaw += 0.16
            moved = True
        elif button == BUTTON_UP:
            inp.reset()
            _pitch += 0.11
            if _pitch > 1.40:
                _pitch = 1.40
            moved = True
        elif button == BUTTON_DOWN:
            inp.reset()
            _pitch -= 0.11
            if _pitch < -0.15:
                _pitch = -0.15
            moved = True
        elif button in (BUTTON_PLUS, BUTTON_EQUAL):
            inp.reset()
            _zoom *= 1.12
            if _zoom > 3.0:
                _zoom = 3.0
            moved = True
        elif button == BUTTON_MINUS:
            inp.reset()
            _zoom *= 0.89
            if _zoom < 0.38:
                _zoom = 0.38
            moved = True
        elif button in (BUTTON_A, BUTTON_START):
            inp.reset()
            _auto = not _auto
            moved = True
        elif button == BUTTON_W:
            inp.reset()
            _style = 0
            moved = True
        elif button == BUTTON_S:
            inp.reset()
            _style = 1
            moved = True
        elif button == BUTTON_R:
            inp.reset()
            _pitch = 0.55
            _yaw = 0.70
            _zoom = 1.0
            _auto = False
            moved = True
        elif button in (BUTTON_H, BUTTON_QUESTION):
            inp.reset()
            _auto = False
            _state = ST_HELP
            _make_help(view_manager)
            return
        elif button == BUTTON_CENTER:
            inp.reset()
            _auto = False
            _state = ST_INPUT
            _begin_input(view_manager, False)
            return
        elif button == BUTTON_C:
            inp.reset()
            _auto = False
            _slice_idx = _grid_n // 2
            _state = ST_SLICE
            _dirty = True
            return
        elif button == BUTTON_P:
            inp.reset()
            _take_shot(view_manager)
            moved = True
        elif button == BUTTON_G:
            inp.reset()
            _grid_n = int(_cycle(GRIDS, float(_grid_n), 1))
            _need_eval = True
            _goto_plot(view_manager)
            return
        elif button in (BUTTON_Z, BUTTON_SPACE):
            inp.reset()
            _range = _cycle(RANGES, _range, 1)
            _need_eval = True
            _goto_plot(view_manager)
            return

        if _auto:
            _yaw += 0.040
            moved = True

        if moved or _dirty:
            _layout(draw)
            _draw_plot(draw)
            _dirty = False


def stop(view_manager) -> None:
    global _menu, _preset_menu, _help_box, _zs
    global _state, _auto, _dirty

    global _saved_menu, _zs2
    if _menu:
        del _menu
        _menu = None
    if _preset_menu:
        del _preset_menu
        _preset_menu = None
    if _help_box:
        del _help_box
        _help_box = None
    if _saved_menu:
        del _saved_menu
        _saved_menu = None
    _zs = None
    _zs2 = None
    _auto = False
    _dirty = True
    _state = ST_MENU
    try:
        view_manager.keyboard.reset()
    except Exception:
        pass
    collect()