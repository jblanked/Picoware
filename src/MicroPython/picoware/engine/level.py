from micropython import const
import engine

CAMERA_FIRST_PERSON = const(0)
CAMERA_THIRD_PERSON = const(1)


class Level(engine.Level):
    """
    Represents a level in the game.
    """

    def __setattr__(self, name, value):
        if name == "name":
            self.set_name(value)
        elif name == "size":
            self.set_size(value)
        elif name == "clear_allowed":
            self.set_clear_allowed(value)
        else:
            super().__setattr__(name, value)
