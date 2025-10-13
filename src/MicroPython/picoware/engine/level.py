from micropython import const
from picoware.system.vector import Vector

CAMERA_FIRST_PERSON = const(0)
CAMERA_THIRD_PERSON = const(1)


class Level:
    """
    Represents a level in the game.
    """

    def __init__(
        self,
        name: str,
        size: Vector,
        game,
        start=None,  # start is a function that is called when the level is created
        stop=None,  # stop is a function that is called when the level is destroyed
    ):
        """
        Initializes the level.

        :param name: str - the name of the level
        :param size: Vector - the size of the level
        :param game: Game - the game to which the level belongs
        :param start: function(Level) - the function called when the level is created
        :param stop: function(Level) - the function called when the level is destroyed
        """
        self.name = name
        self.size = size
        self.game = game
        self.entities = []  # List of entities in the level
        self._clear_allowed: bool = True
        self._start = start
        self._stop = stop

    def __del__(self):
        self.clear()

    @property
    def clear_allowed(self) -> bool:
        """Get if the level is allowed to clear the screen"""
        return self._clear_allowed

    @clear_allowed.setter
    def clear_allowed(self, value: bool):
        """Set if the level is allowed to clear the screen"""
        self._clear_allowed = value

    def clear(self):
        """Clear the level"""
        for entity in self.entities:
            entity.stop(self.game)
        self.entities.clear()

    def collision_list(self, entity) -> list:
        """Return a list of entities that the entity collided with"""
        collided = []
        for other in self.entities:
            if entity != other and self.is_collision(entity, other):
                collided.append(other)
        return collided

    def entity_add(self, entity):
        """Add an entity to the level"""
        self.entities.append(entity)
        entity.start(self.game)
        entity.is_active = True

    def entity_remove(self, entity):
        """Remove an entity from the level"""
        self.entities.remove(entity)

    def has_collided(self, entity) -> bool:
        """Check for collisions with other entities"""
        for other in self.entities:
            if entity != other and self.is_collision(entity, other):
                return True
        return False

    def is_collision(self, entity, other) -> bool:
        """Check if two entities collided using AABB logic"""
        return (
            entity.position.x < other.position.x + other.size.x
            and entity.position.x + entity.size.x > other.position.x
            and entity.position.y < other.position.y + other.size.y
            and entity.position.y + entity.size.y > other.position.y
        )

    def render(self, perspective=CAMERA_FIRST_PERSON, camera_params=None):
        """Render the level"""
        if self._clear_allowed:
            self.game.draw.clear(
                Vector(0, 0), self.game.size, self.game.background_color
            )

        # If using third person perspective but no camera params provided, calculate them from player
        if perspective == CAMERA_THIRD_PERSON and camera_params is None:
            from math import sqrt
            from picoware.engine.camera import CameraParams

            calculated_camera_params = CameraParams()
            # Find the player entity to calculate 3rd person camera
            player = None
            for entity in self.entities:
                if entity is not None and entity.is_player:
                    player = entity
                    break

            if player is not None:
                # Calculate 3rd person camera position behind the player
                # Use same parameters as Player class for consistency
                camera_distance = 2.0  # Closer distance for better visibility

                # Normalize direction vector to ensure consistent behavior
                dir_length = sqrt(
                    player.direction.x * player.direction.x
                    + player.direction.y * player.direction.y
                )
                if dir_length < 0.001:
                    # Fallback if direction is zero
                    dir_length = 1.0
                    player.direction = Vector(1, 0)  # Default forward direction

                normalized_dir = Vector(
                    player.direction.x / dir_length, player.direction.y / dir_length
                )

                calculated_camera_params.position = Vector(
                    player.position.x - normalized_dir.x * camera_distance,
                    player.position.y - normalized_dir.y * camera_distance,
                )
                calculated_camera_params.direction = normalized_dir
                calculated_camera_params.plane = player.plane
                calculated_camera_params.height = 1.6
                camera_params = calculated_camera_params

        for entity in self.entities:
            if entity and entity.is_active:
                entity.render(self.game.draw, self.game)

                if not entity.is_visible:
                    continue  # Skip rendering if entity is not visible

                # Only draw the 2D sprite if it exists
                if entity.sprite:
                    self.game.draw.image_bytearray(
                        Vector(
                            entity.position.x - self.game.position.x,
                            entity.position.y - self.game.position.y,
                        ),
                        entity.size,
                        entity.sprite._raw,
                    )

                # Render 3D sprite if it exists
                if entity.has_3d_sprite:
                    # screen size from the game draw object
                    screen_size = self.game.draw.size

                    if perspective == CAMERA_FIRST_PERSON:

                        # First person: render from player's own perspective
                        if entity.is_player:
                            # Use entity's own direction and plane for rendering
                            entity.render3DSprite(
                                self.game.draw,
                                entity.position,
                                entity.direction,
                                entity.plane,
                                1.5,
                                screen_size,
                            )
                        else:
                            # For non-player entities, render from the player's perspective
                            # We need to find the player entity to get the view parameters
                            player = None
                            for entity in self.entities:
                                if entity is not None and entity.is_player:
                                    player = entity
                                    break
                            if player is not None:
                                entity.render_3d_sprite(
                                    self.game.draw,
                                    player.position,
                                    player.direction,
                                    1.5,
                                    screen_size,
                                )

                    elif perspective == CAMERA_THIRD_PERSON and camera_params:
                        # Third person: render ALL entities (including player) from the external camera perspective
                        entity.render_3d_sprite(
                            self.game.draw,
                            camera_params.position,
                            camera_params.direction,
                            camera_params.height,
                            screen_size,
                        )

        if self._clear_allowed:
            self.game.draw.swap()

    def start(self):
        """Start the level"""
        if self._start:
            self._start(self)

    def stop(self):
        """Stop the level"""
        if self._stop:
            self._stop(self)

    def update(self):
        """Update the level"""
        for entity in self.entities:
            if entity.is_active:
                entity.update(self.game)
                collided = self.collision_list(entity)
                for other in collided:
                    entity.collision(other, self.game)
