# Original from https://github.com/xMasterX/all-the-plugins/blob/dev/base_pack/tetris_game
from micropython import const
from picoware.system.vector import Vector

BLOCK_WIDTH = const(12)
BLOCK_HEIGHT = const(12)

FIELD_WIDTH = const(10)
FIELD_HEIGHT = const(20)

FIELD_X_OFFSET = const(100)
FIELD_Y_OFFSET = const(5)

BORDER_OFFSET = const(1)
MARGIN_OFFSET = const(3)

MAX_FALL_SPEED = const(500)
MIN_FALL_SPEED = const(100)

OFFSET_TYPE_COMMON = const(0)
OFFSET_TYPE_I = const(1)
OFFSET_TYPE_O = const(2)

GAME_STATE_PLAYING = const(0)
GAME_STATE_GAME_OVER = const(1)
GAME_STATE_PAUSED = const(2)


def __random_color() -> int:
    from random import getrandbits

    return (getrandbits(5) << 11) | (getrandbits(6) << 5) | getrandbits(5)


class Point:
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y

    def copy(self):
        """Create a copy of this Point"""
        return Point(self.x, self.y)


class Piece:
    def __init__(
        self, p: list[Point], rot_idx: int, offset_type: int, color: int
    ) -> None:
        self.p = p
        self.rot_idx = rot_idx
        self.offset_type = offset_type
        self.color = color

    def copy(self):
        """Create a deep copy of this Piece"""
        return Piece(
            [pt.copy() for pt in self.p], self.rot_idx, self.offset_type, self.color
        )


class TetrisState:
    def __init__(self) -> None:
        self.field: list[list[bool]] = [
            [False for _ in range(FIELD_WIDTH)] for _ in range(FIELD_HEIGHT)
        ]
        self.colors: list[list[int]] = [
            [0 for _ in range(FIELD_WIDTH)] for _ in range(FIELD_HEIGHT)
        ]
        self.prev_block_positions: list = []
        self.prev_block_count: int = 0
        #
        self.bag: list = [False for _ in range(7)]
        self.next_id: int = -1
        self.current_piece: Piece = None
        self.num_lines: int = 0
        self.fall_speed: int = -1
        self.game_state: int = -1
        #
        self.pos: Vector = Vector(0, 0)
        self.prev_pos: Vector = Vector(0, 0)


# Rotation offset translation table
# [offset_type][rotation_index][kick_attempt] = Point(x, y)
_rot_offset_translation = [
    # OFFSET_TYPE_COMMON
    [
        [Point(0, 0), Point(-1, 0), Point(-1, -1), Point(0, 2), Point(-1, 2)],
        [Point(0, 0), Point(1, 0), Point(1, 1), Point(0, -2), Point(1, -2)],
        [Point(0, 0), Point(1, 0), Point(1, -1), Point(0, 2), Point(1, 2)],
        [Point(0, 0), Point(-1, 0), Point(-1, 1), Point(0, -2), Point(-1, -2)],
    ],
    # OFFSET_TYPE_I
    [
        [Point(1, 0), Point(-1, 0), Point(2, 0), Point(-1, 1), Point(2, -2)],
        [Point(0, 1), Point(-1, 1), Point(2, 1), Point(-1, -1), Point(2, 2)],
        [Point(-1, 0), Point(1, 0), Point(-2, 0), Point(1, -1), Point(-2, 2)],
        [Point(0, -1), Point(1, -1), Point(-2, -1), Point(1, 1), Point(-2, -2)],
    ],
    # OFFSET_TYPE_O
    [
        [Point(0, -1), Point(0, 0), Point(0, 0), Point(0, 0), Point(0, 0)],
        [Point(1, 0), Point(0, 0), Point(0, 0), Point(0, 0), Point(0, 0)],
        [Point(0, 1), Point(0, 0), Point(0, 0), Point(0, 0), Point(0, 0)],
        [Point(-1, 0), Point(0, 0), Point(0, 0), Point(0, 0), Point(0, 0)],
    ],
]

# Global state
_down_repeat_counter = 0
_was_down_move = False
_new_piece = None
_tetris_state = None
_game_engine = None
_shapes = []


