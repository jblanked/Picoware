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

# === Settings ===
CELL_SIZE = 6  # 6 pixels per cell (53x53 grid)
GRID_PIXELS = 320
GRID_SIZE = GRID_PIXELS // CELL_SIZE  # 53x53 grid
GRID_BYTES = GRID_SIZE * GRID_SIZE

LIVE_CHANCE = 0.3  # 30% of cells alive initially

_current_grid = None  # Current state
_next_grid = None  # Next state
_neighbor_counts = None  # Neighbor counts


def _grid_index(x, y):
    """Calculate linear index from x, y coordinates."""
    return y * GRID_SIZE + x


# === Initialize Grid ===
def random_grid():
    """Fill the grid with random initial state."""
    global _current_grid

    for i in range(GRID_BYTES):
        _current_grid[i] = choice([1, 2, 3]) if random() < LIVE_CHANCE else 0


# === Game Update ===
def update():
    global _current_grid, _next_grid, _neighbor_counts

    # Clear neighbor counts and next grid
    for i in range(GRID_BYTES):
        _neighbor_counts[i] = 0
        _next_grid[i] = 0

    # Count neighbors
    for y in range(GRID_SIZE):
        y_offset = y * GRID_SIZE
        y_prev = ((y - 1) % GRID_SIZE) * GRID_SIZE
        y_next = ((y + 1) % GRID_SIZE) * GRID_SIZE

        for x in range(GRID_SIZE):
            idx = y_offset + x
            cell = _current_grid[idx]

            if cell != 0:
                x_prev = (x - 1) % GRID_SIZE
                x_next = (x + 1) % GRID_SIZE

                # Increment all 8 neighbors at once
                _neighbor_counts[y_prev + x_prev] += 1
                _neighbor_counts[y_prev + x] += 1
                _neighbor_counts[y_prev + x_next] += 1
                _neighbor_counts[y_offset + x_prev] += 1
                _neighbor_counts[y_offset + x_next] += 1
                _neighbor_counts[y_next + x_prev] += 1
                _neighbor_counts[y_next + x] += 1
                _neighbor_counts[y_next + x_next] += 1

    # Apply rules
    for i in range(GRID_BYTES):
        neighbor_count = _neighbor_counts[i]
        cell_value = _current_grid[i]

        if cell_value != 0:
            if neighbor_count in (2, 3):
                _next_grid[i] = cell_value  # Stay alive
        elif neighbor_count == 3:
            # Get birth color from neighbors
            y = i // GRID_SIZE
            x = i % GRID_SIZE
            color = pick_birth_color_ram(x, y, _current_grid)
            _next_grid[i] = color

    # Swap buffers
    _current_grid, _next_grid = _next_grid, _current_grid


def pick_birth_color_ram(x, y, grid_data):
    """Optimized birth color picker reading."""
    x_prev = (x - 1) % GRID_SIZE
    x_next = (x + 1) % GRID_SIZE
    y_prev = ((y - 1) % GRID_SIZE) * GRID_SIZE
    y_curr = y * GRID_SIZE
    y_next = ((y + 1) % GRID_SIZE) * GRID_SIZE

    # Check all 8 neighbors
    for idx in (
        y_prev + x_prev,
        y_prev + x,
        y_prev + x_next,
        y_curr + x_prev,
        y_curr + x_next,
        y_next + x_prev,
        y_next + x,
        y_next + x_next,
    ):
        cell = grid_data[idx]
        if cell != 0:
            return cell

    return choice([1, 2, 3])


_COLORS = {}
_vec_size = None
_vec_pos = None


def draw(display):
    # Color mappings
    display.fill_screen(TFT_BLACK)
    idx = 0
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            color = _COLORS.get(_current_grid[idx], TFT_BLACK)
            if color != TFT_BLACK:  # Skip drawing black pixels for speed
                _vec_pos.x = x * CELL_SIZE
                _vec_pos.y = y * CELL_SIZE
                display.fill_rectangle(_vec_pos, _vec_size, color)
            idx += 1
    display.swap()


def start(view_manager) -> bool:
    """Start the app"""
    global _current_grid, _next_grid, _neighbor_counts, _vec_size, _vec_pos, _COLORS

    _vec_size = Vector(CELL_SIZE, CELL_SIZE)
    _vec_pos = Vector(0, 0)

    _COLORS = {
        0: TFT_BLACK,  # dead = black
        1: TFT_RED,  # red
        2: TFT_GREEN,  # green
        3: TFT_BLUE,  # blue
    }

    _current_grid = bytearray(GRID_BYTES)
    _next_grid = bytearray(GRID_BYTES)
    _neighbor_counts = bytearray(GRID_BYTES)

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
    """Stop the app and free resources"""
    from gc import collect

    global _current_grid, _next_grid, _neighbor_counts, _vec_size, _vec_pos, _COLORS

    _vec_size = None
    _vec_pos = None
    _COLORS = {}

    _current_grid = None
    _next_grid = None
    _neighbor_counts = None

    collect()
