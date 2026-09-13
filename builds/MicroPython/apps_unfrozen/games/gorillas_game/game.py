"""Gorillas: a two-player rooftop duel using Picoware's native game engine."""

from math import cos, pi, sin
from random import randint
from time import sleep_ms, ticks_diff, ticks_ms
from framebuf import FrameBuffer, MONO_HLSB

from micropython import const
from picoware.engine.engine import GameEngine
from picoware.engine.entity import ENTITY_TYPE_ICON, ENTITY_TYPE_NPC, ENTITY_TYPE_PLAYER, Entity
from picoware.engine.game import Game
from picoware.engine.level import Level
from picoware.system.buttons import (
    BUTTON_BACK, BUTTON_CENTER, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP,
)
from picoware.system.vector import Vector

from .assets import BANANA_FRAMES, CLOUD_ART, GORILLA_ART, TITLE_ART
from .sprites import SpriteCache

PHASE_AIMING = const(0)
PHASE_FLYING = const(1)
PHASE_EXPLODING = const(2)
PHASE_GAME_OVER = const(3)
PHASE_MENU = const(4)
EXPLOSION_TICKS = const(40)

# RGB565 palette: midnight, slate, peach, cream, turquoise, and coral.
INK = const(0x1085)
PANEL = const(0x18C7)
SLATE = const(0x52F0)
CREAM = const(0xFF35)
GOLD = const(0xFDEA)
TEAL = const(0x5E79)
CORAL = const(0xFBAE)
WHITE = const(0xFFFF)
SKY = (0x18C9, 0x210B, 0x294D, 0x398F, 0x51D0, 0x7251, 0x92D2, 0xB393, 0xD474, 0xED55)
FACADES = ((0x29EC, 0x1949, 0x4B10), (0x4A0E, 0x310B, 0x7352), (0x2A4C, 0x1968, 0x4B71))
DAY_TIMES = ("DAWN", "DAY", "DUSK", "NIGHT")
SEASONS = ("SPRING", "SUMMER", "AUTUMN", "WINTER")

_engine = None
_game = None
_level = None
_state = None


def __ai_score(angle, power):
    """Yield between trajectory ticks so CPU aiming cannot stall rendering."""
    x, y = __launch_position()
    radians = angle * pi / 180
    scale = _state["physics_scale"]
    velocity = power * 0.105 * scale
    vx, vy = -cos(radians) * velocity, -sin(radians) * velocity
    target = _state["gorillas"][0]
    left, top = target.position.x, target.position.y
    right, bottom = left + target.size.x, top + target.size.y
    own = _state["gorillas"][1]
    own_left, own_top = own.position.x, own.position.y
    own_right, own_bottom = own_left + own.size.x, own_top + own.size.y
    tx, ty = (left + right) / 2, (top + bottom) / 2
    closest = 1e12
    for tick in range(160):
        vx += _state["wind"] * 0.003 * scale
        vy += 0.26 * scale
        # CPU predictions use two samples per tick. Real bananas retain their
        # pixel-sized sweep; approximate planning is deliberate, not perfect aim.
        steps = 2
        dx, dy = vx / steps, vy / steps
        for step in range(steps):
            x += dx
            y += dy
            distance = (x - tx) * (x - tx) + (y - ty) * (y - ty)
            closest = min(closest, distance)
            contact = 0 if left <= x < right and top <= y < bottom else -2
            if tick >= 6 and own_left <= x < own_right and own_top <= y < own_bottom:
                contact = 1
            if contact == -2 and __terrain_solid(x, y):
                contact = -1
            if contact == 0:
                yield 0
                return
            if contact != -2:
                # Prefer impacts near the opponent, opening an obstructed route.
                yield distance + (100000 if contact == 1 else 100)
                return
        if x < -20 or x > _state["width"] + 20 or y > _state["baseline"]:
            break
        yield None
    yield closest + _state["width"] ** 2


