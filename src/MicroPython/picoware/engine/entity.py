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
        sprite_3d_color: int = 0x000000,
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
        self.sprite: Image = None
        if sprite_data:
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

        if self.sprite_3d_type != SPRITE_3D_NONE:
            self.create_3d_sprite(self.sprite_3d_type, color=sprite_3d_color)

    def __del__(self):
        if self.sprite:
            del self.sprite
            self.sprite = None
        if self.sprite_left:
            del self.sprite_left
            self.sprite_left = None
        if self.sprite_right:
            del self.sprite_right
            self.sprite_right = None
        if self.sprite_3d:
            del self.sprite_3d
            self.sprite_3d = None

    @property
    def has_3d_sprite(self) -> bool:
        """Returns True if the entity has a 3D sprite."""
        return self.sprite_3d_type != SPRITE_3D_NONE and self.sprite_3d is not None

    @property
    def position(self) -> Vector:
        """Used by the engine to get the position of the entity."""
        return Vector(self._position.x, self._position.y)

    @position.setter
    def position(self, value: Vector):
        """Used by the engine to set the position of the entity."""
        self.position_old = self._position
        self._position = value

    def create_3d_sprite(
        self,
        sprite_3d_type: int,
        height: float = 2.0,
        width: float = 1.0,
        rotation: float = 0.0,
        color: int = 0x000000,
    ):
        """Creates a 3D sprite for the entity."""
        from picoware.engine.spite3d import Sprite3D

        self.destroy_3d_sprite()

        self.sprite_3d_type = sprite_3d_type
        self.sprite_rotation = rotation

        if sprite_3d_type == SPRITE_3D_HUMANOID:
            self.sprite_3d = Sprite3D()
            self.sprite_3d.initialize_as_humanoid(
                self.position, height, rotation, color
            )
        elif sprite_3d_type == SPRITE_3D_TREE:
            self.sprite_3d = Sprite3D()
            self.sprite_3d.initialize_as_tree(self.position, height, color)
        elif sprite_3d_type == SPRITE_3D_HOUSE:
            self.sprite_3d = Sprite3D()
            self.sprite_3d.initialize_as_house(
                self.position, width, height, rotation, color
            )
        elif sprite_3d_type == SPRITE_3D_PILLAR:
            self.sprite_3d = Sprite3D()
            self.sprite_3d.initialize_as_pillar(self.position, height, width, color)

    def collision(self, other, game):
        """Called when the entity collides with another entity."""
        if self._collision:
            self._collision(self, other, game)

    def destroy_3d_sprite(self):
        """Destroys the 3D sprite associated with the entity."""
        if self.sprite_3d:
            del self.sprite_3d
            self.sprite_3d = None
        self.sprite_3d_type = SPRITE_3D_NONE

    def project_3d_to_2d(
        self,
        vertex,
        player_pos: Vector,
        player_dir: Vector,
        view_height: float,
        screen_size: Vector,
    ) -> Vector:
        """Projects a 3D vertex onto the 2D screen."""
        # Transform world coordinates to camera coordinates
        world_dx: float = vertex.x - player_pos.x
        world_dz: float = (
            vertex.z - player_pos.y
        )  # player_pos.y is actually the Z coordinate in world space
        world_dy: float = vertex.y - view_height  # Height difference from camera

        # Create camera coordinate system
        forward_x: float = player_dir.x
        forward_z: float = player_dir.y
        right_x: float = player_dir.y  # Perpendicular to forward
        right_z: float = -player_dir.x

        # Transform to camera space
        cam_x: float = world_dx * right_x + world_dz * right_z
        cam_z: float = world_dx * forward_x + world_dz * forward_z
        cam_y: float = world_dy  # Height difference

        # Prevent division by zero and reject points behind camera
        if cam_z <= 0.1:
            return Vector(-1, -1)  # Invalid point (behind camera)

        # Project to screen coordinates - scale based on screen size
        fov_scale: float = screen_size.y  # Use screen height
        screen_x: float = (
            cam_x / cam_z
        ) * fov_scale + screen_size.x / 2.0  # Center at screen width/2
        screen_y: float = (
            -cam_y / cam_z
        ) * fov_scale + screen_size.y / 2.0  # Center at screen height/2

        return Vector(screen_x, screen_y)

    def render(self, draw, game):
        """Called every frame to render the entity."""
        if self._render:
            self._render(self, draw, game)

    def render_3d_sprite(
        self,
        draw,
        player_pos: Vector,
        player_dir: Vector,
        view_height: float,
        screen_size: Vector,
    ):
        """Renders the 3D sprite."""
        if not self.has_3d_sprite:
            return

        transformed_triangles = self.sprite_3d.get_transformed_triangles(player_pos)

        for tri in transformed_triangles:
            # Only render triangles facing the camera
            if tri.is_facing_camera(player_pos):
                # Project 3D vertices to 2D screen coordinates
                screen_points = [Vector(0, 0) for _ in range(3)]
                all_visible = True

                for j in range(3):
                    screen_point = self.project_3d_to_2d(
                        tri.vertices[j],
                        player_pos,
                        player_dir,
                        view_height,
                        screen_size,
                    )

                    # Check if point is on screen
                    if (
                        screen_point.x < 0
                        or screen_point.x >= screen_size.x
                        or screen_point.y < 0
                        or screen_point.y >= screen_size.y
                    ):
                        all_visible = False
                        break

                    screen_points[j] = screen_point

                if all_visible:
                    # Fill the triangle
                    draw.fill_triangle(
                        screen_points[0],
                        screen_points[1],
                        screen_points[2],
                        self.sprite_3d.color,
                    )

    def set_3d_sprite_scale(self, scale: float):
        """Sets the scale of the 3D sprite."""
        self.sprite_scale = scale
        if self.sprite_3d:
            self.sprite_3d.scale = scale

    def set_3d_sprite_rotation(self, rotation: float):
        """Sets the rotation of the 3D sprite."""
        self.sprite_rotation = rotation
        if self.sprite_3d:
            self.sprite_3d.rotation = rotation

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

    def update_3d_sprite_position(self):
        """Updates the position of the 3D sprite to match the entity's position."""
        if self.sprite_3d:
            self.sprite_3d.pos = self.position
