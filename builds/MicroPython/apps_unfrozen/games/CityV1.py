"""Simple Picoware 3D downtown driving game."""

from math import atan2, cos, pi, sin
from picoware.system.vector import Vector
from picoware.engine.entity import Entity

_city = None


def _player_update(entity, game):
    """Forward the player callback to the active city."""
    if _city is not None:
        _city.update_player(entity, game)


def _person_update(entity, _game):
    """Forward a pedestrian callback to the active city."""
    if _city is not None:
        _city.update_person(entity)


def _player_render(_entity, draw, _game):
    """Draw the city HUD from the player render pass."""
    if _city is not None:
        _city.draw_hud(draw)


def _background_render(_entity, draw, _game):
    """Draw the sky and distant city horizon."""
    if _city is not None:
        _city.draw_background(draw)


class _City:
    """Own the city scene and driving state."""

    WORLD_SIZE = 84.0
    WORLD_HALF = 42.0
    SCENE_ANCHOR_Z = -100.0
    ROAD_WIDTH = 5.5
    SIDEWALK_WIDTH = 1.2
    ROAD_COORDS = (-24.0, 0.0, 24.0)
    ROAD_MARKS = (-39, -33, -27, -21, -15, -9, -3, 3, 9, 15, 21, 27, 33, 39)
    MAX_SPEED = 0.34
    MAX_REVERSE = -0.16
    ACCELERATION = 0.016
    BRAKING = 0.022
    FRICTION = 0.007
    STEER_STEP = 0.12
    CAR_RADIUS = 0.72

    COLOR_BLACK = 0x0000
    COLOR_SKY = 0x5D9F
    COLOR_HORIZON = 0x8C71
    COLOR_GROUND = 0xBDF7
    COLOR_SIDEWALK = 0xD69A
    COLOR_ROAD = 0x39C7
    COLOR_LINE = 0xFFE0
    COLOR_WINDOW = 0x2A8A
    COLOR_ROOF = 0x632C
    COLOR_PLAYER = 0x07FF
    COLOR_GLASS = 0x5D9B
    COLOR_SKIN = 0xFD20
    STREET_TILE_SIZE = 2.5
    SIDEWALK_TILE_SIZE = 8.0
    GROUND_TILE_SIZE = 8.0

    BUILDINGS = (
        (-10.0, -10.0, 4.8, 4.8, 5.5, 0xB5B6, 0x7BEF),
        (-5.0, -9.0, 3.2, 4.0, 3.2, 0xD69A, 0xFBE0),
        (8.5, -10.0, 5.5, 4.5, 6.4, 0x6B4D, 0xC618),
        (12.0, -6.5, 2.7, 3.4, 4.0, 0xA145, 0xFD20),
        (-10.0, 8.5, 5.2, 4.4, 6.8, 0x9CB2, 0x5D9B),
        (-5.0, 11.0, 3.5, 2.8, 3.8, 0xFBE0, 0xFD20),
        (8.5, 8.5, 5.0, 4.5, 5.2, 0xC618, 0x9CB2),
        (12.0, 11.5, 2.8, 3.0, 4.2, 0xA145, 0xFFE0),
        (-17.0, -17.0, 4.8, 4.8, 5.5, 0x6B4D, 0xC618),
        (17.0, -17.0, 4.5, 4.5, 6.0, 0x9CB2, 0x7BEF),
        (-17.0, 17.0, 5.0, 4.2, 6.2, 0xD69A, 0xFBE0),
        (17.0, 17.0, 4.2, 4.8, 4.6, 0xA145, 0xFD20),
    )

    PEOPLE = (
        (-21.0, -18.0, 0x001F),
        (-3.0, -21.0, 0xF800),
        (21.0, -15.0, 0x07E0),
        (-21.0, 15.0, 0xFD20),
        (-3.0, 21.0, 0xF81F),
        (21.0, 15.0, 0x001F),
    )

    PERSON_PATHS = (
        (-21.0, -18.0, -21.0, -10.0),
        (-3.0, -21.0, 9.0, -21.0),
        (21.0, -15.0, 21.0, -7.0),
        (-21.0, 15.0, -21.0, 23.0),
        (-3.0, 21.0, 9.0, 21.0),
        (21.0, 15.0, 21.0, 7.0),
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
        self.people = []
        self.people_progress = []
        self.people_directions = []
        self.people_speeds = []
        self.player = None
        self.speed = 0.0
        self.heading = pi * 0.5

        game = Game(
            "City Drive",
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
        self._build_static_scene()
        self._build_player()
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

    def _ground_rect(
        self, mesh, x, z, width, depth, height, color, segment_size=None, split_both=False
    ):
        z -= self.SCENE_ANCHOR_Z
        if segment_size is None:
            segment_size = self.STREET_TILE_SIZE
        width_steps = max(1, int((width + segment_size - 0.001) / segment_size))
        depth_steps = max(1, int((depth + segment_size - 0.001) / segment_size))
        if not split_both:
            if width >= depth:
                depth_steps = 1
            else:
                width_steps = 1

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

    def _box(self, mesh, x, y, z, width, height, depth, color):
        z -= self.SCENE_ANCHOR_Z
        half_width = width * 0.5
        half_height = height * 0.5
        half_depth = depth * 0.5
        bottom = y - half_height
        top = y + half_height
        front = z + half_depth
        back = z - half_depth
        self._quad(
            mesh,
            (x - half_width, bottom, front),
            (x + half_width, bottom, front),
            (x + half_width, top, front),
            (x - half_width, top, front),
            color,
        )
        self._quad(
            mesh,
            (x + half_width, bottom, back),
            (x - half_width, bottom, back),
            (x - half_width, top, back),
            (x + half_width, top, back),
            color,
        )
        self._quad(
            mesh,
            (x + half_width, bottom, front),
            (x + half_width, bottom, back),
            (x + half_width, top, back),
            (x + half_width, top, front),
            color,
        )
        self._quad(
            mesh,
            (x - half_width, bottom, back),
            (x - half_width, bottom, front),
            (x - half_width, top, front),
            (x - half_width, top, back),
            color,
        )
        self._quad(
            mesh,
            (x - half_width, top, front),
            (x + half_width, top, front),
            (x + half_width, top, back),
            (x - half_width, top, back),
            color,
        )

    def _add_building(self, mesh, building):
        x, z, width, depth, height, color, roof_color = building
        scene_z = z - self.SCENE_ANCHOR_Z
        mesh.create_cube(x, height * 0.5, scene_z, width, height, depth, color)
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
        self._box(
            mesh,
            x,
            window_y,
            z + depth * 0.5 + 0.025,
            width * 0.55,
            window_height,
            0.04,
            self.COLOR_WINDOW,
        )
        if height > 4.5:
            self._box(
                mesh,
                x,
                height * 0.58,
                z + depth * 0.5 + 0.025,
                width * 0.55,
                window_height,
                0.04,
                self.COLOR_WINDOW,
            )

    def _build_people(self):
        from picoware.engine.entity import ENTITY_TYPE_3D_SPRITE, SPRITE_3D_HUMANOID

        for index, person_data in enumerate(self.PEOPLE):
            x, z, color = person_data
            person = Entity(
                "Person %d" % (index + 1),
                ENTITY_TYPE_3D_SPRITE,
                Vector(x, z),
                Vector(0.6, 1.5),
                None,
                None,
                None,
                _person_update,
                None,
                None,
                None,
                None,
                False,
                SPRITE_3D_HUMANOID,
                color,
            )
            person.is_visible = True
            path = self.PERSON_PATHS[index]
            person.set_3d_sprite_rotation(
                atan2(path[3] - path[1], path[2] - path[0]) - pi * 0.5
            )
            self.people.append(person)
            self.people_progress.append(0.0)
            self.people_directions.append(1.0)
            self.people_speeds.append(0.022 + (index % 3) * 0.003)
            self.level.entity_add(person)

    def update_person(self, person):
        index = int(person.name[7:]) - 1
        start_x, start_z, end_x, end_z = self.PERSON_PATHS[index]
        progress = self.people_progress[index]
        direction = self.people_directions[index]
        progress += self.people_speeds[index] * direction
        if progress >= 1.0:
            progress = 1.0
            direction = -1.0
        elif progress <= 0.0:
            progress = 0.0
            direction = 1.0
        self.people_progress[index] = progress
        self.people_directions[index] = direction
        person.position = Vector(
            start_x + (end_x - start_x) * progress,
            start_z + (end_z - start_z) * progress,
        )
        heading_x = (end_x - start_x) * direction
        heading_z = (end_z - start_z) * direction
        person.set_3d_sprite_rotation(atan2(heading_z, heading_x) - pi * 0.5)

    def _build_static_scene(self):
        from picoware.engine.entity import ENTITY_TYPE_ICON, SPRITE_3D_NONE
        from picoware.engine.sprite3d import Sprite3D

        background = Entity(
            "Background",
            ENTITY_TYPE_ICON,
            Vector(0, 1000),
            Vector(1, 1),
            None,
            None,
            None,
            None,
            None,
            None,
            _background_render,
            None,
            False,
            SPRITE_3D_NONE,
            self.COLOR_BLACK,
        )
        background.is_visible = True
        self.level.entity_add(background)

        mesh = Sprite3D()
        self._ground_rect(
            mesh,
            0,
            0,
            self.WORLD_SIZE + 8,
            self.WORLD_SIZE + 8,
            0,
            self.COLOR_GROUND,
            self.GROUND_TILE_SIZE,
            True,
        )

        for coordinate in self.ROAD_COORDS:
            sidewalk_offset = self.ROAD_WIDTH * 0.5 + self.SIDEWALK_WIDTH * 0.5
            self._ground_rect(
                mesh,
                coordinate - sidewalk_offset,
                0,
                self.SIDEWALK_WIDTH,
                self.WORLD_SIZE,
                0.03,
                self.COLOR_SIDEWALK,
                self.SIDEWALK_TILE_SIZE,
            )
            self._ground_rect(
                mesh,
                coordinate + sidewalk_offset,
                0,
                self.SIDEWALK_WIDTH,
                self.WORLD_SIZE,
                0.03,
                self.COLOR_SIDEWALK,
                self.SIDEWALK_TILE_SIZE,
            )
            self._ground_rect(
                mesh,
                coordinate,
                0,
                self.ROAD_WIDTH,
                self.WORLD_SIZE,
                0.06,
                self.COLOR_ROAD,
            )
            for mark in self.ROAD_MARKS:
                self._ground_rect(
                    mesh,
                    coordinate,
                    mark,
                    0.12,
                    2.4,
                    0.10,
                    self.COLOR_LINE,
                )

        for coordinate in self.ROAD_COORDS:
            sidewalk_offset = self.ROAD_WIDTH * 0.5 + self.SIDEWALK_WIDTH * 0.5
            self._ground_rect(
                mesh,
                0,
                coordinate - sidewalk_offset,
                self.WORLD_SIZE,
                self.SIDEWALK_WIDTH,
                0.03,
                self.COLOR_SIDEWALK,
                self.SIDEWALK_TILE_SIZE,
            )
            self._ground_rect(
                mesh,
                0,
                coordinate + sidewalk_offset,
                self.WORLD_SIZE,
                self.SIDEWALK_WIDTH,
                0.03,
                self.COLOR_SIDEWALK,
                self.SIDEWALK_TILE_SIZE,
            )
            self._ground_rect(
                mesh,
                0,
                coordinate,
                self.WORLD_SIZE,
                self.ROAD_WIDTH,
                0.06,
                self.COLOR_ROAD,
            )
            for mark in self.ROAD_MARKS:
                self._ground_rect(
                    mesh,
                    mark,
                    coordinate,
                    2.4,
                    0.12,
                    0.10,
                    self.COLOR_LINE,
                )

        for building in self.BUILDINGS:
            self._add_building(mesh, building)

        mesh.set_wireframe(False)
        self._mesh_entity(
            "Downtown",
            Vector(0, self.SCENE_ANCHOR_Z),
            Vector(self.WORLD_SIZE, self.WORLD_SIZE),
            mesh,
        )
        self._build_people()

    def _car_mesh(self):
        from picoware.engine.sprite3d import Sprite3D

        mesh = Sprite3D()
        mesh.create_cube(0, 0.36, 0, 1.05, 0.34, 1.85, self.COLOR_PLAYER)
        mesh.create_cube(0, 0.62, 0.10, 0.68, 0.24, 0.72, self.COLOR_GLASS)
        mesh.create_cube(0, 0.20, -0.78, 0.85, 0.10, 0.12, self.COLOR_LINE)
        mesh.set_wireframe(False)
        return mesh

    def _build_player(self):
        self.player = self._mesh_entity(
            "Player",
            Vector(0, 8),
            Vector(1.05, 1.85),
            self._car_mesh(),
            _player_update,
            _player_render,
        )
        self.player.is_player = True
        self.player.plane = Vector(-0.72, 0)
        self._place_player()

    def _place_player(self):
        direction_x = cos(self.heading)
        direction_y = sin(self.heading)
        self.player.direction = Vector(direction_x, direction_y)
        self.player.plane = Vector(-0.72, 0)
        self.player.set_3d_sprite_rotation(atan2(direction_y, direction_x) - pi * 0.5)

    def _blocked(self, x, z):
        limit = self.WORLD_HALF - self.CAR_RADIUS
        if abs(x) > limit or abs(z) > limit:
            return True
        for building in self.BUILDINGS:
            building_x, building_z, width, depth = building[0:4]
            if abs(x - building_x) < width * 0.5 + self.CAR_RADIUS:
                if abs(z - building_z) < depth * 0.5 + self.CAR_RADIUS:
                    return True
        return False

    def update_player(self, car, game):
        from picoware.system.buttons import BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP

        button = game.input
        if button == BUTTON_UP:
            self.speed += self.ACCELERATION
        elif button == BUTTON_DOWN:
            self.speed -= self.BRAKING
        elif self.speed > 0:
            self.speed = max(0.0, self.speed - self.FRICTION)
        else:
            self.speed = min(0.0, self.speed + self.FRICTION)

        if button == BUTTON_LEFT:
            steering = -1.0
        elif button == BUTTON_RIGHT:
            steering = 1.0
        else:
            steering = 0.0

        if steering != 0.0:
            turn_scale = 0.55 + min(1.0, abs(self.speed) / self.MAX_SPEED) * 0.45
            if self.speed < 0:
                turn_scale = -turn_scale
            self.heading += steering * self.STEER_STEP * turn_scale

        self.speed = max(self.MAX_REVERSE, min(self.MAX_SPEED, self.speed))
        direction_x = cos(self.heading)
        direction_y = sin(self.heading)
        old_x = car.position.x
        old_z = car.position.y
        next_x = old_x + direction_x * self.speed
        next_z = old_z + direction_y * self.speed

        if not self._blocked(next_x, next_z):
            car.position = Vector(next_x, next_z)
        else:
            if not self._blocked(next_x, old_z):
                car.position = Vector(next_x, old_z)
            elif not self._blocked(old_x, next_z):
                car.position = Vector(old_x, next_z)
            self.speed *= 0.25

        self._place_player()

    def draw_background(self, draw):
        width = int(draw.size.x)
        height = int(draw.size.y)
        horizon = int(height * 0.52)
        draw._fill_rectangle(0, 0, width, horizon, self.COLOR_SKY)
        draw._fill_rectangle(0, horizon, width, height - horizon, self.COLOR_HORIZON)
        draw._fill_rectangle(0, horizon - draw.scale_y(2), width, draw.scale_y(2), self.COLOR_ROOF)

    def draw_hud(self, draw=None):
        if self.engine is None:
            return
        draw = self.draw if draw is None else draw
        width = int(draw.size.x)
        bar_height = draw.scale_y(16)
        draw._fill_rectangle(0, 0, width, bar_height, self.COLOR_BLACK)
        draw._text(draw.scale_x(3), draw.scale_y(2), "CITY", self.COLOR_LINE)
        speed_label = "%3d MPH" % int(self.speed * 280)
        draw._text(width // 2 - draw.scale_x(20), draw.scale_y(2), speed_label, self.COLOR_LINE)
        draw._text(width - draw.scale_x(35), draw.scale_y(2), "DRIVE", self.COLOR_LINE)

    def run(self):
        if self.engine is not None:
            self.engine.run_async(False)

    def stop(self):
        if self.engine is not None:
            self.engine.stop()
            self.engine = None
        self.meshes = []
        self.people = []
        self.people_progress = []
        self.people_directions = []
        self.people_speeds = []
        self.player = None


def start(view_manager) -> bool:
    """Start the city driving view."""
    global _city

    _city = _City(view_manager)
    return _city.engine is not None


def run(view_manager) -> None:
    """Run one city driving frame."""
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
    """Stop the city view and release engine resources."""
    from gc import collect

    global _city

    if _city is not None:
        _city.stop()
        _city = None
    collect()