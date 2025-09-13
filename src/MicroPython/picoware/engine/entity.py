from micropython import const
from picoware.system.vector import Vector

# entity state
ENTITY_STATE_IDLE = const(0)
ENTITY_STATE_MOVING = const(1)
ENTITY_STATE_MOVING_TO_START = const(2)
ENTITY_STATE_MOVING_TO_END = const(3)
ENTITY_STATE_ATTACKING = const(4)
ENTITY_STATE_DEAD = const(5)

# entity type
ENTITY_TYPE_PLAYER = const(0)
ENTITY_TYPE_ENEMY = const(1)
ENTITY_TYPE_ICON = const(2)
ENTITY_TYPE_NPC = const(3)
ENTITY_TYPE_3D_SPRITE = const(4)

# sprite 3D types
SPRITE_3D_NONE = const(0)
SPRITE_3D_HUMANOID = const(1)
SPRITE_3D_TREE = const(2)
SPRITE_3D_HOUSE = const(3)
SPRITE_3D_PILLAR = const(4)
SPRITE_3D_CUSTOM = const(5)


class Entity:
    """
    Represents an entity in the game.
    """

    def __init__(
        self,
        name: str,
        entity_type: int,
        position: Vector,
        size: Vector,
        sprite_data: bytes,
        sprite_data_left: bytes = None,
        sprite_data_right: bytes = None,
        start: callable = None,
        stop: callable = None,
        update: callable = None,
        render: callable = None,
        collision: callable = None,
        sprite_3d_type: int = SPRITE_3D_NONE,
        is_8bit: bool = True,
    ):
        """
        Initializes the entity.

        :param name: The name of the entity.
        :param entity_type: The type of the entity (e.g., player, enemy).
        :param position: The initial position of the entity.
        :param size: The size of the entity.
        :param sprite_data: The sprite data for the entity.
        :param sprite_data_left: The sprite data for the entity facing left (optional).
        :param sprite_data_right: The sprite data for the entity facing right (optional).
        :param start: function(Entity, Game) - the function called when the entity is created
        :param stop: function(Entity, Game) - the function called when the entity is destroyed
        :param update: function(Entity, Game) - the function called every frame
        :param render: function(Entity, Draw, Game) - the function called every frame to render the entity
        :param collision: function(Entity, Entity, Game) - the function called when the entity collides with another entity
        :param sprite_3d_type: The type of 3D sprite (if any).
        :param is_8bit: Whether the sprite is in 8-bit format.
        """
        from picoware.gui.image import Image

        self.name: str = name
        self.type: int = entity_type
        self._position: Vector = position
        self._old_position: Vector = position
        self.size: Vector = size
        self.is_8bit: bool = is_8bit
        #
        self.sprite = Image()
        self.sprite.from_byte_array(sprite_data, size, is_8bit)
        self.sprite_left = None
        self.sprite_right = None
        if sprite_data_left:
            self.sprite_left = Image()
            self.sprite_left.from_byte_array(sprite_data_left, size, is_8bit)
        if sprite_data_right:
            self.sprite_right = Image()
            self.sprite_right.from_byte_array(sprite_data_right, size, is_8bit)
        #
        self._start = start
        self._stop = stop
        self._update = update
        self._render = render
        self._collision = collision
        #
        self.is_active: bool = False
        self.is_visible: bool = True
        self.is_player: bool = False
        #
        self.direction: Vector = Vector(1, 0)
        self.plane: Vector = Vector(0, 0)
        #
        self.state: int = ENTITY_STATE_IDLE
        self.start_position: Vector = position
        self.end_position: Vector = position
        self.move_timer: float = 0
        self.elapsed_move_timer: float = 0
        self.radius: float = self.size.x / 2
        self.speed: float = 0
        self.attack_timer: float = 0
        self.elapsed_attack_timer: float = 0
        self.strength: float = 0
        self.health: float = 0
        self.max_health: float = 0
        self.level: float = 0
        self.xp: float = 0
        self.health_regen: float = 0
        self.elapsed_health_regen: float = 0
        #
        self.sprite_3d = None  # for now
        self.sprite_3d_type: int = sprite_3d_type
        self.sprite_rotation: float = 0.0
        self.sprite_scale: float = 1.0

    def collision(self, other, game):
        """Called when the entity collides with another entity."""
        if self._collision:
            self._collision(self, other, game)

    @property
    def position(self) -> Vector:
        """Used by the engine to get the position of the entity."""
        return Vector(self._position.x, self._position.y)

    @position.setter
    def position(self, value: Vector):
        """Used by the engine to set the position of the entity."""
        self.position_old = self._position
        self._position = value

    def render(self, draw, game):
        """Called every frame to render the entity."""
        if self._render:
            self._render(self, draw, game)

    def start(self, game):
        """Called when the entity is created."""
        if self._start:
            self._start(self, game)
            self.is_active = True

    def stop(self, game):
        """Called when the entity is destroyed."""
        if self._stop:
            self._stop(self, game)
            self.is_active = False

    def update(self, game):
        """Called every frame."""
        if self._update:
            self._update(self, game)
