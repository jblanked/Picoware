"""Camera - 3D camera modes for the game engine."""

from micropython import const
from picoware.system.vector import Vector
import engine

# Camera perspective types for 3D rendering
CAMERA_FIRST_PERSON = const(0)  # Default - render from player's own position/view
CAMERA_THIRD_PERSON = const(1)  # Render from external camera position


class Camera(engine.Camera):
    """Store camera parameters for 3D rendering.

    Args:
        position (Vector): Camera position. Defaults to Vector(0, 0, 0).
        direction (Vector): View direction. Defaults to Vector(1, 0, 0).
        plane (Vector): Camera plane. Defaults to Vector(0, 0.66, 0).
        height (float): Camera height. Defaults to 1.0.
        distance (float): View distance. Defaults to 2.0.
        perspective (int): Camera perspective type. Defaults to CAMERA_FIRST_PERSON.

    Attributes:
        position (Vector): World-space camera position. Writable.
        direction (Vector): Camera view direction. Writable.
        plane (Vector): Camera plane used for projection. Writable.
        height (float): Camera height above the ground. Writable.
        distance (float): Distance to the projection plane. Writable.
        perspective (int): Camera perspective mode. Writable.
        CAMERA_FIRST_PERSON (int): First-person camera perspective.
        CAMERA_THIRD_PERSON (int): Third-person camera perspective.

    Methods:
        - set_position(position): Set the camera position.
        - set_direction(direction): Set the camera view direction.
        - set_plane(plane): Set the camera projection plane.
        - set_height(height): Set the camera height.
        - set_distance(distance): Set the camera projection distance.
        - set_perspective(perspective): Set the camera perspective mode.
        - __del__(): Release the native camera resources.
    """

    def __init__(
        self,
        position=Vector(0, 0, 0),
        direction=Vector(1, 0, 0),
        plane=Vector(0, 0.66, 0),
        height=1.0,
        distance=2.0,
        perspective=CAMERA_FIRST_PERSON,
    ):
        """Initialize the Camera.

        Override so users can pick the perspective.

        Args:
            position (Vector): Camera position. Defaults to Vector(0, 0, 0).
            direction (Vector): View direction. Defaults to Vector(1, 0, 0).
            plane (Vector): Camera plane. Defaults to Vector(0, 0.66, 0).
            height (float): Camera height. Defaults to 1.0.
            distance (float): View distance. Defaults to 2.0.
            perspective (int): Camera perspective type. Defaults to CAMERA_FIRST_PERSON.
        """
        super().__init__(
            position,  # position
            direction,  # direction
            plane,  # plane
            height,  # height
            distance,  # distance
            perspective,  # camera perspective type
        )

    def __setattr__(self, name, value):
        """Set a camera attribute, routing to the matching setter.

        Args:
            name (str): Attribute name to set.
            value (object): New value for the attribute.
        """
        if name == "position":
            self.set_position(value)
        elif name == "direction":
            self.set_direction(value)
        elif name == "plane":
            self.set_plane(value)
        elif name == "height":
            self.set_height(value)
        elif name == "distance":
            self.set_distance(value)
        elif name == "perspective":
            self.set_perspective(value)
        else:
            super().__setattr__(name, value)
