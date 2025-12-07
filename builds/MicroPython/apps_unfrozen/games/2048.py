# translated from https://github.com/lazerduck/PicoCalc_Dashboard/blob/main/2048/2048.py
# 2048 game for MicroPython
# by LazerDuck
from micropython import const
from picoware.system.colors import (
    TFT_BLACK,
    TFT_GREEN,
    TFT_RED,
    TFT_YELLOW,
    TFT_VIOLET,
    TFT_CYAN,
    TFT_BLUE,
    TFT_WHITE,
    TFT_SKYBLUE,
    TFT_DARKGREEN,
    TFT_ORANGE,
    TFT_PINK,
    TFT_LIGHTGREY,
)
from picoware.system.vector import Vector

# Game constants
GRID_SIZE = const(4)
TILE_SIZE = 0
GRID_OFFSET_X = 0
GRID_OFFSET_Y = 0
SCREEN_WIDTH = 0
SCREEN_HEIGHT = 0

# Color constants
COLOR_BG = TFT_BLACK
COLOR_TEXT = TFT_WHITE
COLOR_NUMBER = TFT_BLACK
COLOR_EMPTY = TFT_BLUE
COLOR_WIN = TFT_YELLOW
COLOR_LOSE = TFT_RED

# State constants
STATE_PLAYING = const(0)
STATE_WIN = const(1)
STATE_LOSE = const(2)


def add_tile(grid):
    """Adds a new tile (2 or 4) to a random empty position in the grid."""
    from random import choice, random

    empty = [
        (y, x) for y in range(GRID_SIZE) for x in range(GRID_SIZE) if grid[y][x] == 0
    ]
    if empty:
        y, x = choice(empty)
        grid[y][x] = 2 if random() < 0.9 else 4


def check_win(grid) -> bool:
    """Checks if the player has won the game (i.e., a tile with 2048 exists)."""
    for row in grid:
        if 2048 in row:
            return True
    return False


def check_lose(grid) -> bool:
    """Checks if the player has lost the game (i.e., no moves left)."""
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            if grid[y][x] == 0:
                return False
            for dy, dx in ((0, 1), (1, 0)):
                ny, nx = y + dy, x + dx
                if ny < GRID_SIZE and nx < GRID_SIZE and grid[y][x] == grid[ny][nx]:
                    return False
    return True


def draw_grid(fb, grid, score: int, state: int) -> None:
    """Draws the game grid on the framebuffer."""
    fb.fill_screen(COLOR_BG)
    grid_vector = Vector(0, 0)
    text_vector = Vector(0, 0)
    size_vector = Vector(TILE_SIZE - 4, TILE_SIZE - 4)
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            val = grid[y][x]
            grid_vector.x = GRID_OFFSET_X + x * TILE_SIZE
            grid_vector.y = GRID_OFFSET_Y + y * TILE_SIZE
            color = get_tile_color(val)
            fb.fill_rectangle(grid_vector, size_vector, color)
            if val:
                text_vector.x = grid_vector.x + TILE_SIZE // 2 - 8
                text_vector.y = grid_vector.y + TILE_SIZE // 2 - 8
                fb.text(
                    text_vector,
                    str(val),
                    COLOR_NUMBER,
                )
    text_vector.x = 10
    text_vector.y = 10
    fb.text(text_vector, f"Score: {score}", COLOR_TEXT)
    if state == STATE_WIN:
        text_vector.x = 120
        text_vector.y = 10
        fb.text(text_vector, "YOU WIN!", COLOR_WIN)
    elif state == STATE_LOSE:
        text_vector.x = 120
        text_vector.y = 10
        fb.text(text_vector, "GAME OVER", COLOR_LOSE)
    text_vector.x = 10
    text_vector.y = 300
    fb.text(text_vector, "Back: Quit", COLOR_TEXT)
    text_vector.x = 120
    fb.text(text_vector, "Arrows: Move", COLOR_TEXT)


