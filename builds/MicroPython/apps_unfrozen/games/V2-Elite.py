from picoware.system.vector import Vector
from picoware.system.colors import *
from picoware.system.buttons import *
from picoware.system.storage import Storage
from picoware.system.audio import Audio, AudioNote
import math
import random
import gc

SCREEN_W = 320
SCREEN_H = 320
CX = 160
CY = 128
FOV = 210.0
NEAR = 1.2

COL_STAR_NEAR = TFT_WHITE
COL_STAR_FAR = TFT_LIGHTGREY
COL_STAR_DIM = TFT_DARKGREY
COL_PLANET_DAY = TFT_CYAN
COL_PLANET_NIGHT = TFT_DARKCYAN
COL_ATMOS = 0x02AA
COL_SUN = TFT_YELLOW
COL_SUN_CORE = TFT_WHITE
COL_CORONA = TFT_ORANGE
COL_STATION = TFT_YELLOW
COL_SHIP = TFT_GREEN
COL_ENEMY = TFT_RED
COL_PIRATE2 = TFT_ORANGE
COL_PIRATE3 = TFT_PINK
COL_POLICE = TFT_BLUE
COL_LASER = TFT_WHITE
COL_MISSILE = TFT_ORANGE
COL_HUD = TFT_GREEN
COL_HUD_DIM = TFT_DARKGREEN
COL_ALERT = TFT_RED
COL_BG = TFT_BLACK
COL_COCKPIT = 0x3186
COL_RADAR = TFT_DARKGREEN
COL_TITLE = TFT_YELLOW
COL_RANK = TFT_ORANGE
COL_DEBRIS = TFT_YELLOW

draw = None
input_mgr = None
storage = None
audio = None

player_pos = Vector(0.0, 0.0, 0.0)
pitch = yaw = roll = 0.0
speed = 0.0
max_speed = 4.5
thrust = 0.0

credits = 1000
cargo = {}
cargo_capacity = 20
current_system = 0
docked = True
energy = 100
laser_temp = 0
kills = 0
rank_name = "Harmless"
missiles = 3
max_missiles = 4
equipment = {"pulse_laser": True, "cargo_bay": False, "ecm": False}
laser_power = 1

stars = []
NUM_STARS = 80
title_stars = []
sky_stars = []
dust = []
sparks = []
wrecks = []
target_id = -1
asteroids = []
traffic = []
scan_ang = 0.0
jump_flash = 0
planet_day = TFT_CYAN
planet_night = TFT_DARKCYAN
star_tint = 0.0
sun_hot = False
use_dodo = False
has_moon = False
moon_ang = 0.0

GALAXY_NAMES = ["Lave Cluster", "Riedquat Arm", "Tianve Reach"]
GALAXY_DATA = [
    [
        {"name": "Lave", "tech": 5, "gov": "Democracy", "prod": "Rich Industrial", "pcol": TFT_CYAN, "ncol": TFT_DARKCYAN},
        {"name": "Diso", "tech": 8, "gov": "Corporate State", "prod": "Rich Industrial", "pcol": TFT_BLUE, "ncol": 0x0011, "dodo": 1, "hot": 1},
        {"name": "Riedquat", "tech": 2, "gov": "Anarchy", "prod": "Poor Agricultural", "pcol": TFT_ORANGE, "ncol": 0x8200, "rocks": 1},
        {"name": "Leesti", "tech": 7, "gov": "Democracy", "prod": "Average Industrial", "pcol": TFT_GREEN, "ncol": TFT_DARKGREEN, "moon": 1},
        {"name": "Zaonce", "tech": 9, "gov": "Corporate State", "prod": "Rich Industrial", "pcol": TFT_MAGENTA, "ncol": 0x8010, "ring": 1, "dodo": 1, "moon": 1},
        {"name": "Tianve", "tech": 4, "gov": "Dictatorship", "prod": "Average Agricultural", "pcol": 0x07FF, "ncol": 0x03EF, "moon": 1},
        {"name": "Orrere", "tech": 3, "gov": "Feudal", "prod": "Poor Agricultural", "pcol": 0xFC00, "ncol": 0x8000, "rocks": 1},
        {"name": "Reorte", "tech": 6, "gov": "Democracy", "prod": "Average Industrial", "pcol": TFT_CYAN, "ncol": TFT_DARKCYAN, "hot": 1},
    ],
    [
        {"name": "Uszaa", "tech": 4, "gov": "Anarchy", "prod": "Poor Agricultural", "pcol": TFT_ORANGE, "ncol": 0x8200, "rocks": 1},
        {"name": "Orerve", "tech": 6, "gov": "Feudal", "prod": "Average Agricultural", "pcol": TFT_GREEN, "ncol": TFT_DARKGREEN, "moon": 1},
        {"name": "Teorge", "tech": 8, "gov": "Corporate State", "prod": "Rich Industrial", "pcol": TFT_BLUE, "ncol": 0x0011, "dodo": 1, "hot": 1},
        {"name": "Qutiri", "tech": 3, "gov": "Dictatorship", "prod": "Poor Industrial", "pcol": 0xFC00, "ncol": 0x8000},
        {"name": "Isinor", "tech": 7, "gov": "Democracy", "prod": "Average Industrial", "pcol": TFT_CYAN, "ncol": TFT_DARKCYAN, "ring": 1},
        {"name": "Bemaera", "tech": 5, "gov": "Corporate State", "prod": "Rich Agricultural", "pcol": 0x07E0, "ncol": 0x0320, "moon": 1},
        {"name": "Xeer", "tech": 2, "gov": "Anarchy", "prod": "Poor Agricultural", "pcol": TFT_RED, "ncol": 0x8000, "rocks": 1},
        {"name": "Esbite", "tech": 9, "gov": "Democracy", "prod": "Rich Industrial", "pcol": TFT_MAGENTA, "ncol": 0x8010, "dodo": 1, "hot": 1},
    ],
    [
        {"name": "Onrira", "tech": 6, "gov": "Democracy", "prod": "Average Industrial", "pcol": TFT_CYAN, "ncol": TFT_DARKCYAN},
        {"name": "Arredi", "tech": 4, "gov": "Feudal", "prod": "Poor Agricultural", "pcol": TFT_ORANGE, "ncol": 0x8200, "moon": 1},
        {"name": "Ceedra", "tech": 8, "gov": "Corporate State", "prod": "Rich Industrial", "pcol": TFT_BLUE, "ncol": 0x0011, "dodo": 1, "ring": 1},
        {"name": "Soleri", "tech": 3, "gov": "Anarchy", "prod": "Poor Agricultural", "pcol": TFT_RED, "ncol": 0x8000, "rocks": 1},
        {"name": "Veqa", "tech": 7, "gov": "Dictatorship", "prod": "Average Industrial", "pcol": 0x07FF, "ncol": 0x03EF, "hot": 1},
        {"name": "Laeden", "tech": 5, "gov": "Democracy", "prod": "Rich Agricultural", "pcol": TFT_GREEN, "ncol": TFT_DARKGREEN, "moon": 1},
        {"name": "Quator", "tech": 9, "gov": "Corporate State", "prod": "Rich Industrial", "pcol": TFT_MAGENTA, "ncol": 0x8010, "dodo": 1},
        {"name": "Ritila", "tech": 2, "gov": "Anarchy", "prod": "Poor Industrial", "pcol": 0xFC00, "ncol": 0x8000, "rocks": 1},
    ],
]
SYSTEMS = GALAXY_DATA[0]
current_galaxy = 0
galaxy_sel = 0

COMMODITIES = [
    "Food", "Textiles", "Radioactives", "Slaves", "Liquor/Wines",
    "Luxuries", "Narcotics", "Computers", "Machinery", "Alloys",
    "Firearms", "Furs", "Minerals", "Gold", "Platinum",
    "Water", "Medicine", "Gem-Stones", "Alien Items"
]

ILLEGAL = ("Slaves", "Narcotics", "Firearms")

EQUIP_PRICES = {
    "cargo_bay": 400,
    "ecm": 600,
    "beam_laser": 800,
    "missile": 30,
}

market = {}
market_sel = 0
equip_sel = 0

planet_pos = Vector(0.0, 0.0, 100.0)
planet_radius = 22.0
sun_pos = Vector(-72.0, 18.0, 55.0)
station_angle = 0.0
station_dist = 40.0

enemies = []
spawn_timer = 0
missiles_in_flight = []
debris = []
docking_phase = 0
docking_timer = 0

game_mode = "title"
message = ""
message_timer = 0
title_angle = 0.0
frame = 0
hyperspace_cool = 0
jump_timer = 0
laser_flash = 0
ecm_cool = 0
mission = None
mission_kills = 0
board = []
board_sel = 0
wanted = 0
market_event = None
incoming = []

COBRA_VERTS = [
    (0.0, 0.0, 1.9),
    (0.0, 0.55, 0.6),
    (-2.4, -0.1, -0.2),
    (2.4, -0.1, -0.2),
    (-1.6, 0.35, -1.0),
    (1.6, 0.35, -1.0),
    (-1.6, -0.5, -1.0),
    (1.6, -0.5, -1.0),
    (0.0, -0.55, 0.3),
    (-2.0, -0.15, -0.9),
    (2.0, -0.15, -0.9),
    (0.0, 0.35, 1.1),
]
COBRA_FACES = [
    (0, 11, 1), (0, 1, 2), (0, 3, 1), (0, 2, 8), (0, 8, 3),
    (1, 11, 4), (1, 5, 11), (1, 4, 2), (1, 3, 5),
    (2, 4, 9), (2, 9, 6), (2, 6, 8),
    (3, 10, 5), (3, 7, 10), (3, 8, 7),
    (4, 5, 7), (4, 7, 6), (8, 6, 7), (4, 9, 6), (5, 10, 7),
]

ENEMY_VERTS = [
    (0.0, 0.0, 1.2),
    (-0.95, 0.0, -0.55),
    (0.95, 0.0, -0.55),
    (0.0, 0.72, -0.25),
    (0.0, -0.55, -0.25),
]
ENEMY_FACES = [
    (0, 1, 3), (0, 3, 2), (0, 2, 4), (0, 4, 1), (1, 4, 2), (1, 2, 3),
]

SW_VERTS = [
    (0.0, 0.05, 1.0),
    (-1.6, 0.1, 0.1),
    (1.6, 0.1, 0.1),
    (-1.4, -0.15, -0.7),
    (1.4, -0.15, -0.7),
    (0.0, 0.45, -0.2),
    (0.0, -0.4, 0.2),
    (0.0, 0.0, -1.0),
]
SW_FACES = [
    (0, 1, 5), (0, 5, 2), (0, 6, 1), (0, 2, 6),
    (1, 3, 5), (2, 5, 4), (1, 6, 3), (2, 4, 6),
    (3, 7, 5), (4, 5, 7), (3, 6, 7), (4, 7, 6),
]

ASP_VERTS = [
    (0.0, 0.0, 1.8),
    (-0.55, 0.25, 0.2),
    (0.55, 0.25, 0.2),
    (-0.7, -0.2, 0.1),
    (0.7, -0.2, 0.1),
    (0.0, 0.35, -1.3),
    (-0.4, -0.15, -1.4),
    (0.4, -0.15, -1.4),
]
ASP_FACES = [
    (0, 1, 2), (0, 3, 1), (0, 2, 4), (0, 4, 3),
    (1, 5, 2), (1, 3, 6), (1, 6, 5),
    (2, 5, 7), (2, 7, 4),
    (3, 4, 7), (3, 7, 6), (5, 6, 7),
]

