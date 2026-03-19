from micropython import const
import engine

SPRITE_HUMANOID = const(0)
SPRITE_TREE = const(1)
SPRITE_HOUSE = const(2)
SPRITE_PILLAR = const(3)
SPRITE_CUSTOM = const(4)


class Sprite3D(engine.Sprite3D):
    """3D sprite class for rendering 3D objects"""

    def __setattr__(self, name, value):
        if name == "position":
            self.set_position(value)
        elif name == "rotation_y":
            self.set_rotation_y(value)
        elif name == "scale_factor":
            self.set_scale(value)
        elif name == "active":
            self.set_active(value)
        else:
            super().__setattr__(name, value)
