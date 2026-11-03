from array import array
from math import sin, cos, pi
from random import randint
import micropython
from micropython import const
from picoware.system.buttons import (
    BUTTON_BACK,
    BUTTON_UP,
    BUTTON_DOWN,
    BUTTON_LEFT,
    BUTTON_RIGHT,
    BUTTON_CENTER,
)

_W = const(64)
_H = const(64)
_N = const(_W * _H)
_W16 = const(_W << 16)
_H16 = const(_H << 16)
_GRASS = const(0)
_WATER = const(1)
_FOREST = const(2)
_ROCK = const(3)
_SNOW = const(4)
_HOUSE = const(5)
_ROAD = const(6)
_BRIDGE = const(7)
_NPC = const(8)
_SHRINE = const(9)
_BLK = bytes((0, 1, 0, 1, 1, 1, 0, 0, 1, 0))
_MAXD = 11.0
_PL = 0.66
_EYE = 1.1
_BASE = (
    (70, 150, 60),
    (50, 100, 200),
    (30, 95, 45),
    (120, 110, 100),
    (240, 245, 250),
    (170, 110, 70),
    (190, 170, 120),
    (130, 90, 50),
    (190, 170, 120),
    (190, 120, 230),
)
_SKY = (150, 190, 235)
_NAMES = (
    "Grassland",
    "River",
    "Forest",
    "Mountains",
    "Peaks",
    "Town",
    "Road",
    "Bridge",
    "Town",
    "Shrine",
)
_TOWNS = ((10, 50, "Oakhaven"), (54, 16, "Highfall"), (54, 50, "Eastmere"))
_SHRINE_POS = (12, 10)
_FOES = (("Wolf", 12, 4, 6), ("Bandit", 16, 5, 12), ("Boar", 20, 6, 9))
_DIRS = ("E", "SE", "S", "SW", "W", "NW", "N", "NE")
_TURN_SPEED = 0.18
_WALK_SPEED = 0.7
_BACK_SPEED = 0.5


def _rgb(r, g, b):
    '''Pack 8-bit channels into an RGB565 integer.'''
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


_BAR = _rgb(20, 20, 30)
_SKY_TOP = _rgb(100, 150, 225)
_SKY_LOW = _rgb(_SKY[0], _SKY[1], _SKY[2])
_WHITE = 0xFFFF
_GOLD = _rgb(250, 220, 120)
_MMC = (
    _rgb(70, 150, 60),
    _rgb(50, 100, 200),
    _rgb(30, 95, 45),
    _rgb(120, 110, 100),
    _rgb(240, 245, 250),
    _rgb(170, 110, 70),
    _rgb(190, 170, 120),
    _rgb(130, 90, 50),
    _rgb(250, 210, 60),
    _rgb(190, 120, 230),
)
_SKIN = (225, 185, 145)


def _shade(c, f):
    '''Scale an (r, g, b) tuple by f, clamped to 255. Mirrors shadeColor565.'''
    return (min(255, int(c[0] * f)), min(255, int(c[1] * f)), min(255, int(c[2] * f)))


def _box(x, y, w, h, c):
    '''One model part: center x, center y, width, height, then r, g, b.'''
    return (x, y, w, h, c[0], c[1], c[2])


def _humanoid(c, extra=()):
    '''Humanoid parts with createHumanoid proportions (total height 1.0).'''
    m = [
        _box(-0.063, 0.225, 0.09, 0.45, _shade(c, 0.55)),
        _box(0.063, 0.225, 0.09, 0.45, _shade(c, 0.55)),
        _box(0, 0.625, 0.2, 0.35, c),
        _box(-0.16, 0.675, 0.07, 0.25, _shade(c, 0.75)),
        _box(0.16, 0.675, 0.07, 0.25, _shade(c, 0.75)),
        _box(0, 0.88, 0.24, 0.24, _SKIN),
    ]
    m.extend(extra)
    return tuple(m)


