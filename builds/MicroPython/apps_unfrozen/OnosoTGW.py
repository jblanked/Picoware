from picoware.system.vector import Vector
from picoware.system.colors import (
    TFT_GREEN, TFT_YELLOW, TFT_CYAN, TFT_RED, TFT_ORANGE,
    TFT_WHITE, TFT_DARKGREY, TFT_BLUE, TFT_BLACK
)
from picoware.system.buttons import (
    BUTTON_BACK, BUTTON_ENTER, BUTTON_BACKSPACE, BUTTON_OK, BUTTON_CENTER,
    BUTTON_A, BUTTON_B, BUTTON_C, BUTTON_D, BUTTON_E, BUTTON_F, BUTTON_G,
    BUTTON_H, BUTTON_I, BUTTON_J, BUTTON_K, BUTTON_L, BUTTON_M, BUTTON_N,
    BUTTON_O, BUTTON_P, BUTTON_Q, BUTTON_R, BUTTON_S, BUTTON_T, BUTTON_U,
    BUTTON_V, BUTTON_W, BUTTON_X, BUTTON_Y, BUTTON_Z,
    BUTTON_0, BUTTON_1, BUTTON_2, BUTTON_3, BUTTON_4,
    BUTTON_5, BUTTON_6, BUTTON_7, BUTTON_8, BUTTON_9,
    BUTTON_SPACE, BUTTON_PERIOD, BUTTON_MINUS, BUTTON_SLASH
)

def _rand(n):
    if n <= 0:
        return 0
    try:
        import urandom
        return urandom.getrandbits(16) % n
    except Exception:
        return 3 % n

MAP_W = 25
MAP_H = 25
MAX_LOG = 10
VIEW_W = 21
VIEW_H = 11

EMPTY = 0
BATTLE = 1
OUTPOST = 2
DEPOT = 3
WRECK = 4
EXTRACT = 5

NAMES = {
    0: "Open sector",
    1: "Battlefield",
    2: "Outpost",
    3: "Supply depot",
    4: "Wreckage",
    5: "Extraction point",
}
SYM = {0: ".", 1: "B", 2: "O", 3: "D", 4: "W", 5: "E"}

COL_EMPTY = TFT_BLACK
COL_BATTLE = TFT_RED
COL_OUTPOST = TFT_ORANGE
COL_DEPOT = TFT_BLUE
COL_WRECK = TFT_DARKGREY
COL_EXTRACT = TFT_GREEN
COL_PLAYER = TFT_CYAN

SYM_COL = {
    0: COL_EMPTY,
    1: COL_BATTLE,
    2: COL_OUTPOST,
    3: COL_DEPOT,
    4: COL_WRECK,
    5: COL_EXTRACT,
}

KEYMAP = {
    BUTTON_A: "A", BUTTON_B: "B", BUTTON_C: "C", BUTTON_D: "D",
    BUTTON_E: "E", BUTTON_F: "F", BUTTON_G: "G", BUTTON_H: "H",
    BUTTON_I: "I", BUTTON_J: "J", BUTTON_K: "K", BUTTON_L: "L",
    BUTTON_M: "M", BUTTON_N: "N", BUTTON_O: "O", BUTTON_P: "P",
    BUTTON_Q: "Q", BUTTON_R: "R", BUTTON_S: "S", BUTTON_T: "T",
    BUTTON_U: "U", BUTTON_V: "V", BUTTON_W: "W", BUTTON_X: "X",
    BUTTON_Y: "Y", BUTTON_Z: "Z",
    BUTTON_0: "0", BUTTON_1: "1", BUTTON_2: "2", BUTTON_3: "3",
    BUTTON_4: "4", BUTTON_5: "5", BUTTON_6: "6", BUTTON_7: "7",
    BUTTON_8: "8", BUTTON_9: "9",
    BUTTON_SPACE: " ", BUTTON_PERIOD: ".", BUTTON_MINUS: "-",
    BUTTON_SLASH: "/",
}

lines = []
inp = ""
game_over = False
won = False
px = 0
py = 0
fuel = 100
rations = 50
hull = 50
credits = 40
medkits = 2
world = None
state = "cli"


def add(msg):
    global lines
    s = str(msg)
    if len(s) > 38:
        s = s[:38]
    lines.append(s)
    while len(lines) > MAX_LOG:
        lines.pop(0)


