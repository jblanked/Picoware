from math import pi

from micropython import const
from picoware.system.vector import Vector
from picoware.engine.sprite3d import Sprite3D

# tile types
TILE_EMPTY = const(0)
TILE_WALL = const(1)
TILE_DOOR = const(2)
TILE_TELEPORT = const(3)
TILE_ENEMY_SPAWN = const(4)
TILE_ITEM_SPAWN = const(5)

# defines
MAX_MAP_WIDTH = const(64)
MAX_MAP_HEIGHT = const(64)
MAX_RENDER_WALLS = const(100)


class DynamicMap:
    """Dynamic map structure for free roam game"""

    def __init__(
        self,
        name: str = "",
        width: int = 0,
        height: int = 0,
        add_border: bool = True,
    ) -> None:
        self._width: int = width
        self._height: int = height
        self._name: str = name
        self._tiles = [[TILE_EMPTY for _ in range(width)] for _ in range(height)]
        self._render_walls = []

        if add_border:
            self.add_border_walls()

    def __del__(self) -> None:
        """Clean up the map resources"""
        del self._tiles
        del self._render_walls

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

    def add_border_walls(self, height: float = 2.0, depth: float = 0.2) -> None:
        """Add border walls around the map"""
        # Top border
        self.add_horizontal_wall(0, self._width - 1, 0, height, depth, TILE_WALL)
        # Bottom border
        self.add_horizontal_wall(
            0, self._width - 1, self._height - 1, height, depth, TILE_WALL
        )
        # Left border
        self.add_vertical_wall(0, 0, self._height - 1, height, depth, TILE_WALL)
        # Right border
        self.add_vertical_wall(
            self._width - 1, 0, self._height - 1, height, depth, TILE_WALL
        )

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
        self,
        x1: int,
        x2: int,
        y: int,
        height: float = 5.0,
        depth: float = 0.2,
        tile_type: int = TILE_WALL,
    ) -> None:
        """Add a horizontal wall from (x1, y) to (x2, y)"""
        i = x1
        while i <= x2:
            self.set_tile(i, y, tile_type)
            i += 1
        # create Sprite3D wall for rendering
        if tile_type == TILE_WALL and len(self._render_walls) < MAX_RENDER_WALLS:
            length = x2 - x1 + 1
            wall_sprite = Sprite3D()
            wall_sprite.position = Vector(x1 + length * 0.5, y + 0.5)
            wall_sprite.rotation_y = 0.0
            wall_sprite.create_wall(0, 0.75, 0, length, height, depth)
            wall_sprite.active = True
            self._render_walls.append(wall_sprite)

    def add_room(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        height: float = 5.0,
        depth: float = 0.2,
        add_walls: bool = True,
    ) -> None:
        """Add a room"""

        # clear the room area
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                self.set_tile(x, y, TILE_EMPTY)

        # add walls around the room
        if add_walls:
            self.add_horizontal_wall(x1, x2, y1, height, depth, TILE_WALL)  # Top wall
            self.add_horizontal_wall(
                x1, x2, y2, height, depth, TILE_WALL
            )  # Bottom wall
            self.add_vertical_wall(x1, y1, y2, height, depth, TILE_WALL)  # Left wall
            self.add_vertical_wall(x2, y1, y2, height, depth, TILE_WALL)  # Right wall

    def add_vertical_wall(
        self,
        x: int,
        y1: int,
        y2: int,
        height: float = 5.0,
        depth: float = 0.2,
        tile_type: int = TILE_WALL,
    ) -> None:
        """Add a vertical wall from (x, y1) to (x, y2)"""
        i = y1
        while i <= y2:
            self.set_tile(x, i, tile_type)
            i += 1
        # create Sprite3D wall for rendering
        if tile_type == TILE_WALL and len(self._render_walls) < MAX_RENDER_WALLS:
            length = y2 - y1 + 1
            wall_sprite = Sprite3D()
            wall_sprite.position = Vector(x + 0.5, y1 + length * 0.5)
            wall_sprite.rotation_y = (float)(pi / 2.0)
            wall_sprite.create_wall(0, 0.75, 0, length, height, depth)
            wall_sprite.active = True
            self._render_walls.append(wall_sprite)

    def get_block_at(self, x: int, y: int) -> int:
        """Get the wall block at a specific position"""
        # make sure we're checking within bounds of our actual map
        if x >= self._width or y >= self._height:
            return 0x0  # out of bounds is always empty
        tile = self.get_tile(x, y)
        if tile in (TILE_WALL, TILE_DOOR):
            return 0xF
        return 0x0

    def get_mini_map(self) -> list[list[int]]:
        """Get a simplified 2D array representing the map for mini-map rendering"""
        output = [[0 for _ in range(MAX_MAP_WIDTH)] for _ in range(MAX_MAP_HEIGHT)]
        for y in range(MAX_MAP_HEIGHT):
            for x in range(MAX_MAP_WIDTH):
                if x < self._width and y < self._height:
                    output[y][x] = self._tiles[y][x]
                else:
                    output[y][x] = TILE_EMPTY  # out of bounds is empty
        return output

    def get_render_wall(self, index: int) -> Sprite3D:
        """Get a Sprite3D wall for rendering by index"""
        if 0 <= index < len(self._render_walls):
            return self._render_walls[index]
        return None

    def get_tile(self, x: int, y: int) -> int:
        """Get the tile type at a specific position"""
        if 0 <= x < self._width and 0 <= y < self._height:
            return self._tiles[y][x]
        return TILE_EMPTY

    def set_tile(self, x: int, y: int, tile_type: int) -> None:
        """Set the tile type at a specific position"""
        if 0 <= x < self._width and 0 <= y < self._height:
            self._tiles[y][x] = tile_type

    def release_render_walls(self) -> None:
        """Release all the Sprite3D wall resources"""
        # dont copy the list, just iterate and clear it
        _count = len(self._render_walls)
        for wall in self._render_walls:
            wall.active = False
            wall = None
        self._render_walls.clear()
        return _count

    def render_mini_map(
        self,
        draw,
        position: Vector,
        size: Vector,
        player_pos: Vector,
        player_dir: Vector,
        foreground_color: int,
        background_color: int,
    ) -> None:
        """Render a mini-map representation of the map using a provided Draw object"""
        if (
            not draw
            or size is None
            or position is None
            or player_pos is None
            or player_dir is None
        ):
            return  # invalid parameters

        # background
        draw._fill_rectangle(position.x, position.y, size.x, size.y, background_color)
        draw._rectangle(position.x, position.y, size.x, size.y, foreground_color)

        # scale factors: pixels per map tile
        scale_x: float = size.x / self._width
        scale_y: float = size.y / self._height

        for i in range(self._height):
            for j in range(self._width):
                tile = self._tiles[i][j]
                if tile == TILE_EMPTY:
                    continue

                pos_x = position.x + j * scale_x
                pos_y = position.y + i * scale_y
                size_x = scale_x + 0.5
                size_y = scale_y + 0.5
                size_x = max(size_x, 1)  # ensure at least 1 pixel
                size_y = max(size_y, 1)

                draw._fill_rectangle(pos_x, pos_y, size_x, size_y, foreground_color)

        # draw player dot + direction arrow
        if player_pos.x < 0 or player_pos.y < 0:
            return

        ppx: int = int(position.x + player_pos.x * scale_x)
        ppy: int = int(position.y + player_pos.y * scale_y)

        # 3x3 white square so the dot is visible over walls
        draw._fill_rectangle(ppx - 1, ppy - 1, 3, 3, background_color)

        # Direction arrow: line from centre out 4px in facing direction
        if player_dir.x != 0 or player_dir.y != 0:
            tip_x = int(ppx + player_dir.x * 4)
            tip_y = int(ppy + player_dir.y * 4)
            draw._line(ppx, ppy, tip_x, tip_y, foreground_color)

            # arrowhead: two lines from tip back to flanking points
            base_x = tip_x - int(player_dir.x * 2)
            base_y = tip_y - int(player_dir.y * 2)
            perp_x = int(player_dir.y * 2.0)
            perp_y = int(-player_dir.x * 2.0)
            draw._line(
                tip_x,
                tip_y,
                base_x + perp_x,
                base_y + perp_y,
                foreground_color,
            )
            draw._line(
                tip_x,
                tip_y,
                base_x - perp_x,
                base_y - perp_y,
                foreground_color,
            )

        # Centre dot on top
        draw._pixel(ppx, ppy, foreground_color)
