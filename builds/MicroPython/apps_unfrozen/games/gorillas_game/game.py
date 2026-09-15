"""Gorillas: a two-player rooftop duel using Picoware's native game engine."""

from math import cos, pi, sin
from random import randint
from time import ticks_diff, ticks_ms
from gc import collect

from micropython import const
from picoware.engine.engine import GameEngine
from picoware.engine.entity import ENTITY_TYPE_ICON, ENTITY_TYPE_NPC, ENTITY_TYPE_PLAYER, Entity
from picoware.engine.game import Game
from picoware.engine.level import Level
from picoware.system.buttons import (
    BUTTON_BACK, BUTTON_CENTER, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP,
)
from picoware.system.decorator import native
from picoware.system.vector import Vector

from .assets import BANANA_FRAMES, CLOUD_ART, GORILLA_ART, GORILLA_FALLEN_ART, TITLE_ART
from .sprites import SpriteCache

PHASE_AIMING = const(0)
PHASE_FLYING = const(1)
PHASE_EXPLODING = const(2)
PHASE_GAME_OVER = const(3)
PHASE_MENU = const(4)
EXPLOSION_TICKS = const(40)
DECAL_LIMIT = const(24)
MATCH_WINS = const(3)

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


class _Scenery:
    """Drawing geometry without a native entity or per-frame callbacks."""

    __slots__ = ('name', 'position', 'size')

    def __init__(self, name, position, size):
        self.name, self.position, self.size = name, position, size


class _State:
    """Per-match state with direct attributes, not keyed lookups."""

    __slots__ = (
        'ai_best', 'ai_index', 'ai_search', 'ai_shots', 'ai_ticks',
        'aims', 'angle', 'banana', 'banana_hit', 'banana_hit_order',
        'banana_path', 'banana_vx', 'banana_vy', 'banana_x', 'banana_y',
        'baseline', 'buildings', 'city_seed', 'cloud_offset',
        'cloud_palette', 'compact', 'day_time', 'dead', 'distant_colors',
        'environment', 'explosion_frames', 'explosion_x', 'explosion_y',
        'facades', 'falling', 'flight_ticks', 'font_height', 'gorilla_scale',
        'gorillas', 'height', 'hit_player', 'last_frame', 'left_player', 'menu_selection',
        'message', 'obstacle_hosts', 'obstacle_kinds', 'obstacles',
        'particles', 'phase', 'physics_scale', 'pixel_scale', 'players',
        'power', 'remainder', 'renderer', 'round', 'scores', 'season', 'sky',
        'spawn_buildings', 'starter', 'steps', 'terrain', 'terrain_columns', 'terrain_unit', 'tick', 'trail', 'turn',
        'width', 'wind',
    )

    def __init__(self, draw, width, height, compact, font, scale, gorilla_scale, baseline):
        self.ai_best = (1e12, 50, 80)
        self.ai_index = 0
        self.ai_shots = 0
        self.ai_ticks = 0
        self.aims = [(52, 50), (52, 50)]
        self.angle = 52
        self.banana = None
        self.banana_vx = 0.0
        self.banana_vy = 0.0
        self.banana_hit = None
        self.banana_hit_order = 5
        self.banana_path = []
        self.banana_x = -32.0
        self.banana_y = -32.0
        self.baseline = baseline
        self.buildings = []
        self.city_seed = 0
        self.cloud_offset = 0.0
        self.compact = compact
        self.dead = []
        self.falling = []
        self.explosion_frames = 0
        self.explosion_x = 0
        self.explosion_y = 0
        self.flight_ticks = 0
        self.font_height = font
        self.day_time = 2
        self.environment = "SUMMER / DUSK"
        self.gorillas = []
        self.gorilla_scale = gorilla_scale
        self.height = height
        self.hit_player = -1
        self.menu_selection = 0
        self.left_player = 0
        self.message = ""
        self.particles = []
        self.obstacles = []
        self.obstacle_hosts = []
        self.obstacle_kinds = []
        self.phase = PHASE_MENU
        self.physics_scale = width / 320.0
        self.players = 1
        self.pixel_scale = scale
        self.power = 50
        self.round = 1
        self.scores = [0, 0]
        self.starter = 0
        self.spawn_buildings = (0, 0)
        self.tick = 0
        self.season = 1
        self.sky = SKY
        self.terrain = []
        self.terrain_columns = ()
        self.terrain_unit = scale
        self.trail = []
        self.turn = 0
        self.width = width
        self.wind = 0
        self.renderer = SpriteCache(draw)
        self.ai_search = None
        self.steps = 1
        self.last_frame = ticks_ms()
        self.remainder = 0


