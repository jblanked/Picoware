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
    from picoware.engine.image import Image
    from picoware.system.vector import Vector

    _size = Vector(20, 16)

    player = Entity(
        "Player",  # name
        ENTITY_TYPE_PLAYER,  # type
        Vector(level.size.x // 2, level.size.y // 2),  # position
        _size,  # size
        Image(_size, True, BIRD),  # sprite data (Image)
        None,  # sprite data left (Image)
        None,  # sprite data right (Image)
        None,  # start
        None,  # stop
        __player_update,  # update
        None,  # render
        None,  # collision
        True,  # is_8bit
        SPRITE_3D_NONE,  # 3d type
        0x0000,  # 3d color
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

    button: int = game.input
    position = self.position

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
    from picoware.system.vector import Vector
    from picoware.engine.camera import Camera

    global _game_engine

    draw = view_manager.draw
    c = Camera()

    # Create the game instance with its name, start/stop callbacks, and colors.
    game = Game(
        "Example",  # name
        draw.size,  # size
        draw,  # draw context
        view_manager.input_manager,  # input manager
        0x0000,  # foreground color
        0xFFFF,  # background color
        c,  # camera context
        None,  # start
        None,  # stop
    )

    # Create and add a level to the game.
    level = Level("Example Level", draw.size, game)
    game.level_add(level)

    # Add the player entity to the level
    __player_spawn(level)

    e = level.get_entity(0)
    print(e)
    print(e.position)
    e.position = Vector(9, e.position.y, e.position.z)
    print(e.position)
    print(e)
    e.position = Vector(90, 0, 0)
    print(e.position)
    print(e)

    print(game.camera.position)
    print(dir(game.camera.position))
    game.camera.position = Vector(2, 0, 0)
    print(game.camera.position)
    print(game.camera)

    c.position = Vector(-1, 0, 0)
    print(game.camera)
    print(game.camera.height)

    # Create the game engine (with 240 frames per second target).
    _game_engine = GameEngine(game, 240)

    game.level_switch(0)

    print(_game_engine.game.current_level)

    return _game_engine is not None


def run(view_manager) -> None:
    """Run the app."""
    from picoware.system.buttons import BUTTON_BACK

    if _game_engine:
        _game_engine.run_async(False)

    input_manager = view_manager.input_manager
    button: int = input_manager.button

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


from picoware.system.view_manager import ViewManager
from picoware.system.view import View

vm = None

try:
    vm = ViewManager()
    vm.add(
        View(
            "app_tester",
            run,
            start,
            stop,
        )
    )
    vm.switch_to("app_tester")
    while True:
        vm.run()
finally:
    del vm
    vm = None