def __create_shapes() -> list:
    """Create the 7 tetromino shapes"""
    shapes = []
    # Z piece
    shapes.append(
        Piece(
            [Point(5, 1), Point(4, 0), Point(5, 0), Point(6, 1)],
            0,
            OFFSET_TYPE_COMMON,
            __random_color(),
        )
    )
    # S piece
    shapes.append(
        Piece(
            [Point(5, 1), Point(4, 1), Point(5, 0), Point(6, 0)],
            0,
            OFFSET_TYPE_COMMON,
            __random_color(),
        )
    )
    # L piece
    shapes.append(
        Piece(
            [Point(5, 1), Point(4, 1), Point(6, 1), Point(6, 0)],
            0,
            OFFSET_TYPE_COMMON,
            __random_color(),
        )
    )
    # J piece
    shapes.append(
        Piece(
            [Point(5, 1), Point(4, 0), Point(4, 1), Point(6, 1)],
            0,
            OFFSET_TYPE_COMMON,
            __random_color(),
        )
    )
    # T piece
    shapes.append(
        Piece(
            [Point(5, 1), Point(4, 1), Point(5, 0), Point(6, 1)],
            0,
            OFFSET_TYPE_COMMON,
            __random_color(),
        )
    )
    # I piece
    shapes.append(
        Piece(
            [Point(5, 1), Point(4, 1), Point(6, 1), Point(7, 1)],
            0,
            OFFSET_TYPE_I,
            __random_color(),
        )
    )
    # O piece
    shapes.append(
        Piece(
            [Point(5, 1), Point(5, 0), Point(6, 0), Point(6, 1)],
            0,
            OFFSET_TYPE_O,
            __random_color(),
        )
    )
    return shapes


def __tetris_game_draw_border(draw) -> None:
    """Draw the border around the Tetris playfield"""
    from picoware.system.colors import TFT_BLACK

    total_width = FIELD_WIDTH * BLOCK_WIDTH
    total_height = FIELD_HEIGHT * BLOCK_HEIGHT

    draw.rect(
        Vector(FIELD_X_OFFSET - BORDER_OFFSET, FIELD_Y_OFFSET - BORDER_OFFSET),
        Vector(total_width + 2 * BORDER_OFFSET, total_height + 2 * BORDER_OFFSET),
        TFT_BLACK,
    )


def __tetris_game_draw_block(draw, x_offset: int, y_offset: int, color: int) -> None:
    """Draw a single block at the specified offset with the given color"""
    draw.rect(Vector(x_offset, y_offset), Vector(BLOCK_WIDTH, BLOCK_HEIGHT), color)


def __tetris_game_draw_playfield(draw) -> None:
    """Draw all blocks currently on the playfield"""
    global _tetris_state

    curr_block_positions = []
    cur_block_pos = Vector(0, 0)
    for y in range(FIELD_HEIGHT):
        for x in range(FIELD_WIDTH):
            if _tetris_state.field[y][x]:
                cur_block_pos.x = int(FIELD_X_OFFSET + x * BLOCK_WIDTH)
                cur_block_pos.y = int(FIELD_Y_OFFSET + y * BLOCK_HEIGHT)

                __tetris_game_draw_block(
                    draw, cur_block_pos.x, cur_block_pos.y, _tetris_state.colors[y][x]
                )
                curr_block_positions.append(cur_block_pos)

    _tetris_state.prev_block_positions = curr_block_positions
    _tetris_state.prev_block_count = len(curr_block_positions)


def __tetris_game_draw_next_piece(draw) -> None:
    """Draw the next piece preview"""
    global _tetris_state, _shapes

    next_piece = _shapes[_tetris_state.next_id]

    for i in range(4):
        x = next_piece.p[i].x
        y = next_piece.p[i].y

        next_piece_x = x * BLOCK_WIDTH
        next_piece_y = 32 + y * BLOCK_HEIGHT

        __tetris_game_draw_block(draw, next_piece_x, next_piece_y, next_piece.color)


def __tetris_game_render_callback(draw) -> None:
    """Main render function"""
    from picoware.system.colors import TFT_WHITE, TFT_BLACK

    global _tetris_state

    __tetris_game_draw_border(draw)
    __tetris_game_draw_playfield(draw)

    if (
        _tetris_state.game_state == GAME_STATE_PLAYING
        or _tetris_state.game_state == GAME_STATE_PAUSED
    ):
        __tetris_game_draw_next_piece(draw)
        score_text = str(_tetris_state.num_lines)
        draw.text(Vector(62, 10), score_text, TFT_BLACK)

    if _tetris_state.game_state == GAME_STATE_GAME_OVER:
        draw.fill_rectangle(Vector(1, 52), Vector(82, 24), TFT_WHITE)
        draw.rect(Vector(1, 52), Vector(82, 24), TFT_BLACK)
        draw.text(Vector(4, 56), "Game Over", TFT_BLACK)

        lines_text = "Lines: " + str(_tetris_state.num_lines)
        draw.text(Vector(4, 64), lines_text, TFT_BLACK)


