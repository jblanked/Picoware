"""Entity - Game entities with states and types."""

from micropython import const
import engine

# entity state
ENTITY_STATE_IDLE = const(0)
ENTITY_STATE_MOVING = const(1)
ENTITY_STATE_MOVING_TO_START = const(2)
ENTITY_STATE_MOVING_TO_END = const(3)
ENTITY_STATE_ATTACKING = const(4)
ENTITY_STATE_ATTACKED = const(5)
ENTITY_STATE_DEAD = const(6)

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


class Entity(engine.Entity):
    """Represent a game entity with sprites, callbacks, and gameplay state.

    Args:
        name (str): Entity name.
        type (int): Entity type constant.
        position (Vector): Initial entity position.
        size (Vector): Entity size used for rendering and collision checks.
        sprite_data (Image or None): Main 2D sprite. Defaults to None.
        sprite_left (Image or None): Sprite used when facing left. Defaults to None.
        sprite_right (Image or None): Sprite used when facing right. Defaults to None.
        start (callable or None): Callback invoked when the entity starts. Defaults to None.
        stop (callable or None): Callback invoked when the entity stops. Defaults to None.
        update (callable or None): Callback invoked during entity updates. Defaults to None.
        render (callable or None): Callback invoked during entity rendering. Defaults to None.
        collision (callable or None): Callback invoked after a collision. Defaults to None.
        is_8bit_sprite (bool): Whether the entity uses 8-bit graphics. Defaults to False.
        sprite_3d_type (int): Initial 3D sprite type. Defaults to SPRITE_3D_NONE.
        sprite_3d_color (int): Initial 3D sprite color. Defaults to 0x0000.

    Attributes:
        name (str): Entity name. Writable.
        type (int): Entity type constant. Writable.
        position (Vector): Current entity position. Writable.
        old_position (Vector): Previous entity position. Writable.
        size (Vector): Entity size. Writable.
        is_8bit (bool): Whether the entity uses 8-bit graphics. Writable.
        is_active (bool): Whether the entity participates in updates. Writable.
        is_visible (bool): Whether the entity is rendered. Writable.
        is_player (bool): Whether the entity is the player. Writable.
        direction (Vector): Entity facing direction. Writable.
        plane (Vector): Entity camera plane. Writable.
        state (int): Current gameplay state. Writable.
        start_position (Vector): Movement start position. Writable.
        end_position (Vector): Movement end position. Writable.
        move_timer (float): Movement duration. Writable.
        elapsed_move_timer (float): Elapsed movement time. Writable.
        radius (float): Collision radius. Writable.
        speed (float): Movement speed. Writable.
        attack_timer (float): Attack cooldown duration. Writable.
        elapsed_attack_timer (float): Time since the last attack. Writable.
        strength (float): Damage dealt by the entity. Writable.
        health (float): Current health. Writable.
        max_health (float): Maximum health. Writable.
        level (float): Entity level. Writable.
        xp (float): Experience points. Writable.
        health_regen (float): Health regeneration rate. Writable.
        elapsed_health_regen (float): Time since the last health regeneration. Writable.
        sprite_3d_type (int): 3D sprite type. Writable.
        sprite_rotation (float): 3D sprite rotation. Writable.
        sprite_scale (float): 3D sprite scale. Writable.
        sprite_3d (Sprite3D): Native 3D sprite reference. Writable.
        sprite (Image or None): Main 2D sprite. Writable.
        sprite_left (Image or None): Left-facing 2D sprite. Writable.
        sprite_right (Image or None): Right-facing 2D sprite. Writable.
        ENTITY_PLAYER (int): Player entity type.
        ENTITY_ENEMY (int): Enemy entity type.
        ENTITY_ICON (int): Icon entity type.
        ENTITY_NPC (int): Non-player character entity type.
        ENTITY_3D_SPRITE (int): 3D sprite entity type.
        ENTITY_IDLE (int): Idle entity state.
        ENTITY_MOVING (int): Moving entity state.
        ENTITY_MOVING_TO_START (int): Moving-to-start entity state.
        ENTITY_MOVING_TO_END (int): Moving-to-end entity state.
        ENTITY_ATTACKING (int): Attacking entity state.
        ENTITY_ATTACKED (int): Attacked entity state.
        ENTITY_DEAD (int): Dead entity state.
        SPRITE_3D_NONE (int): No 3D sprite.
        SPRITE_3D_HUMANOID (int): Humanoid 3D sprite.
        SPRITE_3D_TREE (int): Tree 3D sprite.
        SPRITE_3D_HOUSE (int): House 3D sprite.
        SPRITE_3D_PILLAR (int): Pillar 3D sprite.
        SPRITE_3D_CUSTOM (int): Custom 3D sprite.

    Methods:
        - has_3d_sprite(): Return whether the entity has a 3D sprite.
        - set_3d_sprite_rotation(rotation): Set the 3D sprite rotation.
        - set_3d_sprite_scale(scale): Set the 3D sprite scale.
        - update_3d_sprite_position(): Synchronize the 3D sprite position.
        - has_changed_position(): Return whether the position changed.
        - set_name(name): Set the entity name.
        - set_type(type): Set the entity type.
        - set_position(position): Set the entity position.
        - set_old_position(old_position): Set the previous entity position.
        - set_size(size): Set the entity size.
        - set_is_8bit(is_8bit): Set the 8-bit graphics flag.
        - set_is_active(is_active): Set the active flag.
        - set_is_visible(is_visible): Set the visible flag.
        - set_is_player(is_player): Set the player flag.
        - set_direction(direction): Set the facing direction.
        - set_plane(plane): Set the camera plane.
        - set_state(state): Set the gameplay state.
        - set_start_position(start_position): Set the movement start position.
        - set_end_position(end_position): Set the movement end position.
        - set_move_timer(move_timer): Set the movement duration.
        - set_elapsed_move_timer(elapsed_move_timer): Set the elapsed movement time.
        - set_radius(radius): Set the collision radius.
        - set_speed(speed): Set the movement speed.
        - set_attack_timer(attack_timer): Set the attack cooldown duration.
        - set_elapsed_attack_timer(elapsed_attack_timer): Set the elapsed attack time.
        - set_strength(strength): Set the entity strength.
        - set_health(health): Set the current health.
        - set_max_health(max_health): Set the maximum health.
        - set_level(level): Set the entity level.
        - set_xp(xp): Set the experience points.
        - set_health_regen(health_regen): Set the health regeneration rate.
        - set_elapsed_health_regen(elapsed_health_regen): Set the elapsed regeneration time.
        - set_sprite_rotation(sprite_rotation): Set the 3D sprite rotation.
        - set_sprite_scale(sprite_scale): Set the 3D sprite scale.
        - set_sprite3d_type(type): Set the 3D sprite type.
        - set_sprite3d(sprite3d): Set the native 3D sprite reference.
        - set_sprite(sprite): Set the main 2D sprite.
        - set_sprite_left(sprite_left): Set the left-facing 2D sprite.
        - set_sprite_right(sprite_right): Set the right-facing 2D sprite.
        - __del__(): Release the native entity resources.
    """

    def __setattr__(self, name, value):
        """Set an entity attribute, routing to the matching setter.

        Args:
            name (str): Attribute name to set.
            value (object): New value for the attribute.
        """
        if name == "name":
            self.set_name(value)
        elif name == "type":
            self.set_type(value)
        elif name == "position":
            self.set_position(value)
        elif name == "old_position":
            self.set_old_position(value)
        elif name == "size":
            self.set_size(value)
        elif name == "is_8bit":
            self.set_is_8bit(value)
        elif name == "is_active":
            self.set_is_active(value)
        elif name == "is_visible":
            self.set_is_visible(value)
        elif name == "is_player":
            self.set_is_player(value)
        elif name == "direction":
            self.set_direction(value)
        elif name == "plane":
            self.set_plane(value)
        elif name == "state":
            self.set_state(value)
        elif name == "start_position":
            self.set_start_position(value)
        elif name == "end_position":
            self.set_end_position(value)
        elif name == "move_timer":
            self.set_move_timer(value)
        elif name == "elapsed_move_timer":
            self.set_elapsed_move_timer(value)
        elif name == "radius":
            self.set_radius(value)
        elif name == "speed":
            self.set_speed(value)
        elif name == "attack_timer":
            self.set_attack_timer(value)
        elif name == "elapsed_attack_timer":
            self.set_elapsed_attack_timer(value)
        elif name == "strength":
            self.set_strength(value)
        elif name == "health":
            self.set_health(value)
        elif name == "max_health":
            self.set_max_health(value)
        elif name == "level":
            self.set_level(value)
        elif name == "xp":
            self.set_xp(value)
        elif name == "health_regen":
            self.set_health_regen(value)
        elif name == "elapsed_health_regen":
            self.set_elapsed_health_regen(value)
        elif name == "sprite_rotation":
            self.set_3d_sprite_rotation(value)
        elif name == "sprite_scale":
            self.set_3d_sprite_scale(value)
        elif name == "sprite_3d_type":
            self.set_sprite3d_type(value)
        elif name == "sprite_3d":
            self.set_sprite3d(value)
        elif name == "sprite":
            self.set_sprite(value)
        elif name == "sprite_left":
            self.set_sprite_left(value)
        elif name == "sprite_right":
            self.set_sprite_right(value)
        else:
            super().__setattr__(name, value)