def draw_cli(vm):
    d = vm.draw
    d.erase()
    d.text(Vector(2, 1), "ONOSO: THE GREAT WAR", TFT_ORANGE, 1)
    y = 14
    for line in lines:
        col = TFT_GREEN
        if line and line[0] == "!":
            col = TFT_RED
        elif line and line[0] == "*":
            col = TFT_YELLOW
        d.text(Vector(2, y), line, col, 1)
        y += 11
    d.text(Vector(2, 220), ("> " + inp + "_")[:38], TFT_CYAN, 1)
    d.swap()


def draw_map(vm):
    d = vm.draw
    d.erase()
    d.text(Vector(2, 1), "MAP 25x25  OK=back", TFT_ORANGE, 1)
    d.text(Vector(2, 13), "E=Extract @=You", TFT_YELLOW, 1)

    half_w = VIEW_W // 2
    half_h = VIEW_H // 2
    x0 = px - half_w
    y0 = py - half_h
    if x0 < 0:
        x0 = 0
    if y0 < 0:
        y0 = 0
    if x0 + VIEW_W > MAP_W:
        x0 = MAP_W - VIEW_W
    if y0 + VIEW_H > MAP_H:
        y0 = MAP_H - VIEW_H
    if x0 < 0:
        x0 = 0
    if y0 < 0:
        y0 = 0

    cell_w = 14
    start_x = 4
    start_y = 28

    for row in range(VIEW_H):
        y = y0 + row
        if y >= MAP_H:
            break
        for col in range(VIEW_W):
            x = x0 + col
            if x >= MAP_W:
                break
            sx = start_x + col * cell_w
            sy = start_y + row * 14
            if x == px and y == py:
                d.text(Vector(sx, sy), "@", COL_PLAYER, 1)
            else:
                s = world[y][x]
                ch = SYM.get(s, ".")
                colr = SYM_COL.get(s, TFT_DARKGREY)
                d.text(Vector(sx, sy), ch, colr, 1)

    d.text(Vector(2, 200), "B=Red O=Orange D=Blue W=Grey E=Green", TFT_WHITE, 1)
    d.swap()


def draw(vm):
    if state == "map":
        draw_map(vm)
    else:
        draw_cli(vm)


def gen_map():
    global world
    world = [[EMPTY for _ in range(MAP_W)] for _ in range(MAP_H)]
    for y in range(MAP_H):
        for x in range(MAP_W):
            r = _rand(100)
            if r < 12:
                world[y][x] = BATTLE
            elif r < 20:
                world[y][x] = OUTPOST
            elif r < 28:
                world[y][x] = DEPOT
            elif r < 35:
                world[y][x] = WRECK
    world[MAP_H - 1][MAP_W - 1] = EXTRACT
    world[0][0] = EMPTY
    world[0][1] = EMPTY
    world[1][0] = EMPTY


def sector():
    return world[py][px]


def status_line():
    return "F:%d R:%d H:%d C:%d [%d,%d]" % (fuel, rations, hull, credits, px + 1, py + 1)


def do_look():
    s = sector()
    add("* " + NAMES.get(s, "?"))
    add(status_line())


def do_status():
    add("--- STATUS ---")
    add("Fuel %d  Rations %d" % (fuel, rations))
    add("Hull %d  Credits %d" % (hull, credits))
    add("Medkits %d" % medkits)
    add("Pos %d,%d / 25x25" % (px + 1, py + 1))


def do_map():
    global state
    state = "map"


def do_camp():
    global fuel, rations, hull, credits, medkits
    s = sector()
    if s == EMPTY:
        add("Nothing here.")
        return
    if s == OUTPOST:
        g = 5 + _rand(8)
        credits += g
        rations += 2
        add("Trade +%d credits." % g)
    elif s == DEPOT:
        fuel += 6 + _rand(6)
        rations += 3
        add("Depot scavenged.")
    elif s == BATTLE:
        if _rand(100) < 35:
            dmg = 4 + _rand(8)
            hull -= dmg
            add("! Ambush -%d hull." % dmg)
        else:
            credits += 4 + _rand(8)
            add("Salvage ok.")
    elif s == WRECK:
        medkits += 1
        add("+1 medkit.")
    else:
        add("No camp action.")
    check_end()


