from micropython import const

WALL_HEIGHT = const(2.0)
WALL_DEPTH = const(0.2)


def map_first():
    """Create and return the first map."""
    from free_roam.dynamic_map import DynamicMap, TILE_TELEPORT

    # Town: huge open area with 4 houses placed as 3D sprites
    dynamic_map = DynamicMap("First", 64, 57, False)

    # Outer border
    dynamic_map.add_horizontal_wall(0, 63, 0, WALL_HEIGHT, WALL_DEPTH)  # Top
    dynamic_map.add_horizontal_wall(0, 63, 56, WALL_HEIGHT, WALL_DEPTH)  # Bottom
    dynamic_map.add_vertical_wall(0, 0, 56, WALL_HEIGHT, WALL_DEPTH)  # Left
    dynamic_map.add_vertical_wall(63, 0, 56, WALL_HEIGHT, WALL_DEPTH)  # Right

    # Teleport zone in the center
    dynamic_map.set_tile(31, 28, TILE_TELEPORT)
    dynamic_map.set_tile(32, 28, TILE_TELEPORT)
    dynamic_map.set_tile(31, 29, TILE_TELEPORT)

    return dynamic_map


def map_second():
    """Create and return the second map."""
    from free_roam.dynamic_map import DynamicMap, TILE_TELEPORT

    # Forest: huge open area with trees placed as 3D sprites
    dynamic_map = DynamicMap("Second", 64, 57, False)

    # Outer walls
    dynamic_map.add_horizontal_wall(0, 63, 0, WALL_HEIGHT, WALL_DEPTH)  # Top
    dynamic_map.add_horizontal_wall(0, 63, 56, WALL_HEIGHT, WALL_DEPTH)  # Bottom
    dynamic_map.add_vertical_wall(0, 0, 56, WALL_HEIGHT, WALL_DEPTH)  # Left
    dynamic_map.add_vertical_wall(63, 0, 56, WALL_HEIGHT, WALL_DEPTH)  # Right

    # Teleport zone in the center
    dynamic_map.set_tile(31, 28, TILE_TELEPORT)
    dynamic_map.set_tile(32, 28, TILE_TELEPORT)
    dynamic_map.set_tile(31, 29, TILE_TELEPORT)

    return dynamic_map


def map_tutorial(width: int = 20, height: int = 20):
    """Create and return the tutorial map."""
    from free_roam.dynamic_map import DynamicMap, TILE_TELEPORT

    dynamic_map = DynamicMap("Tutorial", width, height, False)

    # Room built from explicit walls:
    #   3 long walls: top, bottom, left
    #   2 short walls on the right side with a gap in the middle for the door
    mid = height // 2
    gap = 2  # half-width of the door opening
    dynamic_map.add_horizontal_wall(
        0, width - 1, 0, WALL_HEIGHT, WALL_DEPTH
    )  # Top wall
    dynamic_map.add_horizontal_wall(
        0, width - 1, height - 1, WALL_HEIGHT, WALL_DEPTH
    )  # Bottom wall
    dynamic_map.add_vertical_wall(
        0, 0, height - 1, WALL_HEIGHT, WALL_DEPTH
    )  # Left wall
    dynamic_map.add_vertical_wall(
        width - 1, 0, mid - gap - 1, WALL_HEIGHT, WALL_DEPTH
    )  # Right wall (above door)
    dynamic_map.add_vertical_wall(
        width - 1, mid + gap + 1, height - 1, WALL_HEIGHT, WALL_DEPTH
    )  # Right wall (below door)

    # Teleport tiles at the door opening (right edge, gap rows)
    for dy in range(gap * 2 + 1):
        dynamic_map.set_tile(width - 1, mid - gap + dy, TILE_TELEPORT)

    return dynamic_map
