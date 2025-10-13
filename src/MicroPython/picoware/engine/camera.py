from micropython import const
from picoware.system.vector import Vector

# Camera perspective types for 3D rendering
CAMERA_FIRST_PERSON = const(0)  # Default - render from player's own position/view
CAMERA_THIRD_PERSON = const(1)  # Render from external camera position


class CameraParams:
    """Camera parameters for 3D rendering"""

    def __init__(
        self,
        position: Vector = Vector(0, 0),
        direction: Vector = Vector(1, 0),
        plane: Vector = Vector(0, 0.66),
        height: float = 1.6,
    ):
        self.position = position  # Camera position
        self.direction = direction  # Camera direction
        self.plane = plane  # Camera plane
        self.height = height  # Camera height
