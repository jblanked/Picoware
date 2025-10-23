from micropython import const
from picoware.system.vector import Vector
from picoware.engine.entity import (
    Entity,
    ENTITY_TYPE_3D_SPRITE,
    ENTITY_STATE_MOVING_TO_START,
    ENTITY_STATE_MOVING_TO_END,
    ENTITY_TYPE_PLAYER,
)

DISTANCE_THRESHOLD = const(0.2)  # Minimum distance to consider "reached"
MOVE_SPEED = const(0.1)  # Even faster movement speed


class Sprite(Entity):
    """3D Sprite entity that can move between two points."""

    def __init__(
        self,
        name: str,
        position: Vector,
        sprite_type: int,
        height: float = 2.0,  # not used in C++ version
        width: float = 1.0,  # not used in C++ version
        rotation: float = 0.0,
        end_position: Vector = Vector(-1, -1),
    ):
        super().__init__(
            name,
            ENTITY_TYPE_3D_SPRITE,
            position,
            Vector(10, 10),
            None,
            sprite_3d_type=sprite_type,
        )
        self.set_3d_sprite_rotation(rotation)
        self.start_position = position
        self.end_position = position if end_position == Vector(-1, -1) else end_position
        self.state = ENTITY_STATE_MOVING_TO_END

    def collision(self, other, game):
        if other.type != ENTITY_TYPE_PLAYER:
            return
        # I'll come back to this...
        # FURI_LOG_I("Sprite", "Collision with player detected: %s", other->name);
        # this->position_set(this->old_position);

    def update(self, game):
        # Only move if start and end positions are different
        if (
            self.start_position.x == self.end_position.x
            and self.start_position.y == self.end_position.y
        ):
            return  # No movement needed

        # move move towards the end position if the state is MOVING_TO_END
        if self.state == ENTITY_STATE_MOVING_TO_END:
            dx = self.end_position.x - self.position.x
            dy = self.end_position.y - self.position.y
            distance = (dx**2 + dy**2) ** 0.5

            if distance > DISTANCE_THRESHOLD:
                # Normalize direction and apply speed
                move_x = (dx / distance) * MOVE_SPEED
                move_y = (dy / distance) * MOVE_SPEED

                # Don't overshoot the target
                if distance < MOVE_SPEED:
                    move_x = dx
                    move_y = dy

                self.position = Vector(
                    self.position.x + move_x, self.position.y + move_y
                )
            else:
                # Snap to exact position when close enough
                self.position = self.end_position
                self.state = ENTITY_STATE_MOVING_TO_START
        elif self.state == ENTITY_STATE_MOVING_TO_START:
            dx = self.start_position.x - self.position.x
            dy = self.start_position.y - self.position.y
            distance = (dx**2 + dy**2) ** 0.5

            if distance > DISTANCE_THRESHOLD:
                # Normalize direction and apply speed
                move_x = (dx / distance) * MOVE_SPEED
                move_y = (dy / distance) * MOVE_SPEED

                # Don't overshoot the target
                if distance < MOVE_SPEED:
                    move_x = dx
                    move_y = dy

                self.position = Vector(
                    self.position.x + move_x, self.position.y + move_y
                )

            else:
                # Snap to exact position when close enough
                self.position = self.start_position
                self.state = ENTITY_STATE_MOVING_TO_END
