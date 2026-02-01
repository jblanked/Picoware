from micropython import const
from picoware.system.vector import Vector

# colors
COLOR_WHITE = const(0xFFFF)
COLOR_BLACK = const(0x0000)

# map dimensions and limits
MAX_MAP_WIDTH = const(64)
MAX_MAP_HEIGHT = const(64)
MAX_WALLS = const(100)

# tile types
TILE_EMPTY = const(0)
TILE_WALL = const(1)
TILE_DOOR = const(2)
TILE_TELEPORT = const(3)
TILE_ENEMY_SPAWN = const(4)
TILE_ITEM_SPAWN = const(5)


class Wall:
    """Wall structure for dynamic walls"""

    def __init__(
        self,
        start: Vector = Vector(0, 0),
        end: Vector = Vector(0, 0),
        tile_type: int = TILE_EMPTY,
        height: int = 0,
        is_solid: bool = False,
    ):
        self.start: Vector = start
        self.end: Vector = end
        self.tile_type: int = tile_type
        self.height: int = height
        self.is_solid: bool = is_solid

    def __del__(self):
        if self.start:
            del self.start
            self.start = None
        if self.end:
            del self.end
            self.end = None


class DynamicMap:
    """Dynamic map structure for free roam game"""

    def __init__(
        self,
        name: str = "",
        width: int = 0,
        height: int = 0,
        add_border: bool = True,
        fill_in: bool = False,
    ) -> None:
        from picoware_game import init_tile_buffer

        self._width: int = width
        self._height: int = height
        self._name: str = name
        self._fill_in: bool = fill_in

        init_tile_buffer(TILE_EMPTY)

        if add_border:
            self.add_border_walls()

    @property
    def width(self) -> int:
        """Get the map width"""
        return self._width

    @property
    def height(self) -> int:
        """Get the map height"""
        return self._height

    @property
    def name(self) -> str:
        """Get the map name"""
        return self._name

    @property
    def fill_in(self) -> bool:
        """Get the fill in status"""
        return self._fill_in

    @fill_in.setter
    def fill_in(self, value: bool) -> None:
        """Set the fill in status"""
        self._fill_in = value

    def add_border_walls(self) -> None:
        """Add border walls around the map"""
        # Top border
        self.add_horizontal_wall(0, self._width - 1, 0, TILE_WALL)
        # Bottom border
        self.add_horizontal_wall(0, self._width - 1, self._height - 1, TILE_WALL)
        # Left border
        self.add_vertical_wall(0, 0, self._height - 1, TILE_WALL)
        # Right border
        self.add_vertical_wall(self._width - 1, 0, self._height - 1, TILE_WALL)

    def add_corridor(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """Add simple L-shaped corridor"""
        if x1 == x2:
            # Vertical corridor
            start_y = min(y1, y2)
            end_y = max(y1, y2)
            for y in range(start_y, end_y + 1):
                self.set_tile(x1, y, TILE_EMPTY)
        elif y1 == y2:
            # Horizontal corridor
            start_x = min(x1, x2)
            end_x = max(x1, x2)
            for x in range(start_x, end_x + 1):
                self.set_tile(x, y1, TILE_EMPTY)
        else:
            # L-shaped corridor (horizontal then vertical)
            start_x = min(x1, x2)
            end_x = max(x1, x2)
            for x in range(start_x, end_x + 1):
                self.set_tile(x, y1, TILE_EMPTY)

            start_y = min(y1, y2)
            end_y = max(y1, y2)
            for y in range(start_y, end_y + 1):
                self.set_tile(x2, y, TILE_EMPTY)

    def add_door(self, x: int, y: int) -> None:
        """Add a door at a specific position"""
        if 0 <= x < self._width and 0 <= y < self._height:
            self.set_tile(x, y, TILE_DOOR)

    def add_horizontal_wall(
        self, x1: int, x2: int, y: int, tile_type: int = TILE_WALL
    ) -> None:
        """Add a horizontal wall from (x1, y) to (x2, y)"""
        i = x1
        while i <= x2:
            self.set_tile(i, y, tile_type)
            i += 1

    def add_room(
        self, x1: int, y1: int, x2: int, y2: int, add_walls: bool = True
    ) -> None:
        """Add a room"""

        # clear the room area
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                self.set_tile(x, y, TILE_EMPTY)

        # add walls around the room
        if add_walls:
            self.add_horizontal_wall(x1, x2, y1, TILE_WALL)  # Top wall
            self.add_horizontal_wall(x1, x2, y2, TILE_WALL)  # Bottom wall
            self.add_vertical_wall(x1, y1, y2, TILE_WALL)  # Left wall
            self.add_vertical_wall(x2, y1, y2, TILE_WALL)  # Right wall

    def add_vertical_wall(
        self, x: int, y1: int, y2: int, tile_type: int = TILE_WALL
    ) -> None:
        """Add a vertical wall from (x, y1) to (x, y2)"""
        i = y1
        while i <= y2:
            self.set_tile(x, i, tile_type)
            i += 1

    def get_block_at(self, x: int, y: int) -> int:
        """Get the wall block at a specific position"""
        # make sure we're checking within bounds of our actual map
        if x >= self._width or y >= self._height:
            return 0x0  # out of bounds is always empty
        tile = self.get_tile(x, y)
        if tile in (TILE_WALL, TILE_DOOR):
            return 0xF
        return 0x0

    def get_tile(self, x: int, y: int) -> int:
        """Get the tile type at a specific position"""
        from picoware_game import get_tile

        if 0 <= x < self._width and 0 <= y < self._height:
            return get_tile(x, y)
        return TILE_EMPTY

    def set_tile(self, x: int, y: int, tile_type: int) -> None:
        """Set the tile type at a specific position"""
        from picoware_game import set_tile

        if 0 <= x < self._width and 0 <= y < self._height:
            set_tile(x, y, tile_type)

    def render(
        self,
        view_height: float,
        player_pos: Vector,
        player_dir: Vector,
        player_plane: Vector,
        size: Vector = Vector(128, 64),
    ) -> None:
        """Render the dynamic map using raycasting"""
        from picoware_game import render_map

        render_map(
            self._width,
            self._height,
            player_pos.x,
            player_pos.y,
            player_dir.x,
            player_dir.y,
            player_plane.x,
            player_plane.y,
            view_height,
            int(size.x),
            int(size.y),
            self._fill_in,
            COLOR_BLACK,
        )
