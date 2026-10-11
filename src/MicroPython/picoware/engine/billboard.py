"""Directional billboard assets."""
import engine


class Billboard(engine.Billboard):
    """Store up to eight directions and eight animation poses.

    Billboard(directions=8, poses=1) takes positional counts.
    set_direction_pose(direction, pose, image) registers an RGB332 Image.
    Each slot owns a native snapshot and retains the Python image buffers.
    Pass None to clear a slot. Entity borrows and retains its Billboard.
    view_for_facing(angle, pose) selects the nearest direction in radians.
    Animate by setting Entity.billboard_pose; world height is set when attached.
    """