def _npc_models():
    '''Return the Elder, Merchant, and Innkeeper models.'''
    elder = _humanoid(
        (110, 80, 170),
        (
            _box(0, 0.79, 0.12, 0.12, (235, 235, 235)),
            _box(-0.25, 0.5, 0.03, 0.95, (130, 90, 50)),
        ),
    )
    merchant = _humanoid(
        (60, 130, 170),
        (
            _box(0, 1.0, 0.32, 0.05, (120, 60, 40)),
            _box(0.24, 0.42, 0.13, 0.16, (150, 100, 50)),
        ),
    )
    inn = _humanoid((190, 110, 60), (_box(0, 0.5, 0.16, 0.28, (240, 240, 240)),))
    return (elder, merchant, inn)


def _foe_models():
    '''Return the Wolf, Bandit, and Boar models, in _FOES order.'''
    g = (120, 120, 130)
    wolf = (
        _box(-0.25, 0.13, 0.07, 0.26, _shade(g, 0.55)),
        _box(-0.15, 0.13, 0.07, 0.26, _shade(g, 0.55)),
        _box(0.15, 0.13, 0.07, 0.26, _shade(g, 0.55)),
        _box(0.25, 0.13, 0.07, 0.26, _shade(g, 0.55)),
        _box(-0.38, 0.46, 0.14, 0.06, _shade(g, 0.8)),
        _box(0, 0.38, 0.62, 0.24, g),
        _box(0.4, 0.5, 0.2, 0.18, _shade(g, 1.1)),
        _box(0.54, 0.46, 0.12, 0.09, _shade(g, 0.9)),
        _box(0.42, 0.63, 0.05, 0.07, _shade(g, 0.6)),
        _box(0.47, 0.53, 0.03, 0.03, (250, 220, 60)),
    )
    bandit = _humanoid(
        (140, 45, 45),
        (
            _box(0, 0.95, 0.27, 0.1, (70, 25, 25)),
            _box(0.27, 0.55, 0.03, 0.22, (200, 200, 210)),
        ),
    )
    b = (110, 70, 45)
    boar = (
        _box(-0.22, 0.1, 0.08, 0.2, _shade(b, 0.55)),
        _box(-0.1, 0.1, 0.08, 0.2, _shade(b, 0.55)),
        _box(0.14, 0.1, 0.08, 0.2, _shade(b, 0.55)),
        _box(0.26, 0.1, 0.08, 0.2, _shade(b, 0.55)),
        _box(0, 0.33, 0.6, 0.32, b),
        _box(0, 0.52, 0.4, 0.06, _shade(b, 0.6)),
        _box(0.36, 0.3, 0.22, 0.22, _shade(b, 1.1)),
        _box(0.5, 0.26, 0.08, 0.1, (200, 150, 140)),
        _box(0.47, 0.2, 0.03, 0.07, (240, 240, 230)),
        _box(0.33, 0.46, 0.06, 0.06, _shade(b, 0.6)),
        _box(0.4, 0.36, 0.03, 0.03, (250, 220, 60)),
    )
    return (wolf, bandit, boar)


def _draw_model(draw, model, ox, gy, scale):
    '''Draw a model for the battle screen: outline pass, then fill pass.'''
    rects = []
    for cx, cy, w, h, r, g, b in model:
        x0 = ox + int((cx - w * 0.5) * scale)
        x1 = ox + int((cx + w * 0.5) * scale)
        yt = gy - int((cy + h * 0.5) * scale)
        yb = gy - int((cy - h * 0.5) * scale)
        rects.append((x0, yt, max(1, x1 - x0), max(1, yb - yt), r, g, b))
    for x, y, w, h, r, g, b in rects:
        draw._fill_rectangle(x - 1, y - 1, w + 2, h + 2, _rgb(r >> 2, g >> 2, b >> 2))
    for x, y, w, h, r, g, b in rects:
        draw._fill_rectangle(x, y, w, h, _rgb(r, g, b))

_st = None


