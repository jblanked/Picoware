from micropython import const
from picoware.system.vector import Vector
import engine

# Camera perspective types for 3D rendering
CAMERA_FIRST_PERSON = const(0)  # Default - render from player's own position/view
CAMERA_THIRD_PERSON = const(1)  # Render from external camera position


class Camera(engine.Camera):
    """Camera parameters for 3D rendering"""

    def __init__(
        self,
        position=Vector(0, 0, 0),
        direction=Vector(1, 0, 0),
        plane=Vector(0, 0.66, 0),
        height=1.0,
        distance=2.0,
        perspective=CAMERA_FIRST_PERSON,
    ):
        """Initialize the Camera (override so users can pick perspective)"""
        super().__init__(
            position,  # position
            direction,  # direction
            plane,  # plane
            height,  # height
            distance,  # distance
            perspective,  # camera perspective type
        )