def draw_grid_with_offsets(fb, grid, score: int, state: int, offsets=None) -> None:
    """Draws the game grid on the framebuffer with tile offsets for animation."""
    fb.fill_screen(COLOR_BG)
    grid_vector = Vector(0, 0)
    text_vector = Vector(0, 0)
    size_vector = Vector(TILE_SIZE - 4, TILE_SIZE - 4)
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            val = grid[y][x]
            dx, dy = 0, 0
            if offsets and (y, x) in offsets:
                dx, dy = offsets[(y, x)]
            grid_vector.x = GRID_OFFSET_X + x * TILE_SIZE + dx
            grid_vector.y = GRID_OFFSET_Y + y * TILE_SIZE + dy
            color = get_tile_color(val)
            fb.fill_rectangle(grid_vector, size_vector, color)
            if val:
                text_vector.x = grid_vector.x + TILE_SIZE // 2 - 8
                text_vector.y = grid_vector.y + TILE_SIZE // 2 - 8
                fb.text(
                    text_vector,
                    str(val),
                    COLOR_NUMBER,
                )
    text_vector.x = 10
    text_vector.y = 10
    fb.text(text_vector, f"Score: {score}", COLOR_TEXT)
    if state == STATE_WIN:
        text_vector.x = 120
        text_vector.y = 10
        fb.text(text_vector, "YOU WIN!", COLOR_WIN)
    elif state == STATE_LOSE:
        text_vector.x = 120
        text_vector.y = 10
        fb.text(text_vector, "GAME OVER", COLOR_LOSE)
    text_vector.x = 10
    text_vector.y = 300
    fb.text(text_vector, "Back: Quit", COLOR_TEXT)
    text_vector.x = 120
    fb.text(text_vector, "Arrows: Move", COLOR_TEXT)


def get_tile_color(number: int) -> int:
    """Returns the color for a given tile number."""
    color_map = {
        0: TFT_BLACK,
        2: TFT_GREEN,
        4: TFT_RED,
        8: TFT_YELLOW,
        16: TFT_VIOLET,
        32: TFT_CYAN,
        64: TFT_BLUE,
        128: TFT_DARKGREEN,
        256: TFT_SKYBLUE,
        512: TFT_ORANGE,
        1024: TFT_PINK,
        2048: TFT_LIGHTGREY,
    }
    return color_map.get(number, TFT_WHITE)


def main(view_manager):
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_RIGHT,
    )

    fb = view_manager.get_draw()
    inp = view_manager.get_input_manager()
    grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
    score = 0
    state = STATE_PLAYING
    add_tile(grid)
    add_tile(grid)

    prev_grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
    while True:
        button = inp.button
        draw_grid(fb, grid, score, state)
        if state != STATE_PLAYING:
            break
        # Input
        moved, s = False, 0  # Always initialize
        if button != -1:
            inp.reset()
            if button == BUTTON_BACK:
                view_manager.back()
                break
            # Copy grid for animation
            for y in range(GRID_SIZE):
                for x in range(GRID_SIZE):
                    prev_grid[y][x] = grid[y][x]
            moved, s = move_grid(grid, button)
            if moved:
                # Animate the slide
                frames = 4  # Reduced from 5 to lower frame rate
                for frame in range(1, frames + 1):
                    offsets = {}
                    # Calculate offset based on direction only
                    # Tiles slide from their "before" position in the direction of movement
                    if button == BUTTON_UP:
                        for y in range(GRID_SIZE):
                            for x in range(GRID_SIZE):
                                if grid[y][x] != 0:
                                    # Find how far this tile should have slid from
                                    # Only animate if grid changed
                                    if prev_grid[y][x] != grid[y][x]:
                                        # Tile came from below
                                        dy = int(
                                            (TILE_SIZE) * (frames - frame) / frames
                                        )
                                        offsets[(y, x)] = (0, dy)
                    elif button == BUTTON_DOWN:
                        for y in range(GRID_SIZE):
                            for x in range(GRID_SIZE):
                                if grid[y][x] != 0:
                                    if prev_grid[y][x] != grid[y][x]:
                                        dy = int(
                                            -(TILE_SIZE) * (frames - frame) / frames
                                        )
                                        offsets[(y, x)] = (0, dy)
                    elif button == BUTTON_LEFT:
                        for y in range(GRID_SIZE):
                            for x in range(GRID_SIZE):
                                if grid[y][x] != 0:
                                    if prev_grid[y][x] != grid[y][x]:
                                        dx = int(
                                            (TILE_SIZE) * (frames - frame) / frames
                                        )
                                        offsets[(y, x)] = (dx, 0)
                    elif button == BUTTON_RIGHT:
                        for y in range(GRID_SIZE):
                            for x in range(GRID_SIZE):
                                if grid[y][x] != 0:
                                    if prev_grid[y][x] != grid[y][x]:
                                        dx = int(
                                            -(TILE_SIZE) * (frames - frame) / frames
                                        )
                                        offsets[(y, x)] = (dx, 0)
                    draw_grid_with_offsets(fb, grid, score, state, offsets)
                add_tile(grid)
                score += s
        if check_win(grid):
            state = STATE_WIN
        elif check_lose(grid):
            state = STATE_LOSE
        fb.swap()