def __tetris_game_get_next_piece() -> int:
    """Get the next piece from the bag system"""
    global _tetris_state

    # Check if bag is full
    full = True
    for i in range(7):
        if not _tetris_state.bag[i]:
            full = False
            break

    # Reset bag if full
    if full:
        for i in range(7):
            _tetris_state.bag[i] = False

    # Pick a random piece not in the bag
    from random import randint

    next_piece = randint(0, 6)
    while _tetris_state.bag[next_piece]:
        next_piece = randint(0, 6)

    _tetris_state.bag[next_piece] = True
    result = _tetris_state.next_id
    _tetris_state.next_id = next_piece

    return result


def __tetris_game_init_state() -> None:
    """Initialize the game state"""
    global _tetris_state, _new_piece, _shapes

    _tetris_state.game_state = GAME_STATE_PLAYING
    _tetris_state.num_lines = 0
    _tetris_state.fall_speed = MAX_FALL_SPEED

    # Clear playfield
    for y in range(FIELD_HEIGHT):
        for x in range(FIELD_WIDTH):
            _tetris_state.field[y][x] = False
            _tetris_state.colors[y][x] = __random_color()

    # Clear bag
    for i in range(7):
        _tetris_state.bag[i] = False

    # Initialize pieces
    __tetris_game_get_next_piece()
    next_piece_id = __tetris_game_get_next_piece()

    _tetris_state.current_piece = _shapes[next_piece_id].copy()
    _new_piece = _shapes[next_piece_id].copy()


def __tetris_game_remove_curr_piece() -> None:
    """Remove current piece from the playfield"""
    global _tetris_state

    for i in range(4):
        x = _tetris_state.current_piece.p[i].x
        y = _tetris_state.current_piece.p[i].y
        if 0 <= y < FIELD_HEIGHT and 0 <= x < FIELD_WIDTH:
            _tetris_state.field[y][x] = False


def __tetris_game_render_curr_piece() -> None:
    """Render current piece to the playfield"""
    global _tetris_state

    for i in range(4):
        x = _tetris_state.current_piece.p[i].x
        y = _tetris_state.current_piece.p[i].y
        if 0 <= y < FIELD_HEIGHT and 0 <= x < FIELD_WIDTH:
            _tetris_state.field[y][x] = True
            _tetris_state.colors[y][x] = _tetris_state.current_piece.color


def __tetris_game_rotate_shape(curr_shape: list, new_shape: list) -> None:
    """Rotate a shape 90 degrees clockwise"""
    # Copy shape data
    for i in range(4):
        new_shape[i].x = curr_shape[i].x
        new_shape[i].y = curr_shape[i].y

    # Rotate around first point (pivot)
    for i in range(1, 4):
        rel_x = curr_shape[i].x - curr_shape[0].x
        rel_y = curr_shape[i].y - curr_shape[0].y

        # 90 degree rotation matrix
        new_rel_x = -rel_y
        new_rel_y = rel_x

        new_shape[i].x = curr_shape[0].x + new_rel_x
        new_shape[i].y = curr_shape[0].y + new_rel_y


def __tetris_game_is_valid_pos(shape: list) -> bool:
    """Check if a shape position is valid"""
    global _tetris_state

    for i in range(4):
        x = shape[i].x
        y = shape[i].y

        # Check bounds
        if x < 0 or x >= FIELD_WIDTH or y < 0 or y >= FIELD_HEIGHT:
            return False

        # Check collision with existing blocks
        if _tetris_state.field[y][x]:
            return False

    return True


def __tetris_game_try_rotation(new_piece: Piece) -> None:
    """Try to rotate the piece with wall kicks"""
    global _tetris_state, _rot_offset_translation

    curr_rot_idx = _tetris_state.current_piece.rot_idx
    rotated = [Point(0, 0) for _ in range(4)]

    # Compute rotated shape
    __tetris_game_rotate_shape(_tetris_state.current_piece.p, rotated)

    # Try all 5 kick offsets
    for i in range(5):
        kicked = [pt.copy() for pt in rotated]

        # Get kick offset
        kick = _rot_offset_translation[new_piece.offset_type][curr_rot_idx][i]

        # Apply kick
        for j in range(4):
            kicked[j].x += kick.x
            kicked[j].y += kick.y

        # Check if valid
        if __tetris_game_is_valid_pos(kicked):
            for j in range(4):
                new_piece.p[j].x = kicked[j].x
                new_piece.p[j].y = kicked[j].y
            new_piece.rot_idx = (curr_rot_idx + 1) % 4
            return