def __ai_update():
    """Spread a bounded aiming search over frames so the city keeps animating."""
    _state["ai_ticks"] += _state["steps"]
    began = ticks_ms()
    while ticks_diff(ticks_ms(), began) < 8:
        index = _state["ai_index"]
        if index >= 35:
            break
        angle = 20 + (index // 5) * 10
        power = 45 + (index % 5) * 12
        if _state["ai_search"] is None:
            _state["ai_search"] = __ai_score(angle, power)
        score = next(_state["ai_search"])
        if score is None:
            continue
        _state["ai_search"] = None
        if score < _state["ai_best"][0]:
            _state["ai_best"] = (score, angle, power)
        _state["ai_index"] += 1
    if _state["ai_index"] >= 35 and _state["ai_ticks"] >= 50:
        _, angle, power = _state["ai_best"]
        # The first two attempts are deliberately rough ranging shots. Later
        # attempts improve, but still have substantial error at blast scale.
        opening = _state["ai_shots"] < 2
        angle_error = randint(-10, 10) if opening else randint(-7, 7)
        power_error = randint(10, 22) if opening else randint(5, 14)
        if randint(0, 1) == 0:
            power_error = -power_error
        _state["angle"] = max(10, min(85, angle + angle_error))
        _state["power"] = max(20, min(100, power + power_error))
        _state["ai_shots"] += 1
        __throw()


def __art(draw, art, x, y, scale, palette, mirror=0, dissolve=0):
    """Blit a cached pose using the native framebuffer compositor."""
    draw.art(art, x, y, scale, palette, mirror, dissolve)


def __banana_collision(entity, other, game):
    """Resolve native engine contacts, keeping track of the actual victim."""
    if _state["phase"] != PHASE_FLYING or other is None:
        return
    if other.type == ENTITY_TYPE_PLAYER:
        victim = int(other.name[-1])
        if victim == _state["turn"] and _state["flight_ticks"] < 6:
            return
        __resolve_shot(victim)
    elif other.type == ENTITY_TYPE_NPC and __terrain_solid(_state["banana_x"], _state["banana_y"]):
        __resolve_shot(-1)


def __banana_step(entity, game):
    """Integrate gravity and wind; retain a bounded motion trail."""
    if _state["phase"] != PHASE_FLYING:
        entity.is_visible = False
        return
    _state["flight_ticks"] += 1
    scale = _state["physics_scale"]
    _state["banana_vx"] += _state["wind"] * 0.003 * scale
    _state["banana_vy"] += 0.26 * scale
    vx, vy = _state["banana_vx"], _state["banana_vy"]
    steps = max(1, int(max(abs(vx), abs(vy))) + 1)
    dx, dy = vx / steps, vy / steps
    # Sweep the projectile: fast throws must not skip a thin surviving wall.
    for step in range(steps):
        _state["banana_x"] += dx
        _state["banana_y"] += dy
        ignore = _state["turn"] if _state["flight_ticks"] < 6 else -1
        contact = __contact(_state["banana_x"], _state["banana_y"], ignore)
        if contact != -2:
            __resolve_shot(contact)
            return
    x, y = _state["banana_x"], _state["banana_y"]
    entity.position = Vector(x, y)
    if _state["flight_ticks"] % 2 == 0:
        _state["trail"].append((x, y))
        if len(_state["trail"]) > 8:
            _state["trail"].pop(0)
    if x < -20 or x > _state["width"] + 20 or y > _state["baseline"] + 4 or _state["flight_ticks"] > 240:
        __resolve_shot(-1)


def __banana_update(entity, game):
    """Advance fixed 30 Hz physics independently of display frame time."""
    for step in range(_state["steps"]):
        __banana_step(entity, game)


def __box(draw, x, y, width, height, color):
    """Draw a pixel-aligned rectangle."""
    x, y = int(x), int(y)
    width, height = max(1, int(width)), max(1, int(height))
    clip = _state["clip"]
    if clip is None:
        draw.fill_rect(x, y, width, height, color)
        return
    bx, by, bw, bh, cols, rows, cells = _state["terrain"][clip]
    unit = _state["terrain_unit"]
    # Rooftop props are drawn only when their supports survive (see renderer).
    if y < by:
        top_height = min(height, by - y)
        draw.fill_rect(x, y, width, top_height, color)
        y += top_height
        height -= top_height
    end_x, end_y = min(x + width, bx + bw), min(y + height, by + bh)
    x, y = max(x, bx), max(y, by)
    while y < end_y:
        row = (y - by) // unit
        bottom = min(end_y, by + (row + 1) * unit)
        xx = x
        while xx < end_x:
            col = (xx - bx) // unit
            solid = bool(cells[row * cols + col])
            right = min(end_x, bx + (col + 1) * unit)
            while right < end_x and bool(cells[row * cols + (right - bx) // unit]) == solid:
                right = min(end_x, right + unit)
            if solid:
                draw.fill_rect(xx, y, right - xx, bottom - y, color)
            xx = right
        y = bottom


def __center_text(draw, text, y, color=CREAM):
    """Center one short line."""
    draw.text(max(0, (_state["width"] - draw.len(text)) // 2), int(y), text, color)


def __contact(x, y, ignore=-1):
    """Return a player index, -1 for solid terrain, or -2 for empty space."""
    for index, gorilla in enumerate(_state["gorillas"]):
        if index != ignore and index not in _state["dead"]:
            pos, size = gorilla.position, gorilla.size
            if pos.x <= x < pos.x + size.x and pos.y <= y < pos.y + size.y:
                return index
    return -1 if __terrain_solid(x, y) else -2


def __create_entity(name, entity_type, position, size, update=None, render=None, collision=None):
    """Create an engine entity with Python update/render/collision callbacks."""
    return Entity(name, entity_type, position, size, None, None, None, None, None, update, render, collision)


def __create_scene(view_manager):
    """Build a layered scene; entities own rendering, animation, and collisions."""
    global _engine, _game, _level, _state
    draw = view_manager.draw
    width, height = int(draw.size.x), int(draw.size.y)
    compact = width < 180 or height < 120
    font = int(draw.font_size.y)
    scale = 1 if compact else max(1, min(width // 150, height // 120))
    gorilla_scale = 1 if compact else max(1, scale * 0.75)
    baseline = height - (font + 3 if compact else max(64, font * 6 + 12))
    _state = {
        "ai_best": (1e12, 50, 80), "ai_index": 0, "ai_shots": 0, "ai_ticks": 0,
        "aims": [(52, 82), (52, 82)], "angle": 52,
        "banana": None, "banana_vx": 0.0, "banana_vy": 0.0,
        "banana_x": -32.0, "banana_y": -32.0, "baseline": baseline,
        "buildings": [], "city_seed": 0, "clip": None, "cloud_offset": 0.0,
        "compact": compact, "dead": [],
        "explosion_frames": 0,
        "explosion_x": 0, "explosion_y": 0, "flight_ticks": 0, "font_height": font,
        "day_time": 2, "environment": "SUMMER / DUSK", "gorillas": [],
        "gorilla_scale": gorilla_scale,
        "height": height, "hit_player": -1,
        "menu_selection": 0, "message": "", "particles": [],
        "obstacles": [], "obstacle_hosts": [], "obstacle_kinds": [],
        "phase": PHASE_MENU, "physics_scale": width / 320.0, "players": 1,
        "pixel_scale": scale, "power": 82, "round": 1, "tick": 0,
        "season": 1, "sky": SKY, "terrain": [], "terrain_unit": scale, "trail": [],
        "turn": 0, "width": width, "wind": 0,
        "renderer": SpriteCache(draw),
        "ai_search": None, "steps": 1, "last_frame": ticks_ms(), "remainder": 0,
    }
    collision_data = bytearray(((width + 7) // 8) * height)
    _state["collision_data"] = collision_data
    _state["collision"] = FrameBuffer(collision_data, width, height, MONO_HLSB, (width + 7) & ~7)
    _game = Game("Gorillas", Vector(width, height), draw, view_manager.input_manager, WHITE, INK)
    _level = Level("Sunset city", Vector(width, height), _game, None, None)
    # The Draw-backed sprite cache clears/swaps once; avoid a duplicate swap.
    _level.clear_allowed = False
    _level.entity_add(__create_entity("sky", ENTITY_TYPE_ICON, Vector(0, 0), Vector(0, 0), render=__draw_sky))
    # Banana precedes solid entities: the engine visits each collision pair once.
    banana = __create_entity("banana", ENTITY_TYPE_ICON, Vector(-32, -32), Vector(3 * scale, 3 * scale), __banana_update, collision=__banana_collision)
    _state["banana"] = banana
    _level.entity_add(banana)
    margin, gap = (3, 2) if compact else (8, 3)
    count = 7 if compact else 9
    building_width = (width - margin * 2 - gap * (count - 1)) // count
    for index in range(count):
        building_height = 8
        x = margin + index * (building_width + gap)
        y = baseline - building_height
        entity = __create_entity("building_" + str(index), ENTITY_TYPE_NPC, Vector(x, y), Vector(building_width, building_height), render=__draw_building)
        _state["buildings"].append(entity)
        _level.entity_add(entity)
    for index in range(2 if compact else 3):
        obstacle = __create_entity("obstacle_" + str(index), ENTITY_TYPE_NPC,
                                   Vector(-32, -32), Vector(1, 1), render=__draw_obstacle)
        _state["obstacles"].append(obstacle)
        _level.entity_add(obstacle)
    gorilla_width, gorilla_height = (10, 11) if compact else (int(20 * gorilla_scale), int(23 * gorilla_scale))
    for index, building in enumerate((_state["buildings"][0], _state["buildings"][-1])):
        x = int(building.position.x + (building.size.x - gorilla_width) / 2)
        y = int(building.position.y - gorilla_height - 2)
        gorilla = __create_entity("gorilla_" + str(index), ENTITY_TYPE_PLAYER, Vector(x, y), Vector(gorilla_width, gorilla_height), render=__draw_gorilla)
        _state["gorillas"].append(gorilla)
        _level.entity_add(gorilla)
    __randomize_city()
    _level.entity_add(__create_entity("hud", ENTITY_TYPE_ICON, Vector(0, 0), Vector(0, 0), render=__draw_hud))
    _game.level_add(_level)
    _engine = GameEngine(_game, 30)


def __damage_terrain(x, y, radius):
    """Carve persistent holes and char the surviving masonry around the blast."""
    unit = _state["terrain_unit"]
    outer = radius + 4 * unit
    building_count = len(_state["buildings"])
    for terrain_index, terrain in enumerate(_state["terrain"]):
        bx, by, bw, bh, cols, rows, cells = terrain
        if x + outer < bx or x - outer >= bx + bw or y + outer < by or y - outer >= by + bh:
            continue
        key = ("building", terrain_index) if terrain_index < building_count else ("obstacle", terrain_index - building_count)
        _state["renderer"].invalidate(key)
        for row in range(max(0, (y - outer - by) // unit), min(rows, (y + outer - by) // unit + 1)):
            for col in range(max(0, (x - outer - bx) // unit), min(cols, (x + outer - bx) // unit + 1)):
                index = row * cols + col
                if not cells[index]:
                    continue
                dx, dy = bx + col * unit + unit // 2 - x, by + row * unit + unit // 2 - y
                distance = dx * dx + dy * dy
                if distance <= radius * radius:
                    cells[index] = 0
                    _state["collision"].fill_rect(bx + col * unit, by + row * unit,
                                                  min(unit, bw - col * unit), min(unit, bh - row * unit), 0)
                elif distance <= (radius + 2 * unit) ** 2:
                    cells[index] = 2 if (row + col) % 4 else 3
                elif distance <= outer * outer and (row * 3 + col * 7) % 5 == 0:
                    cells[index] = 2
    # Unsupported roof fixtures fall away with their destroyed foundation.
    for index, host in enumerate(_state["obstacle_hosts"]):
        terrain = _state["terrain"][len(_state["buildings"]) + index]
        bx, by, bw, bh = terrain[:4]
        roof_y = _state["terrain"][host][1]
        if not any(__terrain_solid(xx, roof_y) for xx in range(bx, bx + bw)):
            cells = terrain[-1]
            for cell in range(len(cells)):
                cells[cell] = 0
            _state["collision"].fill_rect(bx, by, bw, bh, 0)
            _state["renderer"].invalidate(("obstacle", index))


def __draw_building(entity, draw, game):
    """Shaded facades, glowing windows, rooftop props, and painted decals."""
    draw = _state["renderer"]
    index = int(entity.name[-1])
    key = ("building", index)
    cached = draw.terrain.get(key)
    if cached is not None:
        draw.blit(cached)
        __draw_building_lights(index, draw)
        return
    x, y = int(entity.position.x), int(entity.position.y)
    w, h = int(entity.size.x), int(entity.size.y)
    cached = draw.capture(x, y - 20, w, h + 20)
    _state["clip"] = index
    compact, tick = _state["compact"], _state["tick"]
    body, shadow, rim = (WHITE, 0, WHITE) if compact else _state["facades"][(index + _state["city_seed"]) % 3]
    __box(draw, x, y, w, h, body)
    __box(draw, x + w - max(2, w // 6), y, max(2, w // 6), h, shadow)
    unit = _state["terrain_unit"]
    cells = _state["terrain"][index][-1]
    for col in range(_state["terrain"][index][4]):
        if cells[col]:
            roof_color = WHITE if _state["season"] == 3 else rim
            __box(draw, x + col * unit, y - 2, min(unit, w - col * unit), 2, roof_color)
    step = 4 if compact else max(7, w // 5)
    window_w, window_h = (1, 1) if compact else (max(2, step // 3), 4)
    for row, wy in enumerate(range(y + 5, y + h - 3, step + 3)):
        for col, wx in enumerate(range(x + 4, x + w - 5, step)):
            lit = (row * 7 + col * 3 + index * 5 + _state["city_seed"]) % 11 < 5
            if row == 1 and col == 1:
                lit = (tick // 45 + index) % 5 != 0
            window_color = rim if _state["day_time"] == 1 else GOLD
            color = 0 if compact else (window_color if lit else shadow)
            __box(draw, wx, wy, window_w, window_h, color)
    if compact:
        __draw_decals(draw, index)
        _state["clip"] = None
        draw.end_capture(key, cached)
        __draw_building_lights(index, draw)
        return
    if index % 3 == 1:
        for sy in range(y + 16, y + h - 4, 18):
            __box(draw, x + 1, sy, w - 3, 1, shadow)
        __box(draw, x + w - 11, y + 5, 1, h - 8, rim)
        for sy in range(y + 9, y + h - 2, 8):
            __box(draw, x + w - 11, sy, 7, 1, rim)
    roof_intact = __terrain_solid(x + w // 2, y)
    if index == 3 and roof_intact:
        __box(draw, x + w // 2, y - 18, 1, 16, rim)
        __box(draw, x + w // 2 - 6, y - 14, 13, 1, rim)
        __box(draw, x + w // 2 - 3, y - 18, 7, 1, rim)
    if index in (1, 5) and __intact_rectangle(x + 2, y + 11, w - 4, _state["font_height"] + 6):
        label = "BANANA" if index == 1 else "ARCADE"
        if draw.len(label) + 6 > w:
            label = "BN" if index == 1 else "AR"
        sign_w = min(w - 4, draw.len(label) + 4)
        __box(draw, x + 2, y + 11, sign_w, _state["font_height"] + 6, INK)
        neon = TEAL if index == 1 else CORAL
        if index == 5 and tick % 180 < 5:
            neon = SLATE
        __box(draw, x + 2, y + 11, sign_w, 1, neon)
        draw.text(x + 4, y + 14, label, neon)
    if index in (0, len(_state["buildings"]) - 1) and __intact_rectangle(x + 5, y + h - 13, 12, 8):
        draw.text(x + 5, y + h - 13, "01" if index == 0 else "02", TEAL if index == 0 else CORAL)
    __draw_decals(draw, index)
    _state["clip"] = None
    draw.end_capture(key, cached)
    __draw_building_lights(index, draw)


def __draw_building_lights(index, draw):
    """Animate only the blinking window and neon, not the whole facade."""
    cached = draw.lights.get(index)
    if cached is not None:
        window, neon = cached
        if window:
            draw.blit(window[0 if (_state["tick"] // 45 + index) % 5 != 0 else 1])
        if neon:
            draw.blit(neon[0 if _state["tick"] % 180 >= 5 else 1])
        return
    x, y, w, h = _state["terrain"][index][:4]
    compact, tick = _state["compact"], _state["tick"]
    body, shadow, rim = (WHITE, 0, WHITE) if compact else _state["facades"][(index + _state["city_seed"]) % 3]
    step = 4 if compact else max(7, w // 5)
    wx, wy = x + 4 + step, y + 5 + step + 3
    _state["clip"] = index
    window, neon_tiles = [], []
    if wx < x + w - 5 and wy < y + h - 3:
        ww, wh = (1, 1) if compact else (max(2, step // 3), 4)
        for color in ((0, 0) if compact else ((rim if _state["day_time"] == 1 else GOLD), shadow)):
            tile = draw.capture(wx, wy, ww, wh)
            __box(draw, wx, wy, ww, wh, color)
            window.append(tile)
    if not compact and index == 5 and __intact_rectangle(x + 2, y + 11, w - 4, _state["font_height"] + 6):
        label = "ARCADE" if draw.len("ARCADE") + 6 <= w else "AR"
        for color in (CORAL, SLATE):
            tile = draw.capture(x + 2, y + 11, min(w - 4, draw.len(label) + 4), _state["font_height"] + 6)
            __box(draw, x + 2, y + 11, min(w - 4, draw.len(label) + 4), 1, color)
            draw.text(x + 4, y + 14, label, color)
            neon_tiles.append(tile)
    _state["clip"] = None
    draw.release()
    draw.cache_lights(index, window, neon_tiles)
    if window:
        draw.blit(window[0 if (tick // 45 + index) % 5 != 0 else 1])
    if neon_tiles:
        draw.blit(neon_tiles[0 if tick % 180 >= 5 else 1])


def __draw_decals(draw, index):
    """Scorch, chipped brick, and fractures stay attached to solid cells."""
    x, y, w, h, cols, rows, cells = _state["terrain"][index]
    unit = _state["terrain_unit"]
    for row in range(rows):
        col = 0
        while col < cols:
            material = cells[row * cols + col]
            end = col + 1
            while end < cols and cells[row * cols + end] == material:
                end += 1
            if material >= 2:
                color = (0 if material == 2 else WHITE) if _state["compact"] else (0x18A5 if material == 2 else 0x8B4C)
                __box(draw, x + col * unit, y + row * unit, (end - col) * unit, unit, color)
            col = end


def __draw_explosion(draw):
    """Flash, expanding shock ring, lumpy fireball, debris, and lingering smoke."""
    age = EXPLOSION_TICKS - _state["explosion_frames"]
    x, y, scale = _state["explosion_x"], _state["explosion_y"], _state["pixel_scale"]
    compact = _state["compact"]
    if age < 13:
        draw.circle(x, y, max(1, int((4 + age * 1.5) * scale)), WHITE if compact else GOLD)
    # Smoke lobes spread upward while the hot core fades.
    if age >= 10:
        for puff in range(5):
            px = x + int(sin(puff * 2.3) * (4 + age / 5) * scale)
            py = y - int((age - 10) * 0.6 * scale) + (puff % 2) * 3 * scale
            radius = max(1, int((3 + age / 9) * scale))
            color = WHITE if compact else (SLATE if age < 24 else 0x39CD)
            if age < 28:
                draw.fill_circle(px, py, radius, color)
            else:
                draw.circle(px, py, max(1, radius - (age - 28) // 3), color)
    if age < 22:
        radius = max(2, int((4 + min(age, 7) * 1.7 - max(0, age - 7) * 0.8) * scale))
        for lobe in range(6):
            angle = lobe * pi / 3 + age / 15
            px, py = x + int(cos(angle) * radius / 2), y + int(sin(angle) * radius / 2)
            draw.fill_circle(px, py, max(1, radius // 2), WHITE if compact else (CORAL if age < 12 else 0xDAA6))
        draw.fill_circle(x, y, max(1, radius * 2 // 3), 0 if compact else GOLD)
        if age < 9:
            draw.fill_circle(x, y, max(1, radius // 3), WHITE if compact else CREAM)
    for index, (vx, vy, size) in enumerate(_state["particles"]):
        px = x + vx * age
        py = y + vy * age + 0.035 * scale * age * age
        if py < _state["baseline"] and age < (24 if index % 2 else 36):
            color = WHITE if compact else (GOLD if index % 2 else 0x8B4C)
            __box(draw, px, py, size, max(1, size // 2), color)


def __draw_gorilla(entity, draw, game):
    """Shaded fur, expressive faces, a throwing pose, and an active-player marker."""
    draw = _state["renderer"]
    index = int(entity.name[-1])
    compact, tick = _state["compact"], _state["tick"]
    active, scale = index == _state["turn"], _state["gorilla_scale"]
    x, y = int(entity.position.x), int(entity.position.y)
    dead = index in _state["dead"]
    if dead and _state["phase"] != PHASE_EXPLODING:
        return
    throwing = active and _state["phase"] == PHASE_FLYING and _state["flight_ticks"] < 16
    celebrating = _state["phase"] == PHASE_GAME_OVER and not dead
    art = GORILLA_ART[2 if compact else (3 if dead else (1 if throwing or celebrating else 0))]
    palette = {"o": INK, "f": 0x49CA if index == 0 else 0x71E9, "h": 0x8B51 if index == 0 else 0xBBAE, "m": 0xE534, "s": 0x3928}
    if compact:
        palette = {"o": 0, "f": WHITE, "h": WHITE, "m": WHITE, "s": 0}
    dissolve = 0
    if dead:
        age = EXPLOSION_TICKS - _state["explosion_frames"]
        x += int((1 if index else -1) * age * 0.3 * scale)
        y += int((-age * 1.1 + age * age * 0.026) * scale)
        dissolve = max(0, (age - 20) * 12 // 20)
        if age < 6 and age % 2 == 0:
            palette = {"o": WHITE, "f": WHITE, "h": WHITE, "m": WHITE, "s": 0}
        elif not compact:
            palette = {"o": INK, "f": 0x296A, "h": SLATE, "m": 0xACD4, "s": INK}
    __art(draw, art, x, y, scale, palette, (10 if compact else 20) if index == 0 else 0, dissolve)
    if dead:
        for star in range(3):
            angle = _state["tick"] / 6 + star * pi * 2 / 3
            sx = x + entity.size.x / 2 + cos(angle) * 7 * scale
            sy = y - 4 * scale + sin(angle) * 2 * scale
            __box(draw, sx, sy, scale * 3, scale, WHITE if compact else GOLD)
        return
    if active and _state["phase"] == PHASE_AIMING:
        marker_y = y - (5 if compact else 10) - (tick // 15 % 2)
        color = WHITE if compact else (TEAL if index == 0 else CORAL)
        cx = int(x + entity.size.x / 2)
        for row in range(3):
            __box(draw, cx - 2 + row, marker_y + row, 5 - 2 * row, 1, color)
        sx, sy = __launch_position()
        radians = _state["angle"] * pi / 180
        direction = 1 if index == 0 else -1
        for dot in range(1, 5):
            distance = dot * (4 if compact else 7)
            __box(draw, sx + cos(radians) * distance * direction, sy - sin(radians) * distance, 1 if compact else 2, 1 if compact else 2, color)


def __draw_hud(entity, draw, game):
    """Compose motion effects and a responsive arcade HUD over the city."""
    draw = _state["renderer"]
    width, height = _state["width"], _state["height"]
    compact, phase = _state["compact"], _state["phase"]
    scale, font = _state["pixel_scale"], _state["font_height"]
    accent = WHITE if compact else (TEAL if _state["turn"] == 0 else CORAL)
    if phase == PHASE_MENU:
        __draw_menu(draw)
        draw.present()
        return
    if phase == PHASE_FLYING:
        for index, (x, y) in enumerate(_state["trail"]):
            __box(draw, x, y, 1 if compact else 2, 1 if compact else 2, WHITE if compact else (GOLD if index > 4 else SLATE))
        __art(draw, BANANA_FRAMES[(_state["flight_ticks"] // 3) % 4], _state["banana_x"] - 2 * scale, _state["banana_y"] - 2 * scale, scale, {"s": WHITE if compact else 0xA365, "y": WHITE if compact else GOLD, "h": WHITE if compact else CREAM})
    elif phase == PHASE_EXPLODING:
        __draw_explosion(draw)
    if compact:
        __box(draw, 0, 0, width, font + 3, 0)
        side = "CPU" if _state["players"] == 1 and _state["turn"] == 1 else "P{}".format(_state["turn"] + 1)
        status = "{} A{} P{} W{:+d}".format(side, _state["angle"], _state["power"], _state["wind"])
        __center_text(draw, status, 1, WHITE)
        __box(draw, 0, height - font - 2, width, font + 2, 0)
        __center_text(draw, "CPU THINKING..." if __is_cpu_turn() else "^vAim <>Pwr OK:Fire", height - font - 1, WHITE)
    else:
        __box(draw, 0, 0, width, 39, INK)
        title_scale = 2 if width >= 250 else 1
        title_x = (width - 47 * title_scale) // 2
        __art(draw, TITLE_ART, title_x + 1, 8, title_scale, {"#": 0x91E9})
        __art(draw, TITLE_ART, title_x, 7, title_scale, {"#": CREAM})
        __center_text(draw, _state["environment"], 27, SLATE)
        draw.text(10, 9, "P1", TEAL)
        opponent = "CPU" if _state["players"] == 1 else "P2"
        draw.text(width - draw.len(opponent) - 10, 9, opponent, CORAL)
        turn_label = "THINK" if __is_cpu_turn() else ("AIM" if phase == PHASE_AIMING else "FIRE")
        label_x = 10 if _state["turn"] == 0 else width - draw.len(turn_label) - 10
        draw.text(label_x, 23, turn_label, accent)
        panel_y = _state["baseline"] + 3
        __box(draw, 0, panel_y, width, height - panel_y, INK)
        __box(draw, 8, panel_y, width - 16, 1, SLATE)
        label_y = panel_y + 7
        draw.text(12, label_y, "ANGLE", SLATE)
        draw.text(width // 3 + 5, label_y, "POWER", SLATE)
        draw.text(width * 2 // 3 + 4, label_y, "WIND", SLATE)
        value_y = label_y + font + 3
        draw.text(12, value_y, "{} DEG".format(_state["angle"]), CREAM)
        draw.text(width // 3 + 5, value_y, str(_state["power"]), CREAM)
        wind = _state["wind"]
        draw.text(width * 2 // 3 + 4, value_y, "CALM" if wind == 0 else "{} {}".format("<" if wind < 0 else ">", abs(wind)), TEAL)
        bar_x, bar_w = width // 3 + 5, width // 3 - 18
        __box(draw, bar_x, value_y + font + 3, bar_w, 3, PANEL)
        __box(draw, bar_x, value_y + font + 3, bar_w * _state["power"] // 100, 3, accent)
        footer = "CPU IS AIMING...   BACK: MENU" if __is_cpu_turn() else "U/D AIM   L/R POWER   OK FIRE   BACK MENU"
        __center_text(draw, footer, height - font - 4, SLATE)
    if phase == PHASE_GAME_OVER:
        banner_y = height // 2 - (font + 6 if compact else 22)
        __box(draw, 3 if compact else 25, banner_y, width - (6 if compact else 50), font * 2 + 13, 0 if compact else INK)
        __center_text(draw, _state["message"], banner_y + 3, accent)
        __center_text(draw, "OK: REMATCH", banner_y + font + 7, WHITE if compact else CREAM)
    draw.present()


def __draw_menu(draw):
    """Main menu over the animated city, fitted to color and monochrome screens."""
    width, height = _state["width"], _state["height"]
    compact, font = _state["compact"], _state["font_height"]
    selected = _state["menu_selection"]
    if compact:
        __box(draw, 0, 0, width, height, 0)
        __center_text(draw, "GORILLAS", 2, WHITE)
        for index, label in enumerate(("1 PLAYER / CPU", "2 PLAYERS", "EXIT")):
            y = 17 + index * 12
            if index == selected:
                __box(draw, 5, y - 2, width - 10, font + 4, WHITE)
            __center_text(draw, label, y, 0 if index == selected else WHITE)
        __center_text(draw, "U/D SELECT  OK PLAY", height - font - 1, WHITE)
        return
    title_scale = 3 if width >= 250 else 2
    __art(draw, TITLE_ART, (width - 47 * title_scale) // 2, 48, title_scale, {"#": CREAM})
    __center_text(draw, _state["environment"], 48 + 7 * title_scale + 10, CREAM)
    panel_w = min(width - 28, 270)
    panel_h = max(122, font * 11 + 24)
    left, top = (width - panel_w) // 2, max(100, (height - panel_h) // 2)
    __box(draw, left, top, panel_w, panel_h, INK)
    __box(draw, left, top, panel_w, 2, TEAL)
    __center_text(draw, "CHOOSE YOUR GAME", top + 11, SLATE)
    row_height = max(25, font + 15)
    for index, label in enumerate(("1 PLAYER", "2 PLAYERS", "EXIT")):
        y = top + 30 + index * row_height
        if index == selected:
            __box(draw, left + 10, y - 4, panel_w - 20, font + 10, TEAL)
        __center_text(draw, label, y, INK if index == selected else CREAM)
    description = ("YOU VS THE COMPUTER", "LOCAL TWO-PLAYER DUEL", "RETURN TO GAMES")[selected]
    __center_text(draw, description, top + panel_h + 10, CREAM)
    __center_text(draw, "UP/DOWN SELECT   OK START   BACK EXIT", height - font - 5, SLATE)


def __draw_obstacle(entity, draw, game):
    """Render solid, destructible water tanks, roof barriers, and chimneys."""
    draw = _state["renderer"]
    index = int(entity.name[-1])
    terrain_index = len(_state["buildings"]) + index
    x, y, w, h, cols, rows, cells = _state["terrain"][terrain_index]
    if not any(cells):
        return
    key = ("obstacle", index)
    cached = draw.terrain.get(key)
    if cached is not None:
        draw.blit(cached)
        __draw_obstacle_smoke(index, draw)
        return
    cached = draw.capture(x, y, w, h)
    compact, unit = _state["compact"], _state["terrain_unit"]
    kind = _state["obstacle_kinds"][index]
    body = WHITE if compact else (0x4B10, 0x8B4C, 0x626A)[kind]
    edge = WHITE if compact else (0x8495 if _state["season"] != 3 else WHITE)
    _state["clip"] = terrain_index
    __box(draw, x, y, w, h, body)
    __box(draw, x, y, unit, h, edge)
    __box(draw, x + w - unit * 2, y, unit * 2, h, 0 if compact else INK)
    __box(draw, x, y, w, unit, WHITE if _state["season"] == 3 else edge)
    if kind == 0:
        __box(draw, x, y + h // 2, w, unit, 0 if compact else INK)
        __box(draw, x, y + h - 4 * unit, w, unit, edge)
    elif kind == 1:
        # Hazard stripes mark an actual wall the banana must clear or break.
        for stripe in range(1, w - 2, 4 * unit):
            __box(draw, x + stripe, y + 2 * unit, 2 * unit, max(1, h - 4 * unit), 0 if compact else GOLD)
    else:
        for row in range(3 * unit, h, 4 * unit):
            __box(draw, x, y + row, w, unit, 0 if compact else INK)
    __draw_decals(draw, terrain_index)
    _state["clip"] = None
    draw.end_capture(key, cached)
    __draw_obstacle_smoke(index, draw)


def __draw_obstacle_smoke(index, draw):
    """Keep chimney smoke moving independently of cached masonry."""
    x, y, w = _state["terrain"][len(_state["buildings"]) + index][:3]
    kind, compact = _state["obstacle_kinds"][index], _state["compact"]
    if kind == 2 and not compact and __terrain_solid(x + w // 2, y):
        for puff in range(3):
            age = (_state["tick"] + puff * 24) % 72
            sx = x + w // 2 + sin(age / 14) * 3 + age * _state["wind"] / 50
            draw.circle(int(sx), int(y - 3 - age / 4), 2 + age // 22, SLATE)


def __draw_sky(entity, draw, game):
    """Animated clouds, sunset, stars, and a distant city layer."""
    draw = _state["renderer"]
    draw.begin(INK)
    width, baseline, tick = _state["width"], _state["baseline"], _state["tick"]
    if _state["compact"]:
        for cloud in range(2):
            x = int((cloud * 79 + _state["cloud_offset"] * (0.8 + cloud * 0.25)) % (width + 28)) - 24
            __art(draw, CLOUD_ART, x, 12 + cloud * 8, 1, {"h": WHITE, "s": 0})
        return
    sky_top = 39
    band_h = max(1, (baseline - sky_top) // len(SKY) + 1)
    for index, color in enumerate(_state["sky"]):
        __box(draw, 0, sky_top + index * band_h, width, band_h, color)
    night = _state["day_time"] == 3
    for star in range(35 if night else (0 if _state["day_time"] == 1 else 12)):
        x = (star * 71 + 23) % width
        y = sky_top + 8 + (star * 31) % max(12, (baseline - sky_top) // (2 if night else 3))
        __box(draw, x, y, 1, 1, CREAM if (tick // 20 + star) % 7 == 0 else SLATE)
    sun_x, sun_y = int(width * 0.72), int(sky_top + (baseline - sky_top) * 0.30)
    radius = max(12, width // 18)
    draw.fill_circle(sun_x, sun_y, radius, 0xCE9D if night else GOLD)
    draw.fill_circle(sun_x, sun_y - 2, radius - 2, 0xEF7F if night else CREAM)
    surprised = _state["phase"] == PHASE_FLYING and abs(_state["banana_x"] - sun_x) < radius * 2 and abs(_state["banana_y"] - sun_y) < radius * 2
    if night:
        draw.fill_circle(sun_x - radius // 3, sun_y - 4, max(2, radius // 4), 0xADB9)
        draw.fill_circle(sun_x + radius // 3, sun_y + 5, max(1, radius // 6), 0xADB9)
    else:
        __box(draw, sun_x - 6, sun_y - 3, 2, 3, INK)
        __box(draw, sun_x + 4, sun_y - 3, 2, 3, INK)
    if surprised and not night:
        draw.circle(sun_x, sun_y + 5, 3, INK)
    elif not night:
        __box(draw, sun_x - 3, sun_y + 6, 6, 1, INK)
        __box(draw, sun_x - 5, sun_y + 4, 2, 2, INK)
        __box(draw, sun_x + 3, sun_y + 4, 2, 2, INK)
    for cloud in range(4):
        cloud_scale = 2 if cloud % 2 == 0 else 1
        drift = _state["cloud_offset"] * (0.8 + cloud * 0.25)
        x = int((cloud * width // 3 + drift) % (width + 60)) - 50
        y = sky_top + 10 + (cloud * 23) % max(20, (baseline - sky_top) // 2)
        __art(draw, CLOUD_ART, x, y, cloud_scale, _state["cloud_palette"])
    for layer in range(2):
        step = max(12, width // (18 if layer == 0 else 14))
        color = _state["distant_colors"][layer]
        for index in range(width // step + 1):
            h = 15 + ((index * 37 + layer * 23 + _state["city_seed"]) % max(20, (baseline - sky_top) // 3))
            __box(draw, index * step, baseline - h, step - 2, h, color)
            if index % 4 == 1:
                __box(draw, index * step + step // 2, baseline - h - 7, 1, 7, color)
    season = _state["season"]
    if season != 1:
        for fleck in range(22 if season == 3 else 10):
            drift = _state["cloud_offset"] * 2 + sin(tick / 25 + fleck) * 5
            x = int((fleck * 71 + _state["city_seed"] + drift) % width)
            y = sky_top + int((fleck * 37 + tick * (0.45 if season == 3 else 0.65)) % (baseline - sky_top))
            color = WHITE if season == 3 else (0xFDB0 if season == 2 else 0xFCDD)
            __box(draw, x, y, 2 if season == 2 else 1, 2, color)


def __finish_turn():
    """Award the surviving player, or pass control after an impact."""
    if _state["dead"]:
        if len(_state["dead"]) == 2:
            _state["message"] = "DRAW!"
        elif _state["players"] == 1:
            _state["message"] = "CPU WINS!" if 0 in _state["dead"] else "YOU WIN!"
        else:
            _state["message"] = "PLAYER {} WINS!".format(2 - _state["dead"][0])
        _state["phase"] = PHASE_GAME_OVER
        return
    _state["turn"] = 1 - _state["turn"]
    _state["angle"], _state["power"] = _state["aims"][_state["turn"]]
    _state["round"] += 1
    _state["wind"] = (_state["round"] * 7) % 11 - 5
    _state["phase"] = PHASE_AIMING
    _state["trail"].clear()
    _state["ai_index"], _state["ai_ticks"] = 0, 0
    _state["ai_search"] = None
    _state["ai_best"] = (1e12, 50, 80)


def __intact_rectangle(x, y, width, height):
    """Hide a sign or decal when its supporting masonry has been destroyed."""
    step = _state["terrain_unit"]
    for yy in range(y, y + height, step):
        for xx in range(x, x + width, step):
            if not __terrain_solid(xx, yy):
                return False
    return True


def __is_cpu_turn():
    """Return whether the computer currently owns the aiming controls."""
    return _state["players"] == 1 and _state["turn"] == 1 and _state["phase"] == PHASE_AIMING


def __launch_position():
    """Start the projectile completely above the shooter's collision box."""
    gorilla = _state["gorillas"][_state["turn"]]
    return gorilla.position.x + gorilla.size.x / 2, gorilla.position.y - 5 * _state["pixel_scale"]


def __mix_color(first, second, amount):
    """Blend RGB565 palette entries once when the match starts."""
    red = (((first >> 11) & 31) * (256 - amount) + ((second >> 11) & 31) * amount) // 256
    green = (((first >> 5) & 63) * (256 - amount) + ((second >> 5) & 63) * amount) // 256
    blue = ((first & 31) * (256 - amount) + (second & 31) * amount) // 256
    return (red << 11) | (green << 5) | blue


def __randomize_city():
    """Regenerate the skyline while retaining the native scene's entities."""
    _state["renderer"].invalidate()
    compact, width = _state["compact"], _state["width"]
    baseline, unit = _state["baseline"], _state["terrain_unit"]
    count = len(_state["buildings"])
    margin, gap = (3, 2) if compact else (8, 3)
    available = width - 2 * margin - gap * (count - 1)
    hero_width = int(_state["gorillas"][0].size.x)
    minimum = 10 if compact else max(18, width // 20)
    widths = [minimum] * count
    widths[0] = widths[-1] = max(minimum, hero_width)
    extra = available - sum(widths)
    weights = [randint(3, 10) for _ in range(count)]
    total = sum(weights)
    for index in range(count):
        widths[index] += extra * weights[index] // total
    for index in range(available - sum(widths)):
        widths[index % count] += 1
    _state["city_seed"] = randint(0, 65535)
    __set_environment(randint(0, 3), randint(0, 3))
    old_heights = tuple(t[3] for t in _state["terrain"][:count])
    _state["terrain"].clear()
    x = margin
    for index, building in enumerate(_state["buildings"]):
        endpoint = index in (0, count - 1)
        if compact:
            low, high = (8, 16) if endpoint else (12, 25)
        else:
            play_height = max(40, baseline - 40)
            low = max(24, play_height // 5)
            high = max(low + 1, int(play_height * (0.45 if endpoint else 0.66)))
        height = randint(low, high)
        # Even an unlikely repeat must not produce the previous skyline.
        if index < len(old_heights) and height == old_heights[index]:
            height = low if height == high else height + 1
        w, y = widths[index], baseline - height
        building.position, building.size = Vector(x, y), Vector(w, height)
        cols, rows = (w + unit - 1) // unit, (height + unit - 1) // unit
        cells = bytearray(b"\x01" * (cols * rows))
        _state["terrain"].append((x, y, w, height, cols, rows, cells))
        x += w + gap
    _state["obstacle_hosts"].clear()
    _state["obstacle_kinds"].clear()
    for index, obstacle in enumerate(_state["obstacles"]):
        host = 1 + index * (count - 2) // len(_state["obstacles"]) + randint(0, 1)
        bx, by, bw = _state["terrain"][host][:3]
        kind = (index + _state["city_seed"]) % 3
        w = max(3, bw - 4) if kind != 2 else min(bw - 4, 4 * unit)
        h = randint(4, 8) if compact else randint(9, 16) * unit
        x, y = bx + (bw - w) // 2, by - h
        cols, rows = (w + unit - 1) // unit, (h + unit - 1) // unit
        cells = bytearray(b"\x01" * (cols * rows))
        if kind == 0:
            # Water tank legs: the empty gap beneath the tank is shoot-through.
            for row in range(max(0, rows - 3), rows):
                for col in range(1, cols - 1):
                    cells[row * cols + col] = 0
        obstacle.position, obstacle.size = Vector(x, y), Vector(w, h)
        _state["terrain"].append((x, y, w, h, cols, rows, cells))
        _state["obstacle_hosts"].append(host)
        _state["obstacle_kinds"].append(kind)
    for index, gorilla in enumerate(_state["gorillas"]):
        building = _state["buildings"][0 if index == 0 else -1]
        x = int(building.position.x + (building.size.x - gorilla.size.x) / 2)
        y = int(building.position.y - gorilla.size.y - 2)
        gorilla.position = Vector(x, y)
    __rebuild_collision()


def __rebuild_collision():
    """Cache exact occupied pixels in a native one-bit collision surface."""
    mask, unit = _state["collision"], _state["terrain_unit"]
    mask.fill(0)
    for x, y, w, h, cols, rows, cells in _state["terrain"]:
        for row in range(rows):
            col = 0
            while col < cols:
                if not cells[row * cols + col]:
                    col += 1
                    continue
                end = col + 1
                while end < cols and cells[row * cols + end]:
                    end += 1
                mask.fill_rect(x + col * unit, y + row * unit,
                               min(w, end * unit) - col * unit, min(unit, h - row * unit), 1)
                col = end


def __reset_round():
    """Start a fresh match with new buildings and reset the computer's practice."""
    _state["angle"], _state["power"] = 52, 82
    _state["phase"], _state["turn"], _state["round"], _state["wind"] = PHASE_AIMING, 0, 1, 0
    _state["hit_player"] = -1
    _state["dead"].clear()
    _state["aims"] = [(52, 82), (52, 82)]
    _state["ai_index"], _state["ai_ticks"] = 0, 0
    _state["ai_search"] = None
    _state["ai_shots"] = 0
    _state["ai_best"] = (1e12, 50, 80)
    _state["particles"].clear()
    _state["explosion_frames"] = 0
    _state["banana"].position = Vector(-32, -32)
    _state["trail"].clear()
    __randomize_city()
    _state["last_frame"], _state["remainder"], _state["steps"] = ticks_ms(), 0, 1


def __resolve_shot(victim):
    """Destroy masonry, apply blast damage, and start debris and death animations."""
    if _state["phase"] != PHASE_FLYING:
        return
    x, y = int(_state["banana_x"]), int(_state["banana_y"])
    _state["explosion_x"], _state["explosion_y"] = x, y
    _state["explosion_frames"], _state["hit_player"] = EXPLOSION_TICKS, victim
    _state["phase"] = PHASE_EXPLODING
    _state["banana"].is_visible = False
    _state["banana"].position = Vector(-32, -32)
    scale = _state["pixel_scale"]
    radius = (6 if _state["compact"] else 10) * scale
    __damage_terrain(x, y, radius)
    for index, gorilla in enumerate(_state["gorillas"]):
        pos, size = gorilla.position, gorilla.size
        nearest_x = max(pos.x, min(x, pos.x + size.x))
        nearest_y = max(pos.y, min(y, pos.y + size.y))
        if index == victim or (nearest_x - x) ** 2 + (nearest_y - y) ** 2 <= radius * radius:
            _state["dead"].append(index)
    _state["particles"].clear()
    for index in range(10 if _state["compact"] else 22):
        angle = index * 2.399 + _state["tick"] / 10
        speed = (0.4 + index % 5 * 0.17) * scale
        _state["particles"].append((cos(angle) * speed, sin(angle) * speed - scale * 0.5, (1 + index % 3) * scale))
    __settle_gorillas()


def __set_environment(day_time, season):
    """Prepare a time-of-day sky and seasonal materials for this match."""
    _state["day_time"], _state["season"] = day_time, season
    _state["environment"] = SEASONS[season] + " / " + DAY_TIMES[day_time]
    top, bottom = ((0x52D2, 0xFE35), (0x3498, 0xC73F), (SKY[0], SKY[-1]), (0x0843, 0x212C))[day_time]
    tint = (0xABF4, 0xFDD0, 0xEB48, 0xB65E)[season]
    colors = SKY if day_time == 2 else tuple(__mix_color(top, bottom, index * 256 // 9) for index in range(10))
    _state["sky"] = tuple(__mix_color(color, tint, 12 if day_time == 3 else 28) for color in colors)
    facade_tint = (0x3B0D, 0x734D, 0xAB49, 0x8495)[season]
    _state["facades"] = tuple(tuple(__mix_color(color, facade_tint, 60) for color in facade) for facade in FACADES)
    cloud_light, cloud_shadow = ((0xDEDC, 0xA475), (WHITE, 0xAE1B), (0xAD15, 0x83B2), (0x4A70, 0x294A))[day_time]
    _state["cloud_palette"] = {"h": cloud_light, "s": cloud_shadow}
    _state["distant_colors"] = (__mix_color(_state["sky"][7], INK, 100), __mix_color(_state["sky"][7], INK, 175))


def __settle_gorillas():
    """Find surviving support below a rooftop after its masonry is removed."""
    for index, gorilla in enumerate(_state["gorillas"]):
        if index in _state["dead"]:
            continue
        x = int(gorilla.position.x + gorilla.size.x / 2)
        foot_y = int(gorilla.position.y + gorilla.size.y + 2)
        support = foot_y
        while support < _state["baseline"]:
            if any(__terrain_solid(xx, support) for xx in range(x - 2, x + 3)):
                break
            support += 1
        if support >= _state["baseline"]:
            _state["dead"].append(index)
        else:
            gorilla.position = Vector(gorilla.position.x, support - gorilla.size.y - 2)


def __terrain_solid(x, y):
    """Query the exact cached damage mask without searching every building."""
    if x < 0 or y < 0 or x >= _state["width"] or y >= _state["height"]:
        return False
    return bool(_state["collision"].pixel(int(x), int(y)))


def __throw():
    """Launch the spinning banana into the native collision scene."""
    radians = _state["angle"] * pi / 180
    velocity = _state["power"] * 0.105 * _state["physics_scale"]
    _state["banana_x"], _state["banana_y"] = __launch_position()
    _state["banana_vx"] = cos(radians) * velocity * (1 if _state["turn"] == 0 else -1)
    _state["banana_vy"] = -sin(radians) * velocity
    _state["banana"].position = Vector(_state["banana_x"], _state["banana_y"])
    _state["banana"].is_visible = True
    _state["flight_ticks"] = 0
    _state["aims"][_state["turn"]] = (_state["angle"], _state["power"])
    _state["trail"].clear()
    _state["phase"] = PHASE_FLYING


def __update_aim(button):
    """Adjust the selected angle or throwing power."""
    if button == BUTTON_DOWN:
        _state["angle"] = max(5, _state["angle"] - 2)
    elif button == BUTTON_UP:
        _state["angle"] = min(85, _state["angle"] + 2)
    elif button == BUTTON_RIGHT:
        _state["power"] = min(100, _state["power"] + 2)
    elif button == BUTTON_LEFT:
        _state["power"] = max(20, _state["power"] - 2)


def run(view_manager):
    """Consume input and run one native engine frame, including ambient animation."""
    if _engine is None:
        view_manager.back()
        return
    frame_started = ticks_ms()
    elapsed = min(132, max(0, ticks_diff(frame_started, _state["last_frame"])))
    elapsed += _state["remainder"]
    _state["last_frame"] = frame_started
    _state["steps"] = max(1, min(4, elapsed // 33))
    _state["remainder"] = elapsed % 33 if elapsed >= 33 else 0
    button = view_manager.button
    if button == BUTTON_BACK:
        if _state["phase"] == PHASE_MENU:
            view_manager.back()
        else:
            _state["phase"] = PHASE_MENU
            _state["banana"].position = Vector(-32, -32)
            _state["trail"].clear()
        return
    if _state["phase"] == PHASE_MENU:
        if button in (BUTTON_UP, BUTTON_LEFT):
            _state["menu_selection"] = (_state["menu_selection"] - 1) % 3
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            _state["menu_selection"] = (_state["menu_selection"] + 1) % 3
        elif button == BUTTON_CENTER:
            if _state["menu_selection"] == 2:
                view_manager.back()
                return
            _state["players"] = _state["menu_selection"] + 1
            __reset_round()
    elif _state["phase"] == PHASE_GAME_OVER:
        if button == BUTTON_CENTER:
            __reset_round()
    elif _state["phase"] == PHASE_AIMING:
        if __is_cpu_turn():
            __ai_update()
        elif button == BUTTON_CENTER:
            __throw()
        else:
            __update_aim(button)
    if _state["phase"] == PHASE_EXPLODING:
        _state["explosion_frames"] -= _state["steps"]
        if _state["explosion_frames"] <= 0:
            __finish_turn()
    _state["tick"] += _state["steps"]
    # Integrate wind so changing its strength never teleports the cloud layer.
    wind = _state["wind"]
    _state["cloud_offset"] += (wind * 0.09 if wind else 0.015) * _state["steps"]
    _engine.run_async(False)
    # The engine's default delay is additive; spend only the remaining budget.
    remaining = 33 - ticks_diff(ticks_ms(), frame_started)
    if remaining > 0:
        sleep_ms(remaining)


def start(view_manager):
    """Load the scene and the original pixel-art assets."""
    if _engine is not None:
        return True
    try:
        __create_scene(view_manager)
        _engine.run_async(False)
        return True
    except Exception as error:
        print("[Gorillas] Start failed:", error)
        stop(view_manager)
        return False


def stop(view_manager):
    """Drop scene references after leaving the game view."""
    global _engine, _game, _level, _state
    _engine = None
    _game = None
    _level = None
    _state = None