POLICE_VERTS = [
    (0.0, 0.15, 1.3),
    (-0.8, 0.2, 0.2),
    (0.8, 0.2, 0.2),
    (-0.9, -0.25, 0.15),
    (0.9, -0.25, 0.15),
    (0.0, 0.5, -0.2),
    (-0.6, 0.1, -1.1),
    (0.6, 0.1, -1.1),
    (0.0, -0.3, -1.0),
    (-1.3, 0.35, -0.1),
    (1.3, 0.35, -0.1),
]
POLICE_FACES = [
    (0, 1, 5), (0, 5, 2), (0, 3, 1), (0, 2, 4), (0, 4, 3),
    (1, 9, 5), (2, 5, 10), (1, 3, 6), (2, 7, 4),
    (5, 6, 7), (3, 8, 6), (4, 7, 8), (6, 8, 7),
    (1, 6, 9), (2, 10, 7),
]

HULLS = {
    "krait": (ENEMY_VERTS, ENEMY_FACES, COL_ENEMY, 3.0),
    "sidewinder": (SW_VERTS, SW_FACES, COL_PIRATE2, 2.6),
    "asp": (ASP_VERTS, ASP_FACES, COL_PIRATE3, 2.8),
    "viper": (POLICE_VERTS, POLICE_FACES, COL_POLICE, 2.7),
}

def make_station():
    verts = []
    for z in (-1.0, 1.0):
        for i in range(6):
            a = i * math.pi / 3.0
            verts.append((math.cos(a) * 1.35, math.sin(a) * 1.35, z * 0.85))
    verts.append((0.0, 0.0, -1.15))
    verts.append((0.0, 0.0, 1.15))
    verts.append((-0.22, -0.22, -1.0))
    verts.append((0.22, -0.22, -1.0))
    verts.append((0.22, 0.22, -1.0))
    verts.append((-0.22, 0.22, -1.0))
    verts.append((0.0, 0.0, 0.0))
    verts.append((2.1, 0.0, 0.0))
    verts.append((-2.1, 0.0, 0.0))
    faces = []
    faces.append((0, 1, 2))
    faces.append((0, 2, 3))
    faces.append((0, 3, 4))
    faces.append((0, 4, 5))
    faces.append((6, 8, 7))
    faces.append((6, 9, 8))
    faces.append((6, 10, 9))
    faces.append((6, 11, 10))
    for i in range(6):
        a = i
        b = (i + 1) % 6
        faces.append((a, b, b + 6))
        faces.append((a, b + 6, a + 6))
    faces.append((14, 15, 16))
    faces.append((14, 16, 17))
    return verts, faces

STATION_VERTS, STATION_FACES = make_station()

def make_dodo():
    verts = []
    s = 1.15
    for z in (-s, s):
        for y in (-s, s):
            for x in (-s, s):
                verts.append((x, y, z))
    faces = [
        (0, 1, 3), (0, 3, 2),
        (4, 6, 7), (4, 7, 5),
        (0, 4, 5), (0, 5, 1),
        (2, 3, 7), (2, 7, 6),
        (0, 2, 6), (0, 6, 4),
        (1, 5, 7), (1, 7, 3),
    ]
    return verts, faces

DODO_VERTS, DODO_FACES = make_dodo()

ROCK_VERTS = [
    (0.8, 0.2, 0.1),
    (-0.6, 0.5, 0.2),
    (-0.3, -0.6, 0.3),
    (0.2, 0.1, -0.8),
    (0.1, -0.2, 0.7),
]
ROCK_FACES = [
    (0, 1, 4), (0, 4, 2), (0, 2, 3), (0, 3, 1),
    (1, 3, 4), (2, 4, 3),
]

def apply_system_look():
    global planet_day, planet_night, star_tint, sun_hot, use_dodo, has_moon, sun_pos
    sys = SYSTEMS[current_system]
    planet_day = sys.get("pcol", TFT_CYAN)
    planet_night = sys.get("ncol", TFT_DARKCYAN)
    sun_hot = bool(sys.get("hot"))
    use_dodo = bool(sys.get("dodo"))
    has_moon = bool(sys.get("moon"))
    star_tint = 0.12 if sun_hot else 0.0
    if sun_hot:
        sun_pos = Vector(-58.0, 22.0, 42.0)
    else:
        sun_pos = Vector(-72.0, 18.0, 55.0)

def generate_asteroids():
    global asteroids
    asteroids = []
    if not SYSTEMS[current_system].get("rocks"):
        return
    for _ in range(8):
        asteroids.append({
            "x": random.uniform(-50, 50),
            "y": random.uniform(-22, 22),
            "z": random.uniform(25, 90),
            "spin": random.uniform(-0.08, 0.08),
            "ang": random.uniform(0, 6.2),
            "sc": random.uniform(1.4, 2.6)
        })

def generate_traffic():
    global traffic
    traffic = []
    for _ in range(3):
        traffic.append({
            "x": random.uniform(-80, 80),
            "y": random.uniform(-18, 18),
            "z": random.uniform(70, 160),
            "vx": random.uniform(-0.15, 0.15),
            "vz": random.uniform(-0.08, 0.08),
            "hull": random.choice(("krait", "sidewinder", "asp"))
        })

def beep(freq, ms=28):
    if audio is None:
        return
    try:
        audio.play_note(AudioNote(freq, freq, ms))
    except:
        pass

def set_galaxy(idx):
    global SYSTEMS, current_galaxy, current_system
    current_galaxy = idx % len(GALAXY_DATA)
    SYSTEMS = GALAXY_DATA[current_galaxy]
    current_system = 0

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def fade565(c, t):
    t = clamp(t, 0.0, 1.0)
    r = (c >> 11) & 31
    g = (c >> 5) & 63
    b = c & 31
    k = 1.0 - t
    r = int(r * k)
    g = int(g * k)
    b = int(b * k)
    return (r << 11) | (g << 5) | b

def depth_fade(z):
    return clamp((z - 10.0) / 200.0, 0.0, 0.82)

def rotate_point(x, y, z, p, y_, r):
    cr, sr = math.cos(r), math.sin(r)
    x1 = x * cr - y * sr
    y1 = x * sr + y * cr
    z1 = z
    cp, sp = math.cos(p), math.sin(p)
    y2 = y1 * cp - z1 * sp
    z2 = y1 * sp + z1 * cp
    x2 = x1
    cy, sy = math.cos(y_), math.sin(y_)
    x3 = x2 * cy + z2 * sy
    z3 = -x2 * sy + z2 * cy
    y3 = y2
    return x3, y3, z3

def project(x, y, z):
    if z < NEAR:
        return None
    scale = FOV / z
    sx = CX + int(x * scale)
    sy = CY - int(y * scale)
    if sx < -50 or sx > SCREEN_W + 50 or sy < -50 or sy > SCREEN_H + 50:
        return None
    return sx, sy

def rotate_y(x, y, z, a):
    c, s = math.cos(a), math.sin(a)
    return x * c + z * s, y, -x * s + z * c

def generate_stars():
    global stars
    stars = []
    for _ in range(NUM_STARS):
        stars.append([
            random.uniform(-230, 230),
            random.uniform(-170, 170),
            random.uniform(16, 330),
            random.random()
        ])

def generate_title_stars():
    global title_stars
    title_stars = []
    for _ in range(70):
        title_stars.append((random.randint(4, 316), random.randint(4, 316), random.random()))

def generate_sky():
    global sky_stars
    sky_stars = []
    for _ in range(55):
        x = random.uniform(-1, 1)
        y = random.uniform(-1, 1)
        z = random.uniform(-1, 1)
        n = math.sqrt(x * x + y * y + z * z) + 0.001
        sky_stars.append((x / n * 420, y / n * 420, z / n * 420, random.random()))

def generate_dust():
    global dust
    dust = []
    for _ in range(18):
        dust.append([
            random.uniform(-18, 18),
            random.uniform(-12, 12),
            random.uniform(8, 70)
        ])

def update_stars(dx, dy, dz):
    for s in stars:
        s[0] -= dx
        s[1] -= dy
        s[2] -= dz
        if s[2] < 4:
            s[0] = random.uniform(-230, 230)
            s[1] = random.uniform(-170, 170)
            s[2] = random.uniform(180, 330)
            s[3] = random.random()

def roll_market_event(sys_idx):
    global market_event
    r = random.random()
    if r < 0.22:
        market_event = {"kind": "drought", "sys": sys_idx}
    elif r < 0.40:
        market_event = {"kind": "war", "sys": sys_idx}
    else:
        market_event = None

def generate_market(sys_idx):
    global market
    sys = SYSTEMS[sys_idx]
    roll_market_event(sys_idx)
    market = {}
    for i, name in enumerate(COMMODITIES):
        base = 8 + i * 7 + random.randint(-6, 12)
        if "Agricultural" in sys["prod"] and name in ("Food", "Textiles", "Furs", "Liquor/Wines"):
            base = int(base * 0.55)
        if "Industrial" in sys["prod"] and name in ("Computers", "Machinery", "Alloys", "Radioactives"):
            base = int(base * 0.65)
        if sys["gov"] == "Anarchy" and name in ("Slaves", "Narcotics", "Firearms"):
            base = int(base * 1.5)
        if market_event and market_event.get("sys") == sys_idx:
            if market_event["kind"] == "drought" and name in ("Food", "Textiles", "Liquor/Wines"):
                base = int(base * 2.1)
            if market_event["kind"] == "war" and name in ("Firearms", "Alloys", "Narcotics"):
                base = int(base * 1.9)
        market[name] = max(2, base)

def buy(name, qty=1):
    global credits, cargo
    if name not in market:
        return False
    price = market[name] * qty
    if sum(cargo.values()) + qty > cargo_capacity or credits < price:
        return False
    credits -= price
    cargo[name] = cargo.get(name, 0) + qty
    return True

def sell(name, qty=1):
    global credits, cargo
    if cargo.get(name, 0) < qty:
        return False
    credits += market[name] * qty
    cargo[name] -= qty
    if cargo[name] <= 0:
        del cargo[name]
    if mission and mission.get("kind") == "deliver" and name == mission.get("item"):
        if cargo.get(name, 0) < mission.get("qty", 1):
            fail_mission("Delivery dumped")
    return True

def buy_equip(item):
    global credits, cargo_capacity, laser_power, missiles, equipment
    if item == "missile":
        if missiles >= max_missiles or credits < EQUIP_PRICES["missile"]:
            return False
        credits -= EQUIP_PRICES["missile"]
        missiles += 1
        return True
    if item in equipment and equipment[item]:
        return False
    price = EQUIP_PRICES.get(item, 9999)
    if credits < price:
        return False
    credits -= price
    if item == "cargo_bay":
        equipment["cargo_bay"] = True
        cargo_capacity = 35
    elif item == "ecm":
        equipment["ecm"] = True
    elif item == "beam_laser":
        equipment["pulse_laser"] = False
        laser_power = 2
    return True

def update_rank():
    global rank_name
    if kills >= 32 or credits > 8000:
        rank_name = "Elite"
    elif kills >= 16 or credits > 4000:
        rank_name = "Dangerous"
    elif kills >= 8 or credits > 2000:
        rank_name = "Competent"
    elif kills >= 3 or credits > 1200:
        rank_name = "Mostly Harmless"
    else:
        rank_name = "Harmless"

def carrying_illegal():
    for name in ILLEGAL:
        if cargo.get(name, 0) > 0:
            return True
    return False

def spawn_enemy():
    ang = random.uniform(-1.2, 1.2)
    dist = random.uniform(60, 140)
    gov = SYSTEMS[current_system]["gov"]
    police = False
    lawful = gov in ("Democracy", "Corporate State")
    if lawful and (wanted > 0 or carrying_illegal()):
        police = True
    elif lawful and wanted == 0 and not carrying_illegal() and random.random() < 0.08:
        police = True
    if police:
        hull = "viper"
        kind = "police"
        hp = 4 + laser_power
        spd = random.uniform(0.9, 1.5)
    else:
        hull = random.choice(("krait", "sidewinder", "asp"))
        kind = "pirate"
        hp = 3 + laser_power
        spd = random.uniform(0.55, 1.35)
    enemies.append({
        "pos": Vector(math.sin(ang) * dist, random.uniform(-20, 20), math.cos(ang) * dist + 40),
        "pitch": random.uniform(-0.3, 0.3),
        "yaw": random.uniform(-math.pi, math.pi),
        "health": hp,
        "speed": spd,
        "type": kind,
        "hull": hull,
        "cool": random.randint(20, 50),
        "mode": "hunt",
        "orbit": random.choice((-1.0, 1.0))
    })