class _State:
    '''Mutable game state container.'''

    def __init__(self):
        '''Set default player and view values.'''
        self.tiles = None
        self.hts = None
        self.world = None
        self.fog = None
        self.npcs = None
        self.fm = None
        self.mmt = 4
        self.camq = None
        self.tab = None
        self.buf = None
        self.px = 10.5
        self.py = 54.5
        self.pa = -pi / 2
        self.hp = 30
        self.mhp = 30
        self.gold = 15
        self.xp = 0
        self.lvl = 1
        self.quest = 0
        self.mode = 0
        self.enemy = None
        self.msg = ("Welcome to the valley.", "Talk to the elder in Oakhaven.")
        self.last = (-1, -1)
        self.dirty = True
        self.vw = 320
        self.vh = 320
        self.fw = 6
        self.fh = 8
        self.y0 = 0
        self.vb = 0
        self.hor = 0
        self.cw = 5
        self.foc = 240.0


def _fog_table():
    '''Build shaded, fogged colors. Returns a flat list indexed by tile, face, fog.'''
    out = []
    for r, g, b in _BASE:
        for shade in (1.0, 0.75):
            for f in range(4):
                a = f * 0.22
                out.append(
                    _rgb(
                        int(r * shade * (1 - a) + _SKY[0] * a),
                        int(g * shade * (1 - a) + _SKY[1] * a),
                        int(b * shade * (1 - a) + _SKY[2] * a),
                    )
                )
    return out


def _grid(n):
    '''Return an n by n grid of random floats.'''
    from random import random

    return [[random() for _ in range(n)] for _ in range(n)]


@micropython.native
def _sample(g, n, fx, fy):
    '''Bilinear sample of grid g at unit coordinates fx, fy. Returns a float.'''
    gx = fx * (n - 1)
    gy = fy * (n - 1)
    x0 = min(int(gx), n - 2)
    y0 = min(int(gy), n - 2)
    tx = gx - x0
    ty = gy - y0
    tx = tx * tx * (3 - 2 * tx)
    ty = ty * ty * (3 - 2 * ty)
    r0 = g[y0]
    r1 = g[y0 + 1]
    a = r0[x0] + (r0[x0 + 1] - r0[x0]) * tx
    b = r1[x0] + (r1[x0 + 1] - r1[x0]) * tx
    return a + (b - a) * ty


@micropython.native
def _river_x(y):
    '''Return the river center column for row y.'''
    return int(32 + 9 * sin(y * 0.12))


def _carve(tiles, hts, x0, y0, x1, y1):
    '''Lay a two-wide road between two points, bridging any water.'''
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i // n
        y = y0 + (y1 - y0) * i // n
        for oy in (0, 1):
            for ox in (0, 1):
                xx = x + ox
                yy = y + oy
                if 0 <= xx < _W and 0 <= yy < _H:
                    k = yy * _W + xx
                    if tiles[k] == _WATER or tiles[k] == _BRIDGE:
                        tiles[k] = _BRIDGE
                        hts[k] = 1
                    else:
                        tiles[k] = _ROAD
                        hts[k] = 0


def _town(tiles, hts, cx, cy):
    '''Flatten a site, then place the plaza, four houses, and the resident NPC.'''
    for y in range(cy - 6, cy + 7):
        for x in range(cx - 6, cx + 7):
            k = y * _W + x
            tiles[k] = _GRASS
            hts[k] = 0
    for y in range(cy - 2, cy + 3):
        for x in range(cx - 2, cx + 3):
            tiles[y * _W + x] = _ROAD
    for sx in (-1, 1):
        for sy in (-1, 1):
            for a in (3, 4):
                for b in (3, 4):
                    k = (cy + sy * b) * _W + cx + sx * a
                    tiles[k] = _HOUSE
                    hts[k] = 20
    k = cy * _W + cx
    tiles[k] = _NPC
    hts[k] = 0


