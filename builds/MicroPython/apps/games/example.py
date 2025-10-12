BIRD = bytes(
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

_game_engine = None


def __player_spawn(level):
    """Spawn the player in the level."""
    from picoware.engine.entity import Entity, ENTITY_TYPE_PLAYER, SPRITE_3D_NONE
    from picoware.system.vector import Vector

    player = Entity(
        "Player",  # name
        ENTITY_TYPE_PLAYER,  # type
        Vector(160, 160),  # position
        Vector(20, 16),  # size
        BIRD,  # sprite data
        None,  # sprite data left
        None,  # sprite data right
        None,  # start
        None,  # stop
        __player_update,  # update
        None,  # render
        None,  # collide
        SPRITE_3D_NONE,  # 3d type
        True,  # is_8bit
    )
    level.entity_add(player)


def __player_update(self, game):
    """Move the player based on input"""
    from picoware.system.buttons import (
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_RIGHT,
    )
    from picoware.system.vector import Vector

    button: int = game.input
    position: Vector = self.position

    if button == BUTTON_UP:
        position.y -= 5
    elif button == BUTTON_DOWN:
        position.y += 5
    elif button == BUTTON_LEFT:
        position.x -= 5
    elif button == BUTTON_RIGHT:
        position.x += 5

    if (
        position.x >= 0
        and position.x < (game.size.x - self.size.x)
        and position.y >= 0
        and position.y < (game.size.y - self.size.y)
    ):
        self.position = position


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.engine.game import Game
    from picoware.engine.level import Level
    from picoware.engine.engine import GameEngine

    global _game_engine

    draw = view_manager.get_draw()

    # Create the game instance with its name, start/stop callbacks, and colors.
    game = Game(
        "Example",  # name
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
    level = Level("Example Level", draw.size, game)
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

    global _game_engine

    if _game_engine is not None:
        _game_engine.stop()
        del _game_engine
        _game_engine = None

    collect()
