def map_first():
    """Create and return the first map."""
    from free_roam.dynamic_map import DynamicMap, TILE_WALL, TILE_TELEPORT

    dynamic_map = DynamicMap("First", 64, 57)

    # OUTER BORDER - Full perimeter walls
    dynamic_map.add_horizontal_wall(0, 63, 0, TILE_WALL)  # Top border
    dynamic_map.add_horizontal_wall(0, 63, 56, TILE_WALL)  # Bottom border
    dynamic_map.add_vertical_wall(0, 0, 56, TILE_WALL)  # Left border
    dynamic_map.add_vertical_wall(63, 0, 56, TILE_WALL)  # Right border

    # TOP SECTION
    dynamic_map.add_horizontal_wall(1, 28, 1, TILE_WALL)  # Top section wall
    dynamic_map.add_horizontal_wall(40, 62, 1, TILE_WALL)  # Right side of top

    # UPPER LEFT ROOMS AND CORRIDORS
    # Main upper left room structure
    dynamic_map.add_room(6, 2, 25, 6, True)  # Upper left room
    dynamic_map.add_door(26, 4)  # Door to connect areas

    # Upper middle section
    dynamic_map.add_room(30, 2, 45, 8, True)  # Upper middle room
    dynamic_map.add_corridor(25, 4, 30, 4)  # Connect upper rooms

    # MIDDLE SECTION
    # Large central area
    dynamic_map.add_room(1, 10, 30, 25, True)

    # Add internal walls and structures in middle section
    dynamic_map.add_vertical_wall(15, 12, 18, TILE_WALL)  # Internal divider
    dynamic_map.add_horizontal_wall(8, 22, 15, TILE_WALL)  # Horizontal divider

    # RIGHT SIDE - Major wall structure
    dynamic_map.add_vertical_wall(45, 8, 30, TILE_WALL)  # Major right wall
    dynamic_map.add_vertical_wall(50, 10, 25, TILE_WALL)  # Secondary right wall

    # LOWER LEFT - Complex room system
    dynamic_map.add_room(1, 25, 15, 35, True)  # Lower left room
    dynamic_map.add_room(18, 25, 30, 35, True)  # Lower middle room
    dynamic_map.add_corridor(15, 30, 18, 30)  # Connect lower rooms

    # LOWER SECTION - Final room structures
    dynamic_map.add_room(5, 40, 25, 50, True)  # Lower main room
    dynamic_map.add_room(30, 40, 55, 50, True)  # Lower right room
    dynamic_map.add_corridor(25, 45, 30, 45)  # Connect lower sections

    # Add some doors in strategic locations
    dynamic_map.add_door(13, 20)  # Door in middle section
    dynamic_map.add_door(22, 30)  # Door in lower connection
    dynamic_map.add_door(40, 25)  # Door in right section

    # BOTTOM SECTION - Final area
    dynamic_map.add_horizontal_wall(10, 50, 52, TILE_WALL)  # Bottom section wall

    # Add teleport tiles for level transition (in the lower right room center)
    # Teleport in center of lower right room
    dynamic_map.set_tile(45, 45, TILE_TELEPORT)
    dynamic_map.set_tile(46, 45, TILE_TELEPORT)  # Extra teleport area
    dynamic_map.set_tile(45, 46, TILE_TELEPORT)  # Extra teleport area

    return dynamic_map


def map_second():
    """Create and return the second map."""
    from free_roam.dynamic_map import DynamicMap, TILE_WALL, TILE_TELEPORT

    dynamic_map = DynamicMap("Second", 64, 57)

    # Outer walls
    dynamic_map.add_horizontal_wall(0, 63, 0, TILE_WALL)
    dynamic_map.add_horizontal_wall(0, 63, 56, TILE_WALL)
    dynamic_map.add_vertical_wall(0, 0, 56, TILE_WALL)
    dynamic_map.add_vertical_wall(63, 0, 56, TILE_WALL)

    # Main starting area (upper left)
    dynamic_map.add_room(5, 5, 20, 15, True)
    dynamic_map.add_door(20, 10)  # Exit door

    # Central corridor system
    dynamic_map.add_corridor(20, 10, 35, 10)  # Horizontal main corridor
    dynamic_map.add_corridor(35, 10, 35, 25)  # Vertical connector

    # Upper right room
    dynamic_map.add_room(40, 5, 55, 18, True)
    dynamic_map.add_door(40, 12)  # Entry door

    # Central hub area
    dynamic_map.add_room(30, 20, 45, 35, True)
    dynamic_map.add_door(35, 20)  # North door
    dynamic_map.add_door(30, 27)  # West door
    dynamic_map.add_door(45, 27)  # East door

    # Lower left area
    dynamic_map.add_room(5, 25, 25, 40, True)
    dynamic_map.add_corridor(25, 30, 30, 30)  # Connect to central hub

    # Lower right area
    dynamic_map.add_room(50, 25, 60, 40, True)
    dynamic_map.add_corridor(45, 30, 50, 30)  # Connect to central hub

    # Final bottom area
    dynamic_map.add_room(20, 45, 40, 52, True)
    dynamic_map.add_corridor(32, 40, 32, 45)  # Connect to final area

    # Add some internal structures for complexity
    # Internal wall in starting room
    dynamic_map.add_vertical_wall(12, 8, 12, TILE_WALL)
    # Internal wall in central area
    dynamic_map.add_horizontal_wall(42, 48, 30, TILE_WALL)

    # Add teleport tiles for level transition (in the final bottom area)
    dynamic_map.set_tile(30, 48, TILE_TELEPORT)  # Teleport in final bottom room
    dynamic_map.set_tile(31, 48, TILE_TELEPORT)  # Extra teleport area
    dynamic_map.set_tile(30, 49, TILE_TELEPORT)  # Extra teleport area

    return dynamic_map


def map_tutorial(width: int = 10, height: int = 10):
    """Create and return the tutorial map."""
    from free_roam.dynamic_map import DynamicMap, TILE_TELEPORT, TILE_EMPTY

    dynamic_map = DynamicMap("Tutorial", width, height)

    # Create a simple room with walls
    dynamic_map.add_room(1, 1, width - 2, height - 2, True)

    # doorway/corridor exit in the right wall (teleport to next area)

    # Remove a section of the right wall to create an opening
    # Create opening in right wall
    dynamic_map.set_tile(width - 1, height // 2, TILE_EMPTY)
    dynamic_map.set_tile(width - 2, height // 2, TILE_EMPTY)  # Make corridor deeper

    # teleport tiles at the end of the corridor
    # Teleport trigger tile
    dynamic_map.set_tile(width - 3, height // 2, TILE_TELEPORT)
    # Extra teleport area (above)
    dynamic_map.set_tile(width - 3, height // 2 - 1, TILE_TELEPORT)
    # Extra teleport area (below)
    dynamic_map.set_tile(width - 3, height // 2 + 1, TILE_TELEPORT)

    return dynamic_map
