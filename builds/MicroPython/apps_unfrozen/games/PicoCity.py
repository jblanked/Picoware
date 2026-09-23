"""Picoware open-world city game."""

from math import atan2, cos, pi, sin
from picoware.system.vector import Vector
from picoware.engine.entity import Entity

_city = None
_seed = 0x5A3C1D7


def _next_random(limit):
    """Return a pseudo-random integer below limit."""
    global _seed

    _seed = (_seed * 1103515245 + 12345) & 0x7FFFFFFF
    return _seed % limit

def _cell_hash(col, row, salt):
    """Return a stable hash for a block cell and salt."""
    value = (col * 73856093) ^ (row * 19349663) ^ (salt * 83492791)
    return value & 0x7FFFFFFF

def _player_update(entity, game):
    """Forward the player callback to the active city."""
    if _city is not None:
        _city.update_player(entity, game)


def _person_update(entity, _game):
    """Forward a pedestrian callback to the active city."""
    if _city is not None:
        _city.update_person(entity)


def _traffic_update(entity, _game):
    """Forward a traffic car callback to the active city."""
    if _city is not None:
        _city.update_traffic(entity)


def _player_render(_entity, draw, _game):
    """Draw the HUD from the player render pass."""
    if _city is not None:
        _city.draw_hud(draw)


def _background_render(_entity, draw, _game):
    """Draw the sky and distant city horizon."""
    if _city is not None:
        _city.draw_background(draw)


