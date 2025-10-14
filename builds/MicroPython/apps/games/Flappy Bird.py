# picoware/apps/games/Flappy Bird.py
# Original from https://github.com/xMasterX/all-the-plugins/blob/dev/base_pack/flappy_bird

BIRD_ICON = bytes(
    [
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xF6,
        0xED,
        0xED,
        0xF2,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xF6,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xF6,
        0xE9,
        0xC0,
        0xC0,
        0xE4,
        0xF6,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xF6,
        0xC4,
        0xFB,
        0xFF,
        0xFF,
        0xFF,
        0xFB,
        0xC4,
        0xE5,
        0xE9,
        0xEA,
        0xE9,
        0xC4,
        0xF6,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xF6,
        0xC0,
        0xC4,
        0xF6,
        0xFF,
        0xF6,
        0xC4,
        0xE5,
        0xE9,
        0xF2,
        0xFF,
        0xFB,
        0xFB,
        0xE9,
        0xF2,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xF6,
        0xC0,
        0xE5,
        0xE9,
        0xF6,
        0xF6,
        0xC0,
        0xE5,
        0xF2,
        0xFF,
        0xDB,
        0x6D,
        0xFB,
        0xC9,
        0xF2,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xF6,
        0xC0,
        0xE5,
        0xE5,
        0xE9,
        0xE9,
        0xC0,
        0xE9,
        0xFB,
        0xFF,
        0xD6,
        0x92,
        0xFF,
        0xF1,
        0xF1,
        0xFE,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
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
        0xFF,
        0xF6,
        0xF5,
        0xF9,
        0xFA,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xF6,
        0xC0,
        0xE5,
        0xEA,
        0xE5,
        0xE5,
        0xC0,
        0xE9,
        0xF7,
        0xFF,
        0xFB,
        0xF6,
        0xC9,
        0xF6,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
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
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
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
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
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
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
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
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
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
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
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
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
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
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFB,
        0xED,
        0xED,
        0xED,
        0xED,
        0xF6,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
    ]
)

from micropython import const

FLAPPY_BIRD_HEIGHT = const(16)
FLAPPY_BIRD_WIDTH = const(20)

FLAPPY_PILAR_MAX = const(15)
FLAPPY_PILAR_DIST = const(100)

FLAPPY_GAB_HEIGHT = const(100)
FLAPPY_GAB_WIDTH = const(10)

FLAPPY_GRAVITY_JUMP = const(-6.0)
FLAPPY_GRAVITY_TICK = const(0.7)

FLIPPER_LCD_WIDTH = const(320)
FLIPPER_LCD_HEIGHT = const(320)

GAME_STATE_LIFE = const(0)
GAME_STATE_GAME_OVER = const(1)

DIRECTION_UP = const(0)
DIRECTION_RIGHT = const(1)
DIRECTION_DOWN = const(2)
DIRECTION_LEFT = const(3)


class POINT:
    def __init__(self):
        self.x: int = 0
        self.y: int = 0
        self.x2: int = 0
        self.y2: int = 0


class BIRD:
    def __init__(self):
        self.gravity: float = 0.0
        self.point: POINT = POINT()

    def __del__(self):
        if self.point:
            del self.point
            self.point = None


class PILAR:
    def __init__(self):
        self.point: POINT = POINT()
        self.height: int = 0
        self.visible: int = 0
        self.passed: bool = False

    def __del__(self):
        if self.point:
            del self.point
            self.point = None


class GameState:
    def __init__(self):
        self.bird: BIRD = BIRD()
        self.points: int = 0
        self.pilars_count: int = 0
        self.pilars: list[PILAR] = [PILAR() for _ in range(FLAPPY_PILAR_MAX)]
        self.state: int = GAME_STATE_LIFE

    def __del__(self):
        if self.bird:
            del self.bird
            self.bird = None
        if self.pilars:
            for pilar in self.pilars:
                if pilar:
                    del pilar
            self.pilars = None


_game_state: GameState = None
_game_engine = None


