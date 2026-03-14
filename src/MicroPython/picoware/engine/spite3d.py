from micropython import const
import engine

SPRITE_HUMANOID = const(0)
SPRITE_TREE = const(1)
SPRITE_HOUSE = const(2)
SPRITE_PILLAR = const(3)
SPRITE_CUSTOM = const(4)


class Sprite3D(engine.Sprite3D):
    """3D sprite class for rendering 3D objects"""