@micropython.native
def _build_world(st):
    '''Generate terrain, river, roads, towns, and the shrine into the state arrays.'''
    from random import seed
    from time import ticks_ms

    seed(20260)
    ea = _grid(9)
    eb = _grid(17)
    wt = _grid(9)
    tiles = bytearray(_N)
    hts = bytearray(_N)
    for y in range(_H):
        rx = _river_x(y)
        fy = y / (_H - 1)
        for x in range(_W):
            fx = x / (_W - 1)
            e = _sample(ea, 9, fx, fy) * 0.65 + _sample(eb, 17, fx, fy) * 0.35
            e = 0.5 + (e - 0.5) * 1.3
            d = abs(x - rx)
            if d < 8:
                e *= 0.45 + d * 0.07
            k = y * _W + x
            if d <= 1:
                tiles[k] = _WATER
            elif e > 0.68:
                h = (e - 0.5) * 14
                tiles[k] = _SNOW if h > 5.0 else _ROCK
                hts[k] = min(int(h * 16), 255)
            elif e > 0.2 and e <= 0.56 and _sample(wt, 9, fx, fy) > 0.42:
                tiles[k] = _FOREST
                hts[k] = int((0.5 + ((x * 7 + y * 13) % 5) * 0.12) * 16)
            else:
                hts[k] = int(max(0.0, (e - 0.5) * 6) * 16)
    _carve(tiles, hts, _TOWNS[0][0], _TOWNS[0][1], _SHRINE_POS[0], _SHRINE_POS[1])
    for a, b in ((0, 1), (0, 2), (1, 2)):
        _carve(tiles, hts, _TOWNS[a][0], _TOWNS[a][1], _TOWNS[b][0], _TOWNS[b][1])
    for tx, ty, _name in _TOWNS:
        _town(tiles, hts, tx, ty)
    sx, sy = _SHRINE_POS
    for y in range(sy - 1, sy + 2):
        for x in range(sx - 1, sx + 2):
            tiles[y * _W + x] = _ROAD
            hts[y * _W + x] = 0
    tiles[sy * _W + sx] = _SHRINE
    hts[sy * _W + sx] = 24
    st.tiles = tiles
    st.hts = hts
    seed(ticks_ms())


def _prep(st):
    '''Build the integer step table, the packed world, and the viper buffers.

    tab layout (int32): [n, off_kf, off_fi, off_fog, ts..., kf..., fi..., fog...]
    ts  = ray distance in Q8
    kf  = focal / distance, pre-scaled so (height64 - eye64) * kf >> 8 is pixels
    fi  = fog level for that step
    buf layout (int32): [px_q16, py_q16, eye64, hor, y0, vb, rx_q8, ry_q8, ..., runs from 16]
    '''
    ts = []
    t = 0.3
    while t < _MAXD:
        ts.append(t)
        t += 0.16 + t * 0.05
    n = len(ts)
    fog = st.fog
    nf = len(fog)
    tab = array("i", [0] * (4 + n * 3 + nf))
    tab[0] = n
    tab[1] = 4 + n
    tab[2] = 4 + n * 2
    tab[3] = 4 + n * 3
    foc = st.foc
    for s in range(n):
        t = ts[s]
        tab[4 + s] = int(t * 256)
        tab[4 + n + s] = int(foc / t * 4)
        tab[4 + n * 2 + s] = int(t * 0.33)
    for j in range(nf):
        tab[4 + n * 3 + j] = fog[j]
    st.tab = tab
    st.buf = array("i", [0] * (16 + n * 3))
    st.world = st.tiles + st.hts


def _open(st, x, y):
    '''Return True if the world position is walkable.'''
    if x < 0 or y < 0 or x >= _W or y >= _H:
        return False
    return not _BLK[st.tiles[int(y) * _W + int(x)]]


def _step(st, dist):
    '''Move along the facing direction with collision. Returns True if moved.'''
    nx = st.px + cos(st.pa) * dist
    ny = st.py + sin(st.pa) * dist
    moved = False
    if _open(st, nx, st.py):
        st.px = nx
        moved = True
    if _open(st, st.px, ny):
        st.py = ny
        moved = True
    return moved


def _where(st):
    '''Return the nearest town name or the terrain label under the player.'''
    for tx, ty, name in _TOWNS:
        if abs(st.px - tx) < 7 and abs(st.py - ty) < 7:
            return name
    return _NAMES[st.tiles[int(st.py) * _W + int(st.px)]]


def _gain(st, xp, gold):
    '''Add xp and gold, applying level ups. Returns True if a level was gained.'''
    st.xp += xp
    st.gold += gold
    up = False
    while st.xp >= st.lvl * 20:
        st.xp -= st.lvl * 20
        st.lvl += 1
        st.mhp += 8
        st.hp = st.mhp
        up = True
    return up


