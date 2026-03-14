from micropython import const
import engine

CAMERA_FIRST_PERSON = const(0)
CAMERA_THIRD_PERSON = const(1)


class Level(engine.Level):
    """
    Represents a level in the game.
    """