def __flappy_game_random_pilar() -> None:
    """Generate a random pilar"""
    import random

    global _game_state

    pilar: PILAR = PILAR()
    pilar.passed = False
    pilar.visible = 1

    pilar.height = random.randint(1, FLIPPER_LCD_HEIGHT - FLAPPY_GAB_HEIGHT)
    pilar.point.y = 0
    pilar.point.y2 = 0
    pilar.point.x = FLIPPER_LCD_WIDTH + FLAPPY_GAB_WIDTH + 1
    pilar.point.x2 = FLIPPER_LCD_WIDTH + FLAPPY_GAB_WIDTH + 1

    _game_state.pilars_count += 1
    _game_state.pilars[_game_state.pilars_count % FLAPPY_PILAR_MAX] = pilar


def __flappy_game_state_init() -> None:
    """Initialize the game state"""
    global _game_state

    bird = BIRD()
    bird.gravity = 0.0
    # Start near left, vertically centered on 240px screen
    bird.point.x = 15
    bird.point.x2 = 15
    bird.point.y = FLIPPER_LCD_HEIGHT / 2
    bird.point.y2 = FLIPPER_LCD_HEIGHT / 2

    _game_state.bird = bird
    _game_state.pilars_count = 0
    _game_state.points = 0
    _game_state.state = GAME_STATE_LIFE

    __flappy_game_random_pilar()


def __flappy_game_tick() -> None:
    """Advance the game state by one tick"""
    global _game_state

    # save previous bird position
    _game_state.bird.point.x2 = _game_state.bird.point.x
    _game_state.bird.point.y2 = _game_state.bird.point.y

    if _game_state.state != GAME_STATE_LIFE:
        return

    _game_state.bird.gravity += FLAPPY_GRAVITY_TICK
    _game_state.bird.point.y += _game_state.bird.gravity

    # Spawn new pillar if needed
    pilar: PILAR = _game_state.pilars[_game_state.pilars_count % FLAPPY_PILAR_MAX]
    if pilar.point.x == (FLIPPER_LCD_WIDTH - FLAPPY_PILAR_DIST) + 3:
        __flappy_game_random_pilar()

    # If the bird's top goes above y=0 => game over
    if _game_state.bird.point.y <= 0:
        _game_state.bird.point.y = 0
        _game_state.state = GAME_STATE_GAME_OVER

    # If the bird's bottom (y + FLAPPY_BIRD_HEIGHT) goes below screen => game over
    if _game_state.bird.point.y + FLAPPY_BIRD_HEIGHT >= FLIPPER_LCD_HEIGHT:
        _game_state.bird.point.y = FLIPPER_LCD_HEIGHT - FLAPPY_BIRD_HEIGHT
        _game_state.state = GAME_STATE_GAME_OVER

    # Update existing pillars
    for i in range(FLAPPY_PILAR_MAX):
        p = _game_state.pilars[i]
        if p and p.visible and _game_state.state == GAME_STATE_LIFE:
            # save previous pillar position
            p.point.x2 = p.point.x
            p.point.y2 = p.point.y

            p.point.x -= 4

            # Add a point if bird passes pillar
            if (
                _game_state.bird.point.x >= p.point.x + FLAPPY_GAB_WIDTH
                and not p.passed
            ):
                p.passed = True
                _game_state.points += 1
            # Pillar goes off the left side
            if p.point.x < -FLAPPY_GAB_WIDTH:
                p.visible = 0

            # Check collision with the top/bottom pipes
            # if the pillar overlaps the bird horizontally...
            if (
                _game_state.bird.point.x + FLAPPY_BIRD_HEIGHT >= p.point.x
                and _game_state.bird.point.x <= p.point.x + FLAPPY_GAB_WIDTH
            ):
                # ...then check if the bird is outside the gap vertically
                # Bottom pipe collision:
                if (
                    _game_state.bird.point.y + FLAPPY_BIRD_WIDTH - 2
                    >= p.height + FLAPPY_GAB_HEIGHT
                ):
                    _game_state.state = GAME_STATE_GAME_OVER
                    break
                # Top pipe collision:
                if _game_state.bird.point.y < p.height:
                    _game_state.state = GAME_STATE_GAME_OVER
                    break


