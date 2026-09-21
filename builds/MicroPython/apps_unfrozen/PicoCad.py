# picoware/apps/CAD3D.py
# Mini 3D CAD for PicoCalc / Picoware
# Primitives, snap, orbit / move / scale / rotate, save + screenshot.

from micropython import const
from math import sin, cos, sqrt, pi
from gc import collect

from picoware.system.vector import Vector
from picoware.system.font import FONT_SMALL, FONT_MEDIUM
from picoware.system.buttons import (
    BUTTON_BACK,
    BUTTON_LEFT,
    BUTTON_RIGHT,
    BUTTON_UP,
    BUTTON_DOWN,
    BUTTON_CENTER,
    BUTTON_PLUS,
    BUTTON_MINUS,
    BUTTON_EQUAL,
    BUTTON_A,
    BUTTON_C,
    BUTTON_D,
    BUTTON_E,
    BUTTON_G,
    BUTTON_H,
    BUTTON_L,
    BUTTON_M,
    BUTTON_N,
    BUTTON_O,
    BUTTON_P,
    BUTTON_R,
    BUTTON_S,
    BUTTON_T,
    BUTTON_W,
    BUTTON_X,
    BUTTON_Y,
    BUTTON_Z,
    BUTTON_TAB,
    BUTTON_QUESTION,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    BUTTON_5,
)

ST_MENU = const(0)
ST_WORK = const(1)
ST_ADD = const(2)
ST_HELP = const(3)
ST_FILES = const(4)
ST_LIST = const(5)

MD_ORBIT = const(0)
MD_MOVE = const(1)
MD_SCALE = const(2)
MD_ROT = const(3)
MD_NAMES = ("ORBIT", "MOVE", "SCALE", "ROTATE")

KIND_BOX = const(0)
KIND_CYL = const(1)
KIND_WEDGE = const(2)
KIND_PYR = const(3)
KIND_PLATE = const(4)
KIND_NAMES = ("Box", "Cylinder", "Wedge", "Pyramid", "Plate")

C_BG = const(0x0862)
C_PLOT = const(0x0841)
C_PANEL = const(0x10A4)
C_FRAME = const(0x3C9A)
C_ACCENT = const(0x07FF)
C_AMBER = const(0xFD20)
C_TITLE = const(0xFFFF)
C_MUTED = const(0x7BEF)
C_DIM = const(0x4208)
C_ERR = const(0xF800)
C_OK = const(0x07E8)
C_GRID = const(0x1CE7)
C_SEL = const(0xFFE0)
C_AXIS_X = const(0xF800)
C_AXIS_Y = const(0x07E0)
C_AXIS_Z = const(0x051F)
C_WIRE = const(0x7BEF)

HEAD_H = const(22)
FOOT_H = const(40)
MAX_PARTS = const(10)
SNAP = 0.5
DIR_APP = "picoware/cad3d"

PALETTE = (
    0x7D9C,  # steel
    0xFD20,  # amber
    0x07FF,  # cyan
    0xAFE5,  # mint
    0xFC9F,  # pink
    0xFBE4,  # sand
    0x3C9A,  # slate
    0xFDA0,  # orange
)

_state = ST_MENU
_menu = None
_add_menu = None
_file_menu = None
_list_menu = None
_help_box = None
_dirty = True
_parts = []
_sel = 0
_mode = MD_ORBIT
_style = 1  # 0 wire  1 mesh  2 solid
_pitch = 0.55
_yaw = 0.70
_zoom = 1.0
_toast = ""
_storage = None
_sw = 320
_sh = 320
_cx = 160
_cy = 150
_focal = 220.0
_cam = 11.0
_px0 = 0
_py0 = 0
_px1 = 320
_py1 = 320
_file_mode = 0  # 0 save  1 load
_next_id = 1