def do_fight():
    global hull, credits
    s = sector()
    if s == EMPTY or s == EXTRACT:
        add("No hostiles.")
        return
    ehp = 20 + _rand(15)
    edmg = 5 + _rand(6)
    add("! Fight starts")
    pdmg = 10 + _rand(10)
    ehp -= pdmg
    add("You deal %d" % pdmg)
    if ehp > 0:
        hull -= edmg
        add("Enemy deals %d" % edmg)
    if hull <= 0:
        add("! Destroyed")
        check_end()
        return
    if ehp <= 0:
        r = 8 + _rand(12)
        credits += r
        add("Win +%d credits" % r)
    else:
        add("Enemy withdraws")


def move(dx, dy):
    global px, py, fuel, rations, won
    if game_over or won:
        return
    nx = px + dx
    ny = py + dy
    if nx < 0 or nx >= MAP_W or ny < 0 or ny >= MAP_H:
        add("Edge of map.")
        return
    if fuel <= 0 or rations <= 0:
        add("! No resources")
        check_end()
        return
    px = nx
    py = ny
    fuel -= 1
    rations -= 1
    add("To %d,%d" % (px + 1, py + 1))
    if sector() == EXTRACT:
        add("* EXTRACTED - YOU WIN")
        won = True
    check_end()


def check_end():
    global game_over
    if won:
        return
    if hull <= 0:
        add("! HULL FAIL - GAME OVER")
        game_over = True
    elif fuel <= 0:
        add("! NO FUEL - GAME OVER")
        game_over = True
    elif rations <= 0:
        add("! NO RATIONS - GAME OVER")
        game_over = True


def do_help():
    add("N S E W NE NW SE SW")
    add("LOOK STATUS MAP")
    add("CAMP FIGHT HELP QUIT")
    add("MAP is color coded")


def execute(cmd):
    cmd = cmd.strip().upper()
    if not cmd:
        return None
    if game_over or won:
        if cmd == "QUIT":
            return "EXIT"
        add("Game over. QUIT exits.")
        return None
    try:
        if cmd in ("N", "NORTH"):
            move(0, -1)
        elif cmd in ("S", "SOUTH"):
            move(0, 1)
        elif cmd in ("E", "EAST"):
            move(1, 0)
        elif cmd in ("W", "WEST"):
            move(-1, 0)
        elif cmd == "NE":
            move(1, -1)
        elif cmd == "NW":
            move(-1, -1)
        elif cmd == "SE":
            move(1, 1)
        elif cmd == "SW":
            move(-1, 1)
        elif cmd == "LOOK":
            do_look()
        elif cmd == "STATUS":
            do_status()
        elif cmd == "MAP":
            do_map()
        elif cmd == "CAMP":
            do_camp()
        elif cmd == "FIGHT":
            do_fight()
        elif cmd in ("HELP", "?"):
            do_help()
        elif cmd == "QUIT":
            return "EXIT"
        else:
            add("Unknown. HELP")
    except Exception:
        add("! ERR")
    return None


def start(view_manager) -> bool:
    global lines, inp, game_over, won, state
    global px, py, fuel, rations, hull, credits, medkits
    lines = []
    inp = ""
    game_over = False
    won = False
    state = "cli"
    px = 0
    py = 0
    fuel = 100
    rations = 50
    hull = 50
    credits = 40
    medkits = 2
    gen_map()
    add("ONOSO: THE GREAT WAR")
    add("25x25 map - extract at 25,25")
    add("Type MAP for color map")
    add(status_line())
    draw(view_manager)
    return True


def run(view_manager) -> None:
    global inp, state
    button = view_manager.button

    if state == "map":
        if button == BUTTON_ENTER or button == BUTTON_OK or button == BUTTON_CENTER or button == BUTTON_BACK:
            state = "cli"
            draw(view_manager)
        return

    if button == BUTTON_BACK:
        view_manager.back()
        return

    if button == BUTTON_ENTER or button == BUTTON_OK or button == BUTTON_CENTER:
        result = execute(inp)
        inp = ""
        if result == "EXIT":
            view_manager.back()
            return
        draw(view_manager)
        return

    if button == BUTTON_BACKSPACE:
        if len(inp) > 0:
            inp = inp[:-1]
            draw(view_manager)
        return

    if button in KEYMAP:
        ch = KEYMAP[button]
        if len(inp) < 20:
            inp += ch
            draw(view_manager)


def stop(view_manager) -> None:
    global lines, inp, world, state
    lines = []
    inp = ""
    world = None
    state = "cli"