def __tetris_game_row_is_line(row: list) -> bool:
    """Check if a row is complete"""
    for i in range(FIELD_WIDTH):
        if not row[i]:
            return False
    return True


def __tetris_game_check_for_lines() -> list:
    """Check for complete lines and return their indices"""
    global _tetris_state

    lines = []
    for i in range(FIELD_HEIGHT):
        if __tetris_game_row_is_line(_tetris_state.field[i]):
            lines.append(i)
    return lines


def __tetris_game_piece_at_bottom(new_piece: Piece) -> bool:
    """Check if piece has reached the bottom or hit another piece"""
    global _tetris_state

    for i in range(4):
        x = new_piece.p[i].x
        y = new_piece.p[i].y

        # Check if at bottom or hitting another block
        if y >= FIELD_HEIGHT or (y >= 0 and _tetris_state.field[y][x]):
            return True

    return False


def __tetris_game_process_step(was_down_move: bool) -> None:
    """Process one game step"""
    global _tetris_state, _new_piece, _shapes, _was_down_move

    if _tetris_state.game_state in (GAME_STATE_GAME_OVER, GAME_STATE_PAUSED):
        return

    # Remove current piece from playfield
    __tetris_game_remove_curr_piece()

    # Check if any fixed blocks reached the ceiling
    for x in range(FIELD_WIDTH):
        if _tetris_state.field[0][x]:
            _tetris_state.game_state = GAME_STATE_GAME_OVER
            return

    # Handle piece landing
    if was_down_move:
        if __tetris_game_piece_at_bottom(_new_piece):
            __tetris_game_render_curr_piece()

            # Check for completed lines
            lines = __tetris_game_check_for_lines()
            if lines:
                # Clear lines and move rows down
                for line_y in lines:
                    # Zero out the line
                    for x in range(FIELD_WIDTH):
                        _tetris_state.field[line_y][x] = False

                    # Move all rows above down
                    for k in range(line_y, 0, -1):
                        for x in range(FIELD_WIDTH):
                            _tetris_state.field[k][x] = _tetris_state.field[k - 1][x]
                            _tetris_state.colors[k][x] = _tetris_state.colors[k - 1][x]

                    # Clear top row
                    for x in range(FIELD_WIDTH):
                        _tetris_state.field[0][x] = False

                # Update score and speed
                old_num_lines = _tetris_state.num_lines
                _tetris_state.num_lines += len(lines)

                if (old_num_lines // 10) != (_tetris_state.num_lines // 10):
                    next_fall_speed = _tetris_state.fall_speed - (
                        100 // (_tetris_state.num_lines // 10 + 1)
                    )
                    if next_fall_speed >= MIN_FALL_SPEED:
                        _tetris_state.fall_speed = next_fall_speed

            # Spawn next piece
            next_piece_id = __tetris_game_get_next_piece()
            spawned_piece = _shapes[next_piece_id].copy()

            if not __tetris_game_is_valid_pos(spawned_piece.p):
                _tetris_state.game_state = GAME_STATE_GAME_OVER
            else:
                _tetris_state.current_piece = spawned_piece.copy()
                _new_piece = spawned_piece.copy()

            _was_down_move = False
            return

    # Update piece position if valid
    if __tetris_game_is_valid_pos(_new_piece.p):
        _tetris_state.current_piece = _new_piece.copy()

    __tetris_game_render_curr_piece()
    _was_down_move = False


def __player_update(self, game) -> None:
    """Update player input and game logic"""
    from picoware.system.buttons import (
        BUTTON_RIGHT,
        BUTTON_LEFT,
        BUTTON_DOWN,
        BUTTON_UP,
        BUTTON_CENTER,
    )

    global _new_piece, _tetris_state, _was_down_move, _down_repeat_counter

    button = game.input

    if button == BUTTON_RIGHT:
        # Remove current piece from playfield before checking
        __tetris_game_remove_curr_piece()

        # Store original positions
        original = [pt.copy() for pt in _new_piece.p]

        # Try to move right
        for i in range(4):
            _new_piece.p[i].x += 1

        # Revert if invalid
        if not __tetris_game_is_valid_pos(_new_piece.p):
            for i in range(4):
                _new_piece.p[i].x = original[i].x
                _new_piece.p[i].y = original[i].y

        # Re-render the piece at its new (or reverted) position
        __tetris_game_render_curr_piece()
        game.input = -1

    elif button == BUTTON_LEFT:
        # Remove current piece from playfield before checking
        __tetris_game_remove_curr_piece()

        # Store original positions
        original = [pt.copy() for pt in _new_piece.p]

        # Try to move left
        for i in range(4):
            _new_piece.p[i].x -= 1

        # Revert if invalid
        if not __tetris_game_is_valid_pos(_new_piece.p):
            for i in range(4):
                _new_piece.p[i].x = original[i].x
                _new_piece.p[i].y = original[i].y

        # Re-render the piece at its new (or reverted) position
        __tetris_game_render_curr_piece()
        game.input = -1

    elif button == BUTTON_DOWN:
        for i in range(4):
            _new_piece.p[i].y += 1
        _was_down_move = True
        game.input = -1

    elif button in (BUTTON_UP, BUTTON_CENTER):
        if _tetris_state.game_state == GAME_STATE_PLAYING:
            __tetris_game_remove_curr_piece()
            __tetris_game_try_rotation(_new_piece)
            __tetris_game_render_curr_piece()
        else:
            __tetris_game_init_state()
        game.input = -1

    # Auto-fall logic
    if _down_repeat_counter > 4:
        for i in range(4):
            _new_piece.p[i].y += 1
        _down_repeat_counter = 0
        _was_down_move = True
    else:
        _down_repeat_counter += 1

    __tetris_game_process_step(_was_down_move)


def __player_render(self, draw, game) -> None:
    """Render the game"""
    __tetris_game_render_callback(draw)


def __player_spawn(level) -> None:
    """Spawn the player in the level."""
    from picoware.engine.entity import Entity, ENTITY_TYPE_PLAYER, SPRITE_3D_NONE

    player = Entity(
        "Player",  # name
        ENTITY_TYPE_PLAYER,  # type
        Vector(-100, -100),  # position
        Vector(10, 10),  # size
        None,  # sprite data
        None,  # sprite data left
        None,  # sprite data right
        None,  # start
        None,  # stop
        __player_update,  # update
        __player_render,  # render
        None,  # collide
        SPRITE_3D_NONE,  # 3d type
        True,  # is_8bit
    )

    level.entity_add(player)


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.engine.game import Game
    from picoware.engine.level import Level
    from picoware.engine.engine import GameEngine

    global _game_engine, _tetris_state, _new_piece, _shapes, _down_repeat_counter, _was_down_move

    # Initialize global state
    _tetris_state = TetrisState()
    _new_piece = None
    _shapes = __create_shapes()
    _down_repeat_counter = 0
    _was_down_move = False

    draw = view_manager.get_draw()

    # Create the game instance with its name, start/stop callbacks, and colors.
    game = Game(
        "Tetris",  # name
        draw.size,  # size
        draw,  # draw instance
        view_manager.get_input_manager(),  # input manager
        0x0000,  # foreground color
        0xFFFF,  # background color
        0,  # perspective
        None,  # start
        None,  # Stop
    )

    # Create and add a level to the game.
    level = Level("Level", draw.size, game)
    game.level_add(level)

    # Add the player entity to the level
    __player_spawn(level)

    # Initialize the game state
    __tetris_game_init_state()

    # Create the game engine (with 240 frames per second target).
    _game_engine = GameEngine(game, 240)

    return True


def run(view_manager) -> None:
    """Run the app."""
    from picoware.system.buttons import BUTTON_BACK

    global _game_engine

    if _game_engine:
        _game_engine.run_async(False)

    input_manager = view_manager.input_manager
    button: int = input_manager.get_last_button()

    if button == BUTTON_BACK:
        input_manager.reset()
        view_manager.back()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _game_engine, _tetris_state, _new_piece, _shapes, _down_repeat_counter, _was_down_move

    if _game_engine is not None:
        _game_engine.stop()
        del _game_engine
        _game_engine = None

    # Clean up game state
    if _tetris_state is not None:
        del _tetris_state
        _tetris_state = None

    if _new_piece is not None:
        del _new_piece
        _new_piece = None

    if _shapes is not None:
        del _shapes
        _shapes = None

    _down_repeat_counter = 0
    _was_down_move = False

    collect()
