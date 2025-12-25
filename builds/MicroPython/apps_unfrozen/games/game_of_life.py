# translated from https://github.com/thoughtfix/picocalc-lessons/blob/main/life.py

# game_of_life.py
# Life v1.2 - PicoCalc MicroPython Demo
#
# code@danielgentleman.com
# License: Apache 2.0
#
# A simple implementation of Conway's Game of Life
from random import random, choice
from picoware.system.vector import Vector
from picoware.system.colors import TFT_BLACK, TFT_RED, TFT_GREEN, TFT_BLUE
from picoware.system.buttons import BUTTON_BACK, BUTTON_CENTER
from picoware.system.psram import PSRAM

# === Settings ===
CELL_SIZE = 6  # 6 pixels per cell (53x53 grid)
GRID_PIXELS = 320
GRID_SIZE = GRID_PIXELS // CELL_SIZE  # 53x53 grid
GRID_BYTES = GRID_SIZE * GRID_SIZE

LIVE_CHANCE = 0.3  # 30% of cells alive initially

_psram = None
_new_grid_addr = 0
_neighbor_addr = 0

grid = []


def _grid_index(x, y):
    """Calculate linear index from x, y coordinates."""
    return y * GRID_SIZE + x


# === Initialize Grid ===
def random_grid():
    """Fill the grid with random initial state in RAM."""
    global grid

    grid = [
        [choice([1, 2, 3]) if random() < LIVE_CHANCE else 0 for _ in range(GRID_SIZE)]
        for _ in range(GRID_SIZE)
    ]


# === Game Update ===
def update():
    global grid, _new_grid_addr, _neighbor_addr

    # Clear neighbor counts in PSRAM
    _psram.memset(_neighbor_addr, 0, GRID_BYTES)

    # Count neighbors using RAM grid, store counts in PSRAM
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            if grid[y][x] != 0:
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx = (x + dx) % GRID_SIZE
                        ny = (y + dy) % GRID_SIZE
                        neighbor_idx = _grid_index(nx, ny)
                        count = _psram.read8(_neighbor_addr + neighbor_idx)
                        _psram.write8(_neighbor_addr + neighbor_idx, count + 1)

    # Apply rules: read neighbors from PSRAM, write new state to PSRAM
    _psram.memset(_new_grid_addr, 0, GRID_BYTES)
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            idx = _grid_index(x, y)
            neighbors = _psram.read8(_neighbor_addr + idx)
            cell_value = grid[y][x]

            if cell_value != 0:
                if neighbors in (2, 3):
                    _psram.write8(_new_grid_addr + idx, cell_value)  # Stay alive
            else:
                if neighbors == 3:
                    color = pick_birth_color(x, y)
                    _psram.write8(_new_grid_addr + idx, color)

    # Copy new grid from PSRAM back to RAM
    new_grid_buffer = _psram.read(_new_grid_addr, GRID_BYTES)
    idx = 0
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            grid[y][x] = new_grid_buffer[idx]
            idx += 1


def pick_birth_color(x, y):
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nx = (x + dx) % GRID_SIZE
            ny = (y + dy) % GRID_SIZE
            if grid[ny][nx] != 0:
                return grid[ny][nx]
    return choice([1, 2, 3])


# === Drawing ===
# Pre-create color lookup and reusable Vector objects for performance
_COLORS = {
    0: TFT_BLACK,  # dead = black
    1: TFT_RED,  # red
    2: TFT_GREEN,  # green
    3: TFT_BLUE,  # blue
}
_vec_size = Vector(CELL_SIZE, CELL_SIZE)
_vec_pos = Vector(0, 0)


def draw(display):
    # Color mappings
    COLORS = _COLORS

    display.fill_screen(TFT_BLACK)
    vec_size = _vec_size
    vec_pos = _vec_pos

    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            color = COLORS.get(grid[y][x], TFT_BLACK)
            if color != TFT_BLACK:  # Skip drawing black pixels for speed
                vec_pos.x = x * CELL_SIZE
                vec_pos.y = y * CELL_SIZE
                display.fill_rectangle(vec_pos, vec_size, color)
    display.swap()


def start(view_manager) -> bool:
    """Start the app"""
    global _psram, _new_grid_addr, _neighbor_addr, grid

    if not view_manager.has_psram:
        view_manager.alert("Game of Life requires PSRAM to run.")
        return False

    # Initialize PSRAM
    _psram = PSRAM()

    # Allocate memory for calculation buffers in PSRAM for calculations
    _new_grid_addr = _psram.malloc(GRID_BYTES)
    if _new_grid_addr == 0:
        view_manager.alert("Failed to allocate PSRAM for new grid buffer.")
        return False

    _neighbor_addr = _psram.malloc(GRID_BYTES)
    if _neighbor_addr == 0:
        _psram.free(_new_grid_addr)
        view_manager.alert("Failed to allocate PSRAM for neighbor counts.")
        return False

    random_grid()

    return True


def run(view_manager) -> None:
    """Run the app"""
    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
        return

    if button == BUTTON_CENTER:
        inp.reset()
        random_grid()

    draw(view_manager.draw)

    update()


def stop(view_manager) -> None:
    """Stop the app and free PSRAM resources"""
    from gc import collect

    global _psram, _new_grid_addr, _neighbor_addr, grid

    # Free RAM grid
    grid = []

    # Free all allocated PSRAM memory
    if _psram is not None:
        if _new_grid_addr != 0:
            _psram.free(_new_grid_addr)
            _new_grid_addr = 0
        if _neighbor_addr != 0:
            _psram.free(_neighbor_addr)
            _neighbor_addr = 0

        _psram = None

    collect()
