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

    def render(self):
        """Render the level"""
        if self._clear_allowed:
            self.game.draw.clear(
                Vector(0, 0), self.game.size, self.game.background_color
            )

        for entity in self.entities:
            if entity.is_active:
                entity.render(self.game.draw, self.game)

                if not entity.is_visible:
                    continue

                if entity.sprite:
                    self.game.draw.image_bytearray(
                        Vector(
                            entity.position.x - self.game.position.x,
                            entity.position.y - self.game.position.y,
                        ),
                        entity.size,
                        entity.sprite._raw,
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
