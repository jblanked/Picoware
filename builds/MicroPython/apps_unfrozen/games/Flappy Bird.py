# picoware/apps/games/Flappy Bird.py
# Original from https://github.com/xMasterX/all-the-plugins/blob/dev/base_pack/flappy_bird
from random import randint
from micropython import const
from picoware.system.vector import Vector
from picoware.system.buttons import BUTTON_UP, BUTTON_CENTER, BUTTON_BACK
from picoware.system.colors import (
    TFT_BLACK,
    TFT_WHITE,
    TFT_GREEN,
    TFT_CYAN,
    TFT_DARKGREEN,
    TFT_YELLOW,
)

BIRD_ICON = bytes(
    [
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0xF6,
        0xED,
        0xED,
        0xF2,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0xF6,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0xF6,
        0xE9,
        0xC0,
        0xC0,
        0xE4,
        0xF6,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0xF6,
        0xC4,
        0xFB,
        0x1F,
        0x1F,
        0x1F,
        0xFB,
        0xC4,
        0xE5,
        0xE9,
        0xEA,
        0xE9,
        0xC4,
        0xF6,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0xF6,
        0xC0,
        0xC4,
        0xF6,
        0x1F,
        0xF6,
        0xC4,
        0xE5,
        0xE9,
        0xF2,
        0x1F,
        0xFB,
        0xFB,
        0xE9,
        0xF2,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0xF6,
        0xC0,
        0xE5,
        0xE9,
        0xF6,
        0xF6,
        0xC0,
        0xE5,
        0xF2,
        0x1F,
        0xDB,
        0x6D,
        0xFB,
        0xC9,
        0xF2,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0xF6,
        0xC0,
        0xE5,
        0xE5,
        0xE9,
        0xE9,
        0xC0,
        0xE9,
        0xFB,
        0x1F,
        0xD6,
        0x92,
        0x1F,
        0xF1,
        0xF1,
        0xFE,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0xF6,
        0xC0,
        0xE5,
        0xEA,
        0xE5,
        0xC0,
        0xC0,
        0xE9,
        0xFB,
        0xFB,
        0xFB,
        0x1F,
        0xF6,
        0xF5,
        0xF9,
        0xFA,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0xF6,
        0xC0,
        0xE5,
        0xEA,
        0xE5,
        0xE5,
        0xC0,
        0xE9,
        0xF7,
        0x1F,
        0xFB,
        0xF6,
        0xC9,
        0xF6,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0xF6,
        0xC4,
        0xE5,
        0xE5,
        0xE5,
        0xE5,
        0xE5,
        0xE9,
        0xEA,
        0xE9,
        0xC4,
        0xC9,
        0xFB,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0xF6,
        0xE4,
        0xC0,
        0xE5,
        0xEA,
        0xE9,
        0xED,
        0xF0,
        0xEC,
        0xEC,
        0xF0,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0xF2,
        0xC4,
        0xE0,
        0xE9,
        0xED,
        0xF4,
        0xF4,
        0xF4,
        0xF4,
        0xF5,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0xFB,
        0xF6,
        0xF6,
        0xF6,
        0xC4,
        0xE0,
        0xED,
        0xF4,
        0xF4,
        0xF4,
        0xF4,
        0xF4,
        0xF9,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0xF2,
        0xC0,
        0xC0,
        0xC0,
        0xC0,
        0xE0,
        0xE9,
        0xF4,
        0xF4,
        0xF4,
        0xF4,
        0xF9,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0xF2,
        0xC0,
        0xE5,
        0xE5,
        0xE5,
        0xE5,
        0xE8,
        0xF4,
        0xF4,
        0xF4,
        0xFA,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0xF2,
        0xC0,
        0xC0,
        0xC0,
        0xC0,
        0xED,
        0xFB,
        0xFE,
        0xFE,
        0xFE,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0xFB,
        0xED,
        0xED,
        0xED,
        0xED,
        0xF6,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
        0x1F,
    ]
)


FLAPPY_BIRD_HEIGHT = const(16)
FLAPPY_BIRD_WIDTH = const(20)

FLAPPY_PILAR_MAX = const(15)
FLAPPY_PILAR_DIST = 100

FLAPPY_GAB_HEIGHT = 100
FLAPPY_GAB_WIDTH = 10

FLAPPY_GRAVITY_JUMP = -6.0
FLAPPY_GRAVITY_TICK = 0.7

FLIPPER_LCD_WIDTH = 0
FLIPPER_LCD_HEIGHT = 0
_game_scale = 1.0

GAME_STATE_LIFE = const(0)
GAME_STATE_GAME_OVER = const(1)