def fail_mission(why):
    global mission, mission_kills, message, message_timer
    if not mission:
        return
    mission = None
    mission_kills = 0
    message = why
    message_timer = 45

def player_shot():
    global energy, message, message_timer
    energy = max(8, energy - random.randint(6, 14))
    spawn_sparks(player_pos.x, player_pos.y, player_pos.z + 4, 5)
    message = "Incoming fire"
    message_timer = 18
    beep(300, 20)

def enemy_fire(e):
    global incoming
    px, py, pz = e["pos"].x, e["pos"].y, e["pos"].z
    incoming.append({
        "x0": px, "y0": py, "z0": pz,
        "x1": px * 0.15, "y1": py * 0.15, "z1": pz * 0.15,
        "life": 4
    })
    if random.random() < 0.55:
        player_shot()
    if random.random() < 0.12:
        dx = -px
        dy = -py
        dz = -pz
        n = math.sqrt(dx * dx + dy * dy + dz * dz) + 0.01
        missiles_in_flight.append({
            "x": px, "y": py, "z": pz,
            "vx": dx / n * 2.2,
            "vy": dy / n * 2.2,
            "vz": dz / n * 2.2,
            "life": 70,
            "trail": [],
            "hostile": True
        })

def spawn_wreck(e):
    verts, faces, col, sc = HULLS.get(e.get("hull", "krait"), HULLS["krait"])
    n = min(5, len(faces))
    for i in range(n):
        f = faces[i]
        wrecks.append({
            "pts": [verts[f[0]], verts[f[1]], verts[f[2]]],
            "x": e["pos"].x,
            "y": e["pos"].y,
            "z": e["pos"].z,
            "vx": random.uniform(-1.2, 1.2),
            "vy": random.uniform(-1.2, 1.2),
            "vz": random.uniform(-1.2, 1.2),
            "spin": random.uniform(-0.2, 0.2),
            "ang": 0.0,
            "life": random.randint(14, 26),
            "col": col,
            "sc": sc * 0.9
        })

def spawn_sparks(x, y, z, n=6):
    for _ in range(n):
        sparks.append({
            "x": x, "y": y, "z": z,
            "vx": random.uniform(-1.6, 1.6),
            "vy": random.uniform(-1.6, 1.6),
            "vz": random.uniform(-1.6, 1.6),
            "life": random.randint(6, 14)
        })

def spawn_debris(x, y, z, count=10):
    for _ in range(count):
        debris.append({
            "x": x, "y": y, "z": z,
            "vx": random.uniform(-1.8, 1.8),
            "vy": random.uniform(-1.8, 1.8),
            "vz": random.uniform(-1.8, 1.8),
            "lx": random.uniform(-1.4, 1.4),
            "ly": random.uniform(-1.4, 1.4),
            "lz": random.uniform(-1.4, 1.4),
            "life": random.randint(16, 38),
            "maxlife": 38
        })

def clear_mission():
    global mission, mission_kills
    mission = None
    mission_kills = 0

def complete_mission():
    global credits, message, message_timer
    if not mission:
        return
    credits += mission.get("pay", 0)
    message = "Mission complete +" + str(mission.get("pay", 0))
    message_timer = 50
    beep(880, 50)
    clear_mission()

def generate_board():
    global board
    board = []
    need = random.randint(2, 4)
    board.append({
        "kind": "kill",
        "need": need,
        "pay": 80 + need * 40,
        "label": "Destroy " + str(need) + " pirates"
    })
    dest = current_system
    while dest == current_system:
        dest = random.randint(0, len(SYSTEMS) - 1)
    item = random.choice(("Food", "Computers", "Alloys", "Luxuries", "Machinery"))
    qty = random.randint(1, 3)
    board.append({
        "kind": "deliver",
        "item": item,
        "qty": qty,
        "dest": dest,
        "pay": 60 + qty * 35 + SYSTEMS[dest]["tech"] * 8,
        "label": "Deliver " + str(qty) + " " + item + " to " + SYSTEMS[dest]["name"]
    })
    visit = current_system
    while visit == current_system:
        visit = random.randint(0, len(SYSTEMS) - 1)
    board.append({
        "kind": "visit",
        "dest": visit,
        "pay": 90 + SYSTEMS[visit]["tech"] * 10,
        "label": "Scan " + SYSTEMS[visit]["name"]
    })
    hull = random.choice(("krait", "sidewinder", "asp"))
    board.append({
        "kind": "bounty",
        "hull": hull,
        "pay": 160 + random.randint(0, 80),
        "label": "Bounty: " + hull[:1].upper() + hull[1:]
    })

def take_mission(idx):
    global mission, mission_kills, message, message_timer
    if mission:
        message = "Mission already active"
        message_timer = 30
        return
    if idx < 0 or idx >= len(board):
        return
    mission = dict(board[idx])
    mission_kills = 0
    if mission["kind"] == "deliver":
        item = mission["item"]
        qty = mission["qty"]
        if cargo.get(item, 0) < qty:
            if not buy(item, qty):
                message = "Need cargo for contract"
                message_timer = 35
                mission = None
                return
    if mission["kind"] == "bounty" and not docked:
        spawn_bounty(mission["hull"])
    beep(660, 40)
    message = "Contract accepted"
    message_timer = 35

def spawn_bounty(hull):
    ang = random.uniform(-0.8, 0.8)
    dist = random.uniform(50, 90)
    enemies.append({
        "pos": Vector(math.sin(ang) * dist, random.uniform(-10, 10), math.cos(ang) * dist + 30),
        "pitch": 0.0,
        "yaw": 0.0,
        "health": 6 + laser_power,
        "speed": 1.15,
        "type": "pirate",
        "hull": hull,
        "cool": 18,
        "mode": "hunt",
        "orbit": 1.0,
        "bounty": True
    })

def check_visit():
    if not mission or mission.get("kind") != "visit":
        return
    if current_system == mission.get("dest"):
        complete_mission()

def check_delivery():
    if not mission or mission.get("kind") != "deliver":
        return
    if current_system != mission.get("dest"):
        return
    item = mission["item"]
    qty = mission["qty"]
    if cargo.get(item, 0) >= qty:
        cargo[item] -= qty
        if cargo[item] <= 0:
            del cargo[item]
        complete_mission()

def update_enemies():
    global credits, kills, message, message_timer, mission_kills, wanted
    new_list = []
    for e in enemies:
        px, py, pz = e["pos"].x, e["pos"].y, e["pos"].z
        dist = math.sqrt(px * px + py * py + pz * pz) + 0.01
        police_idle = e.get("type") == "police" and wanted <= 0 and not carrying_illegal()
        if police_idle:
            e["mode"] = "circle"
        elif speed > e["speed"] + 1.6 and dist > 35:
            e["mode"] = "flee"
        elif dist < 18:
            e["mode"] = "circle"
        elif dist > 90:
            e["mode"] = "hunt"
        else:
            if e.get("mode") == "flee" and dist < 70:
                e["mode"] = "hunt"
        mode = e.get("mode", "hunt")
        if mode == "flee":
            e["pos"].x += (px / dist) * e["speed"] * 0.45
            e["pos"].y += (py / dist) * e["speed"] * 0.2
            e["pos"].z += (pz / dist) * e["speed"] * 0.45
        elif mode == "circle":
            ox = -pz * e.get("orbit", 1.0)
            oz = px * e.get("orbit", 1.0)
            on = math.sqrt(ox * ox + oz * oz) + 0.01
            e["pos"].x += (ox / on) * e["speed"] * 0.4
            e["pos"].z += (oz / on) * e["speed"] * 0.4
            e["pos"].y += math.sin(frame * 0.05) * 0.08
            if dist > 40:
                e["pos"].x -= (px / dist) * 0.08
                e["pos"].z -= (pz / dist) * 0.08
        else:
            e["pos"].x -= (px / dist) * e["speed"] * 0.32
            e["pos"].y -= (py / dist) * e["speed"] * 0.18
            e["pos"].z -= (pz / dist) * e["speed"] * 0.32
        e["yaw"] += 0.03 if mode == "circle" else 0.02
        e["cool"] = e.get("cool", 0) - 1
        hostile = True
        if e.get("type") == "police" and wanted <= 0 and not carrying_illegal():
            hostile = False
        if hostile and e["cool"] <= 0 and 14 < dist < 72 and mode != "flee":
            enemy_fire(e)
            e["cool"] = random.randint(28, 55)
        if e["health"] > 0 and dist > 7 and dist < 220:
            new_list.append(e)
        elif e["health"] <= 0:
            spawn_debris(e["pos"].x, e["pos"].y, e["pos"].z, 12)
            spawn_wreck(e)
            if e.get("type") == "police":
                credits += 20
                wanted += 2
                message = "Police destroyed"
            else:
                credits += 50 + random.randint(0, 50)
                kills += 1
                update_rank()
                message = "Pirate destroyed"
                if mission and mission.get("kind") == "kill":
                    mission_kills += 1
                    if mission_kills >= mission.get("need", 1):
                        complete_mission()
                if mission and mission.get("kind") == "bounty" and e.get("bounty"):
                    complete_mission()
            beep(220, 40)
            message_timer = 40
    enemies[:] = new_list

def update_missiles():
    global ecm_cool, message, message_timer, energy
    alive = []
    for m in missiles_in_flight:
        m["life"] -= 1
        if m["life"] <= 0:
            continue
        if m.get("hostile") and equipment.get("ecm") and ecm_cool <= 0:
            dx = m["x"] - player_pos.x
            dy = m["y"] - player_pos.y
            dz = m["z"] - player_pos.z
            if dx * dx + dy * dy + dz * dz < 280:
                spawn_debris(m["x"], m["y"], m["z"], 6)
                ecm_cool = 50
                energy = max(0, energy - 8)
                message = "ECM intercept"
                message_timer = 25
                continue
        m["trail"].append((m["x"], m["y"], m["z"]))
        if len(m["trail"]) > 7:
            m["trail"].pop(0)
        if m.get("hostile"):
            dx = player_pos.x - m["x"]
            dy = player_pos.y - m["y"]
            dz = player_pos.z - m["z"]
            dist = math.sqrt(dx * dx + dy * dy + dz * dz) + 0.01
            m["x"] += (dx / dist) * 2.6
            m["y"] += (dy / dist) * 2.6
            m["z"] += (dz / dist) * 2.6
            if dist < 5:
                player_shot()
                spawn_debris(m["x"], m["y"], m["z"], 8)
                continue
            alive.append(m)
            continue
        target = None
        best = 99999
        for e in enemies:
            d = (e["pos"].x - m["x"]) ** 2 + (e["pos"].y - m["y"]) ** 2 + (e["pos"].z - m["z"]) ** 2
            if d < best:
                best = d
                target = e
        if target and best < 900:
            dx = target["pos"].x - m["x"]
            dy = target["pos"].y - m["y"]
            dz = target["pos"].z - m["z"]
            dist = math.sqrt(dx * dx + dy * dy + dz * dz) + 0.01
            m["x"] += (dx / dist) * 3.2
            m["y"] += (dy / dist) * 3.2
            m["z"] += (dz / dist) * 3.2
            if dist < 4:
                target["health"] = 0
                spawn_debris(target["pos"].x, target["pos"].y, target["pos"].z, 14)
                continue
        else:
            m["x"] += m["vx"]
            m["y"] += m["vy"]
            m["z"] += m["vz"]
        alive.append(m)
    missiles_in_flight[:] = alive

