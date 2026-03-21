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
    """
    Represents an entity in the game.
    """

    def __setattr__(self, name, value):
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
