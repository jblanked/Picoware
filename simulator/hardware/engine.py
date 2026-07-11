try:
    from utime import ticks_ms, ticks_diff, sleep_ms
except ImportError:
    from time import sleep

    def ticks_ms():
        import time

        return int(time.time() * 1000)

    def ticks_diff(a, b):
        return a - b

    def sleep_ms(ms):
        sleep(ms / 1000)

try:
    from math import cos, sin, sqrt
except ImportError:
    cos = sin = None

    def sqrt(value):
        return value ** 0.5


class _Native:
    def __init__(self, *args, **kwargs):
        object.__setattr__(self, "_args", args)
        object.__setattr__(self, "_kwargs", kwargs)
        object.__setattr__(self, "_fields", {})

    def __getattr__(self, name):
        fields = self.__dict__.get("_fields", {})
        if name in fields:
            return fields[name]
        if name.startswith("set_"):
            field = name[4:]

            def setter(value):
                fields[field] = value
                object.__setattr__(self, field, value)
                return None

            return setter
        if name.startswith("get_"):
            field = name[4:]
            return lambda: fields.get(field)
        if name.startswith("update_"):
            field = name[7:]

            def updater(value=None, *args):
                fields[field] = value
                object.__setattr__(self, field, value)
                return None

            return updater
        raise AttributeError(name)

    def __setattr__(self, name, value):
        fields = self.__dict__.get("_fields", None)
        if fields is not None:
            fields[name] = value
        object.__setattr__(self, name, value)