def update_debris():
    alive = []
    for d in debris:
        d["x"] += d["vx"]
        d["y"] += d["vy"]
        d["z"] += d["vz"]
        d["life"] -= 1
        if d["life"] > 0:
            alive.append(d)
    debris[:] = alive
    sa = []
    for s in sparks:
        s["x"] += s["vx"]
        s["y"] += s["vy"]
        s["z"] += s["vz"]
        s["life"] -= 1
        if s["life"] > 0:
            sa.append(s)
    sparks[:] = sa
    wa = []
    for w in wrecks:
        w["x"] += w["vx"]
        w["y"] += w["vy"]
        w["z"] += w["vz"]
        w["ang"] += w["spin"]
        w["life"] -= 1
        if w["life"] > 0:
            wa.append(w)
    wrecks[:] = wa
    for ptd in dust:
        ptd[2] -= 1.2 + speed * 0.8
        if ptd[2] < 4:
            ptd[0] = random.uniform(-18, 18)
            ptd[1] = random.uniform(-12, 12)
            ptd[2] = random.uniform(40, 80)

def fire_laser():
    global laser_temp, energy, message, message_timer, laser_flash, wanted
    if laser_temp > 85 or energy < 4:
        message = "Laser overheat"
        message_timer = 20
        return False
    laser_temp = min(100, laser_temp + 22 + laser_power * 4)
    energy = max(0, energy - 3 - laser_power)
    laser_flash = 5
    beep(1400, 18)
    for e in enemies:
        rx, ry, rz = rotate_point(e["pos"].x, e["pos"].y, e["pos"].z, -pitch, -yaw, -roll)
        if rz > 5 and rz < 100:
            ang = math.sqrt(rx * rx + ry * ry) / rz
            if ang < 0.16:
                e["health"] -= laser_power
                spawn_sparks(e["pos"].x, e["pos"].y, e["pos"].z, 7)
                if e.get("type") == "police":
                    wanted += 1
                    message = "Wanted"
                else:
                    message = "Hit"
                message_timer = 15
    return True

def fire_missile():
    global missiles, message, message_timer
    if missiles <= 0:
        message = "No missiles"
        message_timer = 20
        return
    missiles -= 1
    fx, fy, fz = rotate_point(0.0, 0.0, 1.0, pitch, yaw, roll)
    missiles_in_flight.append({
        "x": player_pos.x + fx * 3,
        "y": player_pos.y + fy * 3,
        "z": player_pos.z + fz * 3,
        "vx": fx * 2.5,
        "vy": fy * 2.5,
        "vz": fz * 2.5,
        "life": 90,
        "trail": [],
        "hostile": False
    })
    message = "Missile away"
    message_timer = 20

def transform_verts(verts, ox, oy, oz, scale, p, y_, r, extra_rot_y=0.0):
    out = []
    for vx, vy, vz in verts:
        if extra_rot_y:
            vx, vy, vz = rotate_y(vx, vy, vz, extra_rot_y)
        mx, my, mz = rotate_point(vx * scale, vy * scale, vz * scale, p, y_, r)
        rx, ry, rz = rotate_point(mx + ox, my + oy, mz + oz, -pitch, -yaw, -roll)
        out.append((rx, ry, rz))
    return out

def draw_faces(d, transformed, faces, color):
    seen = {}
    for face in faces:
        pts = []
        zs = []
        ok = True
        for idx in face:
            x, y, z = transformed[idx]
            pr = project(x, y, z)
            if not pr:
                ok = False
                break
            pts.append(pr)
            zs.append(z)
        if not ok or len(pts) < 3:
            continue
        area = (pts[1][0] - pts[0][0]) * (pts[2][1] - pts[0][1]) - (pts[2][0] - pts[0][0]) * (pts[1][1] - pts[0][1])
        if area <= 0:
            continue
        zavg = sum(zs) / len(zs)
        col = fade565(color, depth_fade(zavg))
        n = len(face)
        for i in range(n):
            a = face[i]
            b = face[(i + 1) % n]
            key = (a, b) if a < b else (b, a)
            if key in seen:
                continue
            seen[key] = True
            p1 = project(*transformed[a])
            p2 = project(*transformed[b])
            if p1 and p2:
                d.line_custom(Vector(p1[0], p1[1]), Vector(p2[0], p2[1]), col)

def draw_model_culled(d, verts, faces, ox, oy, oz, scale, p, y_, r, color, extra_rot_y=0.0):
    tr = transform_verts(verts, ox, oy, oz, scale, p, y_, r, extra_rot_y)
    draw_faces(d, tr, faces, color)

def draw_stars(d):
    streak = speed > 2.4
    slen = int(2 + speed * 2.2)
    for sx, sy, sz, b in sky_stars:
        rx, ry, rz = rotate_point(sx, sy, sz, -pitch, -yaw, -roll)
        p = project(rx, ry, rz)
        if p:
            d.pixel(Vector(p[0], p[1]), COL_STAR_DIM if b < 0.6 else fade565(COL_STAR_NEAR, 0.45))
    for s in stars:
        rx, ry, rz = rotate_point(s[0], s[1], s[2], -pitch, -yaw, -roll)
        p = project(rx, ry, rz)
        if p:
            fade = depth_fade(rz)
            col = fade565(COL_STAR_NEAR, fade)
            if streak and rz > 8:
                fx, fy, fz = rotate_point(0.0, 0.0, 1.0, pitch, yaw, roll)
                p2 = project(rx - fx * slen, ry - fy * slen, rz + 0.01)
                if p2:
                    d.line_custom(Vector(p[0], p[1]), Vector(p2[0], p2[1]), col)
                else:
                    d.pixel(Vector(p[0], p[1]), col)
            elif s[3] > 0.75 and rz < 50:
                d.pixel(Vector(p[0], p[1]), fade565(COL_STAR_NEAR, fade * 0.3))
                d.pixel(Vector(p[0] + 1, p[1]), fade565(COL_STAR_NEAR, fade * 0.5))
            else:
                d.pixel(Vector(p[0], p[1]), col)
    if thrust > 0 or speed > 1.2:
        for ptd in dust:
            rx, ry, rz = rotate_point(ptd[0], ptd[1], ptd[2], -pitch, -yaw, -roll)
            p = project(rx, ry, rz)
            if p:
                d.pixel(Vector(p[0], p[1]), COL_STAR_FAR)