def __ai_score(angle, power):
    """Yield between trajectory ticks so CPU aiming cannot stall rendering."""
    width, height, baseline = _state.width, _state.height, _state.baseline
    columns = _state.terrain_columns
    terrain_cell = __terrain_cell
    x, y = __launch_position()
    radians = angle * pi / 180
    scale = _state.physics_scale
    wind = _state.wind * 0.003 * scale
    gravity = 0.26 * scale
    velocity = power * 0.105 * scale
    vx, vy = __direction(1) * cos(radians) * velocity, -sin(radians) * velocity
    target = _state.gorillas[0]
    left, top = target.position.x, target.position.y
    right, bottom = left + target.size.x, top + target.size.y
    own = _state.gorillas[1]
    own_left, own_top = own.position.x, own.position.y
    own_right, own_bottom = own_left + own.size.x, own_top + own.size.y
    tx, ty = (left + right) / 2, (top + bottom) / 2
    closest = 1e12
    for tick in range(160):
        vx += wind
        vy += gravity
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
            if contact == -2 and 0 <= x < width and 0 <= y < height:
                for terrain in columns[int(x) // 16]:
                    if terrain_cell(terrain, x, y):
                        contact = -1
                        break
            if contact == 0:
                yield 0
                return
            if contact != -2:
                # Prefer impacts near the opponent, opening an obstructed route.
                yield distance + (100000 if contact == 1 else 100)
                return
        if x < -20 or x > width + 20 or y > baseline:
            break
        yield None
    yield closest + width ** 2


def __ai_update():
    """Spread a bounded aiming search over frames so the city keeps animating."""
    _state.ai_ticks += _state.steps
    began = ticks_ms()
    while ticks_diff(ticks_ms(), began) < 8:
        index = _state.ai_index
        if index >= 35:
            break
        angle = 20 + (index // 5) * 10
        power = 45 + (index % 5) * 12
        if _state.ai_search is None:
            _state.ai_search = __ai_score(angle, power)
        score = next(_state.ai_search)
        if score is None:
            continue
        _state.ai_search = None
        if score < _state.ai_best[0]:
            _state.ai_best = (score, angle, power)
        _state.ai_index += 1
    if _state.ai_index >= 35 and _state.ai_ticks >= 50:
        _, angle, power = _state.ai_best
        # The first two attempts are deliberately rough ranging shots. Later
        # attempts improve, but still have substantial error at blast scale.
        opening = _state.ai_shots < 2
        angle_error = randint(-10, 10) if opening else randint(-7, 7)
        power_error = randint(10, 22) if opening else randint(5, 14)
        if randint(0, 1) == 0:
            power_error = -power_error
        _state.angle = max(10, min(85, angle + angle_error))
        _state.power = max(20, min(100, power + power_error))
        _state.ai_shots += 1
        __throw()


def __art(draw, art, x, y, scale, palette, mirror=0, dissolve=0):
    """Draw a prebuilt binary pose through the existing Draw API."""
    draw.art(art, x, y, scale, palette, mirror, dissolve)


def __banana_collision(entity, other, game):
    """Refine engine overlaps against swept points and surviving terrain cells."""
    if _state.phase != PHASE_FLYING or other is None:
        return
    if other.type == ENTITY_TYPE_PLAYER:
        victim = int(other.name[-1])
        if victim not in _state.dead:
            position, size = other.position, other.size
            __banana_contact(victim, None, position.x, position.y, size.x, size.y)
    elif other.type == ENTITY_TYPE_NPC and other.name == 'city':
        # One terrain collider represents the city; buildings are plain data.
        for terrain in _state.terrain:
            __banana_contact(-1, terrain, terrain[0], terrain[1], terrain[2], terrain[3])


def __banana_contact(victim, terrain, left, top, width, height):
    """Find the first real contact within one native collision candidate."""
    right, bottom = left + width, top + height
    banana = _state.banana
    position, size = banana.position, banana.size
    if position.x >= right or position.x + size.x <= left or position.y >= bottom or position.y + size.y <= top:
        return
    for segment, (x, y, vx, vy, tick) in enumerate(_state.banana_path):
        if segment >= _state.banana_hit_order:
            break
        if victim == _state.turn and tick < 6:
            continue
        steps = max(1, int(max(abs(vx), abs(vy))) + 1)
        dx, dy = vx / steps, vy / steps
        for sample in range(steps):
            x += dx
            y += dy
            order = segment + (sample + 1) / steps
            if order >= _state.banana_hit_order:
                break
            if left <= x < right and top <= y < bottom:
                # An overlap with a building's bounds is not a hit in a crater.
                if terrain is not None and not __terrain_cell(terrain, x, y):
                    continue
                _state.banana_hit_order = order
                _state.banana_hit = (victim, x, y)
                return


def __banana_finish():
    """Commit the earliest callback hit after updates, before scene rendering."""
    if _state.phase != PHASE_FLYING:
        return
    banana = _state.banana
    banana.size = Vector(3 * _state.pixel_scale, 3 * _state.pixel_scale)
    hit = _state.banana_hit
    if hit is not None:
        victim, _state.banana_x, _state.banana_y = hit
        __resolve_shot(victim)
    else:
        x, y = _state.banana_x, _state.banana_y
        banana.position = Vector(x, y)
        if x < -20 or x > _state.width + 20 or y > _state.baseline + 4 or _state.flight_ticks > 240:
            __resolve_shot(-1)
    _state.banana_path.clear()
    _state.banana_hit = None


def __banana_step(entity, game):
    """Integrate gravity and wind; retain a bounded motion trail."""
    if _state.phase != PHASE_FLYING:
        entity.is_visible = False
        return
    _state.flight_ticks += 1
    scale = _state.physics_scale
    _state.banana_vx += _state.wind * 0.003 * scale
    _state.banana_vy += 0.26 * scale
    vx, vy = _state.banana_vx, _state.banana_vy
    _state.banana_path.append((_state.banana_x, _state.banana_y, vx, vy, _state.flight_ticks))
    # Only collision refinement needs pixel-sized samples; integrate once here.
    _state.banana_x += vx
    _state.banana_y += vy
    x, y = _state.banana_x, _state.banana_y
    if _state.flight_ticks % 2 == 0:
        _state.trail.append((x, y))
        if len(_state.trail) > 8:
            _state.trail.pop(0)


def __banana_update(entity, game):
    """Expose a swept bounding box so native callbacks cannot miss thin walls."""
    _state.banana_path.clear()
    _state.banana_hit = None
    _state.banana_hit_order = 5
    if _state.phase != PHASE_FLYING:
        entity.is_visible = False
        return
    left = right = _state.banana_x
    top = bottom = _state.banana_y
    for step in range(_state.steps):
        __banana_step(entity, game)
        left, right = min(left, _state.banana_x), max(right, _state.banana_x)
        top, bottom = min(top, _state.banana_y), max(bottom, _state.banana_y)
    entity.position = Vector(left, top)
    entity.size = Vector(right - left + 1, bottom - top + 1)


def __center_text(draw, text, y, color=CREAM):
    """Center one short line."""
    draw.text(max(0, (_state.width - draw.len(text)) // 2), y, text, color)


def __create_entity(name, entity_type, position, size, update=None, render=None, collision=None):
    """Create an engine entity with Python update/render/collision callbacks."""
    return Entity(name, entity_type, position, size, None, None, None, None, None, update, render, collision)


def __create_scene(view_manager):
    """Create four collision entities and plain scenery for direct drawing."""
    global _engine, _game, _level, _state
    draw = view_manager.draw
    width, height = int(draw.size.x), int(draw.size.y)
    compact = width < 180 or height < 120
    font = int(draw.font_size.y)
    scale = 1 if compact else max(1, min(width // 150, height // 120))
    gorilla_scale = 1 if compact else max(1, scale * 0.75)
    baseline = height - (font + 3 if compact else max(64, font * 6 + 12))
    _state = _State(draw, width, height, compact, font, scale, gorilla_scale, baseline)
    _game = Game("Gorillas", Vector(width, height), draw, view_manager.input_manager, WHITE, INK)
    _level = Level("Sunset city", Vector(width, height), _game, None, None)
    # Scenery is drawn after engine updates; avoid a duplicate clear/swap.
    _level.clear_allowed = False
    # Banana precedes solid entities: the engine visits each collision pair once.
    banana = __create_entity("banana", ENTITY_TYPE_ICON, Vector(-32, -32), Vector(3 * scale, 3 * scale), __banana_update, collision=__banana_collision)
    _state.banana = banana
    _level.entity_add(banana)
    _level.entity_add(__create_entity('city', ENTITY_TYPE_NPC, Vector(0, 0), Vector(width, baseline + 1)))
    margin, gap = (3, 2) if compact else (8, 3)
    count = 7 if compact else 9
    building_width = (width - margin * 2 - gap * (count - 1)) // count
    for index in range(count):
        building_height = 8
        x = margin + index * (building_width + gap)
        y = baseline - building_height
        entity = _Scenery("building_" + str(index), Vector(x, y), Vector(building_width, building_height))
        _state.buildings.append(entity)
    for index in range(2 if compact else 3):
        obstacle = _Scenery("obstacle_" + str(index), Vector(-32, -32), Vector(1, 1))
        _state.obstacles.append(obstacle)
    gorilla_width, gorilla_height = (10, 11) if compact else (20 * gorilla_scale, 23 * gorilla_scale)
    for index, building in enumerate((_state.buildings[0], _state.buildings[-1])):
        x = building.position.x + (building.size.x - gorilla_width) / 2
        y = building.position.y - gorilla_height - 2
        gorilla = __create_entity("gorilla_" + str(index), ENTITY_TYPE_PLAYER, Vector(x, y), Vector(gorilla_width, gorilla_height), render=__render_scene if index == 0 else None)
        _state.gorillas.append(gorilla)
        _level.entity_add(gorilla)
    __randomize_city()
    _game.level_add(_level)
    _engine = GameEngine(_game, 30)


def __damage_terrain(x, y, radius):
    """Carve persistent holes and char the surviving masonry around the blast."""
    unit = _state.terrain_unit
    outer = radius + 4 * unit
    building_count = len(_state.buildings)
    for terrain_index, terrain in enumerate(_state.terrain):
        bx, by, bw, bh, cols, rows, cells = terrain
        if x + outer < bx or x - outer >= bx + bw or y + outer < by or y - outer >= by + bh:
            continue
        key = ("building", terrain_index) if terrain_index < building_count else ("obstacle", terrain_index - building_count)
        _state.renderer.invalidate(key)
        for row in range(max(0, (y - outer - by) // unit), min(rows, (y + outer - by) // unit + 1)):
            for col in range(max(0, (x - outer - bx) // unit), min(cols, (x + outer - bx) // unit + 1)):
                index = row * cols + col
                if not cells[index]:
                    continue
                dx, dy = bx + col * unit + unit // 2 - x, by + row * unit + unit // 2 - y
                distance = dx * dx + dy * dy
                if distance <= radius * radius:
                    cells[index] = 0
                elif distance <= (radius + 2 * unit) ** 2:
                    cells[index] = 2 if (row + col) % 4 else 3
                elif distance <= outer * outer and (row * 3 + col * 7) % 5 == 0:
                    cells[index] = 2
    # Unsupported roof fixtures fall away with their destroyed foundation.
    for index, host in enumerate(_state.obstacle_hosts):
        terrain = _state.terrain[len(_state.buildings) + index]
        bx, by, bw, bh = terrain[:4]
        roof_y = _state.terrain[host][1]
        if not any(__terrain_solid(xx, roof_y) for xx in range(bx, bx + bw)):
            cells = terrain[-1]
            for cell in range(len(cells)):
                cells[cell] = 0
            _state.renderer.invalidate(("obstacle", index))


def __direction(player):
    """Aim toward the opponent independently of player identity."""
    return 1 if player == _state.left_player else -1


def __draw_building(entity, draw, game):
    """Shaded facades, glowing windows, rooftop props, and painted decals."""
    draw = _state.renderer
    index = int(entity.name[-1])
    key = ("building", index)
    cached = draw.terrain.get(key)
    if cached is not None:
        draw.blit(cached)
        __draw_building_lights(index, draw)
        return
    x, y = entity.position.x, entity.position.y
    w, h = entity.size.x, entity.size.y
    cached = draw.capture(x, y - 20, w, h + 20, key)
    draw.set_terrain_clip(_state.terrain[index], _state.terrain_unit)
    compact, tick = _state.compact, _state.tick
    body, shadow, rim = (WHITE, 0, WHITE) if compact else _state.facades[(index + _state.city_seed) % 3]
    draw.box(x, y, w, h, body)
    draw.box(x + w - max(2, w // 6), y, max(2, w // 6), h, shadow)
    unit = _state.terrain_unit
    cells = _state.terrain[index][-1]
    for col in range(_state.terrain[index][4]):
        if cells[col]:
            roof_color = WHITE if _state.season == 3 else rim
            draw.box(x + col * unit, y - 2, min(unit, w - col * unit), 2, roof_color)
    step = 4 if compact else max(7, w // 5)
    window_w, window_h = (1, 1) if compact else (max(2, step // 3), 4)
    for row, wy in enumerate(range(y + 5, y + h - 3, step + 3)):
        for col, wx in enumerate(range(x + 4, x + w - 5, step)):
            lit = (row * 7 + col * 3 + index * 5 + _state.city_seed) % 11 < 5
            if row == 1 and col == 1:
                lit = (tick // 45 + index) % 5 != 0
            window_color = rim if _state.day_time == 1 else GOLD
            color = 0 if compact else (window_color if lit else shadow)
            draw.box(wx, wy, window_w, window_h, color)
    if compact:
        __draw_decals(draw, index)
        draw.set_terrain_clip(None, 1)
        draw.end_capture(key, cached)
        __draw_building_lights(index, draw)
        return
    if index % 3 == 1:
        for sy in range(y + 16, y + h - 4, 18):
            draw.box(x + 1, sy, w - 3, 1, shadow)
        draw.box(x + w - 11, y + 5, 1, h - 8, rim)
        for sy in range(y + 9, y + h - 2, 8):
            draw.box(x + w - 11, sy, 7, 1, rim)
    roof_intact = __terrain_solid(x + w // 2, y)
    if index == 3 and roof_intact:
        draw.box(x + w // 2, y - 18, 1, 16, rim)
        draw.box(x + w // 2 - 6, y - 14, 13, 1, rim)
        draw.box(x + w // 2 - 3, y - 18, 7, 1, rim)
    if index in (1, 5) and __intact_rectangle(_state.terrain[index], x + 2, y + 11, w - 4, _state.font_height + 6):
        label = "BANANA" if index == 1 else "ARCADE"
        if draw.len(label) + 6 > w:
            label = "BN" if index == 1 else "AR"
        sign_w = min(w - 4, draw.len(label) + 4)
        draw.box(x + 2, y + 11, sign_w, _state.font_height + 6, INK)
        neon = TEAL if index == 1 else CORAL
        if index == 5 and tick % 180 < 5:
            neon = SLATE
        draw.box(x + 2, y + 11, sign_w, 1, neon)
        draw.text(x + 4, y + 14, label, neon)
    if index in _state.spawn_buildings and __intact_rectangle(_state.terrain[index], x + 5, y + h - 13, 12, 8):
        player = _state.spawn_buildings.index(index)
        draw.text(x + 5, y + h - 13, "01" if player == 0 else "02", TEAL if player == 0 else CORAL)
    __draw_decals(draw, index)
    draw.set_terrain_clip(None, 1)
    draw.end_capture(key, cached)
    __draw_building_lights(index, draw)


def __draw_building_lights(index, draw):
    """Animate only the blinking window and neon, not the whole facade."""
    cached = draw.lights.get(index)
    if cached is not None:
        window, neon = cached
        if window:
            draw.blit(window[0 if (_state.tick // 45 + index) % 5 != 0 else 1])
        if neon:
            draw.blit(neon[0 if _state.tick % 180 >= 5 else 1])
        return
    x, y, w, h = _state.terrain[index][:4]
    compact, tick = _state.compact, _state.tick
    body, shadow, rim = (WHITE, 0, WHITE) if compact else _state.facades[(index + _state.city_seed) % 3]
    step = 4 if compact else max(7, w // 5)
    wx, wy = x + 4 + step, y + 5 + step + 3
    draw.set_terrain_clip(_state.terrain[index], _state.terrain_unit)
    window, neon_tiles = [], []
    if wx < x + w - 5 and wy < y + h - 3:
        ww, wh = (1, 1) if compact else (max(2, step // 3), 4)
        for state, color in enumerate((0, 0) if compact else ((rim if _state.day_time == 1 else GOLD), shadow)):
            tile = draw.capture(wx, wy, ww, wh, ('window', index, state))
            draw.box(wx, wy, ww, wh, color)
            window.append(tile)
    if not compact and index == 5 and __intact_rectangle(_state.terrain[index], x + 2, y + 11, w - 4, _state.font_height + 6):
        label = "ARCADE" if draw.len("ARCADE") + 6 <= w else "AR"
        for state, color in enumerate((CORAL, SLATE)):
            tile = draw.capture(x + 2, y + 11, min(w - 4, draw.len(label) + 4), _state.font_height + 6,
                                ('neon', index, state))
            draw.box(x + 2, y + 11, min(w - 4, draw.len(label) + 4), 1, color)
            draw.text(x + 4, y + 14, label, color)
            neon_tiles.append(tile)
    draw.set_terrain_clip(None, 1)
    draw.release()
    draw.cache_lights(index, window, neon_tiles)
    if window:
        draw.blit(window[0 if (tick // 45 + index) % 5 != 0 else 1])
    if neon_tiles:
        draw.blit(neon_tiles[0 if tick % 180 >= 5 else 1])


def __draw_decals(draw, index):
    """Merge solid scorch spans; bound cosmetic commands, never blast holes."""
    x, y, w, h, cols, rows, cells = _state.terrain[index]
    unit = _state.terrain_unit
    active = {}
    remaining = DECAL_LIMIT
    for row in range(rows + 1):
        current = {}
        col = 0
        while row < rows and col < cols:
            material = cells[row * cols + col]
            end = col + 1
            while end < cols and cells[row * cols + end] == material:
                end += 1
            if material >= 2:
                run = (col, end, material)
                current[run] = active.pop(run, row)
            col = end
        for (left, right, material), top in active.items():
            color = (0 if material == 2 else WHITE) if _state.compact else (0x18A5 if material == 2 else 0x8B4C)
            # Every cell in this merged rectangle has the same solid material.
            # Avoid another terrain-clipping pass and its temporary dictionaries.
            draw.fill_rect(x + left * unit, y + top * unit,
                           min(w, right * unit) - left * unit,
                           min(h, row * unit) - top * unit, color)
            remaining -= 1
            if not remaining:
                return
        active = current


def __draw_explosion(draw):
    """Flash, expanding shock ring, lumpy fireball, debris, and lingering smoke."""
    age = EXPLOSION_TICKS - _state.explosion_frames
    x, y, scale = _state.explosion_x, _state.explosion_y, _state.pixel_scale
    compact = _state.compact
    if not draw.layer('explosion', (x, y, age)):
        return
    draw.effect(x, y, scale, compact, age)
    for index, (vx, vy, size) in enumerate(_state.particles):
        px = x + vx * age
        py = y + vy * age + 0.035 * scale * age * age
        if py < _state.baseline and age < (24 if index % 2 else 36):
            color = WHITE if compact else (GOLD if index % 2 else 0x8B4C)
            draw.box(px, py, size, max(1, size // 2), color)
    draw.end_layer()


def __draw_gorilla(entity, draw, game):
    """Shaded fur, expressive faces, a throwing pose, and an active-player marker."""
    draw = _state.renderer
    index = int(entity.name[-1])
    compact, tick = _state.compact, _state.tick
    active, scale = index == _state.turn, _state.gorilla_scale
    x, y = entity.position.x, entity.position.y
    dead = index in _state.dead
    falling = index in _state.falling
    if dead and _state.phase != PHASE_EXPLODING:
        return
    throwing = active and _state.phase == PHASE_FLYING and _state.flight_ticks < 16
    celebrating = _state.phase == PHASE_GAME_OVER and not dead
    revision = (x, y, dead, falling, _state.left_player, throwing or celebrating,
                (tick, _state.explosion_frames) if dead else None)
    if draw.layer(('gorilla', index), revision):
        art = GORILLA_ART[2 if compact else (3 if dead and not falling else (1 if throwing or celebrating else 0))]
        palette = {"o": INK, "f": 0x49CA if index == 0 else 0x71E9, "h": 0x8B51 if index == 0 else 0xBBAE, "m": 0xE534, "s": 0x3928}
        if compact:
            palette = {"o": 0, "f": WHITE, "h": WHITE, "m": WHITE, "s": 0}
        dissolve = 0
        if falling:
            age = EXPLOSION_TICKS - _state.explosion_frames
            landing_y = _state.baseline - entity.size.y
            y += 0.24 * scale * age * age
            if y >= landing_y:
                # Prebaked sideways artwork needs no rotation buffer on-device.
                # Blink by omitting the pose; dirty tracking restores the sky.
                if age // 4 % 2 == 0:
                    art = GORILLA_FALLEN_ART[1 if compact else 0]
                    w, h = (11, 10) if compact else (23, 20)
                    x = max(0, min(_state.width - int(w * scale), x))
                    __art(draw, art, x, _state.baseline - int(h * scale), scale,
                          palette, w if __direction(index) == 1 else 0)
                draw.end_layer()
                return
        elif dead:
            age = EXPLOSION_TICKS - _state.explosion_frames
            x -= __direction(index) * age * 0.3 * scale
            y += (-age * 1.1 + age * age * 0.026) * scale
            dissolve = max(0, (age - 20) * 12 // 20)
            if age < 6 and age % 2 == 0:
                palette = {"o": WHITE, "f": WHITE, "h": WHITE, "m": WHITE, "s": 0}
            elif not compact:
                palette = {"o": INK, "f": 0x296A, "h": SLATE, "m": 0xACD4, "s": INK}
        __art(draw, art, x, y, scale, palette, (10 if compact else 20) if __direction(index) == 1 else 0, dissolve)
        if falling:
            draw.end_layer()
            return
        if dead:
            for star in range(3):
                angle = _state.tick / 6 + star * pi * 2 / 3
                sx = x + entity.size.x / 2 + cos(angle) * 7 * scale
                sy = y - 4 * scale + sin(angle) * 2 * scale
                draw.box(sx, sy, scale * 3, scale, WHITE if compact else GOLD)
            draw.end_layer()
            return
        draw.end_layer()
    if active and _state.phase == PHASE_AIMING:
        if not draw.layer(('aim_marker', index), (x, y, tick // 15 % 2, _state.angle)):
            return
        marker_y = y - (5 if compact else 10) - (tick // 15 % 2)
        color = WHITE if compact else (TEAL if index == 0 else CORAL)
        cx = x + entity.size.x / 2
        for row in range(3):
            draw.box(cx - 2 + row, marker_y + row, 5 - 2 * row, 1, color)
        sx, sy = __launch_position()
        radians = _state.angle * pi / 180
        cosine, sine = cos(radians), sin(radians)
        direction = __direction(index)
        for dot in range(1, 5):
            distance = dot * (4 if compact else 7)
            draw.box(sx + cosine * distance * direction, sy - sine * distance, 1 if compact else 2, 1 if compact else 2, color)
        draw.end_layer()


def __draw_hud(entity, draw, game):
    """Compose motion effects and a responsive arcade HUD over the city."""
    draw = _state.renderer
    width, height = _state.width, _state.height
    compact, phase = _state.compact, _state.phase
    scale, font = _state.pixel_scale, _state.font_height
    accent = WHITE if compact else (TEAL if _state.turn == 0 else CORAL)
    if phase == PHASE_MENU:
        if draw.layer('menu', (_state.menu_selection, _state.environment)):
            __draw_menu(draw)
            draw.end_layer()
        draw.present()
        return
    if phase == PHASE_FLYING:
        if draw.layer('trail', tuple(_state.trail)):
            for index, (x, y) in enumerate(_state.trail):
                draw.box(x, y, 1 if compact else 2, 1 if compact else 2, WHITE if compact else (GOLD if index > 4 else SLATE))
            draw.end_layer()
        # Dirty-region bounds also become integer sprite-buffer slice offsets.
        bx, by = int(_state.banana_x - 2 * scale), int(_state.banana_y - 2 * scale)
        draw.watch('banana', _state.flight_ticks // 3 % 4, (bx, by, bx + 8 * scale, by + 8 * scale))
        __art(draw, BANANA_FRAMES[(_state.flight_ticks // 3) % 4], _state.banana_x - 2 * scale, _state.banana_y - 2 * scale, scale, {"s": WHITE if compact else 0xA365, "y": WHITE if compact else GOLD, "h": WHITE if compact else CREAM})
    elif phase == PHASE_EXPLODING:
        __draw_explosion(draw)
    if compact:
        revision = (phase, _state.turn, _state.players, _state.angle, _state.power, _state.wind, tuple(_state.scores))
        if draw.layer('hud', revision):
            draw.box(0, 0, width, font + 3, 0)
            side = "CPU" if _state.players == 1 and _state.turn == 1 else "P{}".format(_state.turn + 1)
            status = "{} A{} P{} W{:+d}".format(side, _state.angle, _state.power, _state.wind)
            __center_text(draw, status, 1, WHITE)
            draw.box(0, height - font - 2, width, font + 2, 0)
            __center_text(draw, __score_text(), height - font - 1, WHITE)
            draw.end_layer()
    else:
        __draw_hud_static(draw)
        __draw_hud_fields(draw)
    if phase == PHASE_GAME_OVER and draw.layer('result', (_state.message, accent, tuple(_state.scores)), (__game_over_box(),)):
        left, banner_y, right, bottom = __game_over_box()
        draw.box(left, banner_y, right - left, bottom - banner_y, 0 if compact else INK)
        __center_text(draw, _state.message, banner_y + 3, accent)
        __center_text(draw, __score_text(), banner_y + font + 7, WHITE if compact else CREAM)
        __center_text(draw, __result_prompt(), banner_y + font * 2 + 11, WHITE if compact else CREAM)
        draw.end_layer()
    draw.present()


def __draw_hud_fields(draw):
    """Keep angle/power changes local instead of invalidating both HUD panels."""
    width, height, font = _state.width, _state.height, _state.font_height
    turn, phase = _state.turn, _state.phase
    accent = TEAL if turn == 0 else CORAL
    panel_y = _state.baseline + 3
    label_y, value_y = panel_y + 7, panel_y + font + 10
    cpu = __is_cpu_turn()
    if draw.layer('hud_panel', 0):
        draw.box(0, panel_y, width, height - panel_y, INK)
        draw.box(8, panel_y, width - 16, 1, SLATE)
        draw.text(12, label_y, "ANGLE", SLATE)
        draw.text(width // 3 + 5, label_y, "POWER", SLATE)
        draw.text(width * 2 // 3 + 4, label_y, "WIND", SLATE)
        draw.end_layer()
    turn_label = "THINK" if cpu else ("AIM" if phase == PHASE_AIMING else "FIRE")
    if draw.layer('hud_turn', (turn, turn_label, _state.left_player)):
        label_x = 10 if turn == _state.left_player else width - draw.len(turn_label) - 10
        draw.text(label_x, 23, turn_label, accent)
        draw.end_layer()
    if draw.layer('hud_angle', _state.angle):
        draw.text(12, value_y, "{} DEG".format(_state.angle), CREAM)
        draw.end_layer()
    if draw.layer('hud_power', (_state.power, turn)):
        draw.text(width // 3 + 5, value_y, str(_state.power), CREAM)
        bar_x, bar_w = width // 3 + 5, width // 3 - 18
        draw.box(bar_x, value_y + font + 3, bar_w, 3, PANEL)
        draw.box(bar_x, value_y + font + 3, bar_w * _state.power // 100, 3, accent)
        draw.end_layer()
    wind = _state.wind
    if draw.layer('hud_wind', wind):
        draw.text(width * 2 // 3 + 4, value_y, "CALM" if wind == 0 else "{} {}".format("<" if wind < 0 else ">", abs(wind)), TEAL)
        draw.end_layer()
    if draw.layer('hud_footer', cpu):
        footer = "CPU IS AIMING...   BACK: MENU" if cpu else "U/D AIM   L/R POWER   OK FIRE   BACK MENU"
        __center_text(draw, footer, height - font - 4, SLATE)
        draw.end_layer()


def __draw_hud_static(draw):
    """Keep title artwork and labels separate from changing aim information."""
    width = _state.width
    title_scale = 2 if width >= 250 else 1
    title_x = (width - 47 * title_scale) // 2
    if draw.layer('hud_static', (_state.environment, _state.players, tuple(_state.scores), _state.left_player)):
        draw.box(0, 0, width, 39, INK)
        __art(draw, TITLE_ART, title_x + 1, 8, title_scale, {'#': 0x91E9})
        __center_text(draw, _state.environment, 27, SLATE)
        for player in (0, 1):
            label = '{} {}/3'.format('P1' if player == 0 else ('CPU' if _state.players == 1 else 'P2'), _state.scores[player])
            label_x = 10 if player == _state.left_player else width - draw.len(label) - 10
            draw.text(label_x, 9, label, TEAL if player == 0 else CORAL)
        draw.end_layer()
    if draw.layer('hud_title', width):
        __art(draw, TITLE_ART, title_x, 7, title_scale, {'#': CREAM})
        draw.end_layer()


def __draw_menu(draw):
    """Main menu over the animated city, fitted to color and monochrome screens."""
    width, height = _state.width, _state.height
    compact, font = _state.compact, _state.font_height
    selected = _state.menu_selection
    if compact:
        draw.box(0, 0, width, height, 0)
        __center_text(draw, "GORILLAS: FIRST TO 3", 2, WHITE)
        for index, label in enumerate(("1 PLAYER / CPU", "2 PLAYERS", "EXIT")):
            y = 17 + index * 12
            if index == selected:
                draw.box(5, y - 2, width - 10, font + 4, WHITE)
            __center_text(draw, label, y, 0 if index == selected else WHITE)
        __center_text(draw, "U/D SELECT  OK PLAY", height - font - 1, WHITE)
        return
    title_scale = 3 if width >= 250 else 2
    __art(draw, TITLE_ART, (width - 47 * title_scale) // 2, 48, title_scale, {"#": CREAM})
    __center_text(draw, _state.environment, 48 + 7 * title_scale + 10, CREAM)
    panel_w = min(width - 28, 270)
    panel_h = max(122, font * 11 + 24)
    left, top = (width - panel_w) // 2, max(100, (height - panel_h) // 2)
    draw.box(left, top, panel_w, panel_h, INK)
    draw.box(left, top, panel_w, 2, TEAL)
    __center_text(draw, "FIRST TO 3 WINS", top + 11, SLATE)
    row_height = max(25, font + 15)
    for index, label in enumerate(("1 PLAYER", "2 PLAYERS", "EXIT")):
        y = top + 30 + index * row_height
        if index == selected:
            draw.box(left + 10, y - 4, panel_w - 20, font + 10, TEAL)
        __center_text(draw, label, y, INK if index == selected else CREAM)
    description = ("YOU VS THE COMPUTER", "LOCAL TWO-PLAYER DUEL", "RETURN TO GAMES")[selected]
    __center_text(draw, description, top + panel_h + 10, CREAM)
    __center_text(draw, "UP/DOWN SELECT   OK START   BACK EXIT", height - font - 5, SLATE)


def __draw_obstacle(entity, draw, game):
    """Render solid, destructible water tanks, roof barriers, and chimneys."""
    draw = _state.renderer
    index = int(entity.name[-1])
    terrain_index = len(_state.buildings) + index
    x, y, w, h, cols, rows, cells = _state.terrain[terrain_index]
    if not any(cells):
        return
    key = ("obstacle", index)
    cached = draw.terrain.get(key)
    if cached is not None:
        draw.blit(cached)
        __draw_obstacle_smoke(index, draw)
        return
    cached = draw.capture(x, y, w, h, key)
    compact, unit = _state.compact, _state.terrain_unit
    kind = _state.obstacle_kinds[index]
    body = WHITE if compact else (0x4B10, 0x8B4C, 0x626A)[kind]
    edge = WHITE if compact else (0x8495 if _state.season != 3 else WHITE)
    draw.set_terrain_clip(_state.terrain[terrain_index], _state.terrain_unit)
    draw.box(x, y, w, h, body)
    draw.box(x, y, unit, h, edge)
    draw.box(x + w - unit * 2, y, unit * 2, h, 0 if compact else INK)
    draw.box(x, y, w, unit, WHITE if _state.season == 3 else edge)
    if kind == 0:
        draw.box(x, y + h // 2, w, unit, 0 if compact else INK)
        draw.box(x, y + h - 4 * unit, w, unit, edge)
    elif kind == 1:
        # Hazard stripes mark an actual wall the banana must clear or break.
        for stripe in range(1, w - 2, 4 * unit):
            draw.box(x + stripe, y + 2 * unit, 2 * unit, max(1, h - 4 * unit), 0 if compact else GOLD)
    else:
        for row in range(3 * unit, h, 4 * unit):
            draw.box(x, y + row, w, unit, 0 if compact else INK)
    __draw_decals(draw, terrain_index)
    draw.set_terrain_clip(None, 1)
    draw.end_capture(key, cached)
    __draw_obstacle_smoke(index, draw)


def __draw_obstacle_smoke(index, draw):
    """Keep chimney smoke moving independently of cached masonry."""
    x, y, w = _state.terrain[len(_state.buildings) + index][:3]
    kind, compact = _state.obstacle_kinds[index], _state.compact
    if kind == 2 and not compact and __terrain_solid(x + w // 2, y):
        for puff in range(3):
            age = (_state.tick + puff * 24) % 72
            sx = x + w // 2 + sin(age / 14) * 3 + age * _state.wind / 50
            cx, cy, radius = int(sx), int(y - 3 - age / 4), 2 + age // 22
            draw.watch(('smoke', index, puff), radius, (cx - radius, cy - radius, cx + radius + 1, cy + radius + 1))
            draw.circle(cx, cy, radius, SLATE)


def __draw_sky(entity, draw, game):
    """Animated clouds, sunset, stars, and a distant city layer."""
    # Engine updates and all collision callbacks finish before scene drawing.
    __banana_finish()
    draw = _state.renderer
    draw.begin(INK, __ui_boxes(), _state.terrain, _state.terrain_unit)
    width, baseline, tick = _state.width, _state.baseline, _state.tick
    if _state.compact:
        for cloud in range(2):
            # Cache by the final pixel coordinate, including negative positions.
            x = int((cloud * 79 + _state.cloud_offset * (0.8 + cloud * 0.25)) % (width + 28) - 24)
            if draw.layer(('cloud', cloud), 0, background=True, position=(x, 12 + cloud * 8)):
                __art(draw, CLOUD_ART, x, 12 + cloud * 8, 1, {"h": WHITE, "s": 0})
                draw.end_layer()
        return
    sky_top = 39
    band_h = max(1, (baseline - sky_top) // len(SKY) + 1)
    key = ("sky", _state.day_time)
    cached = draw.terrain.get(key)
    if cached is None:
        cached = draw.capture(0, sky_top, width, band_h * len(SKY), 'sky_surface')
        for index, color in enumerate(_state.sky):
            draw.box(0, sky_top + index * band_h, width, band_h, color)
        draw.end_capture(key, cached)
    else:
        draw.blit(cached)
    night = _state.day_time == 3
    star_count = 35 if night else (0 if _state.day_time == 1 else 12)
    if star_count and draw.layer('stars', (_state.day_time, tick // 20 % 7), background=True):
        for star in range(star_count):
            x = (star * 71 + 23) % width
            y = sky_top + 8 + (star * 31) % max(12, (baseline - sky_top) // (2 if night else 3))
            color = CREAM if (tick // 20 + star) % 7 == 0 else SLATE
            draw.box(x, y, 1, 1, color)
        draw.end_layer()
    sun_x, sun_y = int(width * 0.72), int(sky_top + (baseline - sky_top) * 0.30)
    radius = max(12, width // 18)
    surprised = _state.phase == PHASE_FLYING and abs(_state.banana_x - sun_x) < radius * 2 and abs(_state.banana_y - sun_y) < radius * 2
    key = ("sun", night, surprised)
    cached = draw.terrain.get(key)
    if cached is None:
        cached = draw.capture(sun_x - radius, sun_y - radius, radius * 2 + 1, radius * 2 + 1, 'sun_surface')
        draw.fill_circle(sun_x, sun_y, radius, 0xCE9D if night else GOLD)
        draw.fill_circle(sun_x, sun_y - 2, radius - 2, 0xEF7F if night else CREAM)
        if night:
            draw.fill_circle(sun_x - radius // 3, sun_y - 4, max(2, radius // 4), 0xADB9)
            draw.fill_circle(sun_x + radius // 3, sun_y + 5, max(1, radius // 6), 0xADB9)
        else:
            draw.box(sun_x - 6, sun_y - 3, 2, 3, INK)
            draw.box(sun_x + 4, sun_y - 3, 2, 3, INK)
        if surprised and not night:
            draw.circle(sun_x, sun_y + 5, 3, INK)
        elif not night:
            draw.box(sun_x - 3, sun_y + 6, 6, 1, INK)
            draw.box(sun_x - 5, sun_y + 4, 2, 2, INK)
            draw.box(sun_x + 3, sun_y + 4, 2, 2, INK)
        draw.end_capture(key, cached)
    else:
        draw.blit(cached)
    for cloud in range(4):
        cloud_scale = 2 if cloud % 2 == 0 else 1
        drift = _state.cloud_offset * (0.8 + cloud * 0.25)
        # Match art() pixel rounding so subpixel drift reuses the cached layer.
        x = int((cloud * width // 3 + drift) % (width + 60) - 50)
        y = sky_top + 10 + (cloud * 23) % max(20, (baseline - sky_top) // 2)
        if draw.layer(('cloud', cloud), _state.day_time, background=True, position=(x, y)):
            __art(draw, CLOUD_ART, x, y, cloud_scale, _state.cloud_palette)
            draw.end_layer()
    key = ("distant", _state.day_time)
    cached = draw.terrain.get(key)
    if cached is None:
        cached = draw.capture(0, sky_top, width, baseline - sky_top, 'distant_surface')
        for layer in range(2):
            step = max(12, width // (18 if layer == 0 else 14))
            color = _state.distant_colors[layer]
            for index in range(width // step + 1):
                h = 15 + ((index * 37 + layer * 23 + _state.city_seed) % max(20, (baseline - sky_top) // 3))
                draw.box(index * step, baseline - h, step - 2, h, color)
                if index % 4 == 1:
                    draw.box(index * step + step // 2, baseline - h - 7, 1, 7, color)
        draw.end_capture(key, cached)
    else:
        draw.blit(cached)
    season = _state.season
    if season != 1:
        count = 11 if season == 3 else (5 if season == 2 else 10)
        for fleck in range(count):
            drift = _state.cloud_offset * 2 + sin(tick / 25 + fleck) * 5
            x = int((fleck * 71 + _state.city_seed + drift) % width)
            y = sky_top + int((fleck * 37 + tick * (0.45 if season == 3 else 0.65)) % (baseline - sky_top))
            color = WHITE if season == 3 else (0xFDB0 if season == 2 else 0xFCDD)
            draw.watch(('fleck', fleck), color, (x, y, x + (2 if season == 2 else 1), y + 2), True)
            draw.box(x, y, 2 if season == 2 else 1, 2, color)


def __finish_turn():
    """Award the surviving player, or pass control after an impact."""
    if _state.phase != PHASE_EXPLODING:
        return
    if _state.dead:
        if len(_state.dead) == 1:
            winner = 1 - _state.dead[0]
            _state.scores[winner] += 1
            if _state.scores[winner] >= MATCH_WINS:
                _state.message = "CPU wins" if _state.players == 1 and winner == 1 else "Player {} wins".format(winner + 1)
                _state.phase = PHASE_GAME_OVER
                return
        # Non-final wins and draws flow straight into the next duel once the
        # explosion finishes. Scores persist and the starting player alternates.
        __reset_round()
        return
    _state.turn = 1 - _state.turn
    _state.angle, _state.power = _state.aims[_state.turn]
    _state.round += 1
    _state.wind = (_state.round * 7) % 11 - 5
    _state.phase = PHASE_AIMING
    _state.trail.clear()
    _state.ai_index, _state.ai_ticks = 0, 0
    _state.ai_search = None
    _state.ai_best = (1e12, 50, 80)


def __game_over_box():
    """Fit the result panel to its text, leaving the rooftop gorillas visible."""
    draw = _state.renderer
    width, height, font = _state.width, _state.height, _state.font_height
    compact = _state.compact
    padding = 3 if compact else 6
    panel_width = min(width - 6, max(draw.len(_state.message), draw.len(__score_text()), draw.len(__result_prompt())) + padding * 2)
    left = (width - panel_width) // 2
    panel_height = font * 3 + 17
    top = (height - panel_height) // 2
    return (left, top, left + panel_width, top + panel_height)


def __intact_rectangle(terrain, x, y, width, height):
    """Hide a sign or decal when its supporting masonry has been destroyed."""
    step = _state.terrain_unit
    for yy in range(y, y + height, step):
        for xx in range(x, x + width, step):
            if not __terrain_cell(terrain, xx, yy):
                return False
    return True


def __is_cpu_turn():
    """Return whether the computer currently owns the aiming controls."""
    return _state.players == 1 and _state.turn == 1 and _state.phase == PHASE_AIMING


def __launch_position():
    """Start the projectile completely above the shooter's collision box."""
    gorilla = _state.gorillas[_state.turn]
    return gorilla.position.x + gorilla.size.x / 2, gorilla.position.y - 5 * _state.pixel_scale


@native
def __mix_color(first, second, amount):
    """Blend RGB565 palette entries once when the match starts."""
    red = (((first >> 11) & 31) * (256 - amount) + ((second >> 11) & 31) * amount) // 256
    green = (((first >> 5) & 63) * (256 - amount) + ((second >> 5) & 63) * amount) // 256
    blue = ((first & 31) * (256 - amount) + (second & 31) * amount) // 256
    return (red << 11) | (green << 5) | blue


def __randomize_city():
    """Regenerate the skyline while retaining the native scene's entities."""
    _state.renderer.invalidate(artwork=False)
    compact, width = _state.compact, _state.width
    baseline, unit = _state.baseline, _state.terrain_unit
    count = len(_state.buildings)
    left, right = randint(0, count // 2 - 1), randint(count // 2 + 1, count - 1)
    _state.left_player = randint(0, 1)
    _state.spawn_buildings = (left, right) if _state.left_player == 0 else (right, left)
    margin, gap = (3, 2) if compact else (8, 3)
    available = width - 2 * margin - gap * (count - 1)
    hero_width = int(_state.gorillas[0].size.x)
    minimum = 10 if compact else max(18, width // 20)
    widths = [minimum] * count
    widths[left] = widths[right] = max(minimum, hero_width)
    extra = available - sum(widths)
    weights = [randint(3, 10) for _ in range(count)]
    total = sum(weights)
    for index in range(count):
        widths[index] += extra * weights[index] // total
    for index in range(available - sum(widths)):
        widths[index % count] += 1
    _state.city_seed = randint(0, 65535)
    __set_environment(randint(0, 3), randint(0, 3))
    old_heights = tuple(t[3] for t in _state.terrain[:count])
    _state.terrain_columns = ()
    _state.terrain.clear()
    x = margin
    for index, building in enumerate(_state.buildings):
        endpoint = index in _state.spawn_buildings
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
        _state.terrain.append((x, y, w, height, cols, rows, cells))
        x += w + gap
    _state.obstacle_hosts.clear()
    _state.obstacle_kinds.clear()
    hosts = [index for index in range(count) if index not in _state.spawn_buildings]
    for index, obstacle in enumerate(_state.obstacles):
        host = hosts.pop(randint(0, len(hosts) - 1))
        bx, by, bw = _state.terrain[host][:3]
        kind = (index + _state.city_seed) % 3
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
        _state.terrain.append((x, y, w, h, cols, rows, cells))
        _state.obstacle_hosts.append(host)
        _state.obstacle_kinds.append(kind)
    for index, gorilla in enumerate(_state.gorillas):
        building = _state.buildings[_state.spawn_buildings[index]]
        x = building.position.x + (building.size.x - gorilla.size.x) / 2
        y = building.position.y - gorilla.size.y - 2
        gorilla.position = Vector(x, y)
    # The buckets keep references to live cells, so blast holes need no rebuild.
    _state.terrain_columns = tuple(
        tuple(terrain for terrain in _state.terrain
              if terrain[0] < column + 16 and terrain[0] + terrain[2] > column)
        for column in range(0, width, 16)
    )
    _state.renderer.prepare_effect(_state.pixel_scale, compact)


def __render_scene(entity, draw, game):
    """Render/present once through player one's native engine render callback."""
    __draw_sky(None, None, _game)
    for building in _state.buildings:
        __draw_building(building, None, _game)
    for obstacle in _state.obstacles:
        __draw_obstacle(obstacle, None, _game)
    for gorilla in _state.gorillas:
        __draw_gorilla(gorilla, None, _game)
    __draw_hud(None, None, _game)


def __reset_round(new_match=False):
    """Create a fresh duel, keeping match scores unless starting a new match."""
    if new_match:
        _state.scores[:] = [0, 0]
        _state.starter = 0
    else:
        _state.starter = 1 - _state.starter
    _state.message = ""
    _state.angle, _state.power = 52, 50
    _state.phase, _state.turn, _state.round, _state.wind = PHASE_AIMING, _state.starter, 1, 0
    _state.hit_player = -1
    _state.dead.clear()
    _state.falling.clear()
    _state.aims = [(52, 50), (52, 50)]
    _state.ai_index, _state.ai_ticks = 0, 0
    _state.ai_search = None
    _state.ai_shots = 0
    _state.ai_best = (1e12, 50, 80)
    _state.particles.clear()
    _state.explosion_frames = 0
    _state.banana.position = Vector(-32, -32)
    _state.trail.clear()
    __randomize_city()
    _state.last_frame, _state.remainder, _state.steps = ticks_ms(), 0, 1


def __resolve_shot(victim):
    """Destroy masonry, apply blast damage, and start debris and death animations."""
    if _state.phase != PHASE_FLYING:
        return
    x, y = int(_state.banana_x), int(_state.banana_y)
    _state.explosion_x, _state.explosion_y = x, y
    _state.explosion_frames, _state.hit_player = EXPLOSION_TICKS, victim
    _state.phase = PHASE_EXPLODING
    _state.banana.is_visible = False
    _state.banana.position = Vector(-32, -32)
    scale = _state.pixel_scale
    radius = (6 if _state.compact else 10) * scale
    __damage_terrain(x, y, radius)
    for index, gorilla in enumerate(_state.gorillas):
        pos, size = gorilla.position, gorilla.size
        nearest_x = max(pos.x, min(x, pos.x + size.x))
        nearest_y = max(pos.y, min(y, pos.y + size.y))
        if index == victim or (nearest_x - x) ** 2 + (nearest_y - y) ** 2 <= radius * radius:
            _state.dead.append(index)
    _state.particles.clear()
    for index in range(10 if _state.compact else 22):
        angle = index * 2.399 + _state.tick / 10
        speed = (0.4 + index % 5 * 0.17) * scale
        _state.particles.append((cos(angle) * speed, sin(angle) * speed - scale * 0.5, (1 + index % 3) * scale))
    __settle_gorillas()


def __result_prompt():
    """The result screen is shown only after the match is won."""
    return "OK: NEW MATCH"


def __score_text():
    """Show both scores and the first-to-three target on either display."""
    opponent = "CPU" if _state.players == 1 else "P2"
    return "P1 {}-{} {} /3".format(_state.scores[0], _state.scores[1], opponent)


def __set_environment(day_time, season):
    """Prepare a time-of-day sky and seasonal materials for this match."""
    _state.day_time, _state.season = day_time, season
    _state.environment = SEASONS[season] + " / " + DAY_TIMES[day_time]
    top, bottom = ((0x52D2, 0xFE35), (0x3498, 0xC73F), (SKY[0], SKY[-1]), (0x0843, 0x212C))[day_time]
    tint = (0xABF4, 0xFDD0, 0xEB48, 0xB65E)[season]
    colors = SKY if day_time == 2 else tuple(__mix_color(top, bottom, index * 256 // 9) for index in range(10))
    _state.sky = tuple(__mix_color(color, tint, 12 if day_time == 3 else 28) for color in colors)
    facade_tint = (0x3B0D, 0x734D, 0xAB49, 0x8495)[season]
    _state.facades = tuple(tuple(__mix_color(color, facade_tint, 60) for color in facade) for facade in FACADES)
    cloud_light, cloud_shadow = ((0xDEDC, 0xA475), (WHITE, 0xAE1B), (0xAD15, 0x83B2), (0x4A70, 0x294A))[day_time]
    _state.cloud_palette = {"h": cloud_light, "s": cloud_shadow}
    _state.distant_colors = (__mix_color(_state.sky[7], INK, 100), __mix_color(_state.sky[7], INK, 175))


def __settle_gorillas():
    """Losing current footing is fatal, even if lower masonry survives."""
    for index, gorilla in enumerate(_state.gorillas):
        if index in _state.dead:
            continue
        x = int(gorilla.position.x + gorilla.size.x / 2)
        foot_y = int(gorilla.position.y + gorilla.size.y + 2)
        if not any(__terrain_solid(xx, foot_y) for xx in range(x - 2, x + 3)):
            _state.dead.append(index)
            _state.falling.append(index)


def __terrain_cell(terrain, x, y):
    """Read surviving masonry directly; zero cells are holes, not colliders."""
    bx, by, width, height, cols, rows, cells = terrain
    if not bx <= x < bx + width or not by <= y < by + height:
        return False
    unit = _state.terrain_unit
    return bool(cells[((int(y) - by) // unit) * cols + (int(x) - bx) // unit])


def __terrain_solid(x, y):
    """Query terrain cells for aiming/support without a duplicate pixel map."""
    if x < 0 or y < 0 or x >= _state.width or y >= _state.height:
        return False
    for terrain in _state.terrain_columns[int(x) // 16]:
        if __terrain_cell(terrain, x, y):
            return True
    return False


def __throw():
    """Launch the spinning banana into the native collision scene."""
    radians = _state.angle * pi / 180
    velocity = _state.power * 0.105 * _state.physics_scale
    _state.banana_x, _state.banana_y = __launch_position()
    _state.banana_vx = cos(radians) * velocity * __direction(_state.turn)
    _state.banana_vy = -sin(radians) * velocity
    _state.banana.position = Vector(_state.banana_x, _state.banana_y)
    _state.banana.is_visible = True
    _state.flight_ticks = 0
    _state.aims[_state.turn] = (_state.angle, _state.power)
    _state.trail.clear()
    _state.phase = PHASE_FLYING




def __ui_boxes():
    """Opaque UI areas also define the HUD's explicit repaint regions."""
    width, height, font = _state.width, _state.height, _state.font_height
    compact, phase = _state.compact, _state.phase
    if phase == PHASE_MENU:
        if compact:
            return ((0, 0, width, height),)
        panel_w, panel_h = min(width - 28, 270), max(122, font * 11 + 24)
        left, top = (width - panel_w) // 2, max(100, (height - panel_h) // 2)
        return ((left, top, left + panel_w, top + panel_h),)
    boxes = ((0, 0, width, font + 3 if compact else 39),
             (0, height - font - 2 if compact else _state.baseline + 3, width, height))
    if phase == PHASE_GAME_OVER:
        boxes += (__game_over_box(),)
    return boxes


def __update_aim(button):
    """Adjust angle in four-degree steps; retain finer two-unit power steps."""
    if button == BUTTON_DOWN:
        _state.angle = max(5, _state.angle - 4)
    elif button == BUTTON_UP:
        _state.angle = min(85, _state.angle + 4)
    elif button == BUTTON_RIGHT:
        _state.power = min(100, _state.power + 2)
    elif button == BUTTON_LEFT:
        _state.power = max(20, _state.power - 2)


def run(view_manager):
    """Consume input and run one native engine frame, including ambient animation."""
    if _engine is None:
        view_manager.back()
        return
    frame_started = ticks_ms()
    elapsed = min(132, max(0, ticks_diff(frame_started, _state.last_frame)))
    elapsed += _state.remainder
    _state.last_frame = frame_started
    _state.steps = min(4, elapsed // 33)
    _state.remainder = elapsed % 33
    button = view_manager.button
    if button == BUTTON_BACK:
        if _state.phase == PHASE_MENU:
            view_manager.back()
        else:
            _state.phase = PHASE_MENU
            _state.banana.position = Vector(-32, -32)
            _state.trail.clear()
        return
    if _state.phase == PHASE_MENU:
        if button in (BUTTON_UP, BUTTON_LEFT):
            _state.menu_selection = (_state.menu_selection - 1) % 3
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            _state.menu_selection = (_state.menu_selection + 1) % 3
        elif button == BUTTON_CENTER:
            if _state.menu_selection == 2:
                view_manager.back()
                return
            _state.players = _state.menu_selection + 1
            __reset_round(new_match=True)
    elif _state.phase == PHASE_GAME_OVER:
        if button == BUTTON_CENTER:
            __reset_round(new_match=True)
    elif _state.phase == PHASE_AIMING:
        if __is_cpu_turn():
            __ai_update()
        elif button == BUTTON_CENTER:
            __throw()
        else:
            __update_aim(button)
    if _state.phase == PHASE_EXPLODING:
        _state.explosion_frames -= _state.steps
        if _state.explosion_frames <= 0:
            __finish_turn()
    _state.tick += _state.steps
    # Integrate wind so changing its strength never teleports the cloud layer.
    wind = _state.wind
    _state.cloud_offset += (wind * 0.09 if wind else 0.015) * _state.steps
    _engine.run_async(False)


def start(view_manager):
    """Load the scene and the original pixel-art assets."""
    if _engine is not None:
        return True
    collect()
    __create_scene(view_manager)
    _engine.run_async(False)
    collect()
    return True


def stop(view_manager):
    """Drop scene references after leaving the game view."""
    global _engine, _game, _level, _state
    if _state is not None:
        _state.renderer.close()
    if _engine is not None:
        _engine.stop()
        del _engine
    _engine = None
    _game = None
    _level = None
    _state = None
    collect()
