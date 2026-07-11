# minesweeper.py - Minesweeper for PicoCalc
# translated from https://github.com/lazerduck/PicoCalc_Dashboard/blob/main/minesweeper.py
from picoware.system.colors import (
    TFT_BLACK,
    TFT_BLUE,
    TFT_ORANGE,
    TFT_RED,
    TFT_WHITE,
    TFT_GREEN,
)

CELL_SIZE = 20
GRID_W = 12
GRID_H = 12
NUM_MINES = 20
_scale = 1.0
_offset_x = 0
_offset_y = 20
_text_off_x = 6
_text_off_y = 2

grid = []
revealed = []
flagged = []
cursor = [0, 0]
mines_placed = False
game_over = False
win = False

reusable_vec = None
pos_vec = None
size_vec = None


def draw_cell(draw, value, is_revealed, is_flagged) -> None:
    """Draw a single grid cell."""
    reusable_vec.x = pos_vec.x * CELL_SIZE + _offset_x
    reusable_vec.y = pos_vec.y * CELL_SIZE + _offset_y
    if is_revealed:
        draw.fill_rectangle(reusable_vec, size_vec, TFT_ORANGE)
    else:
        draw.fill_rectangle(reusable_vec, size_vec, TFT_BLACK)
    draw.rect(reusable_vec, size_vec, TFT_BLUE)
    reusable_vec.x += _text_off_x
    reusable_vec.y += _text_off_y
    if is_revealed:
        if value == -1:
            draw.text(reusable_vec, "*", TFT_RED)
        elif value > 0:
            draw.text(reusable_vec, str(value), TFT_WHITE)
    elif is_flagged:
        draw.text(reusable_vec, "F", TFT_GREEN)


def draw_grid(draw) -> None:
    """Draw the entire grid with cursor."""
    for y in range(GRID_H):
        for x in range(GRID_W):
            pos_vec.x = x
            pos_vec.y = y
            draw_cell(draw, grid[y][x], revealed[y][x], flagged[y][x])
    cx, cy = cursor
    reusable_vec.x = cx * CELL_SIZE + _offset_x
    reusable_vec.y = cy * CELL_SIZE + _offset_y
    draw.rect(reusable_vec, size_vec, TFT_GREEN)
    draw.swap()


def place_mines(first_x, first_y) -> None:
    """Place mines avoiding the first click cell."""
    from random import randint

    positions = [
        (x, y)
        for x in range(GRID_W)
        for y in range(GRID_H)
        if not (x == first_x and y == first_y)
    ]
    # Manual shuffle for MicroPython
    n = len(positions)
    for i in range(n - 1, 0, -1):
        j = randint(0, i)
        positions[i], positions[j] = positions[j], positions[i]
    for i in range(NUM_MINES):
        x, y = positions[i]
        grid[y][x] = -1
    # Fill numbers
    for y in range(GRID_H):
        for x in range(GRID_W):
            if grid[y][x] == -1:
                continue
            count = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
                        if grid[ny][nx] == -1:
                            count += 1
            grid[y][x] = count


def reveal(x, y) -> None:
    """Reveal cell; flood fill from zeros."""
    if flagged[y][x] or revealed[y][x]:
        return
    revealed[y][x] = True
    if grid[y][x] == 0:
        # Flood fill neighbors
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
                    if not revealed[ny][nx]:
                        reveal(nx, ny)


def check_win() -> bool:
    """Check all non-mine cells revealed."""
    for y in range(GRID_H):
        for x in range(GRID_W):
            if grid[y][x] != -1 and not revealed[y][x]:
                return False
    return True


def start(view_manager) -> bool:
    """Start the app."""
    from picoware.system.vector import Vector
    from picoware.system.colors import TFT_BLACK, TFT_WHITE

    global grid, revealed, flagged, reusable_vec, pos_vec, size_vec
    global _scale, CELL_SIZE, _offset_x, _offset_y, _text_off_x, _text_off_y, NUM_MINES

    draw = view_manager.draw
    sw, sh = draw.size.x, draw.size.y
    screen_min = min(sw, sh)

    _scale = screen_min / 320
    CELL_SIZE = max(6, sw // GRID_W)
    max_cell_h = (sh - 12) // GRID_H
    CELL_SIZE = max(6, min(CELL_SIZE, max_cell_h))
    _offset_y = max(6, int(CELL_SIZE * 0.9))
    _offset_x = max(0, (sw - GRID_W * CELL_SIZE) // 2)
    _text_off_x = max(1, int(CELL_SIZE * 0.3))
    _text_off_y = max(1, int(CELL_SIZE * 0.1))
    NUM_MINES = max(5, int(20 * _scale))

    grid = [[0] * GRID_W for _ in range(GRID_H)]
    revealed = [[False] * GRID_W for _ in range(GRID_H)]
    flagged = [[False] * GRID_W for _ in range(GRID_H)]

    reusable_vec = Vector(0, 0)
    pos_vec = Vector(0, 0)
    size_vec = Vector(CELL_SIZE, CELL_SIZE)

    draw.fill_screen(TFT_BLACK)
    title_x = max(0, (sw - len("MINESWEEPER") * draw.font_size.x) // 2)
    draw.text(Vector(title_x, 2), "MINESWEEPER", TFT_WHITE)
    draw_grid(draw)
    return True


def run(view_manager) -> None:
    """Run the app."""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_RIGHT,
        BUTTON_SPACE,
        BUTTON_F,
    )

    global mines_placed, game_over, win

    inp = view_manager.input_manager
    draw = view_manager.draw
    button = inp.button

    if any([button == BUTTON_BACK, game_over, win]):
        inp.reset()
        view_manager.back()
        return

    if button == BUTTON_UP and cursor[1] > 0:
        inp.reset()
        cursor[1] -= 1
    elif button == BUTTON_DOWN and cursor[1] < GRID_H - 1:
        inp.reset()
        cursor[1] += 1
    elif button == BUTTON_RIGHT and cursor[0] < GRID_W - 1:
        inp.reset()
        cursor[0] += 1
    elif button == BUTTON_LEFT and cursor[0] > 0:
        inp.reset()
        cursor[0] -= 1
    elif button == BUTTON_SPACE:  # Reveal
        inp.reset()
        if not mines_placed:
            place_mines(cursor[0], cursor[1])
            mines_placed = True
        if not flagged[cursor[1]][cursor[0]] and not revealed[cursor[1]][cursor[0]]:
            if grid[cursor[1]][cursor[0]] == -1:
                revealed[cursor[1]][cursor[0]] = True
                game_over = True
                win = False
            else:
                reveal(cursor[0], cursor[1])
    elif button == BUTTON_F:  # Flag
        inp.reset()
        if not revealed[cursor[1]][cursor[0]]:
            flagged[cursor[1]][cursor[0]] = not flagged[cursor[1]][cursor[0]]
    draw_grid(draw)


def stop(view_manager) -> None:
    """Stop the app."""
    from gc import collect

    global grid, revealed, flagged, reusable_vec, pos_vec, size_vec, _scale

    grid = []
    revealed = []
    flagged = []

    reusable_vec = None
    pos_vec = None
    size_vec = None
    _scale = 1.0

    collect()