def move_grid(grid, direction: int):
    """Moves and merges the grid in the specified direction."""
    from picoware.system.buttons import (
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_RIGHT,
    )

    moved = False
    total_score = 0

    def slide(row):
        new_row = [v for v in row if v]
        score_gained = 0
        i = 0
        while i < len(new_row) - 1:
            if new_row[i] == new_row[i + 1]:
                new_row[i] *= 2
                score_gained += new_row[i]
                new_row.pop(i + 1)
                i += 1
            i += 1
        new_row += [0] * (GRID_SIZE - len(new_row))
        return new_row, score_gained

    if direction == BUTTON_UP:
        for x in range(GRID_SIZE):
            col = [grid[y][x] for y in range(GRID_SIZE)]
            new_col, score_gained = slide(col)
            if col != new_col:
                moved = True
            total_score += score_gained
            for y in range(GRID_SIZE):
                grid[y][x] = new_col[y]
    elif direction == BUTTON_DOWN:
        for x in range(GRID_SIZE):
            col = [grid[y][x] for y in range(GRID_SIZE)][::-1]
            new_col, score_gained = slide(col)
            new_col = new_col[::-1]
            if [grid[y][x] for y in range(GRID_SIZE)] != new_col:
                moved = True
            total_score += score_gained
            for y in range(GRID_SIZE):
                grid[y][x] = new_col[y]
    elif direction == BUTTON_LEFT:
        for y in range(GRID_SIZE):
            row = grid[y]
            new_row, score_gained = slide(row)
            if row != new_row:
                moved = True
            total_score += score_gained
            grid[y] = new_row
    elif direction == BUTTON_RIGHT:
        for y in range(GRID_SIZE):
            row = grid[y][::-1]
            new_row, score_gained = slide(row)
            new_row = new_row[::-1]
            if grid[y] != new_row:
                moved = True
            total_score += score_gained
            grid[y] = new_row
    return moved, total_score


def start(view_manager) -> bool:
    """Start the app"""
    global SCREEN_WIDTH, SCREEN_HEIGHT, GRID_OFFSET_X, GRID_OFFSET_Y, TILE_SIZE
    draw = view_manager.get_draw()
    SCREEN_WIDTH = draw.size.x
    SCREEN_HEIGHT = draw.size.y
    GRID_OFFSET_X = int(SCREEN_WIDTH * 0.0625)  # 20
    GRID_OFFSET_Y = GRID_OFFSET_X * 2  # 40
    TILE_SIZE = GRID_OFFSET_X * 3  # 60
    return True


def run(view_manager) -> None:
    """Run the app"""
    main(view_manager)


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    collect()