DIRECTION_UP = const(0)
DIRECTION_RIGHT = const(1)
DIRECTION_DOWN = const(2)
DIRECTION_LEFT = const(3)


_is_flipper = False

class POINT:
    __slots__ = ("x", "y", "x2", "y2")
    def __init__(self):
        self.x: int = 0
        self.y: int = 0
        self.x2: int = 0
        self.y2: int = 0


class BIRD:
    __slots__ = ("gravity", "point")
    def __init__(self):
        self.gravity: float = 0.0
        self.point: POINT = POINT()

    def __del__(self):
        if self.point:
            del self.point
            self.point = None


class PILAR:
    __slots__ = ("point", "height", "visible", "passed", "spawned_next")
    def __init__(self):
        self.point: POINT = POINT()
        self.height: int = 0
        self.visible: int = 0
        self.passed: bool = False
        self.spawned_next: bool = False

    def __del__(self):
        if self.point:
            del self.point
            self.point = None


class GameState:
    __slots__ = ("bird", "points", "pilars_count", "pilars", "state", "text_pos", "cloud_y_positions")
    def __init__(self, draw):

        self.bird: BIRD = BIRD()
        self.points: int = 0
        self.pilars_count: int = 0
        self.pilars: list[PILAR] = [PILAR() for _ in range(FLAPPY_PILAR_MAX)]
        self.state: int = GAME_STATE_LIFE
        self.text_pos = Vector(140, 12)
        self.text_pos.x, self.text_pos.y = draw.scale(140, 12)
        _pos = draw.scale_y(10)
        self.cloud_y_positions = [_pos * 2, _pos * 5, _pos * 8, _pos * 11]

    def __del__(self):
        if self.bird:
            del self.bird
            self.bird = None
        if self.pilars:
            for pilar in self.pilars:
                if pilar:
                    del pilar
            self.pilars = None
        del self.text_pos
        self.text_pos = None
        del self.cloud_y_positions
        self.cloud_y_positions = None


_game_state: GameState = None
_game_engine = None


def __flappy_game_random_pilar() -> None:
    """Generate a random pillar."""
    global _game_state

    pilar: PILAR = PILAR()
    pilar.passed = False
    pilar.visible = 1

    pilar.height = randint(1, int(FLIPPER_LCD_HEIGHT - FLAPPY_GAB_HEIGHT - 21))
    pilar.point.y = 0
    pilar.point.y2 = 0
    pilar.point.x = FLIPPER_LCD_WIDTH + FLAPPY_GAB_WIDTH + 1
    pilar.point.x2 = FLIPPER_LCD_WIDTH + FLAPPY_GAB_WIDTH + 1

    _game_state.pilars_count += 1
    _game_state.pilars[_game_state.pilars_count % FLAPPY_PILAR_MAX] = pilar


def __flappy_game_state_init(draw) -> None:
    """Initialize the game state."""
    global _game_state

    bird = BIRD()
    bird.gravity = 0.0
    # Start near left, vertically centered on 240px screen
    bird.point.x, bird.point.x2 = draw.scale(15, 15)
    bird.point.y = FLIPPER_LCD_HEIGHT / 2
    bird.point.y2 = FLIPPER_LCD_HEIGHT / 2

    _game_state.bird = bird
    _game_state.pilars_count = 0
    _game_state.points = 0
    _game_state.state = GAME_STATE_LIFE

    __flappy_game_random_pilar()