def __flappy_game_flap() -> None:
    """Make the bird flap (jump)"""
    global _game_state

    _game_state.bird.gravity = FLAPPY_GRAVITY_JUMP


def __player_update(self, game):
    """Move the player based on input"""
    from picoware.system.buttons import BUTTON_UP, BUTTON_CENTER

    global _game_state

    button: int = game.input

    if button in (BUTTON_UP, BUTTON_CENTER):
        if _game_state.state == GAME_STATE_GAME_OVER:
            __flappy_game_state_init()
        elif _game_state.state == GAME_STATE_LIFE:
            __flappy_game_flap()
        button = -1

    __flappy_game_tick()


def __player_render(self, draw, game) -> None:
    """Render the player"""
    from picoware.system.vector import Vector
    from picoware.system.colors import TFT_BLACK, TFT_BLUE, TFT_WHITE

    global _game_state

    # draw a border
    draw.rect(
        Vector(0, 0), Vector(FLIPPER_LCD_WIDTH, FLIPPER_LCD_HEIGHT), TFT_BLACK
    )  # black border

    if _game_state.state == GAME_STATE_LIFE:
        # Draw pillars
        for i in range(FLAPPY_PILAR_MAX):
            pilar = _game_state.pilars[i]
            if pilar and pilar.visible == 1:
                # Top pillar outline
                draw.rect(
                    Vector(pilar.point.x, pilar.point.y),
                    Vector(FLAPPY_GAB_WIDTH, pilar.height),
                    TFT_BLUE,
                )

                # Bottom pillar outline
                draw.rect(
                    Vector(
                        pilar.point.x, pilar.point.y + pilar.height + FLAPPY_GAB_HEIGHT
                    ),
                    Vector(
                        FLAPPY_GAB_WIDTH,
                        FLIPPER_LCD_HEIGHT - (pilar.height + FLAPPY_GAB_HEIGHT),
                    ),
                    TFT_BLUE,
                )

        # Draw the bird
        self.position = Vector(_game_state.bird.point.x, _game_state.bird.point.y)

        draw.image_bytearray(
            self.position, Vector(FLAPPY_BIRD_WIDTH, FLAPPY_BIRD_HEIGHT), BIRD_ICON
        )

        # Score
        draw.text(Vector(140, 12), f"Score: {_game_state.points}", TFT_BLACK)

    elif _game_state.state == GAME_STATE_GAME_OVER:
        self.position = Vector(-100, -100)

        # Simple "Game Over" box in upper-left area
        draw.fill_rectangle(Vector(129, 128), Vector(62, 24), TFT_WHITE)
        draw.rect(Vector(129, 128), Vector(62, 24), TFT_BLACK)
        draw.text(Vector(132, 130), "Game Over", TFT_BLACK)
        draw.text(Vector(132, 140), f"Score: {_game_state.points}", TFT_BLACK)


def __player_spawn(level):
    """Spawn the player in the level."""
    from picoware.engine.entity import Entity, ENTITY_TYPE_PLAYER, SPRITE_3D_NONE
    from picoware.system.vector import Vector

    global _game_state

    player = Entity(
        "Player",  # name
        ENTITY_TYPE_PLAYER,  # type
        Vector(-100, -100),  # position
        Vector(FLAPPY_BIRD_WIDTH, FLAPPY_BIRD_HEIGHT),  # size
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
    _game_state = GameState()
    __flappy_game_state_init()


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.engine.game import Game
    from picoware.engine.level import Level
    from picoware.engine.engine import GameEngine

    global _game_engine

    draw = view_manager.get_draw()

    # Create the game instance with its name, start/stop callbacks, and colors.
    game = Game(
        "Flappy Bird",  # name
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

    global _game_engine, _game_state

    if _game_engine is not None:
        _game_engine.stop()
        del _game_engine
        _game_engine = None

    if _game_state is not None:
        del _game_state
        _game_state = None

    collect()