class _City:
    """Own the city scene and open-world state."""

    WORLD_SIZE = 840.0
    WORLD_HALF = 420.0
    GRID_LIMIT = 5
    ROAD_SPACING = 84.0
    ROAD_WIDTH = 5.5
    ROAD_HEIGHT = 0.06
    ROAD_SEGMENT = 4.2
    SIDEWALK_WIDTH = 1.2
    SIDEWALK_OFFSET = 3.35
    SIDEWALK_HEIGHT = 0.03
    SIDEWALK_SEGMENT = 6.0
    MARK_SPACING = 14.0
    MARK_OFFSET = 7.0
    MARK_WIDTH = 0.12
    MARK_LENGTH = 2.6
    MARK_HEIGHT = 0.10
    BLOCK_CENTER = 42.0
    BLOCK_REACH = 40.0
    BUILDING_REACH = 8.0
    SCENE_ANCHOR_Z = -1000.0
    BACKGROUND_Z = 2000.0
    FIELD_OF_VIEW = 40.0
    CHUNK_LAG = 4.0
    MINIMAP_SIZE = 60.0
    MINIMAP_RANGE = 44.0
    WALK_SPEED = 0.35
    WALK_TURN = 0.25
    CAR_ACCEL = 0.05
    CAR_BRAKE = 0.085
    CAR_FRICTION = 0.012
    CAR_STEER = 0.15
    CAR_MAX_SPEED = 1.0
    CAR_MAX_REVERSE = -0.35
    CAR_RADIUS = 0.72
    TRAFFIC_OFFSET = 1.2
    PERSON_COUNT = 6
    RECYCLE_DISTANCE = 56.0
    TRAFFIC_COUNT = 8
    TRAFFIC_SPEED = 0.45
    TRAFFIC_TURN = 0.6
    TRAFFIC_DECISION = 30
    TRAVEL_SPEED = 0.45
    CAR_COLORS = (0xF800, 0xFD20, 0x001F, 0x07FF, 0xF81F, 0x001F)

    COLOR_BLACK = 0x0000
    COLOR_SKY = 0x5D9F
    COLOR_HORIZON = 0x8C71
    COLOR_GROUND = 0xBDF7
    COLOR_SIDEWALK = 0xD69A
    COLOR_ROAD = 0x39C7
    COLOR_LINE = 0xFFE0
    COLOR_WINDOW = 0x2A8A
    COLOR_ROOF = 0x632C
    COLOR_DOOR = 0x1080
    COLOR_PLAYER = 0x07FF
    COLOR_SKIN = 0xFD20
    COLOR_GLASS = 0x5D9B
    COLOR_TRUNK = 0x6B4D
    COLOR_LEAF = 0x07E0
    BUILDING_COLORS = (
        (0xB5B6, 0x7BEF),
        (0xD69A, 0xFBE0),
        (0x6B4D, 0xC618),
        (0xA145, 0xFD20),
        (0x9CB2, 0x5D9B),
        (0xFBE0, 0xFD20),
        (0xC618, 0x9CB2),
        (0xA145, 0xFFE0),
    )
    PERSON_COLORS = (0x001F, 0xF800, 0x07E0, 0xFD20, 0xF81F, 0x001F)
    GARAGE_DOOR_WIDTH = 2.4
    GARAGE_DOOR_HEIGHT = 2.0
    FLOOR_COLOR = 0x9C8A
    CEILING_COLOR = 0x734E

    BLOCK_SLOTS = (
        (-30.0, -20.0),
        (-30.0, 20.0),
        (30.0, -20.0),
        (30.0, 20.0),
        (-20.0, -30.0),
        (20.0, -30.0),
        (-20.0, 30.0),
        (20.0, 30.0),
    )

    def __init__(self, view_manager):
        from picoware.engine.camera import CAMERA_THIRD_PERSON, Camera
        from picoware.engine.engine import GameEngine
        from picoware.engine.game import Game
        from picoware.engine.level import Level

        self.view_manager = view_manager
        self.draw = view_manager.draw
        self.level = None
        self.engine = None
        self.meshes = []
        self.city_mesh = None
        self.buildings = []
        self.people = []
        self.people_dir_x = []
        self.people_dir_z = []
        self.people_walk = []
        self.people_speeds = []
        self.traffic = []
        self.traffic_speed = []
        self.traffic_axis = []
        self.traffic_line = []
        self.traffic_dir = []
        self.player = None
        self.in_car = False
        self.speed = 0.0
        self.heading = pi * 0.5
        self.message = ""
        self.message_timer = 0

        game = Game(
            "Pico City",
            self.draw.size,
            self.draw,
            view_manager.input_manager,
            self.COLOR_LINE,
            self.COLOR_SKY,
            Camera(
                direction=Vector(0, 1),
                plane=Vector(-0.72, 0),
                height=2.2,
                distance=6.2,
                perspective=CAMERA_THIRD_PERSON,
            ),
        )
        self.level = Level("Downtown", self.draw.size, game)
        self.level.set_light_direction(-0.35, 1.0, -0.5)
        self.level.set_shadow_color(0)
        self._build_background()
        self._build_city()
        self._build_player()
        self._build_traffic()
        self._build_people()
        self.anchor_x = self.player.position.x
        self.anchor_z = self.player.position.y
        self._fill_city(self.anchor_x, self.anchor_z)
        game.level_add(self.level)
        self.engine = GameEngine(game, 30)

    def _mesh_entity(
        self, name, position, size, mesh, update=None, render=None, collision=None
    ):
        from picoware.engine.entity import ENTITY_TYPE_3D_SPRITE, SPRITE_3D_CUSTOM

        entity = Entity(
            name,
            ENTITY_TYPE_3D_SPRITE,
            position,
            size,
            None,
            None,
            None,
            None,
            None,
            update,
            render,
            collision,
            False,
            SPRITE_3D_CUSTOM,
            self.COLOR_BLACK,
        )
        mesh.set_wireframe(False)
        entity.sprite_3d = mesh
        entity.sprite_3d_type = SPRITE_3D_CUSTOM
        entity.is_visible = True
        self.meshes.append(mesh)
        self.level.entity_add(entity)
        return entity

    def _triangle(self, mesh, first, second, third, color):
        mesh.add_triangle(
            first[0],
            first[1],
            first[2],
            second[0],
            second[1],
            second[2],
            third[0],
            third[1],
            third[2],
            color,
            False,
        )

    def _quad(self, mesh, first, second, third, fourth, color):
        self._triangle(mesh, first, second, third, color)
        self._triangle(mesh, first, fourth, second, color)

    def _ground_rect(self, mesh, x, z, width, depth, height, color, segment_size):
        """Add a flat rectangle split into near plane safe strips."""
        z -= self.SCENE_ANCHOR_Z
        if width >= depth:
            width_steps = max(1, int((width + segment_size - 0.001) / segment_size))
            depth_steps = 1
        else:
            width_steps = 1
            depth_steps = max(1, int((depth + segment_size - 0.001) / segment_size))

        cell_width = width / width_steps
        cell_depth = depth / depth_steps
        start_x = x - width * 0.5
        start_z = z - depth * 0.5
        for width_index in range(width_steps):
            cell_x = start_x + cell_width * (width_index + 0.5)
            for depth_index in range(depth_steps):
                cell_z = start_z + cell_depth * (depth_index + 0.5)
                half_width = cell_width * 0.5
                half_depth = cell_depth * 0.5
                self._quad(
                    mesh,
                    (cell_x - half_width, height, cell_z - half_depth),
                    (cell_x + half_width, height, cell_z + half_depth),
                    (cell_x + half_width, height, cell_z - half_depth),
                    (cell_x - half_width, height, cell_z + half_depth),
                    color,
                )

    def _add_building(self, mesh, x, z, width, depth, height, wall_color, roof_color, building_type):
        """Add one building and register its collision rectangle."""
        scene_z = z - self.SCENE_ANCHOR_Z
        is_house = building_type == 1
        is_tower = building_type == 2
        if is_house:
            self._build_house(mesh, x, z, width, depth, height, wall_color, roof_color)
        else:
            mesh.create_cube(x, height * 0.5, scene_z, width, height, depth, wall_color)
            mesh.create_cube(
                x,
                height + 0.10,
                scene_z,
                width + 0.12,
                0.20,
                depth + 0.12,
                roof_color,
            )
            window_height = min(0.14, height * 0.07)
            window_y = min(height - 0.35, 1.2)
            front = scene_z + depth * 0.5 + 0.02
            half_width = width * 0.275
            self._window(mesh, x, window_y, front, half_width, window_height)
            if height > 4.5:
                self._window(mesh, x, height * 0.58, front, half_width, window_height)
            if is_tower:
                mesh.create_cube(x, height + 0.5, scene_z, 0.10, 1.0, 0.10, self.COLOR_ROOF)
        self.buildings.append((x, z, width * 0.5, depth * 0.5, is_house))

    def _window(self, mesh, x, y, z, half_width, half_height):
        """Add a flat window quad facing south, double sided."""
        xl = x - half_width
        xr = x + half_width
        yb = y - half_height
        yt = y + half_height
        self._triangle(mesh, (xl, yb, z), (xr, yb, z), (xr, yt, z), self.COLOR_WINDOW)
        self._triangle(mesh, (xl, yb, z), (xr, yt, z), (xl, yt, z), self.COLOR_WINDOW)
        self._triangle(mesh, (xr, yb, z), (xl, yb, z), (xl, yt, z), self.COLOR_WINDOW)
        self._triangle(mesh, (xr, yb, z), (xl, yt, z), (xr, yt, z), self.COLOR_WINDOW)

    def _car_to_mesh(self, mesh, cx, cz, color):
        """Add a small car's three cubes to a mesh at (cx, cz)."""
        mesh.create_cube(cx, 0.36, cz, 1.05, 0.34, 1.85, color)
        mesh.create_cube(cx, 0.62, cz + 0.10, 0.68, 0.24, 0.72, self.COLOR_GLASS)
        mesh.create_cube(cx, 0.20, cz - 0.78, 0.85, 0.10, 0.12, self.COLOR_LINE)

    def _car_mesh(self, color):
        """Build the shared car geometry for one color."""
        from picoware.engine.sprite3d import Sprite3D

        mesh = Sprite3D()
        self._car_to_mesh(mesh, 0, 0, color)
        mesh.set_wireframe(False)
        return mesh

    def _add_tree(self, mesh, x, z):
        """Add a tree trunk and canopy to the city mesh."""
        scene_z = z - self.SCENE_ANCHOR_Z
        mesh.create_cube(x, 0.50, scene_z, 0.24, 1.00, 0.24, self.COLOR_TRUNK)
        mesh.create_cube(x, 1.15, scene_z, 0.85, 0.60, 0.85, self.COLOR_LEAF)
        mesh.create_cube(x, 1.55, scene_z, 0.55, 0.35, 0.55, self.COLOR_LEAF)

    def _squad(self, mesh, first, second, third, fourth, color, both_sides=False):
        """Add a quad. Optional both_sides draws two facing windings."""
        self._quad(mesh, first, second, third, fourth, color)
        if both_sides:
            self._triangle(mesh, first, third, second, color)
            self._triangle(mesh, first, second, fourth, color)

    def _build_garage(self, mesh, x, z, width, depth, height, wall_color):
        """Add a hollow garage inside a house: floor, ceiling, double-sided walls, doorway."""
        scene_z = z - self.SCENE_ANCHOR_Z
        hw = width * 0.5
        hd = depth * 0.5
        floor_y = 0.05
        ceil_y = height - 0.15
        z0 = scene_z - hd + 0.1
        z1 = scene_z + hd - 0.1
        door_half = self.GARAGE_DOOR_WIDTH * 0.5
        # Floor (both sides so it reads from inside and out).
        self._squad(mesh, (x - hw, floor_y, z0), (x + hw, floor_y, z1), (x + hw, floor_y, z0), (x - hw, floor_y, z1), self.FLOOR_COLOR, True)
        # Ceiling, both sides.
        self._squad(mesh, (x - hw, ceil_y, z0), (x + hw, ceil_y, z1), (x + hw, ceil_y, z0), (x - hw, ceil_y, z1), self.CEILING_COLOR, True)
        # Back wall (north side), both sides.
        self._squad(mesh, (x - hw, floor_y, z0), (x + hw, ceil_y, z0), (x + hw, floor_y, z0), (x - hw, ceil_y, z0), wall_color, True)
        # Front wall (south side) with a doorway: two slabs flanking the opening.
        if door_half < hw:
            self._squad(
                mesh,
                (x - hw, floor_y, z1),
                (x - door_half, ceil_y, z1),
                (x - door_half, floor_y, z1),
                (x - hw, ceil_y, z1),
                wall_color,
                True,
            )
            self._squad(
                mesh,
                (x + door_half, floor_y, z1),
                (x + hw, ceil_y, z1),
                (x + hw, floor_y, z1),
                (x + door_half, ceil_y, z1),
                wall_color,
                True,
            )
        # Left wall (west side), both sides.
        self._squad(
            mesh,
            (x - hw, floor_y, z0),
            (x - hw, ceil_y, z1),
            (x - hw, floor_y, z1),
            (x - hw, ceil_y, z0),
            wall_color,
            True,
        )
        # Right wall (east side), both sides.
        self._squad(
            mesh,
            (x + hw, floor_y, z0),
            (x + hw, ceil_y, z1),
            (x + hw, floor_y, z1),
            (x + hw, ceil_y, z0),
            wall_color,
            True,
        )
        # Parked car inside the garage (static triangles on the city mesh).
        self._car_to_mesh(mesh, x + hw * 0.45, z, self.COLOR_PLAYER)

    def _build_house(self, mesh, x, z, width, depth, height, wall_color, roof_color):
        """Add a hollow house (garage) with an open front doorway and double-sided walls."""
        scene_z = z - self.SCENE_ANCHOR_Z
        hw = width * 0.5
        hd = depth * 0.5
        # Roof slab.
        mesh.create_cube(x, height - 0.05, scene_z, width + 0.10, 0.10, depth + 0.10, roof_color)
        # Hollow interior with open front doorway.
        self._build_garage(mesh, x, z, width, depth, height, wall_color)

    def _build_player(self):
        """Create the player pedestrian entity."""
        from picoware.engine.entity import ENTITY_TYPE_3D_SPRITE, SPRITE_3D_HUMANOID

        self.player = Entity(
            "Player",
            ENTITY_TYPE_3D_SPRITE,
            Vector(self.SIDEWALK_OFFSET, -10.0),
            Vector(0.6, 1.5),
            None,
            None,
            None,
            None,
            None,
            _player_update,
            _player_render,
            None,
            False,
            SPRITE_3D_HUMANOID,
            self.COLOR_SKIN,
        )
        self.player.is_player = True
        self.player.is_visible = True
        self.level.entity_add(self.player)
        self.player_car = self._mesh_entity(
            "PlayerCar",
            Vector(self.SIDEWALK_OFFSET, -10.0),
            Vector(1.05, 1.85),
            self._car_mesh(0x07FF),
        )
        self.player_car.is_visible = False

    def _build_traffic(self):
        """Create the AI traffic cars."""
        for index in range(self.TRAFFIC_COUNT):
            color = self.CAR_COLORS[index % len(self.CAR_COLORS)]
            car = self._mesh_entity(
                "Traffic %d" % (index + 1),
                Vector(0, 0),
                Vector(1.05, 1.85),
                self._car_mesh(color),
                _traffic_update,
            )
            self.traffic.append(car)
            self.traffic_axis.append(0)
            self.traffic_line.append(0)
            self.traffic_dir.append(1)
            self.traffic_speed.append(0.0)
            self._spawn_traffic(index)

    def _spawn_traffic(self, index):
        """Place a traffic car on a free street lane near the player."""
        position = self.player.position
        for _attempt in range(10):
            axis = _next_random(2)
            line = _next_random(2 * self.GRID_LIMIT + 1) - self.GRID_LIMIT
            direction = 1 if _next_random(2) == 0 else -1
            lane = -self.TRAFFIC_OFFSET if direction == 1 else self.TRAFFIC_OFFSET
            if axis == 0:
                x = line * self.ROAD_SPACING + lane
                z = position.y + _next_random(41) - 20
            else:
                x = position.x + _next_random(41) - 20
                z = line * self.ROAD_SPACING + lane
            if not self._car_blocked(x, z, index):
                break
        edge = self.WORLD_HALF - 4.0
        if x < -edge:
            x = -edge
        elif x > edge:
            x = edge
        if z < -edge:
            z = -edge
        elif z > edge:
            z = edge
        self.traffic_axis[index] = axis
        self.traffic_line[index] = line
        self.traffic_dir[index] = direction
        car = self.traffic[index]
        car.position = Vector(x, z)
        self.traffic_speed[index] = self.TRAFFIC_SPEED
        car.is_visible = True

    def _build_people(self):
        """Create the sidewalk pedestrian entities."""
        from picoware.engine.entity import ENTITY_TYPE_3D_SPRITE, SPRITE_3D_HUMANOID

        for index in range(self.PERSON_COUNT):
            person = Entity(
                "Person %d" % (index + 1),
                ENTITY_TYPE_3D_SPRITE,
                Vector(0, 0),
                Vector(0.6, 1.5),
                None,
                None,
                None,
                None,
                None,
                _person_update,
                None,
                None,
                False,
                SPRITE_3D_HUMANOID,
                self.PERSON_COLORS[index],
            )
            person.is_visible = True
            self.people.append(person)
            self.people_dir_x.append(0.0)
            self.people_dir_z.append(1.0)
            self.people_walk.append(0.0)
            self.people_speeds.append(0.020 + (index % 4) * 0.004)
            self.level.entity_add(person)
            self._spawn_person(index)

    def _spawn_person(self, index):
        """Place one pedestrian on a sidewalk near the player."""
        position = self.player.position
        offset = _next_random(41) - 20
        along = -1.0 if _next_random(2) == 0 else 1.0
        roll = _next_random(4)
        if roll < 2:
            line = int(position.x // self.ROAD_SPACING)
            if line < -self.GRID_LIMIT:
                line = -self.GRID_LIMIT
            elif line > self.GRID_LIMIT:
                line = self.GRID_LIMIT
            x = line * self.ROAD_SPACING
            x += -self.SIDEWALK_OFFSET if roll == 0 else self.SIDEWALK_OFFSET
            z = position.y + offset
            self.people_dir_x[index] = 0.0
            self.people_dir_z[index] = along
        else:
            line = int(position.y // self.ROAD_SPACING)
            if line < -self.GRID_LIMIT:
                line = -self.GRID_LIMIT
            elif line > self.GRID_LIMIT:
                line = self.GRID_LIMIT
            x = position.x + offset
            z = line * self.ROAD_SPACING
            z += -self.SIDEWALK_OFFSET if roll == 2 else self.SIDEWALK_OFFSET
            self.people_dir_x[index] = along
            self.people_dir_z[index] = 0.0
        edge = self.WORLD_HALF - 4.0
        if x < -edge:
            x = -edge
        elif x > edge:
            x = edge
        if z < -edge:
            z = -edge
        elif z > edge:
            z = edge
        self.people_walk[index] = 12.0 + _next_random(17)
        person = self.people[index]
        person.position = Vector(x, z)
        person.set_3d_sprite_rotation(
            atan2(self.people_dir_z[index], self.people_dir_x[index]) - pi * 0.5
        )
        person.is_visible = True

    def _build_background(self):
        """Create the sky and horizon entity."""
        from picoware.engine.entity import ENTITY_TYPE_ICON, SPRITE_3D_NONE

        background = Entity(
            "Background",
            ENTITY_TYPE_ICON,
            Vector(0, self.BACKGROUND_Z),
            Vector(1, 1),
            None,
            None,
            None,
            None,
            None,
            None, # update
            _background_render,
            None,
            False,
            SPRITE_3D_NONE,
            self.COLOR_BLACK,
        )
        background.is_visible = True
        self.level.entity_add(background)

    def _build_city(self):
        """Create the city mesh entity."""
        from picoware.engine.sprite3d import Sprite3D

        mesh = Sprite3D()
        self.city_mesh = mesh
        self._mesh_entity(
            "Downtown",
            Vector(0, self.SCENE_ANCHOR_Z),
            Vector(self.WORLD_SIZE, self.WORLD_SIZE),
            mesh,
        )

    def _fill_city(self, center_x, center_z):
        """Build the city geometry inside the field of view box."""
        mesh = self.city_mesh
        mesh.clear_triangles()
        self.buildings = []
        half = self.FIELD_OF_VIEW + self.CHUNK_LAG
        self.box_west = center_x - half
        self.box_east = center_x + half
        self.box_north = center_z - half
        self.box_south = center_z + half
        self._add_streets(mesh)
        specs = []
        self._add_blocks(mesh, specs, center_x, center_z)
        specs.sort(reverse=True)
        for spec in specs:
            self._add_building(
                mesh, spec[1], spec[2], spec[3], spec[4], spec[5], spec[6], spec[7], spec[8]
            )
        mesh.set_wireframe(False)

    def _update_city(self):
        """Refill the city mesh when the player drifts from the anchor."""
        position = self.player.position
        offset_x = position.x - self.anchor_x
        offset_z = position.y - self.anchor_z
        if (
            offset_x > self.CHUNK_LAG
            or offset_x < -self.CHUNK_LAG
            or offset_z > self.CHUNK_LAG
            or offset_z < -self.CHUNK_LAG
        ):
            self.anchor_x = position.x
            self.anchor_z = position.y
            self._fill_city(self.anchor_x, self.anchor_z)

    def _add_streets(self, mesh):
        """Add the roads, sidewalks and lane marks inside the box."""
        west = self.box_west
        east = self.box_east
        north = self.box_north
        south = self.box_south
        if west < -self.WORLD_HALF:
            west = -self.WORLD_HALF
        if east > self.WORLD_HALF:
            east = self.WORLD_HALF
        if north < -self.WORLD_HALF:
            north = -self.WORLD_HALF
        if south > self.WORLD_HALF:
            south = self.WORLD_HALF
        if west >= east or north >= south:
            return
        spacing = self.ROAD_SPACING
        limit = self.GRID_LIMIT
        first = -int(-(west - 4.0) // spacing)
        last = int((east + 4.0) // spacing)
        if first < -limit:
            first = -limit
        if last > limit:
            last = limit
        for index in range(first, last + 1):
            self._add_road_line(mesh, index * spacing, north, south, True)
        first = -int(-(north - 4.0) // spacing)
        last = int((south + 4.0) // spacing)
        if first < -limit:
            first = -limit
        if last > limit:
            last = limit
        for index in range(first, last + 1):
            self._add_road_line(mesh, index * spacing, west, east, False)

    def _add_road_line(self, mesh, line, begin, end, vertical):
        """Add one road strip with sidewalks and lane dashes."""
        length = end - begin
        middle = (begin + end) * 0.5
        if vertical:
            self._ground_rect(
                mesh,
                line,
                middle,
                self.ROAD_WIDTH,
                length,
                self.ROAD_HEIGHT,
                self.COLOR_ROAD,
                self.ROAD_SEGMENT,
            )
            self._ground_rect(
                mesh,
                line - self.SIDEWALK_OFFSET,
                middle,
                self.SIDEWALK_WIDTH,
                length,
                self.SIDEWALK_HEIGHT,
                self.COLOR_SIDEWALK,
                self.SIDEWALK_SEGMENT,
            )
            self._ground_rect(
                mesh,
                line + self.SIDEWALK_OFFSET,
                middle,
                self.SIDEWALK_WIDTH,
                length,
                self.SIDEWALK_HEIGHT,
                self.COLOR_SIDEWALK,
                self.SIDEWALK_SEGMENT,
            )
        else:
            self._ground_rect(
                mesh,
                middle,
                line,
                length,
                self.ROAD_WIDTH,
                self.ROAD_HEIGHT,
                self.COLOR_ROAD,
                self.ROAD_SEGMENT,
            )
            self._ground_rect(
                mesh,
                middle,
                line - self.SIDEWALK_OFFSET,
                length,
                self.SIDEWALK_WIDTH,
                self.SIDEWALK_HEIGHT,
                self.COLOR_SIDEWALK,
                self.SIDEWALK_SEGMENT,
            )
            self._ground_rect(
                mesh,
                middle,
                line + self.SIDEWALK_OFFSET,
                length,
                self.SIDEWALK_WIDTH,
                self.SIDEWALK_HEIGHT,
                self.COLOR_SIDEWALK,
                self.SIDEWALK_SEGMENT,
            )
        position = begin + (self.MARK_OFFSET - begin) % self.MARK_SPACING
        while position <= end:
            if vertical:
                self._ground_rect(
                    mesh,
                    line,
                    position,
                    self.MARK_WIDTH,
                    self.MARK_LENGTH,
                    self.MARK_HEIGHT,
                    self.COLOR_LINE,
                    self.MARK_LENGTH,
                )
            else:
                self._ground_rect(
                    mesh,
                    position,
                    line,
                    self.MARK_LENGTH,
                    self.MARK_WIDTH,
                    self.MARK_HEIGHT,
                    self.COLOR_LINE,
                    self.MARK_LENGTH,
                )
            position += self.MARK_SPACING

    def _add_blocks(self, mesh, specs, center_x, center_z):
        """Collect the block buildings and trees whose lots touch the box."""
        spacing = self.ROAD_SPACING
        reach = self.BLOCK_REACH
        first = int((self.box_west - reach) // spacing)
        last = int((self.box_east + reach) // spacing)
        first_row = int((self.box_north - reach) // spacing)
        last_row = int((self.box_south + reach) // spacing)
        limit = self.GRID_LIMIT
        for col in range(first, last + 1):
            if col < -limit or col >= limit:
                continue
            block_x = col * spacing + self.BLOCK_CENTER
            for row in range(first_row, last_row + 1):
                if row < -limit or row >= limit:
                    continue
                self._add_block(
                    mesh,
                    specs,
                    col,
                    row,
                    block_x,
                    row * spacing + self.BLOCK_CENTER,
                    center_x,
                    center_z,
                )

    def _add_block(self, mesh, specs, col, row, block_x, block_z, center_x, center_z):
        """Collect the hash varied buildings and trees of one city block."""
        if _cell_hash(col, row, 1) % 7 == 0:
            self._add_tree(mesh, block_x, block_z)
            return
        reach = self.BUILDING_REACH
        for index, slot in enumerate(self.BLOCK_SLOTS):
            detail = _cell_hash(col, row, index + 2)
            x = block_x + slot[0]
            z = block_z + slot[1]
            if x < self.box_west - reach or x > self.box_east + reach:
                continue
            if z < self.box_north - reach or z > self.box_south + reach:
                continue
            if detail % 5 == 0:
                self._add_tree(mesh, x, z)
                continue
            wall, roof = self.BUILDING_COLORS[detail % 8]
            width = 9.0 + (detail >> 4) % 5
            depth = 9.0 + (detail >> 7) % 5
            height = 3.2 + ((detail >> 10) % 5) * 0.9
            building_type = (detail >> 12) % 3
            if building_type == 1:
                width = 7.0
                depth = 7.0
                height = 2.5
            elif building_type == 2:
                height = 10.0 + (detail >> 10) % 6
            distance = (x - center_x) ** 2 + (z - center_z) ** 2
            specs.append((distance, x, z, width, depth, height, wall, roof, building_type))

    def _blocked(self, x, z, is_car):
        """Return whether a position would hit a building or the world edge."""
        limit = self.WORLD_HALF - self.CAR_RADIUS
        if abs(x) > limit or abs(z) > limit:
            return True
        for building in self.buildings:
            if not is_car and building[4]:
                continue
            if abs(x - building[0]) < building[2] + self.CAR_RADIUS:
                if abs(z - building[1]) < building[3] + self.CAR_RADIUS:
                    return True
        return False

    def _car_blocked(self, x, z, skip_index):
        """Return whether a position hits another car or a person."""
        for index, car in enumerate(self.traffic):
            if index == skip_index:
                continue
            if not car.is_visible:
                continue
            dx = x - car.position.x
            if dx < 0:
                dx = -dx
            dz = z - car.position.y
            if dz < 0:
                dz = -dz
            if dx < 1.05 and dz < 1.85:
                return True
        if skip_index < self.TRAFFIC_COUNT:
            dx = x - self.player.position.x
            if dx < 0:
                dx = -dx
            dz = z - self.player.position.y
            if dz < 0:
                dz = -dz
            if dx < 1.05 and dz < 1.85:
                return True
        for index, person in enumerate(self.people):
            if not person.is_visible:
                continue
            pos = person.position
            dx = x - pos.x
            if dx < 0:
                dx = -dx
            dz = z - pos.y
            if dz < 0:
                dz = -dz
            if dx < 0.825 and dz < 1.675:
                return True
        return False

    def update_player(self, player, game):
        """Move the player on foot or in a car."""
        from picoware.system.buttons import BUTTON_CENTER

        self._update_message()
        if game.input == BUTTON_CENTER:
            self._toggle_car(player)
        if self.in_car:
            self._drive_car(player, game)
        else:
            self._walk_player(player, game)
        self._update_city()

    def _walk_player(self, player, game):
        """Walk the player on foot."""
        from picoware.system.buttons import BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP

        button = game.input
        if button == BUTTON_UP:
            self.speed = self.WALK_SPEED
        elif button == BUTTON_DOWN:
            self.speed = -self.WALK_SPEED * 0.5
        else:
            self.speed = 0.0

        if button == BUTTON_LEFT:
            self.heading -= self.WALK_TURN
        elif button == BUTTON_RIGHT:
            self.heading += self.WALK_TURN

        dx = cos(self.heading)
        dz = sin(self.heading)
        old_x = player.position.x
        old_z = player.position.y
        next_x = old_x + dx * self.speed
        next_z = old_z + dz * self.speed
        if not self._blocked(next_x, next_z, False) and not self._car_blocked(next_x, next_z, self.TRAFFIC_COUNT):
            player.position = Vector(next_x, next_z)
        else:
            if not self._blocked(next_x, old_z, False) and not self._car_blocked(next_x, old_z, self.TRAFFIC_COUNT):
                player.position = Vector(next_x, old_z)
            elif not self._blocked(old_x, next_z, False) and not self._car_blocked(old_x, next_z, self.TRAFFIC_COUNT):
                player.position = Vector(old_x, next_z)
            self.speed *= 0.25

        player.direction = Vector(dx, dz)
        player.set_3d_sprite_rotation(atan2(dz, dx) - pi * 0.5)

    def _drive_car(self, player, game):
        """Drive the player car with building collision."""
        from picoware.system.buttons import BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP

        button = game.input
        if button == BUTTON_UP:
            self.speed += self.CAR_ACCEL
        elif button == BUTTON_DOWN:
            self.speed -= self.CAR_BRAKE
        elif self.speed > 0:
            self.speed = max(0.0, self.speed - self.CAR_FRICTION)
        else:
            self.speed = min(0.0, self.speed + self.CAR_FRICTION)

        if button == BUTTON_LEFT:
            steering = -1.0
        elif button == BUTTON_RIGHT:
            steering = 1.0
        else:
            steering = 0.0

        if steering != 0.0:
            turn_scale = 0.70 + min(1.0, abs(self.speed) / self.CAR_MAX_SPEED) * 0.30
            if self.speed < 0:
                turn_scale = -turn_scale
            self.heading += steering * self.CAR_STEER * turn_scale

        self.speed = max(self.CAR_MAX_REVERSE, min(self.CAR_MAX_SPEED, self.speed))
        dx = cos(self.heading)
        dz = sin(self.heading)
        old_x = player.position.x
        old_z = player.position.y
        next_x = old_x + dx * self.speed
        next_z = old_z + dz * self.speed

        if not self._blocked(next_x, next_z, True) and not self._car_blocked(next_x, next_z, self.TRAFFIC_COUNT):
            player.position = Vector(next_x, next_z)
        else:
            if not self._blocked(next_x, old_z, True) and not self._car_blocked(next_x, old_z, self.TRAFFIC_COUNT):
                player.position = Vector(next_x, old_z)
            elif not self._blocked(old_x, next_z, True) and not self._car_blocked(old_x, next_z, self.TRAFFIC_COUNT):
                player.position = Vector(old_x, next_z)
            self.speed *= 0.25

        player.direction = Vector(dx, dz)
        player.plane = Vector(-0.72, 0)
        player.set_3d_sprite_rotation(atan2(dz, dx) - pi * 0.5)
        self._sync_player_car(player)

    def _toggle_car(self, player):
        """Toggle the player between walking and driving."""
        if self.in_car:
            self.in_car = False
            self.speed = 0.0
            player.is_visible = True
            player.set_3d_sprite_rotation(
                atan2(sin(self.heading), cos(self.heading)) - pi * 0.5
            )
            self.player_car.is_visible = False
            self.message = "Walk mode"
            self.message_timer = 60
        else:
            self.in_car = True
            self.speed = 0.0
            player.is_visible = False
            self.player_car.is_visible = True
            self.message = "Drive mode"
            self.message_timer = 60

    def _sync_player_car(self, player):
        """Track the player car to the player position and heading."""
        dx = cos(self.heading)
        dz = sin(self.heading)
        self.player_car.position = player.position
        self.player_car.direction = Vector(dx, dz)
        self.player_car.plane = Vector(-0.72, 0)
        self.player_car.set_3d_sprite_rotation(atan2(dz, dx) - pi * 0.5)

    def update_traffic(self, car):
        """Drive a traffic car along the street grid."""
        index = int(car.name[-1]) - 1
        speed = self.traffic_speed[index]
        axis = self.traffic_axis[index]
        direction = self.traffic_dir[index]

        if axis == 0:
            heading = pi * 0.5 if direction == 1 else -pi * 0.5
        else:
            heading = 0.0 if direction == 1 else pi

        dx = cos(heading)
        dz = sin(heading)
        old_x = car.position.x
        old_z = car.position.y
        next_x = old_x + dx * speed
        next_z = old_z + dz * speed

        if not self._blocked(next_x, next_z, True) and not self._car_blocked(next_x, next_z, index):
            car.position = Vector(next_x, next_z)
        else:
            direction = -direction
            self.traffic_dir[index] = direction
            if axis == 0:
                heading = pi * 0.5 if direction == 1 else -pi * 0.5
            else:
                heading = 0.0 if direction == 1 else pi
            dx = cos(heading)
            dz = sin(heading)
            next_x = old_x + dx * speed
            next_z = old_z + dz * speed
            car.position = Vector(next_x, next_z)

        car.direction = Vector(dx, dz)
        car.plane = Vector(-0.72, 0)
        car.set_3d_sprite_rotation(atan2(dz, dx) - pi * 0.5)

        player = self.player.position
        offset_x = car.position.x - player.x
        offset_z = car.position.y - player.y
        if offset_x < 0.0:
            offset_x = -offset_x
        if offset_z < 0.0:
            offset_z = -offset_z
        edge = self.WORLD_HALF - 4.0
        if (
            offset_x > self.RECYCLE_DISTANCE
            or offset_z > self.RECYCLE_DISTANCE
            or car.position.x < -edge
            or car.position.x > edge
            or car.position.y < -edge
            or car.position.y > edge
        ):
            self._spawn_traffic(index)
        elif offset_x > self.FIELD_OF_VIEW + 8.0 or offset_z > self.FIELD_OF_VIEW + 8.0:
            car.is_visible = False
        else:
            car.is_visible = True

    def update_person(self, person):
        """Walk one pedestrian and recycle it when far away."""
        index = int(person.name[7:]) - 1
        position = person.position
        x = position.x + self.people_dir_x[index] * self.people_speeds[index]
        z = position.y + self.people_dir_z[index] * self.people_speeds[index]
        walk = self.people_walk[index] - self.people_speeds[index]
        if walk <= 0.0:
            self.people_dir_x[index] = -self.people_dir_x[index]
            self.people_dir_z[index] = -self.people_dir_z[index]
            walk = 12.0 + _next_random(17)
            person.set_3d_sprite_rotation(
                atan2(self.people_dir_z[index], self.people_dir_x[index]) - pi * 0.5
            )
        self.people_walk[index] = walk
        person.position = Vector(x, z)
        car = self.player.position
        offset_x = x - car.x
        offset_z = z - car.y
        if offset_x < 0.0:
            offset_x = -offset_x
        if offset_z < 0.0:
            offset_z = -offset_z
        edge = self.WORLD_HALF - 4.0
        if (
            offset_x > self.RECYCLE_DISTANCE
            or offset_z > self.RECYCLE_DISTANCE
            or x < -edge
            or x > edge
            or z < -edge
            or z > edge
        ):
            self._spawn_person(index)
            return
        if offset_x > self.FIELD_OF_VIEW + 8.0 or offset_z > self.FIELD_OF_VIEW + 8.0:
            person.is_visible = False
            return
        person.is_visible = not self._hidden_by_building(x, z)

    def _hidden_by_building(self, x, z):
        """Return whether a building blocks the view of a point."""
        car = self.player.position
        for building in self.buildings:
            if self._crosses_building(car.x, car.y, x, z, building):
                return True
        return False

    def _crosses_building(self, x0, z0, x1, z1, building):
        """Return whether a segment crosses a building rectangle."""
        left = building[0] - building[2]
        right = building[0] + building[2]
        near = building[1] - building[3]
        far = building[1] + building[3]
        dx = x1 - x0
        dz = z1 - z0
        begin = 0.0
        end = 1.0
        if dx > -0.0001 and dx < 0.0001:
            if x0 < left or x0 > right:
                return False
        else:
            inverse = 1.0 / dx
            enter = (left - x0) * inverse
            leave = (right - x0) * inverse
            if enter > leave:
                enter, leave = leave, enter
            begin = max(begin, enter)
            end = min(end, leave)
            if begin > end:
                return False
        if 0.0001 > dz > -0.0001:
            if z0 < near or z0 > far:
                return False
        else:
            inverse = 1.0 / dz
            enter = (near - z0) * inverse
            leave = (far - z0) * inverse
            if enter > leave:
                enter, leave = leave, enter
            begin = max(begin, enter)
            end = min(end, leave)
            if begin > end:
                return False
        return True

    def _update_message(self):
        """Count down the message timer."""
        if self.message_timer > 0:
            self.message_timer -= 1
            if self.message_timer == 0:
                self.message = ""

    def draw_background(self, draw):
        """Draw the sky, horizon haze and distant ground."""
        width = int(draw.size.x)
        height = int(draw.size.y)
        horizon = int(height * 0.52)
        haze = draw.scale_y(18)
        draw._fill_rectangle(0, 0, width, horizon, self.COLOR_SKY)
        draw._fill_rectangle(0, horizon, width, haze, self.COLOR_HORIZON)
        draw._fill_rectangle(0, horizon + haze, width, height - horizon - haze, self.COLOR_GROUND)
        draw._fill_rectangle(0, horizon - draw.scale_y(2), width, draw.scale_y(2), self.COLOR_ROOF)

    def draw_hud(self, draw=None):
        """Draw the mode, speed and control hints."""
        if self.engine is None:
            return
        draw = self.draw if draw is None else draw
        width = int(draw.size.x)
        bar_height = draw.scale_y(16)
        draw._fill_rectangle(0, 0, width, bar_height, self.COLOR_BLACK)

        if self.in_car:
            label = "DRIVE  %d MPH" % int(abs(self.speed) * 150)
        else:
            label = "WALK"
        draw._text(draw.scale_x(3), draw.scale_y(2), label, self.COLOR_LINE)

        if self.message_timer > 0:
            draw._text(
                width // 2 - draw.scale_x(len(self.message) * 3),
                int(draw.size.y) // 2 - draw.scale_y(4),
                self.message,
                self.COLOR_LINE,
            )
        self._draw_minimap(draw)

    def _draw_minimap(self, draw):
        """Draw the local street and building overview."""
        width = int(draw.size.x)
        size = draw.scale_y(self.MINIMAP_SIZE)
        left = width - size - draw.scale_x(3)
        top = draw.scale_y(19)
        car = self.player.position
        step = size / (self.MINIMAP_RANGE * 2.0)
        middle_x = left + size * 0.5
        middle_z = top + size * 0.5
        thickness = draw.scale_y(2)
        if thickness < 1:
            thickness = 1
        draw._fill_rectangle(left, top, size, size, self.COLOR_BLACK)
        first = int((car.x - self.MINIMAP_RANGE) // self.ROAD_SPACING)
        last = int((car.x + self.MINIMAP_RANGE) // self.ROAD_SPACING)
        for index in range(first, last + 1):
            line = index * self.ROAD_SPACING
            if line < -self.WORLD_HALF or line > self.WORLD_HALF:
                continue
            offset = int(middle_x + (line - car.x) * step) - thickness // 2
            draw._fill_rectangle(offset, top, thickness, size, self.COLOR_HORIZON)
        first = int((car.y - self.MINIMAP_RANGE) // self.ROAD_SPACING)
        last = int((car.y + self.MINIMAP_RANGE) // self.ROAD_SPACING)
        for index in range(first, last + 1):
            line = index * self.ROAD_SPACING
            if line < -self.WORLD_HALF or line > self.WORLD_HALF:
                continue
            offset = int(middle_z + (line - car.y) * step) - thickness // 2
            draw._fill_rectangle(left, offset, size, thickness, self.COLOR_HORIZON)
        for building in self.buildings:
            start_x = middle_x + (building[0] - car.x) * step - building[2] * step
            end_x = start_x + building[2] * step * 2.0
            start_z = middle_z + (building[1] - car.y) * step - building[3] * step
            end_z = start_z + building[3] * step * 2.0
            if start_x < left:
                start_x = left
            if start_z < top:
                start_z = top
            if end_x > left + size:
                end_x = left + size
            if end_z > top + size:
                end_z = top + size
            if end_x - start_x < 1.0 or end_z - start_z < 1.0:
                continue
            draw._fill_rectangle(
                int(start_x),
                int(start_z),
                int(end_x - start_x),
                int(end_z - start_z),
                self.COLOR_SIDEWALK,
            )
        draw._rectangle(left, top, size, size, self.COLOR_HORIZON)
        dot = draw.scale_y(3)
        if dot < 2:
            dot = 2
        tip = dot + draw.scale_y(3)
        draw._fill_rectangle(
            int(middle_x + cos(self.heading) * tip) - 1,
            int(middle_z + sin(self.heading) * tip) - 1,
            2,
            2,
            self.COLOR_LINE,
        )
        draw._fill_rectangle(
            int(middle_x) - dot // 2,
            int(middle_z) - dot // 2,
            dot,
            dot,
            self.COLOR_PLAYER,
        )
        draw._text(
            left,
            top + size + draw.scale_y(2),
            "%d,%d"
            % (
                int(car.x // self.ROAD_SPACING),
                int(car.y // self.ROAD_SPACING),
            ),
            self.COLOR_LINE,
        )

    def run(self):
        """Refill the local city and run one engine frame."""
        self._update_city()
        if self.engine is not None:
            self.engine.run_async(False)

    def stop(self):
        """Stop the engine and release the city resources."""
        if self.engine is not None:
            self.engine.stop()
            self.engine = None
        self.meshes = []
        self.city_mesh = None
        self.buildings = []
        self.people = []
        self.people_dir_x = []
        self.people_dir_z = []
        self.people_walk = []
        self.people_speeds = []
        self.traffic = []
        self.traffic_speed = []
        self.traffic_axis = []
        self.traffic_line = []
        self.traffic_dir = []
        self.player = None


def start(view_manager) -> bool:
    """Start the Pico City view."""
    global _city

    _city = _City(view_manager)
    return _city.engine is not None


def run(view_manager) -> None:
    """Run one Pico City frame."""
    from picoware.system.buttons import BUTTON_BACK

    if _city is None:
        view_manager.back()
        return

    button = view_manager.input_manager.button
    if button == BUTTON_BACK:
        view_manager.input_manager.reset()
        view_manager.back()
        return

    _city.run()


def stop(_view_manager) -> None:
    """Stop Pico City and release engine resources."""
    from gc import collect

    global _city

    if _city is not None:
        _city.stop()
        _city = None
    collect()