def __flappy_game_tick() -> None:
    """Advance game state by one tick."""
    global _game_state

    _game_state.bird.point.x2 = _game_state.bird.point.x
    _game_state.bird.point.y2 = _game_state.bird.point.y

    if _game_state.state != GAME_STATE_LIFE:
        return

    _game_state.bird.gravity += FLAPPY_GRAVITY_TICK
    _game_state.bird.point.y += _game_state.bird.gravity

    # Spawn the next pillar once the current leading pillar crosses the spacing threshold.
    pilar: PILAR = _game_state.pilars[_game_state.pilars_count % FLAPPY_PILAR_MAX]
    spawn_x = (FLIPPER_LCD_WIDTH - FLAPPY_PILAR_DIST) + 3
    if pilar.visible and not pilar.spawned_next and pilar.point.x <= spawn_x:
        pilar.spawned_next = True
        __flappy_game_random_pilar()

    # Bird above screen
    if _game_state.bird.point.y <= 0:
        _game_state.bird.point.y = 0
        _game_state.state = GAME_STATE_GAME_OVER

    # Bird below screen
    if _game_state.bird.point.y + FLAPPY_BIRD_HEIGHT >= FLIPPER_LCD_HEIGHT:
        _game_state.bird.point.y = FLIPPER_LCD_HEIGHT - FLAPPY_BIRD_HEIGHT
        _game_state.state = GAME_STATE_GAME_OVER

    # Update pillars
    for i in range(FLAPPY_PILAR_MAX):
        p = _game_state.pilars[i]
        if p and p.visible and _game_state.state == GAME_STATE_LIFE:
            p.point.x2 = p.point.x
            p.point.y2 = p.point.y

            p.point.x -= 4

            # Score if bird passes pillar
            if (
                _game_state.bird.point.x >= p.point.x + FLAPPY_GAB_WIDTH
                and not p.passed
            ):
                p.passed = True
                _game_state.points += 1
            # Pillar off left side
            if p.point.x < -FLAPPY_GAB_WIDTH:
                p.visible = 0

            # Horizontal overlap check
            if (
                _game_state.bird.point.x + FLAPPY_BIRD_HEIGHT >= p.point.x
                and _game_state.bird.point.x <= p.point.x + FLAPPY_GAB_WIDTH
            ):
                # Bottom pipe
                if (
                    _game_state.bird.point.y + FLAPPY_BIRD_WIDTH - 2
                    >= p.height + FLAPPY_GAB_HEIGHT
                ):
                    _game_state.state = GAME_STATE_GAME_OVER
                    break
                # Top pipe
                if _game_state.bird.point.y < p.height:
                    _game_state.state = GAME_STATE_GAME_OVER
                    break


def __flappy_game_flap() -> None:
    """Make the bird jump."""
    global _game_state

    _game_state.bird.gravity = FLAPPY_GRAVITY_JUMP


def __player_update(self, game):
    """Move the player based on input."""

    global _game_state

    button: int = game.input

    if button in (BUTTON_UP, BUTTON_CENTER):
        if _game_state.state == GAME_STATE_GAME_OVER:
            __flappy_game_state_init(game.draw)
        elif _game_state.state == GAME_STATE_LIFE:
            __flappy_game_flap()
        button = -1

    __flappy_game_tick()


def __player_render(self, draw, game) -> None:
    """Render the player."""

    global _game_state, _game_scale

    s = _game_scale

    # Sky background
    draw._fill_rectangle(0, 0, FLIPPER_LCD_WIDTH, FLIPPER_LCD_HEIGHT, TFT_CYAN)

    # Clouds
    cloud_x_offset = int(_game_state.points * 2) % FLIPPER_LCD_WIDTH
    for i, y in enumerate(_game_state.cloud_y_positions):
        x = (i * int(80 * s) - cloud_x_offset) % (FLIPPER_LCD_WIDTH + int(80 * s)) - int(40 * s)
        if -int(40 * s) < x < FLIPPER_LCD_WIDTH:
            draw._fill_circle(x, y, max(3, int(12 * s)), TFT_WHITE)
            draw._fill_circle(x + int(10 * s), y - int(5 * s), max(3, int(10 * s)), TFT_WHITE)
            draw._fill_circle(x - int(8 * s), y - int(3 * s), max(2, int(8 * s)), TFT_WHITE)

    # Ground
    ground_height = max(8, int(20 * s))
    draw._fill_rectangle(
        0, FLIPPER_LCD_HEIGHT - ground_height,
        FLIPPER_LCD_WIDTH, ground_height,
        TFT_GREEN,
    )
    # Grass lines
    for x in range(0, FLIPPER_LCD_WIDTH, max(5, int(15 * s))):
        draw._line(
            x,FLIPPER_LCD_HEIGHT - ground_height,
            x,FLIPPER_LCD_HEIGHT - ground_height + max(2, int(5 * s)),
            TFT_DARKGREEN if not _is_flipper else TFT_WHITE,
        )

    if _game_state.state == GAME_STATE_LIFE:
        # Draw pillars
        for i in range(FLAPPY_PILAR_MAX):
            pilar = _game_state.pilars[i]
            if (
                pilar
                and pilar.visible == 1
                and pilar.point.x >= 0
                and pilar.point.x < FLIPPER_LCD_WIDTH
            ):
                # Top pillar
                draw._fill_rectangle(
                    pilar.point.x,pilar.point.y,
                    FLAPPY_GAB_WIDTH, pilar.height,
                    TFT_GREEN if not _is_flipper else TFT_WHITE,
                )
                draw._rectangle(
                    pilar.point.x,pilar.point.y,
                    FLAPPY_GAB_WIDTH, pilar.height,
                    TFT_DARKGREEN if not _is_flipper else TFT_WHITE,
                )

                # Bottom pillar
                y = (
                    FLIPPER_LCD_HEIGHT
                    - (pilar.height + FLAPPY_GAB_HEIGHT)
                    - ground_height
                )
                if y > 0:
                    draw._fill_rectangle(
                        pilar.point.x, pilar.point.y + pilar.height + FLAPPY_GAB_HEIGHT,
                        FLAPPY_GAB_WIDTH, y,
                        TFT_GREEN if not _is_flipper else TFT_WHITE,
                    )
                    draw._rectangle(
                        pilar.point.x, pilar.point.y + pilar.height + FLAPPY_GAB_HEIGHT,
                        FLAPPY_GAB_WIDTH, y,
                        TFT_DARKGREEN if not _is_flipper else TFT_WHITE,
                    )

        # Draw the bird
        self.position.x = _game_state.bird.point.x
        self.position.y = _game_state.bird.point.y

        draw._bytearray(_game_state.bird.point.x, _game_state.bird.point.y, FLAPPY_BIRD_WIDTH, FLAPPY_BIRD_HEIGHT, BIRD_ICON)

        # Score
        draw._text(_game_state.text_pos.x, _game_state.text_pos.y, f"Score: {_game_state.points}", TFT_BLACK)

    elif _game_state.state == GAME_STATE_GAME_OVER:
        self.position = Vector(-100, -100)

        # Game over box
        bx = int(120 * s)
        by = int(100 * s)
        bw = int(100 * s)
        bh = int(60 * s)
        draw._fill_rectangle(bx, by, bw, bh, TFT_YELLOW)
        draw._rectangle(bx, by, bw, bh, TFT_BLACK)
        draw._text(int(130 * s), int(110 * s), "Game Over!", TFT_BLACK)
        draw._text(int(125 * s), int(125 * s), f"Score: {_game_state.points}", TFT_BLACK)
        draw._text(int(125 * s), int(140 * s), "Press to Retry", TFT_BLACK)


