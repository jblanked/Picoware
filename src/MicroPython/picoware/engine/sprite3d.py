"""Sprite3D - 3D sprites for the game engine."""

from micropython import const
import engine

SPRITE_HUMANOID = const(0)
SPRITE_TREE = const(1)
SPRITE_HOUSE = const(2)
SPRITE_PILLAR = const(3)
SPRITE_CUSTOM = const(4)


class Sprite3D(engine.Sprite3D):
    """Represent a native 3D sprite made from triangles.

    Attributes:
        position (Vector): Sprite position. Writable.
        rotation_y (float): Rotation around the Y axis. Writable.
        scale_factor (float): Sprite scale factor. Writable.
        type (int): Sprite type constant. Read-only.
        active (bool): Whether the sprite is active. Writable.
        triangle_count (int): Number of triangles in the sprite. Read-only.
        MAX_TRIANGLES_PER_SPRITE (int): Maximum supported triangle count.
        SPRITE_HUMANOID (int): Humanoid sprite type.
        SPRITE_TREE (int): Tree sprite type.
        SPRITE_HOUSE (int): House sprite type.
        SPRITE_PILLAR (int): Pillar sprite type.
        SPRITE_CUSTOM (int): Custom sprite type.

    Methods:
        - add_triangle(x1, y1, z1, x2, y2, z2, x3, y3, z3, color=0x0000, wireframe=True): Add a triangle to the sprite.
        - clear_triangles(): Remove all triangles from the sprite.
        - create_humanoid(height=1.8, color=0x0000): Create a humanoid mesh.
        - create_tree(height=2.0, color=0x0000): Create a tree mesh.
        - create_house(width=2.0, height=2.5, color=0x0000): Create a house mesh.
        - create_pillar(height=3.0, radius=0.3, color=0x0000): Create a pillar mesh.
        - create_wall(x, y, z, width=4.0, height=1.5, depth=0.2, color=0x0000): Create a wall mesh.
        - create_cube(x, y, z, width, height, depth, color=0x0000): Create a cube mesh.
        - create_cylinder(x, y, z, radius, height, segments, color=0x0000): Create a cylinder mesh.
        - create_sphere(x, y, z, radius, segments, color=0x0000): Create a sphere mesh.
        - create_triangular_prism(x, y, z, width, height, depth, color=0x0000): Create a triangular prism mesh.
        - initialize_as_house(position, width, height, rotation, color=0x0000): Initialize a house at a position.
        - initialize_as_humanoid(position, height, rotation, color=0x0000): Initialize a humanoid at a position.
        - initialize_as_pillar(position, height, radius, color=0x0000): Initialize a pillar at a position.
        - initialize_as_tree(position, height, color=0x0000): Initialize a tree at a position.
        - set_position(position): Set the sprite position.
        - set_rotation_y(rotation_y): Set the Y-axis rotation.
        - set_scale(scale_factor): Set the sprite scale.
        - set_active(active): Set whether the sprite is active.
        - set_wireframe(wireframe): Set wireframe rendering for the mesh.
        - from_path(path, wireframe=True): Load a sprite mesh from a file.
        - to_path(path): Save the sprite mesh to a file.
        - bake_transform(): Apply rotation and scale to stored triangles.
        - __del__(): Release the native sprite resources.
    """

    def __setattr__(self, name, value):
        """Set a sprite attribute, routing to the matching setter.

        Args:
            name (str): Attribute name to set.
            value (object): New value for the attribute.
        """
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
