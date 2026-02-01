# Tetris game for Picoware - MicroPython/CircuitPython implementation
# originally from https://github.com/lazerduck/PicoCalc_Dashboard/blob/main/tetris.py
from random import randint

try:
    from utime import ticks_ms, ticks_diff
except ImportError:
    from supervisor import ticks_ms

    def ticks_diff(a, b):
        return a - b


from picoware.system.colors import TFT_WHITE, TFT_BLACK, TFT_RED
from picoware.system.vector import Vector
from picoware.system.buttons import (
    BUTTON_RIGHT,
    BUTTON_LEFT,
    BUTTON_DOWN,
    BUTTON_UP,
    BUTTON_CENTER,
    BUTTON_BACK,
)

# Grid size
GRID_W = 10
GRID_H = 20
CELL_SIZE = 14  # Each cell is 14x14px
GRID_X = 20  # Left margin
GRID_Y = 10  # Top margin

# Global game instance
_game = None


class Tetris:
    """Tetris game logic and rendering"""

    def __init__(self, draw):
        self.colors = ()
        self.tetrominos = []
        self.draw = draw
        self.well_pos = None
        self.well_size = None
        self.grid_pos = None
        self.grid_size = None
        self.text_pos = None
        self.grid = []
        self.score = 0
        self.level = 1
        self.lines = 0
        self.current = None
        self.next = None
        self.x = 0
        self.y = 0
        self.rotation = 0
        self.game_over = False
        self.drop_timer = ticks_ms()
        self.last_draw = 0

        self.reset(draw)

    def __del__(self):
        self.colors = ()
        self.tetrominos = []
        self.well_pos = None
        self.well_size = None
        self.grid_pos = None
        self.grid_size = None
        self.text_pos = None
        self.grid = []

    def spawn_piece(self):
        self.current = self.next
        self.next = self._random_piece()
        self.x = GRID_W // 2 - 2
        self.y = 0
        self.rotation = 0
        if self.collision(self.x, self.y, self.rotation):
            self.game_over = True

    def reset(self, draw):
        from picoware.system.colors import (
            TFT_GREEN,
            TFT_WHITE,
            TFT_CYAN,
            TFT_YELLOW,
            TFT_RED,
            TFT_BLUE,
            TFT_VIOLET,
        )

        self.colors = (
            TFT_GREEN,
            TFT_WHITE,
            TFT_CYAN,
            TFT_YELLOW,
            TFT_RED,
            TFT_BLUE,
            TFT_VIOLET,
        )

        # Tetromino shapes (4x4 matrices)
        self.tetrominos = [
            # I
            [[1, 1, 1, 1]],
            # O
            [[1, 1], [1, 1]],
            # T
            [[0, 1, 0], [1, 1, 1]],
            # S
            [[0, 1, 1], [1, 1, 0]],
            # Z
            [[1, 1, 0], [0, 1, 1]],
            # J
            [[1, 0, 0], [1, 1, 1]],
            # L
            [[0, 0, 1], [1, 1, 1]],
        ]

        self.draw = draw

        well_width = GRID_W * CELL_SIZE
        well_height = GRID_H * CELL_SIZE

        self.well_pos = Vector(GRID_X - 2, GRID_Y - 2)
        self.well_size = Vector(well_width + 4, well_height + 4)

        self.grid_pos = Vector(GRID_X, GRID_Y)
        self.grid_size = Vector(CELL_SIZE, CELL_SIZE)

        self.text_pos = Vector(180, 20)

        self.grid = [[0 for _ in range(GRID_W)] for _ in range(GRID_H)]
        self.score = 0
        self.level = 1
        self.lines = 0
        self.current = None
        self.next = self._random_piece()
        self.x = 0
        self.y = 0
        self.rotation = 0
        self.game_over = False
        self.drop_timer = ticks_ms()
        self.last_draw = 0
        self.spawn_piece()

    def rotate(self):
        new_rot = (self.rotation + 1) % 4
        if not self.collision(self.x, self.y, new_rot):
            self.rotation = new_rot
            return
        # Simple wall kicks: try shifting left/right if rotation collides
        if not self.collision(self.x - 1, self.y, new_rot):
            self.x -= 1
            self.rotation = new_rot
        elif not self.collision(self.x + 1, self.y, new_rot):
            self.x += 1
            self.rotation = new_rot

    def move(self, dx):
        if not self.collision(self.x + dx, self.y, self.rotation):
            self.x += dx

    def drop(self):
        while not self.collision(self.x, self.y + 1, self.rotation):
            self.y += 1
        self.lock_piece()

    def step(self):
        if not self.collision(self.x, self.y + 1, self.rotation):
            self.y += 1
        else:
            self.lock_piece()

    def lock_piece(self):
        if self.current is None:
            return
        shape = self.get_shape(self.current, self.rotation)
        piece_index = self.current
        for r, row in enumerate(shape):
            for c, val in enumerate(row):
                if val:
                    gx = self.x + c
                    gy = self.y + r
                    if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
                        self.grid[gy][gx] = piece_index + 1
        self.clear_lines()
        self.spawn_piece()

    def clear_lines(self):
        new_grid = [list(row) for row in self.grid if any(cell == 0 for cell in row)]
        cleared = GRID_H - len(new_grid)
        if cleared:
            self.score += [0, 40, 100, 300, 1200][cleared] * self.level
            self.lines += cleared
            self.level = 1 + self.lines // 10
            for _ in range(cleared):
                new_grid.insert(0, [0] * GRID_W)
            self.grid = new_grid

    def collision(self, x, y, rot):
        if self.current is None:
            return False
        shape = self.get_shape(self.current, rot)
        for r, row in enumerate(shape):
            for c, val in enumerate(row):
                if val:
                    gx = x + c
                    gy = y + r
                    if gx < 0 or gx >= GRID_W or gy >= GRID_H:
                        return True
                    if gy >= 0 and self.grid[gy][gx]:
                        return True
        return False

    def get_shape(self, idx, rot):
        shape = self.tetrominos[idx]
        for _ in range(rot):
            shape = [list(row) for row in zip(*shape[::-1])]
        return shape

    def _random_piece(self):
        return randint(0, len(self.tetrominos) - 1)

    def _drop_interval(self):
        base = 700 - (self.level - 1) * 60
        return max(120, base)

    def _get_color(self, piece_idx):
        """Get color for piece based on index"""

        return self.colors[piece_idx % len(self.colors)]

    def render(self):
        """Render the current game state"""
        draw = self.draw

        # Clear screen
        draw.fill_screen(TFT_BLACK)

        # Well outline
        draw.rect(
            self.well_pos,
            self.well_size,
            TFT_WHITE,
        )

        # Draw grid
        for r in range(GRID_H):
            for c in range(GRID_W):
                val = self.grid[r][c]
                if val:
                    color = self._get_color(val - 1)
                    self.grid_pos.x, self.grid_pos.y = (
                        GRID_X + c * CELL_SIZE,
                        GRID_Y + r * CELL_SIZE,
                    )
                    draw.fill_rectangle(self.grid_pos, self.grid_size, color)

        # Draw current piece
        if self.current is not None:
            shape = self.get_shape(self.current, self.rotation)
            color = self._get_color(self.current)
            for r, row in enumerate(shape):
                for c, val in enumerate(row):
                    if val:
                        self.grid_pos.x, self.grid_pos.y = (
                            GRID_X + (self.x + c) * CELL_SIZE,
                            GRID_Y + (self.y + r) * CELL_SIZE,
                        )
                        draw.fill_rectangle(self.grid_pos, self.grid_size, color)

        # Draw next piece preview
        self.text_pos.x, self.text_pos.y = (180, 20)
        draw.text(self.text_pos, "Next:", TFT_WHITE)
        if self.next is not None:
            next_shape = self.get_shape(self.next, 0)
            next_color = self._get_color(self.next)
            for r, row in enumerate(next_shape):
                for c, val in enumerate(row):
                    if val:
                        self.grid_pos.x, self.grid_pos.y = (
                            220 + c * CELL_SIZE,
                            40 + r * CELL_SIZE,
                        )
                        draw.fill_rectangle(self.grid_pos, self.grid_size, next_color)

        # Draw score/level
        self.text_pos.x, self.text_pos.y = (180, 120)
        draw.text(self.text_pos, f"Score: {self.score}", TFT_WHITE)
        self.text_pos.y += 20
        draw.text(self.text_pos, f"Level: {self.level}", TFT_WHITE)
        self.text_pos.y += 20
        draw.text(self.text_pos, f"Lines: {self.lines}", TFT_WHITE)

        # Controls help
        self.text_pos.x, self.text_pos.y = (170, 180)
        draw.text(self.text_pos, "Arrows: move", TFT_WHITE)
        self.text_pos.y += 14
        draw.text(self.text_pos, "Up/Center: rotate", TFT_WHITE)
        self.text_pos.y += 14
        draw.text(self.text_pos, "Back: quit", TFT_WHITE)

        if self.game_over:
            # Draw game over overlay
            draw.fill_rectangle(Vector(60, 130), Vector(200, 60), TFT_BLACK)
            draw.rect(Vector(60, 130), Vector(200, 60), TFT_WHITE)
            self.text_pos.x, self.text_pos.y = 100, 145
            draw.text(self.text_pos, "GAME OVER", TFT_RED)
            self.text_pos.x, self.text_pos.y = 80, 165
            draw.text(self.text_pos, "Press Center to restart", TFT_WHITE)

        draw.swap()

    def update(self, input_button):
        """Non-blocking update - process one frame"""
        if self.game_over:
            # Handle restart
            if input_button == BUTTON_CENTER:
                self.reset(self.draw)
            return

        # Handle input
        if input_button == BUTTON_RIGHT:
            self.move(1)
        elif input_button == BUTTON_LEFT:
            self.move(-1)
        elif input_button == BUTTON_DOWN:
            self.step()
            self.drop_timer = ticks_ms()
        elif input_button in (BUTTON_UP, BUTTON_CENTER):
            self.rotate()

        # Auto-fall logic
        now = ticks_ms()
        interval = self._drop_interval()
        if ticks_diff(now, self.drop_timer) >= interval:
            self.step()
            self.drop_timer = ticks_ms()

        # Redraw at ~20fps
        if ticks_diff(now, self.last_draw) >= 50:
            self.render()
            self.last_draw = now


def start(view_manager) -> bool:
    """Start the app"""
    global _game

    draw = view_manager.draw
    _game = Tetris(draw)

    # Initial render
    _game.render()

    return True


def run(view_manager) -> None:
    """Run the app (non-blocking)"""

    global _game

    if _game is None:
        return

    input_manager = view_manager.input_manager
    button = input_manager.button

    if button == BUTTON_BACK:
        input_manager.reset()
        view_manager.back()
        return

    # Update game state with current input
    _game.update(button)

    # Reset button after processing
    if button != -1:
        input_manager.reset()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _game

    if _game is not None:
        del _game
        _game = None

    collect()