def _clamp(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _snap(v):
    return round(v / SNAP) * SNAP


def _rgb_mul(col, s):
    r = ((col >> 11) & 0x1F) * 255 // 31
    g = ((col >> 5) & 0x3F) * 255 // 63
    b = (col & 0x1F) * 255 // 31
    r = int(_clamp(r * s, 0, 255))
    g = int(_clamp(g * s, 0, 255))
    b = int(_clamp(b * s, 0, 255))
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def _new_part(kind, x=0.0, y=0.0, z=0.5):
    global _next_id
    sx, sy, sz = 1.0, 1.0, 1.0
    if kind == KIND_CYL:
        sx, sy, sz = 0.7, 0.7, 1.2
    elif kind == KIND_PLATE:
        sx, sy, sz = 3.0, 3.0, 0.12
        z = 0.06
    elif kind == KIND_WEDGE:
        sx, sy, sz = 1.4, 0.8, 0.8
    elif kind == KIND_PYR:
        sx, sy, sz = 1.2, 1.2, 1.2
    p = {
        "id": _next_id,
        "kind": kind,
        "x": _snap(x),
        "y": _snap(y),
        "z": _snap(z) if kind != KIND_PLATE else z,
        "sx": sx,
        "sy": sy,
        "sz": sz,
        "yaw": 0.0,
        "col": PALETTE[_next_id % len(PALETTE)],
    }
    _next_id += 1
    return p


def _part_name(p):
    return "{} {}".format(KIND_NAMES[p["kind"]], p["id"])


def _default_scene():
    global _parts, _sel, _next_id
    _next_id = 1
    _parts = [
        _new_part(KIND_PLATE, 0, 0, 0.06),
        _new_part(KIND_BOX, 0, 0, 0.6),
    ]
    _sel = 1


# ---------------------------------------------------------------------------
# Mesh builders — local space, then scale / yaw / translate
# ---------------------------------------------------------------------------
def _xf_part(p, x, y, z):
    x *= p["sx"]
    y *= p["sy"]
    z *= p["sz"]
    c = cos(p["yaw"])
    s = sin(p["yaw"])
    xr = x * c - y * s
    yr = x * s + y * c
    return (xr + p["x"], yr + p["y"], z + p["z"])


def _box_tris(p):
    # unit cube -0.5..0.5
    v = (
        _xf_part(p, -0.5, -0.5, -0.5),
        _xf_part(p, 0.5, -0.5, -0.5),
        _xf_part(p, 0.5, 0.5, -0.5),
        _xf_part(p, -0.5, 0.5, -0.5),
        _xf_part(p, -0.5, -0.5, 0.5),
        _xf_part(p, 0.5, -0.5, 0.5),
        _xf_part(p, 0.5, 0.5, 0.5),
        _xf_part(p, -0.5, 0.5, 0.5),
    )
    faces = (
        (0, 1, 2),
        (0, 2, 3),
        (4, 6, 5),
        (4, 7, 6),
        (0, 4, 5),
        (0, 5, 1),
        (1, 5, 6),
        (1, 6, 2),
        (2, 6, 7),
        (2, 7, 3),
        (3, 7, 4),
        (3, 4, 0),
    )
    return [(v[a], v[b], v[c]) for a, b, c in faces]


def _cyl_tris(p):
    n = 8
    bot = []
    top = []
    for i in range(n):
        a = (2.0 * pi * i) / n
        bot.append(_xf_part(p, 0.5 * cos(a), 0.5 * sin(a), -0.5))
        top.append(_xf_part(p, 0.5 * cos(a), 0.5 * sin(a), 0.5))
    bc = _xf_part(p, 0, 0, -0.5)
    tc = _xf_part(p, 0, 0, 0.5)
    out = []
    for i in range(n):
        j = (i + 1) % n
        out.append((bot[i], bot[j], top[j]))
        out.append((bot[i], top[j], top[i]))
        out.append((bc, bot[j], bot[i]))
        out.append((tc, top[i], top[j]))
    return out


def _wedge_tris(p):
    # prism pointing +X
    v = (
        _xf_part(p, -0.5, -0.5, -0.5),
        _xf_part(p, 0.5, 0.0, -0.5),
        _xf_part(p, -0.5, 0.5, -0.5),
        _xf_part(p, -0.5, -0.5, 0.5),
        _xf_part(p, 0.5, 0.0, 0.5),
        _xf_part(p, -0.5, 0.5, 0.5),
    )
    faces = (
        (0, 1, 2),
        (3, 5, 4),
        (0, 3, 4),
        (0, 4, 1),
        (1, 4, 5),
        (1, 5, 2),
        (2, 5, 3),
        (2, 3, 0),
    )
    return [(v[a], v[b], v[c]) for a, b, c in faces]


def _pyr_tris(p):
    v = (
        _xf_part(p, -0.5, -0.5, -0.5),
        _xf_part(p, 0.5, -0.5, -0.5),
        _xf_part(p, 0.5, 0.5, -0.5),
        _xf_part(p, -0.5, 0.5, -0.5),
        _xf_part(p, 0.0, 0.0, 0.5),
    )
    faces = (
        (0, 2, 1),
        (0, 3, 2),
        (0, 1, 4),
        (1, 2, 4),
        (2, 3, 4),
        (3, 0, 4),
    )
    return [(v[a], v[b], v[c]) for a, b, c in faces]


def _mesh_of(p):
    k = p["kind"]
    if k == KIND_CYL:
        return _cyl_tris(p)
    if k == KIND_WEDGE:
        return _wedge_tris(p)
    if k == KIND_PYR:
        return _pyr_tris(p)
    return _box_tris(p)


# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------
def _layout(draw):
    global _sw, _sh, _cx, _cy, _focal, _cam, _px0, _py0, _px1, _py1
    _sw = int(draw.size.x)
    _sh = int(draw.size.y)
    _px0 = 6
    _py0 = HEAD_H + 2
    _px1 = _sw - 7
    _py1 = _sh - FOOT_H - 2
    _cx = (_px0 + _px1) // 2
    _cy = (_py0 + _py1) // 2 + 6
    short = min(_px1 - _px0, _py1 - _py0)
    _focal = short * 0.82
    _cam = 10.5


def _xform(x, z_up, y_depth):
    cy = cos(_yaw)
    sy = sin(_yaw)
    x1 = x * cy - y_depth * sy
    z1 = x * sy + y_depth * cy
    cp = cos(_pitch)
    sp = sin(_pitch)
    y2 = z_up * cp - z1 * sp
    z2 = z_up * sp + z1 * cp
    zc = _cam - z2
    if zc < 0.4:
        return None
    s = (_focal * _zoom) / zc
    sx = int(_cx + x1 * s)
    sy = int(_cy - y2 * s)
    return (sx, sy, zc, x1, y2, z2)


def _pt_ok(p):
    if p is None:
        return False
    if p[0] < _px0 - 50 or p[0] > _px1 + 50:
        return False
    if p[1] < _py0 - 50 or p[1] > _py1 + 50:
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
    x0, y0 = a[0], a[1]
    x1, y1 = b[0], b[1]
    c0 = _outcode(x0, y0)
    c1 = _outcode(x1, y1)
    xmin, xmax, ymin, ymax = _px0, _px1, _py0, _py1
    while True:
        if not (c0 | c1):
            draw.line_custom(Vector(int(x0), int(y0)), Vector(int(x1), int(y1)), color)
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


def _shade(p0, p1, p2):
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
    nd = (nx * 0.28 + ny * 0.86 + nz * 0.22) / ln
    if nd < 0.0:
        nd = -nd
    return 0.34 + 0.66 * nd


def _area2(p0, p1, p2):
    return (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p2[0] - p0[0]) * (p1[1] - p0[1])


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
def _ensure_dir(storage):
    if not storage:
        return False
    try:
        if not storage.exists("picoware"):
            storage.mkdir("picoware")
        if not storage.exists(DIR_APP):
            storage.mkdir(DIR_APP)
        return True
    except Exception:
        return False


def _list_models(storage):
    names = []
    if not storage or not _ensure_dir(storage):
        return names
    try:
        items = storage.listdir(DIR_APP)
    except Exception:
        items = []
    if items:
        for name in items:
            n = str(name)
            if n.endswith(".cad") or n.endswith(".txt"):
                names.append(n)
    names.sort()
    return names


def _save_model(storage, name):
    if not storage or not _ensure_dir(storage):
        return False
    path = DIR_APP + "/" + name
    lines = ["# PicoCAD", "v1"]
    for p in _parts:
        lines.append(
            "{} {} {:.4g} {:.4g} {:.4g} {:.4g} {:.4g} {:.4g} {:.4g} {}".format(
                KIND_NAMES[p["kind"]].upper(),
                p["id"],
                p["x"],
                p["y"],
                p["z"],
                p["sx"],
                p["sy"],
                p["sz"],
                p["yaw"],
                int(p["col"]),
            )
        )
    try:
        storage.write(path, "\n".join(lines) + "\n", "w")
        return True
    except Exception:
        return False


def _load_model(storage, name):
    global _parts, _sel, _next_id
    path = DIR_APP + "/" + name
    try:
        raw = storage.read(path, "r")
    except Exception:
        return False
    if not raw:
        return False
    kind_map = {
        "BOX": KIND_BOX,
        "CYLINDER": KIND_CYL,
        "CYL": KIND_CYL,
        "WEDGE": KIND_WEDGE,
        "PYRAMID": KIND_PYR,
        "PYR": KIND_PYR,
        "PLATE": KIND_PLATE,
    }
    parts = []
    max_id = 0
    for line in str(raw).split("\n"):
        line = line.strip()
        if not line or line[0] == "#" or line == "v1":
            continue
        bits = line.split()
        if len(bits) < 10:
            continue
        k = kind_map.get(bits[0], None)
        if k is None:
            continue
        try:
            pid = int(bits[1])
            p = {
                "id": pid,
                "kind": k,
                "x": float(bits[2]),
                "y": float(bits[3]),
                "z": float(bits[4]),
                "sx": float(bits[5]),
                "sy": float(bits[6]),
                "sz": float(bits[7]),
                "yaw": float(bits[8]),
                "col": int(bits[9]),
            }
        except Exception:
            continue
        parts.append(p)
        if pid > max_id:
            max_id = pid
    if not parts:
        return False
    _parts = parts
    _sel = 0
    _next_id = max_id + 1
    return True


def _next_name(storage, prefix, ext):
    n = 1
    while n < 100:
        name = "{}{:02d}{}".format(prefix, n, ext)
        path = DIR_APP + "/" + name
        try:
            if not storage.exists(path):
                return name
        except Exception:
            return name
        n += 1
    return prefix + "99" + ext


# ---------------------------------------------------------------------------
# Draw
# ---------------------------------------------------------------------------
def _paint_chrome(draw, subtitle, f1, f2):
    draw.fill_rectangle(Vector(0, 0), Vector(_sw, HEAD_H), C_PANEL)
    draw.fill_rectangle(Vector(0, 0), Vector(_sw, 2), C_ACCENT)
    draw.text(Vector(6, 5), "CAD 3D", C_ACCENT, FONT_SMALL)
    if subtitle:
        draw.text(Vector(70, 5), subtitle, C_TITLE, FONT_SMALL)
    fy = _sh - FOOT_H
    draw.fill_rectangle(Vector(0, fy), Vector(_sw, FOOT_H), C_PANEL)
    draw.fill_rectangle(Vector(0, fy), Vector(_sw, 1), C_FRAME)
    if f1:
        draw.text(Vector(6, fy + 5), f1, C_ACCENT, FONT_SMALL)
    if f2:
        draw.text(Vector(6, fy + 22), f2, C_MUTED, FONT_SMALL)


def _draw_gizmo(draw):
    ox = _px0 + 20
    oy = _py0 + 20
    L = 16
    cy, sy = cos(_yaw), sin(_yaw)
    cp, sp = cos(_pitch), sin(_pitch)

    def tip(x, z_up, y_d):
        x1 = x * cy - y_d * sy
        z1 = x * sy + y_d * cy
        y2 = z_up * cp - z1 * sp
        return ox + int(x1 * L), oy - int(y2 * L)

    for vec, col, ch in (
        ((1, 0, 0), C_AXIS_X, "X"),
        ((0, 0, 1), C_AXIS_Y, "Y"),
        ((0, 1, 0), C_AXIS_Z, "Z"),
    ):
        tx, ty = tip(vec[0], vec[1], vec[2])
        draw.line_custom(Vector(ox, oy), Vector(tx, ty), col)
        draw.text(Vector(tx + 2, ty - 4), ch, col, FONT_SMALL)


def _draw_grid(draw):
    lim = 4
    step = 1.0
    g = -lim
    while g <= lim + 0.01:
        a = _xform(-lim, 0.0, g)
        b = _xform(lim, 0.0, g)
        c = _xform(g, 0.0, -lim)
        d = _xform(g, 0.0, lim)
        col = C_FRAME if abs(g) < 0.01 else C_GRID
        _clip_line(draw, a, b, col)
        _clip_line(draw, c, d, col)
        g += step


def _collect_faces():
    faces = []
    for pi, p in enumerate(_parts):
        tris = _mesh_of(p)
        for t in tris:
            q0 = _xform(t[0][0], t[0][2], t[0][1])
            q1 = _xform(t[1][0], t[1][2], t[1][1])
            q2 = _xform(t[2][0], t[2][2], t[2][1])
            if not (_pt_ok(q0) and _pt_ok(q1) and _pt_ok(q2)):
                continue
            if abs(_area2(q0, q1, q2)) < 2:
                continue
            depth = q0[2] + q1[2] + q2[2]
            faces.append((depth, q0, q1, q2, p["col"], pi))
    faces.sort(key=lambda f: f[0], reverse=True)
    return faces


def _draw_work(draw):
    global _toast
    draw.fill_screen(C_BG)
    draw.fill_rectangle(
        Vector(_px0, _py0),
        Vector(_px1 - _px0 + 1, _py1 - _py0 + 1),
        C_PLOT,
    )
    _draw_grid(draw)
    faces = _collect_faces()

    if _style >= 1:
        for depth, a, b, c, col, pi in faces:
            sh = _shade(a, b, c)
            if pi == _sel:
                sh = _clamp(sh * 1.12 + 0.08, 0.2, 1.0)
            draw.fill_triangle(
                Vector(a[0], a[1]),
                Vector(b[0], b[1]),
                Vector(c[0], c[1]),
                _rgb_mul(col, sh),
            )

    if _style == 0:
        for depth, a, b, c, col, pi in faces:
            w = C_SEL if pi == _sel else col
            _clip_line(draw, a, b, w)
            _clip_line(draw, b, c, w)
            _clip_line(draw, c, a, w)
    elif _style == 1:
        for depth, a, b, c, col, pi in faces:
            w = C_SEL if pi == _sel else C_WIRE
            _clip_line(draw, a, b, w)
            _clip_line(draw, b, c, w)
            _clip_line(draw, c, a, w)

    # selected origin mark
    if _parts:
        p = _parts[_sel]
        o = _xform(p["x"], p["z"], p["y"])
        if _pt_ok(o):
            draw.fill_circle(Vector(o[0], o[1]), 3, C_SEL)

    _draw_gizmo(draw)
    draw.rect(Vector(_px0, _py0), Vector(_px1 - _px0, _py1 - _py0), C_FRAME)

    n = len(_parts)
    if n == 0:
        name = "(empty)"
    else:
        p = _parts[_sel]
        name = _part_name(p)
    sub = _toast if _toast else name
    f1 = "{}   {}/{}   {}".format(MD_NAMES[_mode], _sel + 1 if n else 0, n, STY(_style))
    if n:
        p = _parts[_sel]
        f1 = "{}  {}  {:.1f},{:.1f},{:.1f}".format(
            MD_NAMES[_mode], name, p["x"], p["y"], p["z"]
        )
    f2 = "O orbit  G move  T scale  Y rot   N add  TAB next"
    _paint_chrome(draw, sub, f1, f2)
    draw.swap()
    if _toast:
        _toast = ""


def STY(s):
    return ("WIRE", "MESH", "SOLID")[s] if 0 <= s <= 2 else "?"


def _kill(which):
    global _menu, _add_menu, _file_menu, _list_menu, _help_box
    if which == "menu" and _menu:
        del _menu
        _menu = None
    elif which == "add" and _add_menu:
        del _add_menu
        _add_menu = None
    elif which == "file" and _file_menu:
        del _file_menu
        _file_menu = None
    elif which == "list" and _list_menu:
        del _list_menu
        _list_menu = None
    elif which == "help" and _help_box:
        del _help_box
        _help_box = None


def _make_menu(vm):
    global _menu
    from picoware.gui.menu import Menu

    _kill("menu")
    draw = vm.draw
    _menu = Menu(
        draw,
        "CAD 3D",
        0,
        draw.size.y,
        vm.foreground_color,
        vm.background_color,
        vm.selected_color,
        vm.foreground_color,
    )
    _menu.add_item("Workspace")
    _menu.add_item("Add part")
    _menu.add_item("Parts list")
    _menu.add_item("Save model")
    _menu.add_item("Load model")
    _menu.add_item("New scene")
    _menu.add_item("Help")
    _menu.add_item("Quit")
    _menu.set_selected(0)


def _make_add(vm):
    global _add_menu
    from picoware.gui.menu import Menu

    _kill("add")
    draw = vm.draw
    _add_menu = Menu(
        draw,
        "Add part",
        0,
        draw.size.y,
        vm.foreground_color,
        vm.background_color,
        vm.selected_color,
        vm.foreground_color,
    )
    for name in KIND_NAMES:
        _add_menu.add_item(name)
    _add_menu.set_selected(0)


def _make_files(vm, saving):
    global _file_menu, _file_mode
    from picoware.gui.menu import Menu

    _kill("file")
    _file_mode = 0 if saving else 1
    draw = vm.draw
    title = "Save   ENTER writes" if saving else "Load   ENTER opens"
    _file_menu = Menu(
        draw,
        title,
        0,
        draw.size.y,
        vm.foreground_color,
        vm.background_color,
        vm.selected_color,
        vm.foreground_color,
    )
    if saving:
        _file_menu.add_item("Save as new file")
    names = _list_models(_storage)
    if names:
        for n in names:
            _file_menu.add_item(n)
    elif not saving:
        _file_menu.add_item("(no models)")
    _file_menu.set_selected(0)


def _make_list(vm):
    global _list_menu
    from picoware.gui.menu import Menu

    _kill("list")
    draw = vm.draw
    _list_menu = Menu(
        draw,
        "Parts   ENTER select",
        0,
        draw.size.y,
        vm.foreground_color,
        vm.background_color,
        vm.selected_color,
        vm.foreground_color,
    )
    if not _parts:
        _list_menu.add_item("(empty)")
    else:
        for p in _parts:
            _list_menu.add_item(_part_name(p))
    _list_menu.set_selected(_sel if _parts else 0)


def _make_help(vm):
    global _help_box
    from picoware.gui.textbox import TextBox

    _kill("help")
    draw = vm.draw
    _help_box = TextBox(
        draw,
        0,
        draw.size.y,
        vm.foreground_color,
        vm.background_color,
    )
    _help_box.set_text(
        "CAD 3D\n"
        "Small solid modeler.\n"
        "Not Fusion. On purpose.\n"
        "\n"
        "MODES\n"
        "  O   orbit camera\n"
        "  G   grab / move part\n"
        "  T   scale part\n"
        "  Y   yaw / rotate part\n"
        "  Arrows act on the mode.\n"
        "  In MOVE, +/- is Z.\n"
        "  In SCALE, +/- is height.\n"
        "\n"
        "PARTS\n"
        "  N or 1-5   add\n"
        "  TAB/ENTER  next part\n"
        "  D          duplicate\n"
        "  X          delete\n"
        "  C          next color\n"
        "  W / S      style\n"
        "\n"
        "FILE\n"
        "  P   screenshot\n"
        "  E   save model\n"
        "  L   load model\n"
        "  files in picoware/cad3d/\n"
        "\n"
        "VIEW\n"
        "  + - zoom   R reset cam\n"
        "  Z-up world, snap 0.5\n"
        "  Max 10 parts.\n"
        "\n"
        "BACK is the menu."
    )


def _add_kind(kind):
    global _sel, _toast
    if len(_parts) >= MAX_PARTS:
        _toast = "max {} parts".format(MAX_PARTS)
        return False
    # drop near selected, or origin
    x = y = 0.0
    z = 0.6
    if _parts:
        s = _parts[_sel]
        x = s["x"] + 1.5
        y = s["y"]
        z = s["z"]
    p = _new_part(kind, x, y, z)
    if kind == KIND_PLATE:
        p["z"] = 0.06
    _parts.append(p)
    _sel = len(_parts) - 1
    _toast = "added " + _part_name(p)
    return True


def _dup_sel():
    global _sel, _toast
    if not _parts or len(_parts) >= MAX_PARTS:
        _toast = "can't duplicate"
        return
    src = _parts[_sel]
    p = _new_part(src["kind"], src["x"] + 1.0, src["y"], src["z"])
    p["sx"] = src["sx"]
    p["sy"] = src["sy"]
    p["sz"] = src["sz"]
    p["yaw"] = src["yaw"]
    p["col"] = src["col"]
    _parts.append(p)
    _sel = len(_parts) - 1
    _toast = "copied " + _part_name(p)


def _del_sel():
    global _sel, _toast
    if not _parts:
        return
    name = _part_name(_parts[_sel])
    _parts.pop(_sel)
    if _sel >= len(_parts):
        _sel = max(0, len(_parts) - 1)
    _toast = "deleted " + name


def _cycle_sel(step):
    global _sel
    n = len(_parts)
    if n == 0:
        return
    _sel = (_sel + step) % n


def _apply_arrows(dx, dy):
    if not _parts:
        return
    p = _parts[_sel]
    if _mode == MD_ORBIT:
        return False
    if _mode == MD_MOVE:
        p["x"] = _snap(p["x"] + dx * SNAP)
        p["y"] = _snap(p["y"] + dy * SNAP)
    elif _mode == MD_SCALE:
        p["sx"] = _clamp(p["sx"] + dx * 0.25, 0.25, 8.0)
        p["sy"] = _clamp(p["sy"] + dy * 0.25, 0.25, 8.0)
    elif _mode == MD_ROT:
        p["yaw"] += dx * (pi / 12.0)
    return True


def _apply_plus(sign):
    global _zoom
    if _mode == MD_ORBIT:
        if sign > 0:
            _zoom = _clamp(_zoom * 1.12, 0.35, 3.2)
        else:
            _zoom = _clamp(_zoom * 0.89, 0.35, 3.2)
        return
    if not _parts:
        return
    p = _parts[_sel]
    if _mode == MD_MOVE:
        p["z"] = _snap(p["z"] + sign * SNAP)
    elif _mode == MD_SCALE:
        p["sz"] = _clamp(p["sz"] + sign * 0.25, 0.12, 8.0)
    elif _mode == MD_ROT:
        p["yaw"] += sign * (pi / 12.0)


def _reset_cam():
    global _pitch, _yaw, _zoom
    _pitch = 0.55
    _yaw = 0.70
    _zoom = 1.0


def _goto_work(vm):
    global _state, _dirty
    _layout(vm.draw)
    _state = ST_WORK
    _dirty = True


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
def start(view_manager) -> bool:
    global _state, _dirty, _menu, _add_menu, _file_menu, _list_menu, _help_box
    global _storage, _toast, _mode, _style, _sel

    _storage = view_manager.storage
    _ensure_dir(_storage)
    _layout(view_manager.draw)
    _default_scene()
    _mode = MD_ORBIT
    _style = 1
    _toast = ""
    _dirty = True
    _state = ST_MENU
    _menu = None
    _add_menu = None
    _file_menu = None
    _list_menu = None
    _help_box = None
    view_manager.input_manager.reset()
    _make_menu(view_manager)
    return True


def run(view_manager) -> None:
    global _state, _dirty, _mode, _style, _pitch, _yaw, _zoom
    global _toast, _sel, _file_mode

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
                _goto_work(view_manager)
            elif idx == 1:
                _state = ST_ADD
                _make_add(view_manager)
            elif idx == 2:
                _state = ST_LIST
                _make_list(view_manager)
            elif idx == 3:
                _state = ST_FILES
                _make_files(view_manager, True)
            elif idx == 4:
                _state = ST_FILES
                _make_files(view_manager, False)
            elif idx == 5:
                _default_scene()
                _toast = "new scene"
                _goto_work(view_manager)
            elif idx == 6:
                _state = ST_HELP
                _make_help(view_manager)
            elif idx == 7:
                view_manager.back()

    elif _state == ST_ADD:
        if _add_menu is None:
            _make_add(view_manager)
        if button == BUTTON_UP:
            inp.reset()
            _add_menu.scroll_up()
        elif button == BUTTON_DOWN:
            inp.reset()
            _add_menu.scroll_down()
        elif button == BUTTON_BACK:
            inp.reset()
            _kill("add")
            _state = ST_MENU
            _make_menu(view_manager)
        elif button == BUTTON_CENTER:
            inp.reset()
            _add_kind(_add_menu.selected_index)
            _kill("add")
            _goto_work(view_manager)

    elif _state == ST_LIST:
        if _list_menu is None:
            _make_list(view_manager)
        if button == BUTTON_UP:
            inp.reset()
            _list_menu.scroll_up()
        elif button == BUTTON_DOWN:
            inp.reset()
            _list_menu.scroll_down()
        elif button == BUTTON_BACK:
            inp.reset()
            _kill("list")
            _state = ST_MENU
            _make_menu(view_manager)
        elif button == BUTTON_CENTER:
            inp.reset()
            if _parts:
                _sel = _list_menu.selected_index
                if _sel < 0:
                    _sel = 0
                if _sel >= len(_parts):
                    _sel = len(_parts) - 1
            _kill("list")
            _goto_work(view_manager)

    elif _state == ST_FILES:
        if _file_menu is None:
            _make_files(view_manager, _file_mode == 0)
        if button == BUTTON_UP:
            inp.reset()
            _file_menu.scroll_up()
        elif button == BUTTON_DOWN:
            inp.reset()
            _file_menu.scroll_down()
        elif button == BUTTON_BACK:
            inp.reset()
            _kill("file")
            _state = ST_MENU
            _make_menu(view_manager)
        elif button == BUTTON_CENTER:
            inp.reset()
            idx = _file_menu.selected_index
            names = _list_models(_storage)
            if _file_mode == 0:
                if idx == 0:
                    name = _next_name(_storage, "model", ".cad")
                elif names and idx - 1 < len(names):
                    name = names[idx - 1]
                else:
                    name = _next_name(_storage, "model", ".cad")
                if _save_model(_storage, name):
                    _toast = "saved " + name
                else:
                    _toast = "save failed"
                _kill("file")
                _goto_work(view_manager)
            else:
                if names and idx < len(names):
                    if _load_model(_storage, names[idx]):
                        _toast = "loaded " + names[idx]
                    else:
                        _toast = "load failed"
                else:
                    _toast = "no models"
                _kill("file")
                _goto_work(view_manager)

    elif _state == ST_HELP:
        if _help_box is None:
            _make_help(view_manager)
        if button == BUTTON_BACK:
            inp.reset()
            _kill("help")
            _state = ST_MENU
            _make_menu(view_manager)
        elif button == BUTTON_UP:
            inp.reset()
            _help_box.scroll_up()
        elif button == BUTTON_DOWN:
            inp.reset()
            _help_box.scroll_down()

    elif _state == ST_WORK:
        moved = False
        if button == BUTTON_BACK:
            inp.reset()
            _state = ST_MENU
            _make_menu(view_manager)
            return
        if button == BUTTON_LEFT:
            inp.reset()
            if _mode == MD_ORBIT:
                _yaw -= 0.16
            else:
                _apply_arrows(-1, 0)
            moved = True
        elif button == BUTTON_RIGHT:
            inp.reset()
            if _mode == MD_ORBIT:
                _yaw += 0.16
            else:
                _apply_arrows(1, 0)
            moved = True
        elif button == BUTTON_UP:
            inp.reset()
            if _mode == MD_ORBIT:
                _pitch = _clamp(_pitch + 0.11, -0.2, 1.4)
            else:
                _apply_arrows(0, 1)
            moved = True
        elif button == BUTTON_DOWN:
            inp.reset()
            if _mode == MD_ORBIT:
                _pitch = _clamp(_pitch - 0.11, -0.2, 1.4)
            else:
                _apply_arrows(0, -1)
            moved = True
        elif button in (BUTTON_PLUS, BUTTON_EQUAL):
            inp.reset()
            _apply_plus(1)
            moved = True
        elif button == BUTTON_MINUS:
            inp.reset()
            _apply_plus(-1)
            moved = True
        elif button == BUTTON_O:
            inp.reset()
            _mode = MD_ORBIT
            moved = True
        elif button in (BUTTON_G, BUTTON_M):
            inp.reset()
            _mode = MD_MOVE
            moved = True
        elif button == BUTTON_T:
            inp.reset()
            _mode = MD_SCALE
            moved = True
        elif button == BUTTON_Y:
            inp.reset()
            _mode = MD_ROT
            moved = True
        elif button == BUTTON_TAB:
            inp.reset()
            _cycle_sel(1)
            moved = True
        elif button == BUTTON_N:
            inp.reset()
            _state = ST_ADD
            _make_add(view_manager)
            return
        elif button == BUTTON_1:
            inp.reset()
            _add_kind(KIND_BOX)
            moved = True
        elif button == BUTTON_2:
            inp.reset()
            _add_kind(KIND_CYL)
            moved = True
        elif button == BUTTON_3:
            inp.reset()
            _add_kind(KIND_WEDGE)
            moved = True
        elif button == BUTTON_4:
            inp.reset()
            _add_kind(KIND_PYR)
            moved = True
        elif button == BUTTON_5:
            inp.reset()
            _add_kind(KIND_PLATE)
            moved = True
        elif button == BUTTON_D:
            inp.reset()
            _dup_sel()
            moved = True
        elif button == BUTTON_X:
            inp.reset()
            _del_sel()
            moved = True
        elif button == BUTTON_C:
            inp.reset()
            if _parts:
                p = _parts[_sel]
                try:
                    i = PALETTE.index(p["col"])
                except Exception:
                    i = 0
                p["col"] = PALETTE[(i + 1) % len(PALETTE)]
            moved = True
        elif button == BUTTON_W:
            inp.reset()
            _style = 0
            moved = True
        elif button == BUTTON_S:
            inp.reset()
            _style = (_style + 1) % 3
            moved = True
        elif button == BUTTON_R:
            inp.reset()
            _reset_cam()
            moved = True
        elif button == BUTTON_P:
            inp.reset()
            if _ensure_dir(_storage):
                name = _next_name(_storage, "shot", ".bmp")
                try:
                    draw.screenshot(DIR_APP + "/" + name)
                    _toast = "shot " + name
                except Exception:
                    _toast = "shot failed"
            else:
                _toast = "no SD"
            moved = True
        elif button == BUTTON_E:
            inp.reset()
            _state = ST_FILES
            _make_files(view_manager, True)
            return
        elif button == BUTTON_L:
            inp.reset()
            _state = ST_FILES
            _make_files(view_manager, False)
            return
        elif button in (BUTTON_H, BUTTON_QUESTION):
            inp.reset()
            _state = ST_HELP
            _make_help(view_manager)
            return
        elif button == BUTTON_CENTER:
            inp.reset()
            _cycle_sel(1)
            moved = True

        if moved or _dirty:
            _layout(draw)
            _draw_work(draw)
            _dirty = False


def stop(view_manager) -> None:
    global _menu, _add_menu, _file_menu, _list_menu, _help_box
    global _parts, _state, _dirty
    for name in ("menu", "add", "file", "list", "help"):
        _kill(name)
    _parts = []
    _dirty = True
    _state = ST_MENU
    collect()