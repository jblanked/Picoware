from micropython import const
from engine import Camera

# Camera perspective types for 3D rendering
CAMERA_FIRST_PERSON = const(0)  # Default - render from player's own position/view
CAMERA_THIRD_PERSON = const(1)  # Render from external camera position


class CameraParams(Camera):
    """Camera parameters for 3D rendering"""