def _respawn(st):
    '''Return the player to Oakhaven after defeat, losing half the gold.'''
    st.px = 10.5
    st.py = 54.5
    st.pa = -pi / 2
    st.hp = st.mhp
    st.gold //= 2
    st.mode = 0
    st.msg = ("You were defeated.", "You wake in Oakhaven.")


def _encounter(st):
    '''Start a battle with a random foe scaled to the player level.'''
    i = randint(0, 2)
    f = _FOES[i]
    hp = f[1] + st.lvl * 3
    st.enemy = [f[0], hp, hp, f[2] + st.lvl // 2, f[3], i]
    st.mode = 1
    st.msg = (f"A {f[0]} attacks!", "OK attack. DOWN flee.")


def _arrive(st):
    '''Handle events when the player enters a new tile.'''
    cell = (int(st.px), int(st.py))
    if cell == st.last:
        return
    st.last = cell
    tile = st.tiles[cell[1] * _W + cell[0]]
    if tile == _SHRINE and st.quest == 1:
        st.quest = 2
        st.msg = ("You take the ancient relic.", "Return it to the elder.")
    elif tile == _FOREST and randint(1, 100) <= 12:
        _encounter(st)


def _shop(st, who, cost, heal):
    '''Sell healing. who is the speaker, cost is gold, heal is hit points restored.'''
    if st.hp >= st.mhp:
        st.msg = (f"{who}: You look healthy.", "")
    elif st.gold < cost:
        st.msg = (f"{who}: That costs {cost} gold.", "You cannot afford it.")
    else:
        st.gold -= cost
        st.hp = min(st.mhp, st.hp + heal)
        st.msg = (f"{who}: Healed for {cost} gold.", "")


def _talk(st, n):
    '''Run dialogue and services for the NPC in town index n.'''
    if n == 0:
        if st.quest == 0:
            st.quest = 1
            st.msg = ("Elder: Bring the relic from", "the shrine far to the north.")
        elif st.quest == 1:
            st.msg = ("Elder: Follow the north road", "to the shrine in the peaks.")
        elif st.quest == 2:
            st.quest = 3
            up = _gain(st, 40, 60)
            st.msg = (
                "Elder: Well done. +60 gold.",
                "Level up!" if up else "The valley is safe.",
            )
        else:
            st.msg = ("Elder: The valley is at peace.", "")
    elif n == 1:
        _shop(st, "Merchant", 10, 20)
    else:
        _shop(st, "Innkeeper", 5, 999)


def _interact(st):
    '''Talk to an adjacent NPC. Always returns True so the view redraws.'''
    ix = int(st.px)
    iy = int(st.py)
    for ty in range(iy - 1, iy + 2):
        for tx in range(ix - 1, ix + 2):
            if 0 <= tx < _W and 0 <= ty < _H and st.tiles[ty * _W + tx] == _NPC:
                for n in range(3):
                    if _TOWNS[n][0] == tx and _TOWNS[n][1] == ty:
                        _talk(st, n)
                        return True
    st.msg = ("Nobody is close enough.", "")
    return True


def _battle_input(st, button):
    '''Apply a battle action for the pressed button. Returns True if state changed.'''
    e = st.enemy
    if button == BUTTON_CENTER:
        dmg = randint(3, 6) + st.lvl * 2
        e[1] -= dmg
        if e[1] <= 0:
            gold = e[4] + randint(0, 4)
            up = _gain(st, 8 + st.lvl * 3, gold)
            st.msg = (f"{e[0]} defeated. +{gold} gold.", "Level up!" if up else "Victory.")
            st.mode = 0
            return True
        line = f"You hit {e[0]} for {dmg}."
    elif button == BUTTON_DOWN:
        if randint(0, 1):
            st.msg = ("You escaped.", "")
            st.mode = 0
            return True
        line = "You could not escape."
    else:
        return False
    hit = randint(1, e[3])
    st.hp -= hit
    if st.hp <= 0:
        _respawn(st)
        return True
    st.msg = (line, f"{e[0]} hits you for {hit}.")
    return True


def _bar(draw, x, y, w, h, cur, mx, color):
    '''Draw a filled progress bar. cur and mx set the filled fraction.'''
    draw._fill_rectangle(x, y, w, h, _rgb(60, 60, 70))
    fill = w * max(0, cur) // max(1, mx)
    if fill > 0:
        draw._fill_rectangle(x, y, fill, h, color)


def _draw_battle(view_manager, st):
    '''Draw the battle screen with both health bars and the message log.'''
    draw = view_manager.draw
    w = st.vw
    fh = st.fh
    e = st.enemy
    draw._fill_rectangle(0, 0, w, st.vh, _rgb(25, 20, 30))
    draw._text(10, 10, e[0], _WHITE)
    _bar(draw, 10, 12 + fh, w - 20, 10, e[1], e[2], _rgb(200, 50, 50))
    gy = st.vh // 2 - 8
    sc = (gy - (26 + fh)) / 1.05
    draw._fill_rectangle(w // 2 - int(sc * 0.45), gy, int(sc * 0.9), 3, _rgb(10, 8, 14))
    _draw_model(draw, st.fm[e[5]], w // 2, gy, sc)
    draw._text(10, st.vh // 2, f"You  Lv {st.lvl}  HP {st.hp}/{st.mhp}", _WHITE)
    _bar(draw, 10, st.vh // 2 + fh + 2, w - 20, 10, st.hp, st.mhp, _rgb(60, 190, 80))
    draw._text(10, st.vh - fh * 4, st.msg[0], _WHITE)
    draw._text(10, st.vh - fh * 3 + 2, st.msg[1], _GOLD)
    draw._text(10, st.vh - fh - 4, "OK attack   DOWN flee", _rgb(160, 160, 170))
    draw.swap()


def _hud(view_manager, st):
    '''Draw the status bars with stats, heading, location, and messages.'''
    draw = view_manager.draw
    w = st.vw
    draw._fill_rectangle(0, 0, w, st.y0, _BAR)
    draw._fill_rectangle(0, st.vb, w, st.vh - st.vb, _BAR)
    left = f"HP {st.hp}/{st.mhp}  Lv {st.lvl}  G {st.gold}"
    right = f"{_DIRS[int(round(st.pa / (pi / 4))) % 8]} {_where(st)}"
    draw._text(3, 2, left, _WHITE)
    draw._text(w - len(right) * st.fw - 3, 2, right, _WHITE)
    mc = w // st.fw
    draw._text(3, st.vb + 3, st.msg[0][:mc], _WHITE)
    draw._text(3, st.vb + 4 + st.fh, st.msg[1][:mc], _GOLD)


def _blocked(st, nx, ny, eye):
    '''Return True if terrain hides the point (nx, ny) from the player.'''
    px = st.px
    py = st.py
    ex = nx - px
    ey = ny - py
    n = int((ex * ex + ey * ey) ** 0.5 * 2) + 1
    hts = st.hts
    for i in range(1, n):
        s = i / n
        k = int(py + ey * s) * _W + int(px + ex * s)
        if hts[k] * 0.0625 > eye + (0.9 - eye) * s:
            return True
    return False


def _draw_npcs(draw, st, dx, dy, eye):
    '''Draw visible NPC models as camera-facing billboards, far to near.'''
    vw = st.vw
    foc = st.foc
    hor = st.hor
    y0 = st.y0
    vb = st.vb
    fill = draw._fill_rectangle
    vis = []
    for nx, ny, model in st.npcs:
        ex = nx - st.px
        ey = ny - st.py
        f = ex * dx + ey * dy
        if f < 0.5 or f > _MAXD:
            continue
        sxc = vw / 2 + (-ex * dy + ey * dx) / f * foc
        if sxc < -40 or sxc > vw + 40 or _blocked(st, nx, ny, eye):
            continue
        vis.append((f, sxc, model))
    vis.sort()
    for v in range(len(vis) - 1, -1, -1):
        f, sxc, model = vis[v]
        inv = foc / f
        fa = min(3, int(f * 0.33)) * 0.22
        for cx, cy, w, h, r, g, b in model:
            x0 = int(sxc + (cx - w * 0.5) * inv)
            x1 = max(int(sxc + (cx + w * 0.5) * inv), x0 + 1)
            ya = hor - int((cy + h * 0.5 - eye) * inv)
            yb = hor - int((cy - h * 0.5 - eye) * inv)
            x0 = max(x0, 0)
            x1 = min(x1, vw)
            ya = max(ya, y0)
            yb = min(yb, vb)
            if x1 > x0 and yb > ya:
                fill(
                    x0, ya, x1 - x0, yb - ya,
                    _rgb(
                        int(r * (1 - fa) + _SKY[0] * fa),
                        int(g * (1 - fa) + _SKY[1] * fa),
                        int(b * (1 - fa) + _SKY[2] * fa),
                    ),
                )


def _minimap(draw, st):
    '''Draw a north-up minimap of the nearby tiles in the top-right corner.'''
    r = 6
    n = r * 2 + 1
    ts = st.mmt
    size = n * ts
    ox = st.vw - size - 3
    oy = st.y0 + 3
    cx = int(st.px) - r
    cy = int(st.py) - r
    tiles = st.tiles
    fill = draw._fill_rectangle
    fill(ox - 1, oy - 1, size + 2, size + 2, _WHITE)
    for j in range(n):
        ty = cy + j
        row = ty * _W
        i = 0
        while i < n:
            tx = cx + i
            if 0 <= tx < _W and 0 <= ty < _H:
                c = _MMC[tiles[row + tx]]
            else:
                c = _BAR
            k = i + 1
            while k < n:
                tx = cx + k
                if 0 <= tx < _W and 0 <= ty < _H:
                    c2 = _MMC[tiles[row + tx]]
                else:
                    c2 = _BAR
                if c2 != c:
                    break
                k += 1
            fill(ox + i * ts, oy + j * ts, (k - i) * ts, ts, c)
            i = k
    mx = ox + int((st.px - cx) * ts)
    my = oy + int((st.py - cy) * ts)
    fill(mx - 1, my - 1, 3, 3, _rgb(255, 60, 60))
    fill(mx + int(cos(st.pa) * 4), my + int(sin(st.pa) * 4), 1, 1, _WHITE)


@micropython.native
def _march(buf, world, tab):
    '''March one ray with integer math and write its draw runs into buf.

    Reads the ray and view setup from buf[0:8]. Writes (y, height, color)
    triples from buf[16]. Returns the number of runs written.
    '''
    n = int(tab[0])
    okf = int(tab[1])
    ofi = int(tab[2])
    ofg = int(tab[3])
    pxq = int(buf[0])
    pyq = int(buf[1])
    eye64 = int(buf[2])
    hor = int(buf[3])
    y0 = int(buf[4])
    top = int(buf[5])
    rxq = int(buf[6])
    ryq = int(buf[7])
    lx = -2
    cnt = 0
    o = 16
    s = 0
    while s < n:
        tq = int(tab[4 + s])
        wx = pxq + rxq * tq
        wy = pyq + ryq * tq
        if wx < 0 or wy < 0 or wx >= _W16 or wy >= _H16:
            tile = _ROCK
            h16 = 96
            ix = -1
        else:
            ix = wx >> 16
            k = (wy >> 16) * _W + ix
            tile = int(world[k])
            h16 = int(world[_N + k])
        y = hor - (((h16 * 4 - eye64) * int(tab[okf + s])) >> 8)
        if y < top:
            if y < y0:
                y = y0
            face = 0
            if ix != lx and h16 > 6:
                face = 4
            buf[o] = y
            buf[o + 1] = top - y
            buf[o + 2] = int(tab[ofg + ((tile << 3) | face | int(tab[ofi + s]))])
            o += 3
            cnt += 1
            top = y
            if y <= y0:
                break
        lx = ix
        s += 1
    return cnt


@micropython.native
def _render(view_manager, st):
    '''Draw the first-person terrain view, one integer-marched ray per column.'''
    draw = view_manager.draw
    fill = draw._fill_rectangle
    tiles = st.tiles
    hts = st.hts
    fog = st.fog
    camq = st.camq
    buf = st.buf
    tab = st.tab
    world = st.world
    w = st.vw
    y0 = st.y0
    vb = st.vb
    hor = st.hor
    cw = st.cw
    px = st.px
    py = st.py
    dx = cos(st.pa)
    dy = sin(st.pa)
    dxq = int(dx * 256)
    dyq = int(dy * 256)
    plxq = int(-dy * _PL * 256)
    plyq = int(dx * _PL * 256)
    pk = int(py) * _W + int(px)
    eye64 = 70
    if tiles[pk] != _FOREST:
        eye64 += hts[pk] * 4
    buf[0] = int(px * 65536)
    buf[1] = int(py * 65536)
    buf[2] = eye64
    buf[3] = hor
    buf[4] = y0
    buf[5] = vb
    mid = (hor - y0) // 2
    fill(0, y0, w, mid, _SKY_TOP)
    fill(0, y0 + mid, w, hor - y0 - mid, _SKY_LOW)
    fill(0, hor, w, vb - hor, fog[tiles[pk] << 3])
    for i in range(len(camq)):
        c = camq[i]
        buf[6] = dxq + ((plxq * c) >> 12)
        buf[7] = dyq + ((plyq * c) >> 12)
        cnt = _march(buf, world, tab)
        sx = i * cw
        o = 16
        for _j in range(cnt):
            fill(sx, buf[o], cw, buf[o + 1], buf[o + 2])
            o += 3
    _draw_npcs(draw, st, dx, dy, eye64 / 64)
    _minimap(draw, st)
    _hud(view_manager, st)
    draw.swap()


def start(view_manager):
    '''Show a loading note, build the world, and prepare view geometry. Returns True.'''
    from gc import collect
    global _st
    draw = view_manager.draw
    draw.clear()
    draw._text(10, 10, "Generating valley...", _SKY_TOP)
    draw.swap()
    st = _State()
    size = draw.size
    st.vw = int(size.x)
    st.vh = int(size.y)
    st.fw = max(1, int(draw.font_size.x))
    st.fh = max(1, int(draw.font_size.y))
    st.y0 = st.fh + 4
    st.vb = st.vh - (st.fh * 2 + 8)
    st.hor = st.y0 + (st.vb - st.y0) * 45 // 100
    st.cw = max(3, st.vw // 64)
    cols = st.vw // st.cw
    st.camq = array("i", [int(((2 * i + 1) / cols - 1) * 4096) for i in range(cols)])
    st.foc = (st.vw / 2) / _PL
    st.fog = _fog_table()
    _build_world(st)
    _prep(st)
    st.mmt = 4 if st.vw >= 240 else 3
    st.fm = _foe_models()
    nm = _npc_models()
    npcs = []
    for i in range(3):
        npcs.append((_TOWNS[i][0] + 0.5, _TOWNS[i][1] + 0.5, nm[i]))
    st.npcs = tuple(npcs)
    collect()
    _st = st
    view_manager.input_manager.reset()
    return True


def run(view_manager):
    '''Read input, update the game, and redraw only when something changed.'''
    st = _st
    button = view_manager.button
    if button == BUTTON_BACK:
        view_manager.back()
        return
    if st.mode == 1:
        if _battle_input(st, button):
            st.dirty = True
    elif button == BUTTON_UP:
        if _step(st, _WALK_SPEED):
            _arrive(st)
            st.dirty = True
    elif button == BUTTON_DOWN:
        if _step(st, -_BACK_SPEED):
            _arrive(st)
            st.dirty = True
    elif button == BUTTON_LEFT:
        st.pa -= _TURN_SPEED
        st.dirty = True
    elif button == BUTTON_RIGHT:
        st.pa += _TURN_SPEED
        st.dirty = True
    elif button == BUTTON_CENTER:
        st.dirty = _interact(st)
    if st.dirty:
        st.dirty = False
        if st.mode == 1:
            _draw_battle(view_manager, st)
        else:
            _render(view_manager, st)


def stop(view_manager):
    '''Release game state and free memory.'''
    from gc import collect

    global _st
    _st = None
    collect()