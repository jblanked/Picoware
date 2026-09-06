"""Level - Game levels with camera settings."""

from micropython import const
import engine

CAMERA_FIRST_PERSON = const(0)
CAMERA_THIRD_PERSON = const(1)


class Level(engine.Level):
    """Represent a game level containing entities and rendering state.

    Args:
        name (str): Level name.
        size (Vector): Level world size.
        game (Game): Game that owns the level.
        start (callable or None): Callback called when the level starts. Defaults to None.
        stop (callable or None): Callback called when the level stops. Defaults to None.

    Attributes:
        name (str): Level name. Writable.
        size (Vector): Level world size. Writable.
        entity_count (int): Number of entities in the level. Read-only.
        clear_allowed (bool): Whether level clearing is allowed. Writable.

    Methods:
        - clear(): Clear the level's non-player entities.
        - entity_add(entity): Add an entity to the level.
        - entity_remove(entity): Remove an entity from the level.
        - set_name(name): Set the level name.
        - set_size(size): Set the level world size.
        - set_clear_allowed(clear_allowed): Set whether clearing is allowed.
        - set_light_direction(x, y, z): Set the 3D lighting direction.
        - set_shadow_color(color): Set the 3D shadow color.
        - get_entity(index): Return an entity by index.
        - render_3d_sprite(path, view_height=0.0, clamp=False, wireframe=True): Render a file-backed 3D sprite for the player.
        - __del__(): Release the native level resources.
    """

    def __setattr__(self, name, value):
        """Set a level attribute, routing to the matching setter.

        Args:
            name (str): Attribute name to set.
            value (object): New value for the attribute.
        """
        if name == "name":
            self.set_name(value)
        elif name == "size":
            self.set_size(value)
        elif name == "clear_allowed":
            self.set_clear_allowed(value)
        else:
            super().__setattr__(name, value)
