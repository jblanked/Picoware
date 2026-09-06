"""Simple Picoware 3D racing game."""

from math import atan2, cos, pi, sin, sqrt
from picoware.system.vector import Vector
from picoware.engine.entity import Entity

_race = None


def _player_update(entity, game):
    """Forward the native entity callback to the active race."""
    if _race is not None:
        _race.update_player(entity, game)


def _rival_update(entity, game):
    """Forward the native entity callback to the active race."""
    if _race is not None:
        _race.update_rival(entity, game)


def _car_collision(entity, other, game):
    """Forward car collisions to the active race."""
    if _race is not None:
        _race.handle_collision(entity, other, game)


def _player_render(_entity, draw, _game):
    """Draw the HUD from the player's render pass."""
    if _race is not None:
        _race.draw_hud(draw)


def _background_render(_entity, draw, _game):
    """Draw the two-tone race background."""
    if _race is not None:
        _race.draw_background(draw)


class _Race:
    """Own the race state and Pico Game Engine objects."""

    TRACK_RADIUS_X = 18.0
    TRACK_RADIUS_Y = 10.0
    TRACK_WIDTH = 5.5
    TRACK_SEGMENTS = 32
    START_PROGRESS = 0.03
    MAX_SPEED = 0.34
    ACCELERATION = 0.018
    BRAKING = 0.028
    FRICTION = 0.008
    STEER_STEP = 0.22
    CAR_HITBOX_LENGTH = 1.55
    CAR_HITBOX_LANE = 0.65
    CAR_PUSH_PROGRESS = 0.004
    CAR_PUSH_SPEED = 0.025
    LAPS_TO_WIN = 3

    COLOR_GRASS = 0x0320
    COLOR_SKY = 0x3D7F
    COLOR_ROAD = 0x4208
    COLOR_LINE = 0xFFE0
    COLOR_CURB = 0xF800
    COLOR_TREE = 0x07E0
    COLOR_TRUNK = 0x9A60
    COLOR_PLAYER = 0x07FF
    COLOR_RIVAL = 0xF800
    COLOR_RIVAL_DARK = 0xFBE0
    COLOR_BLACK = 0x0000

    def __init__(self, view_manager):
        from picoware.engine.camera import CAMERA_THIRD_PERSON, Camera
        from picoware.engine.engine import GameEngine
        from picoware.engine.game import Game
        from picoware.engine.level import Level

        self.view_manager = view_manager
        self.draw = view_manager.draw
        self.level = None
        self.engine = None
        self.background = None
        self.meshes = []
        self.scenery = []
        self.track = []
        self.cars = []
        self.rival_progress = []
        self.rival_lanes = []
        self.rival_speeds = []
        self.player = None
        self.player_progress = self.START_PROGRESS
        self.player_lane = 0.0
        self.player_speed = 0.0
        self.lap = 1
        self.position = 1
        self.finished = False
        self.finish_timer = 0
        self.message = ""
        self.message_timer = 0

        game = Game(
            "Pico GP",
            self.draw.size,
            self.draw,
            view_manager.input_manager,
            self.COLOR_LINE,
            self.COLOR_SKY,
            Camera(
                direction=Vector(0, 1),
                plane=Vector(-0.72, 0),
                height=1.8,
                distance=5.5,
                perspective=CAMERA_THIRD_PERSON,
            ),
        )
        self.level = Level("Sunset Circuit", self.draw.size, game)
        self.level.set_light_direction(-0.35, 1.0, -0.4)
        self.level.set_shadow_color(0)
        self._build_static_scene()
        self._build_cars()
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
            False
        )

    def _quad(self, mesh, first, second, third, fourth, color):
        self._triangle(mesh, first, second, third, color)
        self._triangle(mesh, first, fourth, second, color)

    def _offset_point(self, points, index, offset):
        count = len(points)
        previous_x, previous_y = points[(index - 1) % count]
        next_x, next_y = points[(index + 1) % count]
        tangent_x = next_x - previous_x
        tangent_y = next_y - previous_y
        tangent_length = sqrt(tangent_x * tangent_x + tangent_y * tangent_y)
        normal_x = -tangent_y / tangent_length
        normal_y = tangent_x / tangent_length
        point_x, point_y = points[index]
        return point_x + normal_x * offset, point_y + normal_y * offset

    def _add_loop_strip(self, mesh, points, offset, half_width, height, color):
        count = len(points)
        for index in range(count):
            next_index = (index + 1) % count
            start_left_x, start_left_y = self._offset_point(points, index, offset + half_width)
            start_right_x, start_right_y = self._offset_point(points, index, offset - half_width)
            end_right_x, end_right_y = self._offset_point(points, next_index, offset - half_width)
            end_left_x, end_left_y = self._offset_point(points, next_index, offset + half_width)
            self._quad(
                mesh,
                (start_left_x, height, start_left_y),
                (end_right_x, height, end_right_y),
                (start_right_x, height, start_right_y),
                (end_left_x, height, end_left_y),
                color,
            )

    def _add_box(self, mesh, x, y, z, width, height, depth, color):
        half_width = width * 0.5
        half_height = height * 0.5
        half_depth = depth * 0.5
        bottom = y - half_height
        top = y + half_height
        front = z + half_depth
        back = z - half_depth
        self._triangle(mesh, (x - half_width, bottom, front), (x + half_width, bottom, front), (x + half_width, top, front), color)
        self._triangle(mesh, (x - half_width, bottom, front), (x + half_width, top, front), (x - half_width, top, front), color)
        self._triangle(mesh, (x + half_width, bottom, back), (x - half_width, bottom, back), (x - half_width, top, back), color)
        self._triangle(mesh, (x + half_width, bottom, back), (x - half_width, top, back), (x + half_width, top, back), color)
        self._triangle(mesh, (x + half_width, bottom, front), (x + half_width, bottom, back), (x + half_width, top, back), color)
        self._triangle(mesh, (x + half_width, bottom, front), (x + half_width, top, back), (x + half_width, top, front), color)
        self._triangle(mesh, (x - half_width, bottom, back), (x - half_width, bottom, front), (x - half_width, top, front), color)
        self._triangle(mesh, (x - half_width, bottom, back), (x - half_width, top, front), (x - half_width, top, back), color)

    def _add_tree_geometry(self, mesh):
        tree_specs = (
            (0.10, -4.8, 3.3),
            (0.19, 4.7, 3.8),
            (0.31, -5.2, 3.0),
            (0.43, 4.9, 3.6),
            (0.56, -4.9, 3.8),
            (0.68, 4.8, 3.2),
            (0.80, -5.1, 3.5),
            (0.92, 4.6, 3.0),
        )
        for progress, lane, height in tree_specs:
            x, y, _direction_x, _direction_y = self._sample_track(progress, lane)
            trunk_height = height * 0.4
            crown_height = height * 0.6
            self._add_box(
                mesh,
                x,
                trunk_height * 0.5,
                y,
                height * 0.18,
                trunk_height,
                height * 0.18,
                self.COLOR_TRUNK,
            )
            self._add_box(
                mesh,
                x,
                trunk_height + crown_height * 0.5,
                y,
                height * 0.65,
                crown_height,
                height * 0.65,
                self.COLOR_TREE,
            )
            self.scenery.append((x, y, height))

    def _build_static_scene(self):
        from picoware.engine.entity import ENTITY_TYPE_ICON, SPRITE_3D_NONE
        from picoware.engine.sprite3d import Sprite3D

        self.background = Entity(
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
        self.background.is_visible = True
        self.level.entity_add(self.background)

        mesh = Sprite3D()
        self._triangle(
            mesh,
            (-100, 0, -100),
            (100, 0, 100),
            (100, 0, -100),
            self.COLOR_GRASS,
        )
        self._triangle(
            mesh,
            (-100, 0, -100),
            (-100, 0, 100),
            (100, 0, 100),
            self.COLOR_GRASS,
        )

        points = []
        for index in range(self.TRACK_SEGMENTS + 1):
            angle = 2.0 * pi * index / self.TRACK_SEGMENTS
            points.append(
                (
                    self.TRACK_RADIUS_X * cos(angle),
                    self.TRACK_RADIUS_Y * sin(angle),
                )
            )

        for index in range(self.TRACK_SEGMENTS):
            x1, y1 = points[index]
            x2, y2 = points[index + 1]
            dx = x2 - x1
            dy = y2 - y1
            length = sqrt(dx * dx + dy * dy)
            self.track.append((x1, y1, x2, y2, length))

        self._add_tree_geometry(mesh)
        loop_points = points[:-1]
        self._add_loop_strip(mesh, loop_points, 0, self.TRACK_WIDTH * 0.5, 0.04, self.COLOR_ROAD)
        self._add_loop_strip(mesh, loop_points, 0, 0.07, 0.08, self.COLOR_LINE)
        curb_offset = self.TRACK_WIDTH * 0.5 - 0.18
        self._add_loop_strip(mesh, loop_points, -curb_offset, 0.11, 0.09, self.COLOR_CURB)
        self._add_loop_strip(mesh, loop_points, curb_offset, 0.11, 0.09, self.COLOR_CURB)
        self._quad(
            mesh,
            (self.TRACK_RADIUS_X - self.TRACK_WIDTH * 0.5, 0.12, -0.12),
            (self.TRACK_RADIUS_X + self.TRACK_WIDTH * 0.5, 0.12, 0.12),
            (self.TRACK_RADIUS_X + self.TRACK_WIDTH * 0.5, 0.12, -0.12),
            (self.TRACK_RADIUS_X - self.TRACK_WIDTH * 0.5, 0.12, 0.12),
            self.COLOR_LINE,
        )

        mesh.set_wireframe(False)
        self._mesh_entity("Circuit", Vector(0, 0), Vector(200, 200), mesh)

    def _car_mesh(self, color):
        from picoware.engine.sprite3d import Sprite3D

        mesh = Sprite3D()
        mesh.create_cube(0, 0.42, 0, 1.15, 0.42, 2.1, color)
        mesh.create_cube(0, 0.72, 0.18, 0.78, 0.28, 0.78, self.COLOR_LINE)
        mesh.set_wireframe(False)
        return mesh

    def _build_cars(self):
        rival_colors = (0xF800, 0xFD20, 0x001F)
        starts = (0.055, 0.095, 0.135)
        for index in range(3):
            rival = self._mesh_entity(
                "Rival %d" % (index + 1),
                Vector(0, 0),
                Vector(1.0, 1.8),
                self._car_mesh(rival_colors[index]),
                _rival_update,
                None,
                _car_collision,
            )
            rival.is_player = False
            self.cars.append(rival)
            self.rival_progress.append(starts[index])
            self.rival_lanes.append((-1.25, 1.1, -0.8)[index])
            self.rival_speeds.append((0.17, 0.185, 0.2)[index])
            self._place_car(rival, starts[index], self.rival_lanes[index])

        self.player = self._mesh_entity(
            "Player",
            Vector(0, 0),
            Vector(1.15, 2.1),
            self._car_mesh(self.COLOR_PLAYER),
            _player_update,
            _player_render,
            _car_collision,
        )
        self.player.is_player = True
        self.player.direction = Vector(0, 1)
        self.player.plane = Vector(-0.72, 0)
        self._place_car(self.player, self.player_progress, self.player_lane)

    def _sample_track(self, progress, lane):
        angle = 2.0 * pi * (progress % 1.0)
        x = self.TRACK_RADIUS_X * cos(angle)
        y = self.TRACK_RADIUS_Y * sin(angle)
        tangent_x = -self.TRACK_RADIUS_X * sin(angle)
        tangent_y = self.TRACK_RADIUS_Y * cos(angle)
        tangent_length = sqrt(tangent_x * tangent_x + tangent_y * tangent_y)
        tangent_x /= tangent_length
        tangent_y /= tangent_length
        normal_x = -tangent_y
        normal_y = tangent_x
        return (
            x + normal_x * lane,
            y + normal_y * lane,
            tangent_x,
            tangent_y,
        )

    def _place_car(self, car, progress, lane):
        x, y, direction_x, direction_y = self._sample_track(progress, lane)
        car.position = Vector(x, y)
        car.direction = Vector(direction_x, direction_y)
        car.set_3d_sprite_rotation(atan2(direction_y, direction_x) - pi * 0.5)

    def update_player(self, car, game):
        from picoware.system.buttons import BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP

        button = game.input
        if self.finished:
            self._place_car(car, self.player_progress, self.player_lane)
            return

        if button == BUTTON_UP:
            self.player_speed += self.ACCELERATION
        elif button == BUTTON_DOWN:
            self.player_speed -= self.BRAKING
        else:
            self.player_speed -= self.FRICTION

        if button == BUTTON_LEFT:
            self.player_lane -= self.STEER_STEP
        elif button == BUTTON_RIGHT:
            self.player_lane += self.STEER_STEP

        self.player_speed = max(0.0, min(self.MAX_SPEED, self.player_speed))
        self.player_lane = max(-1.85, min(1.85, self.player_lane))
        old_progress = self.player_progress
        self.player_progress = (self.player_progress + self.player_speed * 0.006) % 1.0
        self._place_car(car, self.player_progress, self.player_lane)

        if self.player_progress < old_progress and self.player_speed > 0:
            self.lap += 1
            if self.lap > self.LAPS_TO_WIN:
                self.finished = True
                self.finish_timer = 180
            else:
                self.message = "LAP %d" % self.lap
                self.message_timer = 90

        self._update_position()

    def update_rival(self, car, _game):
        rival_index = int(car.name[-1]) - 1
        progress = self.rival_progress[rival_index]
        progress = (progress + self.rival_speeds[rival_index] * 0.006) % 1.0
        self.rival_progress[rival_index] = progress
        self._place_car(car, progress, self.rival_lanes[rival_index])

    def _is_car(self, entity):
        return entity is not None and (
            entity.name == "Player" or entity.name.startswith("Rival")
        )

    def _tight_car_contact(self, car, other):
        delta_x = other.position.x - car.position.x
        delta_y = other.position.y - car.position.y
        forward = delta_x * car.direction.x + delta_y * car.direction.y
        lateral = abs(-delta_x * car.direction.y + delta_y * car.direction.x)
        facing = car.direction.x * other.direction.x + car.direction.y * other.direction.y

        if lateral > self.CAR_HITBOX_LANE:
            return None
        if abs(forward) > self.CAR_HITBOX_LENGTH:
            return None
        if facing < 0.5:
            return None
        return forward

    def _car_speed(self, car):
        if car.name == "Player":
            return self.player_speed
        rival_index = int(car.name[-1]) - 1
        return self.rival_speeds[rival_index]

    def _push_car_forward(self, car, impact_speed):
        if car.name == "Player":
            self.player_progress = (self.player_progress + self.CAR_PUSH_PROGRESS) % 1.0
            self.player_speed = min(
                self.MAX_SPEED,
                max(self.player_speed, impact_speed) + self.CAR_PUSH_SPEED,
            )
            self._place_car(car, self.player_progress, self.player_lane)
            return

        rival_index = int(car.name[-1]) - 1
        self.rival_progress[rival_index] = (
            self.rival_progress[rival_index] + self.CAR_PUSH_PROGRESS
        ) % 1.0
        self.rival_speeds[rival_index] = min(
            self.MAX_SPEED,
            max(self.rival_speeds[rival_index], impact_speed) + self.CAR_PUSH_SPEED,
        )
        self._place_car(car, self.rival_progress[rival_index], self.rival_lanes[rival_index])

    def handle_collision(self, car, other, _game):
        if not self._is_car(car) or not self._is_car(other) or car.name == other.name:
            return

        forward = self._tight_car_contact(car, other)
        if forward is None or forward <= 0:
            return

        self._push_car_forward(other, self._car_speed(car))
        if car.name == "Player":
            self.player_speed *= 0.35
        else:
            rival_index = int(car.name[-1]) - 1
            self.rival_speeds[rival_index] *= 0.35

    def _update_position(self):
        ahead = 0
        for progress in self.rival_progress:
            distance = (progress - self.player_progress) % 1.0
            if distance > 0.0:
                ahead += 1
        self.position = ahead + 1

    def draw_background(self, draw):
        width = int(draw.size.x)
        height = int(draw.size.y)
        half_height = height // 2
        draw._fill_rectangle(0, 0, width, half_height, self.COLOR_SKY)
        draw._fill_rectangle(0, half_height, width, height - half_height, self.COLOR_GRASS)

    def draw_hud(self, draw=None):
        if self.engine is None:
            return
        draw = self.draw if draw is None else draw
        width = draw.size.x
        draw._fill_rectangle(0, 0, width, draw.scale_y(18), self.COLOR_BLACK)
        draw._text(
            draw.scale_x(4), 
            draw.scale_y(3),
            "LAP %d/%d" % (min(self.lap, self.LAPS_TO_WIN), self.LAPS_TO_WIN),
            self.COLOR_LINE
        )
        draw._text(
            width // 2 - draw.scale_x(12), 
            draw.scale_y(3),
            "%02d MPH" % int(self.player_speed * 280),
            self.COLOR_LINE,
        )
        draw._text(
            width - draw.scale_x(42), draw.scale_y(3),
            "P%d/4" % self.position,
            self.COLOR_LINE,
        )
        if self.message_timer > 0:
            alert_width = draw.scale_x(58)
            alert_height = draw.scale_y(18)
            alert_x = width // 2 - alert_width // 2
            alert_y = int(draw.size.y) // 2 - alert_height // 2
            draw._fill_rectangle(
                alert_x, alert_y, alert_width, alert_height, self.COLOR_BLACK
            )
            draw._text(
                width // 2 - draw.scale_x(18),
                alert_y + draw.scale_y(5),
                self.message,
                self.COLOR_LINE,
            )
            self.message_timer -= 1
        if self.finished:
            draw._fill_rectangle(
                width // 2 - draw.scale_x(38), int(draw.size.y) // 2 - draw.scale_y(10),
                draw.scale_x(76), draw.scale_y(20),
                self.COLOR_BLACK,
            )
            draw._text(
                width // 2 - draw.scale_x(30), int(draw.size.y) // 2 - draw.scale_y(4),
                "FINISH!",
                self.COLOR_LINE,
            )


    def run(self):
        if self.engine is not None:
            self.engine.run_async(False)

    def stop(self):
        if self.engine is not None:
            self.engine.stop()
            self.engine = None
        self.meshes = []


def start(view_manager) -> bool:
    """Start the 3D race."""
    global _race

    _race = _Race(view_manager)
    return _race.engine is not None


def run(view_manager) -> None:
    """Run one race frame."""
    from picoware.system.buttons import BUTTON_BACK

    if _race is None:
        view_manager.back()
        return

    button = view_manager.input_manager.button
    if button == BUTTON_BACK:
        view_manager.input_manager.reset()
        view_manager.back()
        return

    _race.run()


def stop(_view_manager) -> None:
    """Stop the race and release engine resources."""
    from gc import collect

    global _race

    if _race is not None:
        _race.stop()
        _race = None
    collect()