def draw_sun(d):
    rx, ry, rz = rotate_point(sun_pos.x - player_pos.x, sun_pos.y - player_pos.y, sun_pos.z - player_pos.z, -pitch, -yaw, -roll)
    if rz < 6:
        return
    p = project(rx, ry, rz)
    if not p:
        return
    sx, sy = p
    base = 12 if sun_hot else 9
    rad = max(3, int(base * FOV / rz))
    rad = min(rad, 42)
    d.circle(Vector(sx, sy), rad + 6, fade565(COL_CORONA, depth_fade(rz) * 0.35))
    d.circle(Vector(sx, sy), rad + 2, fade565(COL_SUN, depth_fade(rz) * 0.2))
    d.fill_circle(Vector(sx, sy), rad, COL_SUN if not sun_hot else TFT_WHITE)
    if rad > 4:
        d.fill_circle(Vector(sx, sy), max(2, rad // 3), COL_SUN_CORE)
    ang = math.sqrt((sx - CX) * (sx - CX) + (sy - CY) * (sy - CY))
    if ang < 70 and rz < 160:
        for i in range(6):
            a = i * 1.047
            x1 = sx + int(math.cos(a) * (rad + 4))
            y1 = sy + int(math.sin(a) * (rad + 4))
            x2 = sx + int(math.cos(a) * (rad + 16 + (70 - ang) * 0.2))
            y2 = sy + int(math.sin(a) * (rad + 16 + (70 - ang) * 0.2))
            d.line_custom(Vector(x1, y1), Vector(x2, y2), fade565(COL_SUN, 0.35))
        if ang < 28:
            d.fill_rectangle(Vector(0, 0), Vector(320, 250), fade565(TFT_WHITE, 0.88))

def draw_planet(d):
    relx = planet_pos.x - player_pos.x
    rely = planet_pos.y - player_pos.y
    relz = planet_pos.z - player_pos.z
    rx, ry, rz = rotate_point(relx, rely, relz, -pitch, -yaw, -roll)
    if rz < 6:
        return
    p = project(rx, ry, rz)
    if not p:
        return
    sx, sy = p
    rad = max(5, int(planet_radius * FOV / rz))
    rad = min(rad, 115)
    srx, sry, srz = rotate_point(sun_pos.x - player_pos.x, sun_pos.y - player_pos.y, sun_pos.z - player_pos.z, -pitch, -yaw, -roll)
    ldx = srx - rx
    ldy = sry - ry
    ln = math.sqrt(ldx * ldx + ldy * ldy) + 0.01
    ux = ldx / ln
    uy = ldy / ln
    if rad > 10:
        d.circle(Vector(sx, sy), rad + 3, COL_ATMOS)
    d.circle(Vector(sx, sy), rad, fade565(planet_day, depth_fade(rz) * 0.35))
    steps = 8
    for i in range(steps):
        t0 = (i / steps) * math.pi - math.pi / 2
        t1 = ((i + 1) / steps) * math.pi - math.pi / 2
        c0 = math.cos(t0)
        c1 = math.cos(t1)
        x0 = sx - int(ux * rad * c0)
        y0 = sy - int(uy * rad * c0)
        x1 = sx - int(ux * rad * c1)
        y1 = sy - int(uy * rad * c1)
        d.fill_triangle(Vector(sx, sy), Vector(x0, y0), Vector(x1, y1), fade565(planet_night, 0.05))
        d.line_custom(Vector(x0, y0), Vector(x1, y1), fade565(planet_night, 0.15))
    capx = sx + int(-uy * rad * 0.72)
    capy = sy + int(ux * rad * 0.72)
    if rad > 12:
        d.circle(Vector(capx, capy), max(2, rad // 7), fade565(TFT_WHITE, 0.35))
    if rad > 16:
        for cr in ((0.28, 0.18), (-0.22, 0.32), (0.12, -0.25)):
            cxp = sx + int(uy * rad * cr[0] + ux * rad * cr[1] * 0.3)
            cyp = sy + int(-ux * rad * cr[0] + uy * rad * cr[1] * 0.3)
            d.circle(Vector(cxp, cyp), max(1, rad // 16), fade565(planet_night, 0.2))
    for k in (-0.55, 0.0, 0.55):
        pts = []
        for j in range(9):
            a = -1.1 + j * 0.28
            px = sx + int(math.sin(a) * rad * 0.92 * math.cos(k))
            py = sy + int(math.cos(a) * rad * 0.55 + k * rad * 0.35)
            pts.append((px, py))
        for j in range(len(pts) - 1):
            d.line_custom(Vector(pts[j][0], pts[j][1]), Vector(pts[j + 1][0], pts[j + 1][1]), fade565(planet_day, depth_fade(rz) * 0.5))
    if has_moon:
        global moon_ang
        moon_ang += 0.01
        mx = planet_pos.x + math.cos(moon_ang) * 34
        my = planet_pos.y + math.sin(moon_ang * 0.4) * 8
        mz = planet_pos.z + math.sin(moon_ang) * 34
        mrx, mry, mrz = rotate_point(mx - player_pos.x, my - player_pos.y, mz - player_pos.z, -pitch, -yaw, -roll)
        if mrz > 6:
            mp = project(mrx, mry, mrz)
            if mp:
                mr = max(2, int(5.5 * FOV / mrz))
                mr = min(mr, 18)
                d.circle(Vector(mp[0], mp[1]), mr, fade565(TFT_LIGHTGREY, depth_fade(mrz) * 0.3))
                d.circle(Vector(mp[0] - mr // 3, mp[1]), max(1, mr // 2), fade565(TFT_DARKGREY, 0.2))
    if SYSTEMS[current_system].get("ring") and rad > 8:
        for t in range(18):
            a0 = t * 0.35
            a1 = (t + 1) * 0.35
            px0 = sx + int(math.cos(a0) * rad * 1.55)
            py0 = sy + int(math.sin(a0) * rad * 0.38)
            px1 = sx + int(math.cos(a1) * rad * 1.55)
            py1 = sy + int(math.sin(a1) * rad * 0.38)
            d.line_custom(Vector(px0, py0), Vector(px1, py1), fade565(TFT_LIGHTGREY, depth_fade(rz) * 0.25))

def draw_station(d):
    global station_angle
    station_angle += 0.016
    sa = station_angle
    stx = planet_pos.x + math.cos(sa) * station_dist
    sty = planet_pos.y + math.sin(sa * 0.28) * 7
    stz = planet_pos.z + math.sin(sa) * station_dist
    ox = stx - player_pos.x
    oy = sty - player_pos.y
    oz = stz - player_pos.z
    sv, sf = (DODO_VERTS, DODO_FACES) if use_dodo else (STATION_VERTS, STATION_FACES)
    sc = 4.4 if use_dodo else 5.0
    draw_model_culled(d, sv, sf, ox, oy, oz, sc, 0.15, sa * 0.7, 0.25, COL_STATION)
    for arm in ((2.6, 0.0, 0.0), (-2.6, 0.0, 0.0), (0.0, 2.6, 0.0), (0.0, -2.6, 0.0)):
        tr = transform_verts([(0, 0, 0), arm], ox, oy, oz, sc, 0.15, sa * 0.7, 0.25)
        p1 = project(*tr[0])
        p2 = project(*tr[1])
        if p1 and p2:
            d.line_custom(Vector(p1[0], p1[1]), Vector(p2[0], p2[1]), fade565(COL_STATION, 0.25))
        if p2 and (frame // 8) % 2 == 0:
            d.pixel(Vector(p2[0], p2[1]), TFT_WHITE)
            d.pixel(Vector(p2[0] + 1, p2[1]), TFT_RED)
    slit = transform_verts([(-0.18, -0.18, -1.05), (0.18, -0.18, -1.05), (0.18, 0.18, -1.05), (-0.18, 0.18, -1.05)], ox, oy, oz, sc, 0.15, sa * 0.7, 0.25)
    sp = []
    ok = True
    for v in slit:
        pr = project(*v)
        if not pr:
            ok = False
            break
        sp.append(pr)
    if ok:
        for i in range(4):
            a = sp[i]
            b = sp[(i + 1) % 4]
            d.line_custom(Vector(a[0], a[1]), Vector(b[0], b[1]), COL_STAR_DIM)
    dist = math.sqrt(ox * ox + oy * oy + oz * oz)
    if not docked and dist < 55 and speed < 2.2 and ok:
        mid = ((sp[0][0] + sp[2][0]) // 2, (sp[0][1] + sp[2][1]) // 2)
        d.line_custom(Vector(CX - 40, 236), Vector(mid[0] - 8, mid[1] + 8), COL_HUD_DIM)
        d.line_custom(Vector(CX + 40, 236), Vector(mid[0] + 8, mid[1] + 8), COL_HUD_DIM)

def draw_bracket(d, sx, sy, sz):
    s = max(6, int(18 * FOV / max(sz, 8)))
    s = min(s, 28)
    c = COL_HUD
    d.line_custom(Vector(sx - s, sy - s), Vector(sx - s + 5, sy - s), c)
    d.line_custom(Vector(sx - s, sy - s), Vector(sx - s, sy - s + 5), c)
    d.line_custom(Vector(sx + s, sy - s), Vector(sx + s - 5, sy - s), c)
    d.line_custom(Vector(sx + s, sy - s), Vector(sx + s, sy - s + 5), c)
    d.line_custom(Vector(sx - s, sy + s), Vector(sx - s + 5, sy + s), c)
    d.line_custom(Vector(sx - s, sy + s), Vector(sx - s, sy + s - 5), c)
    d.line_custom(Vector(sx + s, sy + s), Vector(sx + s - 5, sy + s), c)
    d.line_custom(Vector(sx + s, sy + s), Vector(sx + s, sy + s - 5), c)

def draw_enemies(d):
    global target_id
    best_ang = 0.22
    target_id = -1
    tgt_scr = None
    for i, e in enumerate(enemies):
        rx, ry, rz = rotate_point(e["pos"].x, e["pos"].y, e["pos"].z, -pitch, -yaw, -roll)
        if rz < 4:
            continue
        p = project(rx, ry, rz)
        verts, faces, col, sc = HULLS.get(e.get("hull", "krait"), HULLS["krait"])
        if rz > 95:
            if p:
                d.pixel(Vector(p[0], p[1]), col)
        elif rz > 48:
            if p:
                d.line_custom(Vector(p[0] - 2, p[1]), Vector(p[0] + 2, p[1]), col)
                d.line_custom(Vector(p[0], p[1] - 1), Vector(p[0], p[1] + 1), col)
        else:
            draw_model_culled(d, verts, faces, e["pos"].x, e["pos"].y, e["pos"].z, sc, e["pitch"], e["yaw"], 0.0, col)
            glow = transform_verts([(-0.22, -0.12, -1.15), (0.22, -0.12, -1.15), (-0.9, 0.2, 0.0), (0.9, 0.2, 0.0)], e["pos"].x, e["pos"].y, e["pos"].z, sc, e["pitch"], e["yaw"], 0.0)
            hot = TFT_WHITE if (frame % 6) < 4 else TFT_YELLOW
            for gv in glow[:2]:
                gp = project(*gv)
                if gp:
                    d.pixel(Vector(gp[0], gp[1]), hot)
                    d.pixel(Vector(gp[0], gp[1] + 1), TFT_ORANGE)
                    if (frame % 6) < 3:
                        d.pixel(Vector(gp[0] + 1, gp[1]), TFT_YELLOW)
            if (frame // 7) % 2 == 0:
                for gv in glow[2:]:
                    gp = project(*gv)
                    if gp:
                        d.pixel(Vector(gp[0], gp[1]), TFT_RED)
        if p:
            ang = math.sqrt(rx * rx + ry * ry) / rz
            if ang < best_ang:
                best_ang = ang
                target_id = i
                tgt_scr = (p[0], p[1], rz)
    if tgt_scr:
        draw_bracket(d, tgt_scr[0], tgt_scr[1], tgt_scr[2])

def draw_asteroids(d):
    for a in asteroids:
        a["ang"] += a["spin"]
        rx, ry, rz = rotate_point(a["x"] - player_pos.x, a["y"] - player_pos.y, a["z"] - player_pos.z, -pitch, -yaw, -roll)
        if rz < 4:
            continue
        p = project(rx, ry, rz)
        if rz > 70:
            if p:
                d.pixel(Vector(p[0], p[1]), TFT_LIGHTGREY)
        elif rz > 38:
            if p:
                d.line_custom(Vector(p[0] - 2, p[1]), Vector(p[0] + 2, p[1]), TFT_LIGHTGREY)
        else:
            draw_model_culled(d, ROCK_VERTS, ROCK_FACES, a["x"] - player_pos.x, a["y"] - player_pos.y, a["z"] - player_pos.z, a["sc"], a["ang"], a["ang"] * 0.4, 0.2, TFT_LIGHTGREY)

def draw_traffic(d):
    for t in traffic:
        t["x"] += t["vx"]
        t["z"] += t["vz"]
        if t["z"] < 40:
            t["z"] = random.uniform(110, 170)
            t["x"] = random.uniform(-80, 80)
        rx, ry, rz = rotate_point(t["x"] - player_pos.x, t["y"] - player_pos.y, t["z"] - player_pos.z, -pitch, -yaw, -roll)
        p = project(rx, ry, rz)
        if not p:
            continue
        col = COL_SHIP
        if rz > 90:
            d.pixel(Vector(p[0], p[1]), col)
        elif rz > 50:
            d.line_custom(Vector(p[0] - 2, p[1]), Vector(p[0] + 2, p[1]), col)
        else:
            verts, faces, _, sc = HULLS.get(t["hull"], HULLS["krait"])
            draw_model_culled(d, verts, faces, t["x"] - player_pos.x, t["y"] - player_pos.y, t["z"] - player_pos.z, sc * 0.7, 0.1, frame * 0.01, 0.0, col)

def draw_missiles_and_debris(d):
    for m in missiles_in_flight:
        prev = None
        n = len(m["trail"])
        for i, (tx, ty, tz) in enumerate(m["trail"]):
            rx, ry, rz = rotate_point(tx - player_pos.x, ty - player_pos.y, tz - player_pos.z, -pitch, -yaw, -roll)
            p = project(rx, ry, rz)
            if p and prev:
                fade = 1.0 - (i / max(1, n))
                d.line_custom(Vector(prev[0], prev[1]), Vector(p[0], p[1]), fade565(COL_MISSILE, fade * 0.55))
            if p:
                prev = p
        rx, ry, rz = rotate_point(m["x"] - player_pos.x, m["y"] - player_pos.y, m["z"] - player_pos.z, -pitch, -yaw, -roll)
        p = project(rx, ry, rz)
        if p:
            d.fill_circle(Vector(p[0], p[1]), 2, COL_MISSILE)
    for deb in debris:
        rx, ry, rz = rotate_point(deb["x"] - player_pos.x, deb["y"] - player_pos.y, deb["z"] - player_pos.z, -pitch, -yaw, -roll)
        rx2, ry2, rz2 = rotate_point(deb["x"] + deb["lx"] - player_pos.x, deb["y"] + deb["ly"] - player_pos.y, deb["z"] + deb["lz"] - player_pos.z, -pitch, -yaw, -roll)
        p1 = project(rx, ry, rz)
        p2 = project(rx2, ry2, rz2)
        fade = 1.0 - (deb["life"] / max(1, deb["maxlife"]))
        col = fade565(COL_DEBRIS, fade * 0.7)
        if p1 and p2:
            d.line_custom(Vector(p1[0], p1[1]), Vector(p2[0], p2[1]), col)
        elif p1:
            d.pixel(Vector(p1[0], p1[1]), col)
    for s in sparks:
        rx, ry, rz = rotate_point(s["x"] - player_pos.x, s["y"] - player_pos.y, s["z"] - player_pos.z, -pitch, -yaw, -roll)
        p = project(rx, ry, rz)
        if p:
            d.pixel(Vector(p[0], p[1]), TFT_WHITE if s["life"] > 7 else TFT_ORANGE)
    for w in wrecks:
        pts = []
        ok = True
        for vx, vy, vz in w["pts"]:
            mx, my, mz = rotate_y(vx * w["sc"], vy * w["sc"], vz * w["sc"], w["ang"])
            rx, ry, rz = rotate_point(mx + w["x"], my + w["y"], mz + w["z"], -pitch, -yaw, -roll)
            pr = project(rx, ry, rz)
            if not pr:
                ok = False
                break
            pts.append(pr)
        if ok and len(pts) >= 2:
            col = fade565(w["col"], 1.0 - w["life"] / 26.0)
            d.line_custom(Vector(pts[0][0], pts[0][1]), Vector(pts[1][0], pts[1][1]), col)
            if len(pts) > 2:
                d.line_custom(Vector(pts[1][0], pts[1][1]), Vector(pts[2][0], pts[2][1]), col)
                d.line_custom(Vector(pts[2][0], pts[2][1]), Vector(pts[0][0], pts[0][1]), col)

def draw_laser_fx(d):
    if laser_flash > 0 or laser_temp > 38:
        d.line_custom(Vector(CX - 58, 232), Vector(CX - 5, CY + 7), COL_LASER)
        d.line_custom(Vector(CX - 56, 234), Vector(CX - 4, CY + 9), TFT_CYAN)
        d.line_custom(Vector(CX + 58, 232), Vector(CX + 5, CY + 7), COL_LASER)
        d.line_custom(Vector(CX + 56, 234), Vector(CX + 4, CY + 9), TFT_CYAN)
        if laser_flash > 2:
            d.line_custom(Vector(CX - 57, 233), Vector(CX - 5, CY + 8), TFT_WHITE)
            d.line_custom(Vector(CX + 57, 233), Vector(CX + 5, CY + 8), TFT_WHITE)
        if laser_flash > 3:
            d.fill_rectangle(Vector(0, 0), Vector(320, 250), fade565(TFT_WHITE, 0.82))
    ia = []
    for shot in incoming:
        shot["life"] -= 1
        p0 = project(*rotate_point(shot["x0"] - player_pos.x, shot["y0"] - player_pos.y, shot["z0"] - player_pos.z, -pitch, -yaw, -roll))
        p1 = project(*rotate_point(shot["x1"] - player_pos.x, shot["y1"] - player_pos.y, shot["z1"] - player_pos.z, -pitch, -yaw, -roll))
        if p0 and p1:
            d.line_custom(Vector(p0[0], p0[1]), Vector(p1[0], p1[1]), TFT_RED)
        if shot["life"] > 0:
            ia.append(shot)
    incoming[:] = ia

def draw_hyperspace(d):
    d.fill_screen(COL_BG)
    for i in range(10):
        r = int(8 + (i * 18 + frame * 7) % 160)
        d.circle(Vector(CX, CY), r, fade565(TFT_WHITE, 0.35 + i * 0.05))
    for i in range(28):
        a = i * 0.22 + frame * 0.08
        r0 = 12 + (i * 11 + frame * 9) % 140
        x0 = CX + int(math.cos(a) * r0 * 0.15)
        y0 = CY + int(math.sin(a) * r0 * 0.15)
        x1 = CX + int(math.cos(a) * r0)
        y1 = CY + int(math.sin(a) * r0)
        d.line_custom(Vector(x0, y0), Vector(x1, y1), fade565(TFT_WHITE, 0.4))
    d.text(Vector(110, 290), "HYPERSPACE", COL_TITLE, 1)

def draw_cockpit_and_hud(d):
    d.line_custom(Vector(0, 8), Vector(42, 248), COL_COCKPIT)
    d.line_custom(Vector(320, 8), Vector(278, 248), COL_COCKPIT)
    d.line_custom(Vector(18, 0), Vector(52, 248), fade565(COL_COCKPIT, 0.25))
    d.line_custom(Vector(302, 0), Vector(268, 248), fade565(COL_COCKPIT, 0.25))
    d.fill_rectangle(Vector(0, 250), Vector(320, 70), TFT_BLACK)
    d.line_custom(Vector(0, 250), Vector(320, 250), COL_HUD)
    d.line_custom(Vector(CX - 9, CY), Vector(CX - 3, CY), COL_HUD)
    d.line_custom(Vector(CX + 3, CY), Vector(CX + 9, CY), COL_HUD)
    d.line_custom(Vector(CX, CY - 9), Vector(CX, CY - 3), COL_HUD)
    d.line_custom(Vector(CX, CY + 3), Vector(CX, CY + 9), COL_HUD)
    rx, ry = 160, 286
    d.circle(Vector(rx, ry), 24, COL_RADAR)
    d.circle(Vector(rx, ry), 12, COL_RADAR)
    d.line_custom(Vector(rx - 24, ry), Vector(rx + 24, ry), fade565(COL_RADAR, 0.4))
    d.line_custom(Vector(rx, ry - 24), Vector(rx, ry + 24), fade565(COL_RADAR, 0.4))
    global scan_ang
    scan_ang += 0.09
    d.line_custom(Vector(rx, ry), Vector(rx + int(math.cos(scan_ang) * 23), ry + int(math.sin(scan_ang) * 23)), fade565(COL_HUD, 0.45))
    d.pixel(Vector(rx, ry), COL_HUD)
    srx = planet_pos.x - player_pos.x
    srz = planet_pos.z - player_pos.z
    bdx = int(clamp(srx * 0.11, -22, 22))
    bdy = int(clamp(-srz * 0.11, -22, 22))
    d.line_custom(Vector(rx + bdx, ry + bdy - 2), Vector(rx + bdx + 2, ry + bdy), COL_STATION)
    d.line_custom(Vector(rx + bdx + 2, ry + bdy), Vector(rx + bdx, ry + bdy + 2), COL_STATION)
    d.line_custom(Vector(rx + bdx, ry + bdy + 2), Vector(rx + bdx - 2, ry + bdy), COL_STATION)
    d.line_custom(Vector(rx + bdx - 2, ry + bdy), Vector(rx + bdx, ry + bdy - 2), COL_STATION)
    for e in enemies:
        edx = int(clamp(e["pos"].x * 0.12, -22, 22))
        edy = int(clamp(-e["pos"].z * 0.12, -22, 22))
        bx = rx + edx
        by = ry + edy
        if e.get("type") == "police":
            d.line_custom(Vector(bx - 2, by), Vector(bx + 2, by), COL_POLICE)
            d.line_custom(Vector(bx, by - 2), Vector(bx, by + 2), COL_POLICE)
        else:
            d.fill_rectangle(Vector(bx - 1, by - 1), Vector(3, 3), COL_ENEMY)
        if e["pos"].y > 6:
            d.pixel(Vector(bx, by - 4), COL_HUD)
        elif e["pos"].y < -6:
            d.pixel(Vector(bx, by + 4), COL_HUD)
    hx = 160
    hy = 258
    hr = 10
    d.line_custom(Vector(hx - hr, hy), Vector(hx + hr, hy), COL_HUD_DIM)
    ox = int(math.sin(roll) * 8)
    oy = int(-math.cos(roll) * 3)
    d.line_custom(Vector(hx - 8 + ox, hy + oy), Vector(hx + 8 + ox, hy + oy), COL_HUD)
    if speed > 2.5:
        for _ in range(7):
            a = random.uniform(-1.1, 1.1)
            r0 = random.randint(40, 90)
            r1 = r0 + int(8 + speed * 3)
            x0 = CX + int(math.sin(a) * r0)
            y0 = CY + int(math.cos(a) * r0 * 0.7)
            x1 = CX + int(math.sin(a) * r1)
            y1 = CY + int(math.cos(a) * r1 * 0.7)
            if 0 < y0 < 248 and 0 < y1 < 248:
                d.line_custom(Vector(x0, y0), Vector(x1, y1), COL_STAR_DIM)
    sys = SYSTEMS[current_system]
    d.text(Vector(6, 268), sys["name"][:8], COL_HUD, 1)
    d.text(Vector(6, 282), str(credits), COL_HUD, 1)
    d.text(Vector(6, 296), rank_name[:10], COL_RANK, 1)
    d.fill_rectangle(Vector(228, 268), Vector(int(energy * 0.7), 6), COL_HUD if energy > 30 else COL_ALERT)
    d.rect(Vector(228, 268), Vector(70, 6), COL_HUD_DIM)
    d.fill_rectangle(Vector(228, 282), Vector(int(laser_temp * 0.7), 6), COL_ALERT if laser_temp > 70 else COL_HUD)
    d.rect(Vector(228, 282), Vector(70, 6), COL_HUD_DIM)
    d.fill_rectangle(Vector(228, 296), Vector(int(speed / max_speed * 70), 6), COL_HUD)
    d.rect(Vector(228, 296), Vector(70, 6), COL_HUD_DIM)
    if docked:
        d.text(Vector(132, 254), "DOCKED", COL_ALERT, 1)
    if docking_phase > 0:
        d.text(Vector(108, 96), "DOCKING", COL_TITLE, 2)
    if wanted > 0:
        d.text(Vector(118, 254), "WANTED", COL_ALERT, 1)
    if message_timer > 0:
        d.text(Vector(70, 108), message, COL_ALERT, 1)

def draw_title(d):
    global title_angle, pitch, yaw, roll
    d.fill_screen(COL_BG)
    for sx, sy, b in title_stars:
        d.pixel(Vector(sx, sy), COL_STAR_NEAR if b > 0.55 else COL_STAR_DIM)
    d.fill_circle(Vector(268, 48), 7, COL_SUN)
    d.circle(Vector(268, 48), 11, COL_CORONA)
    d.circle(Vector(52, 168), 18, COL_PLANET_DAY)
    d.circle(Vector(52, 168), 12, COL_PLANET_NIGHT)
    d.circle(Vector(86, 156), 6, COL_STATION)
    d.line_custom(Vector(80, 156), Vector(92, 156), COL_STATION)
    d.line_custom(Vector(86, 150), Vector(86, 162), COL_STATION)
    old_p, old_y, old_r = pitch, yaw, roll
    pitch = yaw = roll = 0.0
    title_angle += 0.032
    draw_model_culled(d, COBRA_VERTS, COBRA_FACES, 0, 0.15, 6.4, 27.0, 0.22, title_angle, 0.12 + math.sin(title_angle * 0.4) * 0.08, COL_SHIP)
    pitch, yaw, roll = old_p, old_y, old_r
    d.text(Vector(68, 10), "PICO ELITE", COL_TITLE, 3)
    d.line_custom(Vector(64, 34), Vector(256, 34), COL_TITLE)
    old_p, old_y, old_r = pitch, yaw, roll
    pitch = yaw = roll = 0.0
    draw_model_culled(d, STATION_VERTS, STATION_FACES, 2.8, -0.6, 9.5, 9.0, 0.4, title_angle * 0.6, 0.2, COL_STATION)
    pitch, yaw, roll = old_p, old_y, old_r
    d.text(Vector(52, 40), "A tribute to Braben & Bell", COL_HUD, 1)
    d.text(Vector(28, 198), "CENTER Launch", TFT_WHITE, 1)
    d.text(Vector(28, 214), "F Laser   M Missile", TFT_WHITE, 1)
    d.text(Vector(28, 230), "H Jump    D Dock", TFT_WHITE, 1)
    d.text(Vector(28, 246), "1 Status  2 System  3 Chart", TFT_WHITE, 1)
    d.text(Vector(28, 262), "4 Save  L Load  5 Missions", TFT_WHITE, 1)
    d.text(Vector(28, 278), "6 Galaxy  7 News", TFT_WHITE, 1)
    d.text(Vector(70, 296), rank_name, COL_RANK, 1)

def draw_market(d):
    d.fill_screen(COL_BG)
    sys = SYSTEMS[current_system]
    d.text(Vector(8, 4), f"MARKET  -  {sys['name']}", COL_TITLE, 2)
    ev = ""
    if market_event and market_event.get("sys") == current_system:
        ev = "  DROUGHT" if market_event["kind"] == "drought" else "  WAR"
    d.text(Vector(8, 28), f"{sys['gov']}   Tech {sys['tech']}   {sys['prod']}{ev}", COL_HUD_DIM, 1)
    d.text(Vector(8, 42), f"Credits: {credits}    Cargo: {sum(cargo.values())}/{cargo_capacity}", COL_HUD, 1)
    d.text(Vector(8, 60), "  Commodity        Price  Own", COL_HUD, 1)
    d.line_custom(Vector(8, 74), Vector(300, 74), COL_HUD_DIM)
    y = 78
    start_i = max(0, market_sel - 10)
    for i, name in enumerate(COMMODITIES):
        if i < start_i:
            continue
        if y > 240:
            break
        price = market.get(name, 0)
        own = cargo.get(name, 0)
        selected = (i == market_sel)
        if selected:
            d.fill_rectangle(Vector(6, y - 1), Vector(308, 13), 0x0841)
            col = TFT_YELLOW
            prefix = ">"
        else:
            col = TFT_GREEN if own > 0 else TFT_WHITE
            prefix = " "
        d.text(Vector(8, y), f"{prefix}{name[:14]:14} {price:4}   {own:2}", col, 1)
        y += 13
    d.text(Vector(8, 255), "EQUIPMENT", COL_TITLE, 1)
    equip_items = ["cargo_bay", "ecm", "beam_laser", "missile"]
    names = {"cargo_bay": "Cargo Bay +15", "ecm": "ECM System", "beam_laser": "Beam Laser", "missile": "Missile"}
    ey = 270
    for j, item in enumerate(equip_items):
        owned = equipment.get(item, False) if item != "missile" else False
        price = EQUIP_PRICES[item]
        sel = (j == equip_sel)
        col = TFT_YELLOW if sel else (TFT_GREEN if owned else TFT_WHITE)
        pre = ">" if sel else " "
        own_txt = "OWNED" if owned else f"{price} Cr"
        if item == "missile":
            own_txt = f"{missiles}/{max_missiles}"
        d.text(Vector(8, ey), f"{pre}{names[item]:16} {own_txt}", col, 1)
        ey += 12

def draw_status(d):
    d.fill_screen(COL_BG)
    d.text(Vector(80, 8), "COMMANDER STATUS", COL_TITLE, 2)
    d.text(Vector(20, 40), f"Rank: {rank_name}", COL_RANK, 1)
    d.text(Vector(20, 58), f"Credits: {credits}", COL_HUD, 1)
    d.text(Vector(20, 76), f"Kills: {kills}", COL_HUD, 1)
    d.text(Vector(20, 128), f"Wanted: {'YES' if wanted > 0 else 'No'}", COL_ALERT if wanted > 0 else COL_HUD, 1)
    d.text(Vector(20, 94), f"Missiles: {missiles}", COL_HUD, 1)
    d.text(Vector(20, 112), f"Energy: {energy}", COL_HUD, 1)
    d.text(Vector(20, 140), "EQUIPMENT", COL_TITLE, 1)
    d.text(Vector(30, 158), f"Laser: {'Beam' if laser_power > 1 else 'Pulse'}", COL_HUD, 1)
    d.text(Vector(30, 176), f"Cargo Bay: {'Expanded' if equipment.get('cargo_bay') else 'Standard'}", COL_HUD, 1)
    d.text(Vector(30, 194), f"ECM: {'Fitted' if equipment.get('ecm') else 'None'}", COL_HUD, 1)
    d.text(Vector(20, 230), "CARGO", COL_TITLE, 1)
    y = 248
    if not cargo:
        d.text(Vector(30, y), "Empty", COL_HUD_DIM, 1)
    else:
        for name, qty in cargo.items():
            d.text(Vector(30, y), f"{name}: {qty}", COL_HUD, 1)
            y += 14
            if y > 300:
                break

def draw_system(d):
    d.fill_screen(COL_BG)
    sys = SYSTEMS[current_system]
    d.text(Vector(60, 8), "SYSTEM DATA", COL_TITLE, 2)
    d.text(Vector(20, 50), f"System: {sys['name']}", COL_HUD, 1)
    d.text(Vector(20, 70), f"Government: {sys['gov']}", COL_HUD, 1)
    d.text(Vector(20, 90), f"Tech Level: {sys['tech']}", COL_HUD, 1)
    d.text(Vector(20, 110), f"Economy: {sys['prod']}", COL_HUD, 1)
    d.text(Vector(20, 150), "Police patrol lawful systems.", COL_HUD_DIM, 1)
    d.text(Vector(20, 166), "Illegal cargo draws Vipers.", COL_HUD_DIM, 1)
    if market_event and market_event.get("sys") == current_system:
        kind = market_event["kind"]
        d.text(Vector(20, 190), "Event: " + ("Drought" if kind == "drought" else "War"), COL_RANK, 1)
    if wanted > 0:
        d.text(Vector(20, 210), "Status: WANTED", COL_ALERT, 1)

def draw_chart(d):
    d.fill_screen(COL_BG)
    d.text(Vector(40, 8), GALAXY_NAMES[current_galaxy][:18], COL_TITLE, 2)
    positions = [
        (80, 100), (200, 70), (50, 160), (180, 140),
        (250, 110), (40, 220), (160, 200), (120, 250)
    ]
    for i, sys in enumerate(SYSTEMS):
        x, y = positions[i]
        col = COL_TITLE if i == current_system else COL_HUD
        d.fill_circle(Vector(x, y), 4, col)
        d.text(Vector(x - 20, y + 8), sys["name"][:8], col, 1)
        if i == current_system:
            d.circle(Vector(x, y), 8, COL_ALERT)

def draw_missions(d):
    d.fill_screen(COL_BG)
    d.text(Vector(80, 8), "MISSION BOARD", COL_TITLE, 2)
    if mission:
        d.text(Vector(16, 36), "ACTIVE", COL_RANK, 1)
        d.text(Vector(16, 52), mission.get("label", ""), COL_HUD, 1)
        if mission.get("kind") == "kill":
            d.text(Vector(16, 68), "Progress " + str(mission_kills) + "/" + str(mission.get("need", 0)), COL_HUD, 1)
        elif mission.get("kind") == "deliver":
            d.text(Vector(16, 68), "Take cargo to " + SYSTEMS[mission["dest"]]["name"], COL_HUD, 1)
        elif mission.get("kind") == "visit":
            d.text(Vector(16, 68), "Jump to " + SYSTEMS[mission["dest"]]["name"], COL_HUD, 1)
        else:
            d.text(Vector(16, 68), "Destroy marked " + str(mission.get("hull", "")), COL_HUD, 1)
        d.text(Vector(16, 84), "Pay " + str(mission.get("pay", 0)) + " Cr", COL_HUD, 1)
    else:
        d.text(Vector(16, 36), "No active contract", COL_HUD_DIM, 1)
    y = 120
    d.text(Vector(16, 104), "AVAILABLE", COL_TITLE, 1)
    for i, m in enumerate(board):
        sel = i == board_sel
        col = TFT_YELLOW if sel else TFT_WHITE
        pre = ">" if sel else " "
        d.text(Vector(16, y), pre + m["label"], col, 1)
        d.text(Vector(24, y + 14), str(m["pay"]) + " Cr", COL_HUD_DIM, 1)
        y += 28
    d.text(Vector(16, 292), "Up/Dn  CENTER accept  BACK", COL_HUD_DIM, 1)

def draw_galaxy(d):
    d.fill_screen(COL_BG)
    d.text(Vector(70, 8), "GALAXY MAP", COL_TITLE, 2)
    d.text(Vector(16, 36), "Now: " + GALAXY_NAMES[current_galaxy], COL_HUD, 1)
    y = 70
    for i, name in enumerate(GALAXY_NAMES):
        sel = i == galaxy_sel
        col = TFT_YELLOW if sel else (COL_TITLE if i == current_galaxy else TFT_WHITE)
        pre = ">" if sel else " "
        d.text(Vector(24, y), pre + name, col, 1)
        d.text(Vector(40, y + 14), str(len(GALAXY_DATA[i])) + " systems", COL_HUD_DIM, 1)
        y += 40
    d.text(Vector(16, 250), "CENTER jump galaxy", COL_HUD_DIM, 1)
    d.text(Vector(16, 268), "Costs 200 Cr", COL_HUD_DIM, 1)

def draw_news(d):
    d.fill_screen(COL_BG)
    d.text(Vector(90, 8), "BULLETIN", COL_TITLE, 2)
    d.text(Vector(16, 40), GALAXY_NAMES[current_galaxy] + " / " + SYSTEMS[current_system]["name"], COL_HUD, 1)
    if market_event and market_event.get("sys") == current_system:
        kind = market_event["kind"]
        d.text(Vector(16, 64), "Market: " + ("DROUGHT" if kind == "drought" else "WAR"), COL_RANK, 1)
    else:
        d.text(Vector(16, 64), "Market: stable", COL_HUD_DIM, 1)
    d.text(Vector(16, 88), "Wanted: " + ("YES" if wanted > 0 else "No"), COL_ALERT if wanted > 0 else COL_HUD, 1)
    if mission:
        d.text(Vector(16, 112), "Contract: " + mission.get("label", ""), COL_HUD, 1)
    else:
        d.text(Vector(16, 112), "No active contract", COL_HUD_DIM, 1)
    d.text(Vector(16, 148), "Galaxies: " + str(len(GALAXY_NAMES)), COL_HUD, 1)
    d.text(Vector(16, 164), "Rank: " + rank_name, COL_RANK, 1)
    d.text(Vector(16, 196), "Police hunt illegal cargo", COL_HUD_DIM, 1)
    d.text(Vector(16, 212), "and anyone who fires on Vipers.", COL_HUD_DIM, 1)

def launch():
    global docked, game_mode, speed, message, message_timer, spawn_timer, docking_phase
    if not docked:
        return
    docked = False
    docking_phase = 0
    game_mode = "flight"
    speed = 0.8
    message = "Launch sequence complete"
    message_timer = 40
    beep(520, 35)
    generate_stars()
    generate_dust()
    enemies.clear()
    sparks.clear()
    wrecks.clear()
    if mission and mission.get("kind") == "bounty":
        spawn_bounty(mission["hull"])
    spawn_timer = 100

def attempt_dock():
    global game_mode, message, message_timer, docking_phase, docking_timer, speed
    if docked:
        game_mode = "market"
        return
    if docking_phase > 0:
        return
    dist = math.sqrt(
        (player_pos.x - planet_pos.x) ** 2 +
        (player_pos.y - planet_pos.y) ** 2 +
        (player_pos.z - planet_pos.z) ** 2)
    if dist < planet_radius + 28 and speed < 2.0:
        docking_phase = 1
        docking_timer = 45
        speed = 0.3
        message = "Aligning with station"
        message_timer = 40
    else:
        message = "Approach slowly and closer"
        message_timer = 30

def finish_dock():
    global docked, game_mode, speed, message, message_timer, docking_phase
    docked = True
    speed = 0
    docking_phase = 0
    game_mode = "market"
    message = "Docking successful"
    message_timer = 50
    beep(400, 45)
    generate_market(current_system)
    generate_board()
    enemies.clear()
    missiles_in_flight.clear()
    debris.clear()
    sparks.clear()
    wrecks.clear()
    check_delivery()

def do_hyperspace():
    global current_system, player_pos, pitch, yaw, roll, speed
    global message, message_timer, game_mode, docked, hyperspace_cool, jump_timer, docking_phase, jump_flash
    if hyperspace_cool > 0:
        message = "Drive recharging"
        message_timer = 25
        return
    if mission and mission.get("kind") in ("kill", "bounty"):
        fail_mission("Contract abandoned")
    hyperspace_cool = 40
    jump_flash = 3
    jump_timer = 28
    apply_system_look()
    generate_asteroids()
    generate_traffic()
    old = current_system
    while current_system == old:
        current_system = random.randint(0, len(SYSTEMS) - 1)
    player_pos = Vector(0, 0, 0)
    pitch = yaw = roll = 0.0
    speed = 0.0
    generate_stars()
    generate_market(current_system)
    generate_board()
    enemies.clear()
    missiles_in_flight.clear()
    debris.clear()
    message = f"Hyperspace to {SYSTEMS[current_system]['name']}"
    message_timer = 60
    game_mode = "flight"
    docked = False
    docking_phase = 0
    check_delivery()
    check_visit()
    beep(180, 60)

def jump_galaxy():
    global credits, message, message_timer, game_mode, docked, player_pos, pitch, yaw, roll, speed
    if credits < 200:
        message = "Need 200 Cr"
        message_timer = 30
        return
    credits -= 200
    if mission and mission.get("kind") in ("kill", "bounty", "visit", "deliver"):
        fail_mission("Contract abandoned")
    set_galaxy(galaxy_sel)
    player_pos = Vector(0, 0, 0)
    pitch = yaw = roll = 0.0
    speed = 0.0
    docked = False
    game_mode = "flight"
    generate_stars()
    generate_market(current_system)
    generate_board()
    apply_system_look()
    generate_asteroids()
    generate_traffic()
    enemies.clear()
    missiles_in_flight.clear()
    debris.clear()
    message = "Entered " + GALAXY_NAMES[current_galaxy]
    message_timer = 50
    beep(160, 70)

def save_commander():
    global message, message_timer
    if storage is None:
        message = "No storage"
        message_timer = 30
        return
    try:
        lines = []
        lines.append("credits=" + str(int(credits)))
        lines.append("kills=" + str(int(kills)))
        lines.append("rank=" + rank_name)
        lines.append("missiles=" + str(int(missiles)))
        lines.append("laser=" + str(int(laser_power)))
        lines.append("cap=" + str(int(cargo_capacity)))
        lines.append("sys=" + str(int(current_system)))
        lines.append("energy=" + str(int(energy)))
        lines.append("ecm=" + ("1" if equipment.get("ecm") else "0"))
        lines.append("bay=" + ("1" if equipment.get("cargo_bay") else "0"))
        clist = []
        for k, v in cargo.items():
            clist.append(k.replace(" ", "_") + ":" + str(int(v)))
        lines.append("cargo=" + ",".join(clist))
        storage.write("picoware/elite_save.txt", "\n".join(lines) + "\n", mode="w")
        message = "Commander saved"
        message_timer = 40
    except:
        message = "Save failed"
        message_timer = 30

def load_commander():
    global credits, kills, rank_name, missiles, cargo, equipment, laser_power
    global cargo_capacity, current_system, energy, message, message_timer
    if storage is None:
        message = "No storage"
        message_timer = 30
        return
    try:
        raw = storage.read("picoware/elite_save.txt")
        if not raw:
            message = "No save found"
            message_timer = 30
            return
        data = {}
        for line in raw.split("\n"):
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
        credits = int(data.get("credits", "1000"))
        kills = int(data.get("kills", "0"))
        rank_name = data.get("rank", "Harmless")
        missiles = int(data.get("missiles", "3"))
        laser_power = int(data.get("laser", "1"))
        cargo_capacity = int(data.get("cap", "20"))
        current_system = int(data.get("sys", "0"))
        energy = int(data.get("energy", "100"))
        equipment["ecm"] = data.get("ecm", "0") == "1"
        equipment["cargo_bay"] = data.get("bay", "0") == "1"
        equipment["pulse_laser"] = laser_power <= 1
        cargo = {}
        cs = data.get("cargo", "")
        if cs:
            for part in cs.split(","):
                if ":" in part:
                    n, q = part.split(":", 1)
                    cargo[n.replace("_", " ")] = int(q)
        message = "Commander loaded"
        message_timer = 40
        generate_market(current_system)
        generate_board()
        apply_system_look()
        generate_asteroids()
        generate_traffic()
        update_rank()
    except:
        message = "Load failed"
        message_timer = 30

def update_flight(button):
    global pitch, yaw, roll, speed, thrust, player_pos
    global laser_temp, energy, message_timer, spawn_timer, frame
    global docking_phase, docking_timer, hyperspace_cool, jump_timer, laser_flash, ecm_cool, jump_flash

    if jump_flash > 0:
        jump_flash -= 1
        frame += 1
        return
    if jump_timer > 0:
        jump_timer -= 1
        frame += 1
        return

    if docking_phase > 0:
        docking_timer -= 1
        if docking_timer <= 0:
            finish_dock()
        return

    if button == BUTTON_UP or button == BUTTON_W:
        pitch -= 0.055
    elif button == BUTTON_DOWN or button == BUTTON_S:
        pitch += 0.055
    if button == BUTTON_LEFT or button == BUTTON_A:
        yaw -= 0.055
    elif button == BUTTON_RIGHT or button == BUTTON_D:
        yaw += 0.055
    if button == BUTTON_Q:
        roll -= 0.07
    elif button == BUTTON_E:
        roll += 0.07

    if button in (BUTTON_SPACE, BUTTON_CENTER, BUTTON_OK, BUTTON_ENTER):
        thrust = 0.12
    else:
        thrust = -0.035

    speed = clamp(speed + thrust, 0.0, max_speed)

    fx, fy, fz = rotate_point(0.0, 0.0, 1.0, pitch, yaw, roll)
    dx = fx * speed * 0.75
    dy = fy * speed * 0.75
    dz = fz * speed * 0.75
    player_pos.x += dx
    player_pos.y += dy
    player_pos.z += dz

    update_stars(dx * 0.45, dy * 0.45, dz * 0.45)

    if laser_temp > 0:
        laser_temp = max(0, laser_temp - 1.6)
    if energy < 100 and frame % 2 == 0:
        energy = min(100, energy + 1)
    if hyperspace_cool > 0:
        hyperspace_cool -= 1
    if laser_flash > 0:
        laser_flash -= 1
    if ecm_cool > 0:
        ecm_cool -= 1

    spawn_timer -= 1
    if spawn_timer <= 0 and len(enemies) < 2 and not docked:
        if random.random() < 0.55:
            spawn_enemy()
        spawn_timer = random.randint(100, 260)

    update_enemies()
    update_missiles()
    update_debris()

    if message_timer > 0:
        message_timer -= 1
    frame += 1

def start(view_manager):
    global draw, input_mgr, storage, game_mode, credits, cargo, current_system
    global player_pos, pitch, yaw, roll, speed, docked
    global energy, laser_temp, kills, rank_name, missiles, equipment, laser_power
    global cargo_capacity, enemies, market_sel, equip_sel, docking_phase, jump_timer, laser_flash
    global mission, mission_kills, board_sel, ecm_cool, jump_flash, wanted, audio, galaxy_sel

    draw = view_manager.draw
    input_mgr = view_manager.input_manager
    try:
        storage = Storage()
    except:
        storage = None
    try:
        audio = Audio()
        audio.set_volume(60)
    except:
        audio = None
    set_galaxy(0)

    game_mode = "title"
    credits = 1000
    cargo = {}
    current_system = 0
    player_pos = Vector(0, 0, 0)
    pitch = yaw = roll = 0.0
    speed = 0.0
    docked = True
    energy = 100
    laser_temp = 0
    kills = 0
    rank_name = "Harmless"
    missiles = 3
    equipment = {"pulse_laser": True, "cargo_bay": False, "ecm": False}
    laser_power = 1
    cargo_capacity = 20
    enemies = []
    market_sel = 0
    equip_sel = 0
    docking_phase = 0
    jump_timer = 0
    laser_flash = 0
    ecm_cool = 0
    mission = None
    mission_kills = 0
    board_sel = 0
    wanted = 0
    incoming.clear()
    generate_market(0)
    generate_board()
    generate_stars()
    generate_title_stars()
    generate_sky()
    generate_dust()
    apply_system_look()
    generate_asteroids()
    generate_traffic()
    sparks.clear()
    wrecks.clear()
    jump_flash = 0
    draw.fill_screen(COL_BG)
    draw.swap()
    return True

def run(view_manager):
    global game_mode, message_timer, market_sel, equip_sel, message, board_sel, galaxy_sel

    button = input_mgr.button
    input_mgr.reset()

    if button == BUTTON_BACK or button == BUTTON_ESCAPE:
        if game_mode in ("market", "status", "system", "chart", "missions", "galaxy", "news"):
            game_mode = "flight" if not docked else "title"
        elif game_mode == "flight":
            game_mode = "title"
        else:
            view_manager.back()
            return

    if game_mode == "title":
        if button in (BUTTON_CENTER, BUTTON_SPACE, BUTTON_OK, BUTTON_ENTER):
            launch()
        if button == BUTTON_L:
            load_commander()
        draw_title(draw)
        draw.swap()
        return

    if game_mode == "market":
        if button == BUTTON_UP:
            if market_sel > 0 or equip_sel > 0:
                if equip_sel > 0:
                    equip_sel -= 1
                else:
                    market_sel = max(0, market_sel - 1)
        elif button == BUTTON_DOWN:
            if market_sel < len(COMMODITIES) - 1:
                market_sel += 1
            else:
                equip_sel = min(3, equip_sel + 1)
        elif button in (BUTTON_CENTER, BUTTON_OK, BUTTON_ENTER):
            if market_sel < len(COMMODITIES) and equip_sel == 0:
                name = COMMODITIES[market_sel]
                if buy(name):
                    message = f"Bought {name}"
                    message_timer = 25
                else:
                    message = "Cannot buy"
                    message_timer = 25
            else:
                items = ["cargo_bay", "ecm", "beam_laser", "missile"]
                item = items[equip_sel]
                if buy_equip(item):
                    message = "Purchased"
                    message_timer = 25
                else:
                    message = "Cannot buy"
                    message_timer = 25
        elif button == BUTTON_0 or button == BUTTON_S:
            name = COMMODITIES[market_sel]
            if sell(name):
                message = f"Sold {name}"
                message_timer = 25
            else:
                message = "Nothing to sell"
                message_timer = 25
        draw_market(draw)
        if message_timer > 0:
            message_timer -= 1
        draw.swap()
        return

    if game_mode == "status":
        draw_status(draw)
        draw.swap()
        return
    if game_mode == "system":
        draw_system(draw)
        draw.swap()
        return
    if game_mode == "chart":
        draw_chart(draw)
        draw.swap()
        return
    if game_mode == "galaxy":
        if button == BUTTON_UP:
            galaxy_sel = (galaxy_sel - 1) % len(GALAXY_NAMES)
        elif button == BUTTON_DOWN:
            galaxy_sel = (galaxy_sel + 1) % len(GALAXY_NAMES)
        elif button in (BUTTON_CENTER, BUTTON_OK, BUTTON_ENTER):
            jump_galaxy()
        draw_galaxy(draw)
        if message_timer > 0:
            message_timer -= 1
        draw.swap()
        return
    if game_mode == "news":
        draw_news(draw)
        draw.swap()
        return
    if game_mode == "missions":
        if button == BUTTON_UP:
            board_sel = (board_sel - 1) % max(1, len(board))
        elif button == BUTTON_DOWN:
            board_sel = (board_sel + 1) % max(1, len(board))
        elif button in (BUTTON_CENTER, BUTTON_OK, BUTTON_ENTER):
            take_mission(board_sel)
        draw_missions(draw)
        if message_timer > 0:
            message_timer -= 1
        draw.swap()
        return

    if jump_timer <= 0:
        if button == BUTTON_H:
            do_hyperspace()
        elif button == BUTTON_D:
            attempt_dock()
        elif button == BUTTON_F:
            fire_laser()
        elif button == BUTTON_M:
            fire_missile()
        elif button == BUTTON_1:
            game_mode = "status"
        elif button == BUTTON_2:
            game_mode = "system"
        elif button == BUTTON_3:
            game_mode = "chart"
        elif button == BUTTON_4:
            save_commander()
        elif button == BUTTON_5:
            if not board:
                generate_board()
            game_mode = "missions"
        elif button == BUTTON_6:
            game_mode = "galaxy"
        elif button == BUTTON_7:
            game_mode = "news"

    update_flight(button)

    if jump_flash > 0:
        draw.fill_screen(TFT_WHITE)
        draw.swap()
        return
    if jump_timer > 0:
        draw_hyperspace(draw)
        draw.swap()
        return

    draw.fill_screen(COL_BG)
    draw_stars(draw)
    draw_sun(draw)
    draw_planet(draw)
    draw_station(draw)
    draw_asteroids(draw)
    draw_traffic(draw)
    draw_enemies(draw)
    draw_missiles_and_debris(draw)
    draw_laser_fx(draw)
    draw_cockpit_and_hud(draw)
    draw.swap()

def stop(view_manager):
    global draw, input_mgr, storage, stars, cargo, market, enemies, missiles_in_flight, debris, title_stars
    draw = None
    input_mgr = None
    storage = None
    if audio:
        try:
            audio.stop()
        except:
            pass
    audio = None
    stars = []
    title_stars = []
    cargo = {}
    market = {}
    enemies = []
    missiles_in_flight = []
    debris = []
    sparks = []
    wrecks = []
    dust = []
    sky_stars = []
    gc.collect()