class Engine(_Native):
    def __init__(self, game=None, fps=30):
        super().__init__(game, fps)
        self.game = game
        self.fps = fps
        self.is_running = True
        fields = self.__dict__.get("_fields", {})
        fields["input"] = -1
        object.__setattr__(self, "input", -1)
        frame_ms = 0
        if fps and fps > 0:
            frame_ms = max(1, int(1000 / fps))
        fields["frame_ms"] = frame_ms
        fields["last_frame_ms"] = ticks_ms()
        object.__setattr__(self, "frame_ms", frame_ms)
        object.__setattr__(self, "last_frame_ms", ticks_ms())
        fields["trace_frames"] = 0
        object.__setattr__(self, "trace_frames", 0)

    def update_game_input(self, value):
        fields = self.__dict__.get("_fields", {})
        fields["input"] = value
        object.__setattr__(self, "input", value)
        if self.game:
            self.game.input = value
        return None

    def run(self):
        return self.run_async(False)

    def run_async(self, threaded=True):
        if not self.is_running:
            return False
        self._pace_frame()
        if self.game:
            self._trace_frame()
            try:
                self.game._update()
            except Exception:
                pass
            self._update_entities()
            self._collide_entities()
            self.draw()
        return True

    def _trace_frame(self):
        try:
            import sim_runtime

            if not getattr(sim_runtime, "trace_views", False):
                return
        except Exception:
            return
        count = getattr(self, "trace_frames", 0)
        if count >= 5:
            return
        game = self.game
        level = getattr(game, "current_level", None) if game else None
        entity_count = getattr(level, "entity_count", 0) if level else 0
        print("[sim:engine] frame", count, "game=", getattr(game, "name", ""), "level=", getattr(level, "name", None), "entities=", entity_count)
        count += 1
        fields = self.__dict__.get("_fields", {})
        fields["trace_frames"] = count
        object.__setattr__(self, "trace_frames", count)

    def _pace_frame(self):
        frame_ms = getattr(self, "frame_ms", 0)
        if frame_ms <= 0:
            return
        now = ticks_ms()
        elapsed = ticks_diff(now, getattr(self, "last_frame_ms", now))
        if elapsed < frame_ms:
            sleep_ms(frame_ms - elapsed)
            now = ticks_ms()
        fields = self.__dict__.get("_fields", {})
        fields["last_frame_ms"] = now
        object.__setattr__(self, "last_frame_ms", now)

    def _update_entities(self):
        game = self.game
        level = getattr(game, "current_level", None) if game else None
        if level is None:
            return
        for entity in list(getattr(level, "entities", [])):
            if not getattr(entity, "is_active", True):
                continue
            callback = getattr(entity, "update_callback", None)
            if callback is None:
                continue
            try:
                callback(entity, game)
            except TypeError:
                try:
                    callback(game)
                except TypeError:
                    callback()
            except Exception as exc:
                print("[sim:engine] entity update failed:", exc)

    def _collide_entities(self):
        game = self.game
        level = getattr(game, "current_level", None) if game else None
        if level is None:
            return
        entities = list(getattr(level, "entities", []))
        for i in range(len(entities)):
            a = entities[i]
            if not getattr(a, "is_active", True):
                continue
            cb = getattr(a, "collision_callback", None)
            if cb is None:
                continue
            for j in range(i + 1, len(entities)):
                b = entities[j]
                if getattr(b, "is_active", True) and self._intersects(a, b):
                    try:
                        cb(a, b, game)
                    except TypeError:
                        try:
                            cb(b, game)
                        except TypeError:
                            cb(b)

    def _intersects(self, a, b):
        ap = getattr(a, "position", None)
        bp = getattr(b, "position", None)
        az = getattr(a, "size", None)
        bz = getattr(b, "size", None)
        if ap is None or bp is None or az is None or bz is None:
            return False
        try:
            return (
                ap.x < bp.x + bz.x
                and ap.x + az.x > bp.x
                and ap.y < bp.y + bz.y
                and ap.y + az.y > bp.y
            )
        except Exception:
            return False

    def draw(self, *args, **kwargs):
        game = self.game
        draw = getattr(game, "draw", None) if game else None
        if draw is None:
            return None
        try:
            level = getattr(game, "current_level", None)
            if level:
                self._render_entities(draw, game, level)
            else:
                bg = getattr(game, "background_color", 0)
                fg = getattr(game, "foreground_color", 0xFFFF)
                draw.clear(color=bg)
                draw._text(4, 4, getattr(game, "name", "Engine"), fg)
            draw.swap()
        except Exception as exc:
            print("[sim:engine] draw failed:", exc)
        return None

    def _render_entities(self, draw, game, level):
        bg = getattr(game, "background_color", 0)
        if getattr(level, "clear_allowed", True):
            try:
                draw.clear(color=bg)
            except TypeError:
                draw.clear()
        self._render_3d_scene(draw, game, level)
        for entity in list(getattr(level, "entities", [])):
            if not getattr(entity, "is_visible", True):
                continue
            if self._is_3d_entity(entity):
                continue
            callback = getattr(entity, "render_callback", None)
            if callback is not None:
                try:
                    callback(entity, draw, game)
                except TypeError:
                    try:
                        callback(draw, game)
                    except TypeError:
                        callback(draw)
                except Exception as exc:
                    print("[sim:engine] entity render failed:", exc)
                continue
            self._render_entity_fallback(draw, entity, getattr(game, "foreground_color", 0xFFFF))

    def _render_entity_fallback(self, draw, entity, color):
        pos = getattr(entity, "position", None)
        size = getattr(entity, "size", None)
        if pos is None or size is None:
            return
        sprite = getattr(entity, "sprite", None)
        try:
            data = getattr(sprite, "data", None) if sprite is not None else None
            if data:
                draw.image_bytearray(pos, size, data)
            else:
                draw.fill_rectangle(pos, size, color)
        except Exception:
            pass

    def _is_3d_entity(self, entity):
        return bool(
            getattr(entity, "sprite_3d", None) is not None
            or getattr(entity, "sprite_3d_type", 0)
            or getattr(entity, "sprite_3d_color", 0)
        )

    def _render_3d_scene(self, draw, game, level):
        items = []
        for entity in list(getattr(level, "entities", [])):
            if not getattr(entity, "is_visible", True):
                continue
            if not getattr(entity, "is_active", True):
                continue
            if not self._is_3d_entity(entity):
                continue
            item = self._project_entity(draw, game, entity)
            if item is not None:
                items.append(item)
        items.sort(key=lambda item: item[0], reverse=True)
        for item in items:
            _, kind, payload = item
            try:
                if kind == "wall":
                    self._draw_wall(draw, payload)
                else:
                    self._draw_billboard(draw, payload)
            except Exception as exc:
                print("[sim:engine] 3d render failed:", exc)

    def _camera_basis(self, game):
        cam = getattr(game, "camera", None)
        pos = getattr(cam, "position", None)
        direction = getattr(cam, "direction", None)
        if pos is None:
            pos = self._vec(0, 0, 0)
        if direction is None:
            direction = self._vec(1, 0, 0)
        dx = float(getattr(direction, "x", 1) or 0)
        dy = float(getattr(direction, "y", 0) or 0)
        length = sqrt(dx * dx + dy * dy)
        if length <= 0.0001:
            dx, dy, length = 1.0, 0.0, 1.0
        dx /= length
        dy /= length
        return pos, dx, dy, -dy, dx

    def _project_point(self, draw, game, point):
        cam_pos, dir_x, dir_y, right_x, right_y = self._camera_basis(game)
        px = float(getattr(point, "x", 0) or 0) - float(getattr(cam_pos, "x", 0) or 0)
        py = float(getattr(point, "y", 0) or 0) - float(getattr(cam_pos, "y", 0) or 0)
        depth = px * dir_x + py * dir_y
        side = px * right_x + py * right_y
        if depth <= 0.05:
            return None
        width = int(getattr(draw, "width", getattr(getattr(draw, "size", None), "x", 320)))
        height = int(getattr(draw, "height", getattr(getattr(draw, "size", None), "y", 320)))
        focal = width * 0.72
        sx = int(width // 2 + (side / depth) * focal)
        return sx, depth, width, height

    def _project_entity(self, draw, game, entity):
        sprite3d = getattr(entity, "sprite_3d", None)
        pos = getattr(sprite3d, "position", None) if sprite3d is not None else getattr(entity, "position", None)
        if pos is None:
            return None
        projected = self._project_point(draw, game, pos)
        if projected is None:
            return None
        sx, depth, width, height = projected
        color = getattr(entity, "sprite_3d_color", 0)
        if not color and sprite3d is not None:
            color = getattr(sprite3d, "color", 0x7BEF)
        if not color:
            color = 0x7BEF
        scale = float(getattr(sprite3d, "scale_factor", getattr(entity, "sprite_scale", 1.0)) or 1.0) if sprite3d is not None else 1.0
        wall_length = float(getattr(sprite3d, "wall_length", 0) or 0) if sprite3d is not None else 0
        wall_height = float(getattr(sprite3d, "wall_height", 0) or 0) if sprite3d is not None else 0
        if wall_length > 0:
            rotation = float(getattr(sprite3d, "rotation_y", 0) or 0)
            half = wall_length * 0.5
            if cos is not None:
                ax = float(getattr(pos, "x", 0)) - cos(rotation) * half
                ay = float(getattr(pos, "y", 0)) - sin(rotation) * half
                bx = float(getattr(pos, "x", 0)) + cos(rotation) * half
                by = float(getattr(pos, "y", 0)) + sin(rotation) * half
            else:
                ax = float(getattr(pos, "x", 0)) - half
                ay = float(getattr(pos, "y", 0))
                bx = float(getattr(pos, "x", 0)) + half
                by = float(getattr(pos, "y", 0))
            pa = self._project_point(draw, game, self._vec(ax, ay, 0))
            pb = self._project_point(draw, game, self._vec(bx, by, 0))
            if pa is None or pb is None:
                return None
            avg_depth = (pa[1] + pb[1]) * 0.5
            h = max(6, int((wall_height or 2.0) * 95 / max(0.15, avg_depth)))
            return avg_depth, "wall", (pa[0], pb[0], height // 2 - h // 2, h, color)
        entity_size = getattr(entity, "size", None)
        base_h = float(getattr(entity_size, "y", 1.5) or 1.5)
        base_w = float(getattr(entity_size, "x", 1.0) or 1.0)
        h = max(4, int(base_h * scale * 90 / max(0.15, depth)))
        w = max(3, int(base_w * scale * 70 / max(0.15, depth)))
        return depth, "billboard", (sx - w // 2, height // 2 - h // 2, w, h, color)

    def _draw_wall(self, draw, payload):
        x1, x2, y, h, color = payload
        left = min(x1, x2)
        right = max(x1, x2)
        w = max(2, right - left)
        self._fill_rect(draw, left, y, w, h, color)
        self._rect(draw, left, y, w, h, 0xFFFF)

    def _draw_billboard(self, draw, payload):
        x, y, w, h, color = payload
        self._fill_rect(draw, x, y, w, h, color)
        self._rect(draw, x, y, w, h, 0xFFFF)

    def _fill_rect(self, draw, x, y, w, h, color):
        if hasattr(draw, "_fill_rectangle"):
            draw._fill_rectangle(int(x), int(y), int(w), int(h), color)
        else:
            from picoware.system.vector import Vector

            draw.fill_rectangle(Vector(int(x), int(y)), Vector(int(w), int(h)), color)

    def _rect(self, draw, x, y, w, h, color):
        if hasattr(draw, "_rectangle"):
            draw._rectangle(int(x), int(y), int(w), int(h), color)

    def _vec(self, x=0, y=0, z=0):
        class V:
            pass

        v = V()
        v.x = x
        v.y = y
        v.z = z
        return v

    def stop(self):
        if self.game and getattr(self.game, "stop_callback", None):
            try:
                self.game.stop_callback(self.game)
            except TypeError:
                self.game.stop_callback()
        self.is_running = False
        return None


class Entity(_Native):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        names = (
            "name",
            "type",
            "position",
            "size",
            "sprite",
            "sprite_left",
            "sprite_right",
            "start_callback",
            "stop_callback",
            "update_callback",
            "render_callback",
            "collision_callback",
            "is_8bit",
            "sprite_3d_type",
            "sprite_3d_color",
        )
        defaults = {
            "name": "Entity",
            "type": 0,
            "position": None,
            "size": None,
            "sprite": None,
            "sprite_left": None,
            "sprite_right": None,
            "start_callback": None,
            "stop_callback": None,
            "update_callback": None,
            "render_callback": None,
            "collision_callback": None,
            "is_8bit": True,
            "sprite_3d_type": 0,
            "sprite_3d_color": 0,
        }
        for i, name in enumerate(names):
            value = args[i] if i < len(args) else defaults[name]
            setattr(self, name, value)
        self.old_position = getattr(self, "position", None)
        self.direction = kwargs.get("direction", None)
        self.plane = kwargs.get("plane", None)
        self.state = kwargs.get("state", 0)
        self.start_position = kwargs.get("start_position", getattr(self, "position", None))
        self.end_position = kwargs.get("end_position", getattr(self, "position", None))
        self.move_timer = kwargs.get("move_timer", 0)
        self.elapsed_move_timer = kwargs.get("elapsed_move_timer", 0)
        self.radius = kwargs.get("radius", 0)
        self.speed = kwargs.get("speed", 0)
        self.attack_timer = kwargs.get("attack_timer", 0)
        self.elapsed_attack_timer = kwargs.get("elapsed_attack_timer", 0)
        self.strength = kwargs.get("strength", 0)
        self.health = kwargs.get("health", 1)
        self.max_health = kwargs.get("max_health", self.health)
        self.level = kwargs.get("level", None)
        self.xp = kwargs.get("xp", 0)
        self.health_regen = kwargs.get("health_regen", 0)
        self.elapsed_health_regen = kwargs.get("elapsed_health_regen", 0)
        self.is_active = True
        self.is_visible = True
        self.is_player = getattr(self, "type", 0) == 0
        object.__setattr__(self, "sprite_3d", None)
        object.__setattr__(self, "sprite_scale", 1.0)
        object.__setattr__(self, "sprite_rotation", 0.0)
        if self.start_callback:
            try:
                self.start_callback(self)
            except TypeError:
                self.start_callback()

    def __setattr__(self, name, value):
        if name == "sprite_3d":
            self.set_sprite3d(value)
        elif name == "sprite_3d_type":
            self.set_sprite3d_type(value)
        elif name == "sprite_3d_color":
            self.set_sprite3d_color(value)
        else:
            super().__setattr__(name, value)

    def has_3d_sprite(self):
        return getattr(self, "sprite_3d", None) is not None

    def set_sprite3d(self, value):
        object.__setattr__(self, "sprite_3d", value)
        self.__dict__.get("_fields", {})["sprite_3d"] = value
        if value is not None and getattr(value, "position", None) is None:
            value.position = getattr(self, "position", None)
        return None

    def set_sprite3d_type(self, value):
        object.__setattr__(self, "sprite_3d_type", value)
        self.__dict__.get("_fields", {})["sprite_3d_type"] = value
        return None

    def set_sprite3d_color(self, value):
        object.__setattr__(self, "sprite_3d_color", value)
        self.__dict__.get("_fields", {})["sprite_3d_color"] = value
        sprite = getattr(self, "sprite_3d", None)
        if sprite is not None:
            sprite.color = value
        return None

    def create_3d_sprite(self, sprite_3d_type=0, height=1.0, width=1.0, rotation=0.0, color=0x7BEF, image=None):
        sprite = Sprite3D(getattr(self, "position", None), rotation, 1.0, True)
        sprite.sprite_type = sprite_3d_type
        sprite.height = height
        sprite.width = width
        sprite.color = color
        sprite.image = image
        if sprite_3d_type:
            sprite.wall_length = float(width or 1.0)
            sprite.wall_height = float(height or 1.0)
        self.set_sprite3d(sprite)
        self.set_sprite3d_type(sprite_3d_type)
        self.set_sprite3d_color(color)
        return True

    def set_3d_sprite_rotation(self, value):
        object.__setattr__(self, "sprite_rotation", value)
        self.__dict__.get("_fields", {})["sprite_rotation"] = value
        sprite = getattr(self, "sprite_3d", None)
        if sprite is not None:
            sprite.rotation_y = value
        return None

    def set_3d_sprite_scale(self, value):
        object.__setattr__(self, "sprite_scale", value)
        self.__dict__.get("_fields", {})["sprite_scale"] = value
        sprite = getattr(self, "sprite_3d", None)
        if sprite is not None:
            sprite.scale_factor = value
            sprite.scale = value
        return None

    def update_3d_sprite_position(self):
        sprite = getattr(self, "sprite_3d", None)
        if sprite is not None:
            sprite.position = getattr(self, "position", None)
        return None

    def start(self, game=None):
        if self.start_callback:
            self._call_callback(self.start_callback, self, game)
        self.is_active = True
        return True

    def stop(self, game=None):
        if self.stop_callback:
            self._call_callback(self.stop_callback, self, game)
        self.is_active = False
        return True

    def update(self, game=None):
        if self.update_callback:
            self._call_callback(self.update_callback, self, game)
        self.update_3d_sprite_position()
        return True

    def render(self, draw=None, game=None):
        if self.render_callback:
            self._call_callback(self.render_callback, self, draw, game)
        return True

    def collision(self, other, game=None):
        if self.collision_callback:
            self._call_callback(self.collision_callback, self, other, game)
        return True

    def _call_callback(self, callback, *args):
        for count in range(len(args), -1, -1):
            try:
                return callback(*args[:count])
            except TypeError:
                continue
        return None


class Game(_Native):
    def __init__(self, name="", size=None, foreground_color=0xFFFF, background_color=0, camera=None, start=None, stop=None, update=None, draw=None):
        super().__init__(name, size, foreground_color, background_color, camera, start, stop, update, draw)
        self.name = name
        self.size = size
        self.foreground_color = foreground_color
        self.background_color = background_color
        self.camera = camera
        self.start_callback = start
        self.stop_callback = stop
        self.update_callback = update
        self.draw = draw
        self.levels = []
        self.current_level = None
        self.is_active = True
        self.input = -1

    def _update(self):
        if self.update_callback:
            self.update_callback()
        return None

    def start(self):
        if self.start_callback:
            try:
                self.start_callback(self)
            except TypeError:
                self.start_callback()
        self.is_active = True
        return True

    def stop(self):
        if self.stop_callback:
            try:
                self.stop_callback(self)
            except TypeError:
                self.stop_callback()
        self.is_active = False
        return True

    def level_add(self, level):
        self.levels.append(level)
        if self.current_level is None:
            self.current_level = level
        return True

    def level_exists(self, name):
        for level in self.levels:
            if getattr(level, "name", None) == name:
                return True
        return False

    def level_switch(self, target):
        if isinstance(target, int):
            if 0 <= target < len(self.levels):
                self.current_level = self.levels[target]
                return True
            return False
        for level in self.levels:
            if getattr(level, "name", None) == target:
                self.current_level = level
                return True
        return False

    def level_remove(self, level):
        try:
            self.levels.remove(level)
        except ValueError:
            return False
        if self.current_level is level:
            self.current_level = self.levels[0] if self.levels else None
        return True

    def clamp(self, value, lower, upper):
        return max(lower, min(upper, value))

    def update(self):
        self._update()
        return True

    def render(self):
        if self.current_level is not None:
            self.current_level.render(0, self.camera)
        return True


class Level(_Native):
    def __init__(self, name="", size=None, game=None, start=None, stop=None):
        super().__init__(name, size, game, start, stop)
        self.name = name
        self.size = size
        self.game = game
        self.start_callback = start
        self.stop_callback = stop
        self.entities = []
        self.clear_allowed = True
        self.is_active = True

    @property
    def entity_count(self):
        return len(self.entities)

    def entity_add(self, entity):
        self.entities.append(entity)
        try:
            entity.level = self
        except Exception:
            pass
        return True

    def get_entity(self, index):
        if 0 <= int(index) < len(self.entities):
            return self.entities[int(index)]
        return None

    def entity_remove(self, entity):
        try:
            self.entities.remove(entity)
            return True
        except ValueError:
            return False

    def clear(self):
        for entity in list(self.entities):
            try:
                entity.stop(getattr(self, "game", None))
            except Exception:
                pass
        self.entities = []
        return True

    def is_collision(self, entity, other):
        return Engine(None, 0)._intersects(entity, other)

    def has_collided(self, entity):
        return bool(self.collision_list(entity))

    def collision_list(self, entity):
        out = []
        for other in list(self.entities):
            if other is entity or not getattr(other, "is_active", True):
                continue
            if self.is_collision(entity, other):
                out.append(other)
        return out

    def start(self):
        if self.start_callback:
            self._call_callback(self.start_callback, self)
        self.is_active = True
        for entity in list(self.entities):
            try:
                entity.start(getattr(self, "game", None))
            except Exception:
                pass
        return True

    def stop(self):
        if self.stop_callback:
            self._call_callback(self.stop_callback, self)
        self.is_active = False
        for entity in list(self.entities):
            try:
                entity.stop(getattr(self, "game", None))
            except Exception:
                pass
        return True

    def update(self):
        game = getattr(self, "game", None)
        for entity in list(self.entities):
            if getattr(entity, "is_active", True):
                entity.update(game)
        for entity in list(self.entities):
            for other in self.collision_list(entity):
                entity.collision(other, game)
        return True

    def render(self, perspective=0, camera_params=None):
        game = getattr(self, "game", None)
        draw = getattr(game, "draw", None) if game is not None else None
        if draw is None:
            return False
        Engine(game, 0).draw()
        return True

    def _call_callback(self, callback, *args):
        for count in range(len(args), -1, -1):
            try:
                return callback(*args[:count])
            except TypeError:
                continue
        return None


class Camera(_Native):
    def __init__(self, position=None, direction=None, plane=None, height=1.0, distance=2.0, perspective=0):
        super().__init__(position, direction, plane, height, distance, perspective)
        self.position = position
        self.direction = direction
        self.plane = plane
        self.height = height
        self.distance = distance
        self.perspective = perspective


class Image(_Native):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.size = args[0] if args else None
        self.data = b""
        self.path = ""
        self.is_8bit = True

    def from_path(self, path):
        self.path = path
        try:
            import sd_mp

            self.data = sd_mp.read(path)
            return True
        except Exception:
            return False

    def from_byte_array(self, data, size, is_8bit=True):
        self.data = bytes(data)
        self.size = size
        self.is_8bit = is_8bit
        return True

    def from_string(self, image_str):
        self.data = str(image_str).encode()
        return True


class Sprite3D(_Native):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if len(args) >= 6:
            self.sprite_type = args[0]
            self.position = args[1]
            self.height = args[2]
            self.width = args[3]
            self.rotation_y = args[4]
            self.color = args[5]
            self.image = args[6] if len(args) > 6 else None
            self.scale_factor = kwargs.get("scale_factor", 1.0)
            self.active = True
        else:
            self.sprite_type = kwargs.get("sprite_type", 0)
            self.position = args[0] if len(args) > 0 else kwargs.get("position", None)
            self.rotation_y = args[1] if len(args) > 1 else kwargs.get("rotation_y", 0.0)
            self.scale_factor = args[2] if len(args) > 2 else kwargs.get("scale_factor", 1.0)
            self.active = args[3] if len(args) > 3 else kwargs.get("active", True)
            self.height = kwargs.get("height", 1.0)
            self.width = kwargs.get("width", 1.0)
            self.color = kwargs.get("color", 0x7BEF)
            self.image = kwargs.get("image", None)
        self.scale = self.scale_factor
        self.triangles = []
        self.wall_length = 0.0
        self.wall_height = 0.0
        self.wall_depth = 0.0
        self.is_visible = True

    def set_scale(self, value):
        object.__setattr__(self, "scale_factor", value)
        object.__setattr__(self, "scale", value)
        fields = self.__dict__.get("_fields", {})
        fields["scale_factor"] = value
        fields["scale"] = value
        return None

    def create_wall(self, x=0, y=0, z=0, length=1.0, height=1.0, depth=0.2, color=0x7BEF):
        self.wall_length = float(length)
        self.wall_height = float(height)
        self.wall_depth = float(depth)
        self.color = color
        self.triangles = (
            Triangle3D(x, y, z, x + length, y, z, x + length, y + height, z, color, True, 0),
            Triangle3D(x, y, z, x + length, y + height, z, x, y + height, z, color, True, 0),
        )
        return True


class Triangle3D(_Native):
    def __init__(self, x1=0, y1=0, z1=0, x2=0, y2=0, z2=0, x3=0, y3=0, z3=0, color=0xFFFF, visible=True, distance=0):
        super().__init__(x1, y1, z1, x2, y2, z2, x3, y3, z3, color, visible, distance)
        self.x1 = x1
        self.y1 = y1
        self.z1 = z1
        self.x2 = x2
        self.y2 = y2
        self.z2 = z2
        self.x3 = x3
        self.y3 = y3
        self.z3 = z3
        self.color = color
        self.visible = visible
        self.distance = distance