def __player_spawn(level, draw):
    """Spawn the player entity."""
    from picoware.engine.entity import Entity, ENTITY_TYPE_PLAYER, SPRITE_3D_NONE

    global _game_state

    player = Entity(
        "Player",
        ENTITY_TYPE_PLAYER,
        Vector(-100, -100),
        Vector(FLAPPY_BIRD_WIDTH, FLAPPY_BIRD_HEIGHT),
        None,
        None,
        None,
        None,
        None,
        __player_update,
        __player_render,
        None,
        True,
        SPRITE_3D_NONE,
        0x0000,
    )

    level.entity_add(player)
    _game_state = GameState(draw)
    __flappy_game_state_init(draw)


def start(view_manager) -> bool:
    """Start the app."""
    from picoware.engine.game import Game
    from picoware.engine.level import Level
    from picoware.engine.engine import GameEngine
    from picoware.system.boards import BOARD_FLIPPER_ZERO, BOARD_POOM

    global _game_engine, _game_scale, FLIPPER_LCD_WIDTH, FLIPPER_LCD_HEIGHT, FLAPPY_PILAR_DIST, FLAPPY_GAB_HEIGHT, FLAPPY_GAB_WIDTH
    global _is_flipper

    _is_flipper = view_manager.board_id in (BOARD_FLIPPER_ZERO, BOARD_POOM)

    draw = view_manager.draw
    FLIPPER_LCD_WIDTH = draw.size.x
    FLIPPER_LCD_HEIGHT = draw.size.y
    _game_scale = min(FLIPPER_LCD_WIDTH, FLIPPER_LCD_HEIGHT) / 240

    FLAPPY_GAB_WIDTH, FLAPPY_GAB_HEIGHT = draw.scale(16, 140)
    FLAPPY_PILAR_DIST = int(FLIPPER_LCD_WIDTH * 0.35)

    game = Game(
        "Flappy Bird",
        draw.size,
        draw,
        view_manager.input_manager,
        0x0000,
        0xFFFF,
        None,
        None,
        None,
    )

    level = Level("Level", draw.size, game)

    game.level_add(level)

    __player_spawn(level, draw)

    _game_engine = GameEngine(game, 240)
    return _game_engine is not None


def run(view_manager) -> None:
    """Run the app."""
    button: int = view_manager.button

    if button == BUTTON_BACK:
        view_manager.back()
        return

    if _game_engine:
        _game_engine.run_async(False)


def stop(view_manager) -> None:
    """Stop the app."""
    from gc import collect

    global _game_engine, _game_state, _game_scale

    if _game_engine is not None:
        _game_engine.stop()
        del _game_engine
        _game_engine = None
    _game_scale = 1.0

    if _game_state is not None:
        del _game_state
        _game_state = None

    collect()
