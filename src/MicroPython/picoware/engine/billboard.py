"""Billboard - Managing billboard elements in the game engine."""

import engine

class Billboard(engine.Billboard):
    """Store directional and pose images for a billboard.

    Args:
        dirs (int): Number of directions, from 1 to 8. Defaults to 8.
        poses (int): Number of poses, from 1 to 8. Defaults to 1.

    Methods:
        - set_counts(dirs, poses): Set the number of directions and poses.
        - set_direction_pose(direction, pose, image): Set an image for a direction and pose.


    Images assigned with ``set_direction_pose`` must have RGB332 pixel data and
    dimensions from 1 to 1024 pixels. The billboard copies the image data, so
    the source ``Image`` can be released after assignment. Pass ``None`` to
    clear a direction and pose.
    """