"""PGE Adventure: open-world 3D RPG."""
from gc import collect
from math import atan2, cos, pi, sin
from picoware.system.vector import Vector
from picoware.engine.entity import (
    Entity, ENTITY_TYPE_ENEMY, ENTITY_TYPE_3D_SPRITE,
    SPRITE_3D_CUSTOM, SPRITE_3D_NONE, ENTITY_TYPE_PLAYER,
    ENTITY_TYPE_NPC
)
from picoware.engine.sprite3d import Sprite3D
from picoware.engine.camera import CAMERA_FIRST_PERSON, CAMERA_THIRD_PERSON

from picoware.system.buttons import (
    BUTTON_BACK, BUTTON_CENTER, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP,
    BUTTON_1, BUTTON_2, BUTTON_3, BUTTON_4, BUTTON_5, BUTTON_K, BUTTON_L,
    BUTTON_O, BUTTON_P, BUTTON_SPACE
)

from picoware.system.decorator import wifi_required, storage_required, server_settings_required

_adv = None
_seed = 0x51F0A3D


def xp_for_level(level):
    """XP required to advance from level-1 to level."""
    if level < 2:
        return 0
    return int(100 * (1.5 ** (level - 2)))


def health_for_level(level):
    """Max health awarded at a level."""
    return 100 + (level - 1) * 10


def strength_for_level(level):
    """Attack strength awarded at a level."""
    return 10 + (level - 1)


def zone_for(x, z):
    """Map world X/Z to a faction quadrant."""
    if x < 0:
        return 0 if z < 0 else 2
    return 1 if z < 0 else 3


def _next_random(limit):
    """Return a pseudo-random integer below limit."""
    global _seed

    _seed = (_seed * 1103515245 + 12345) & 0x7FFFFFFF
    return _seed % limit


def _hash(col, row, salt):
    """Return a stable hash for a world cell and salt."""
    value = (col * 73856093) ^ (row * 19349663) ^ (salt * 83492791)
    return value & 0x7FFFFFFF


def _shade(color, factor):
    """Scale an RGB565 color toward black."""
    r = int(((color >> 11) & 0x1F) * factor)
    g = int(((color >> 5) & 0x3F) * factor)
    b = int(((color & 0x1F) * factor))
    return (r << 11) | (g << 5) | b


def _player_update(entity, game):
    """Forward the player callback to the active game."""
    if _adv is not None:
        _adv.update_player(entity, game)


def _enemy_update(entity, _game):
    """Forward an enemy callback to the active game."""
    if _adv is not None:
        _adv.update_enemy(entity)

def _enemy_render(entity, draw, game):
    """Draw the health bar above an enemy."""
    if _adv is None:
        return
    if not entity.is_visible or entity.max_health <= 0:
        return
    screen_w = draw.size.x
    screen_h = draw.size.y
    bar_h = draw.scale_y(3)
    bar_w = int(draw.scale_y(20) * entity.sprite_scale)
    bar_w = max(bar_w, draw.scale_x(10))
    px, py = _adv._project(entity.position.x, entity.position.y,
                            2.0 * entity.sprite_scale, screen_w, screen_h)
    if px < 0:
        return
    left = int(px - bar_w * 0.5)
    top = int(py)
    if left < 0 or left + bar_w > screen_w or top < 0 or top + bar_h > screen_h:
        return
    ratio = max(0.0, min(1.0, entity.health / entity.max_health))
    draw._fill_rectangle(left, top, bar_w, bar_h, _adv.COLOR_HP_BACK)
    draw._fill_rectangle(left, top, bar_w * ratio, bar_h, _adv.COLOR_HP)

def _background_render(_entity, draw, _game):
    """Draw sky, horizon haze and ground by zone."""
    if _adv is None:
        return
    zone = zone_for(_adv.player.position.x, _adv.player.position.y)
    width = draw.size.x
    height = draw.size.y
    horizon = int(height * 0.54)
    haze = min(draw.scale_y(16), height - horizon)
    sky = _shade(_adv.ZONE_SKY[zone], _adv.light)
    fog = _shade(_adv.ZONE_FOG[zone], _adv.light)
    ground_top = horizon + haze
    draw._fill_rectangle(0, 0, width, horizon, sky)
    draw._fill_rectangle(0, horizon, width, haze, fog)
    draw._fill_rectangle(0, ground_top, width, height - ground_top,
                    _adv.ZONE_GROUND[zone])

def _effect_update(entity, _game):
    """Expire one timed visual effect."""
    if not entity.is_visible:
        return
    entity.attack_timer -= 1
    if entity.attack_timer <= 0:
        entity.attack_timer = 0
        entity.is_visible = False


def _on_projectile_collision(entity, other, _game):
    """Damage the enemy struck by a projectile."""
    if _adv is None or other.type != ENTITY_TYPE_ENEMY:
        return
    _adv._projectile_hit(entity, other)

def _projectile_update(entity, _game):
    """Move one projectile and resolve its lifetime and hits."""
    if _adv is None or not entity.is_visible:
        return
    if entity.elapsed_attack_timer > 0:
        _adv._finish_projectile(entity)
        return
    direction = entity.start_position
    position = entity.position
    entity.position_set(
        position.x + direction.x * entity.speed,
        position.y + direction.y * entity.speed,
        1.0,
    )
    if entity.state == 1:
        entity.sprite_scale += _adv.PROJECTILE_ORB_GROWTH
    pos = entity.position
    hit_sq = _adv.PROJECTILE_HIT_RADIUS * _adv.PROJECTILE_HIT_RADIUS
    for enemy in _adv._target_list:
        if not enemy.is_visible:
            continue
        dx = pos.x - enemy.position.x
        dz = pos.y - enemy.position.y
        if dx * dx + dz * dz < hit_sq:
            _adv._projectile_hit(entity, enemy)
            break
    entity.attack_timer -= 1
    if entity.elapsed_attack_timer > 0 or entity.attack_timer <= 0:
        _adv._finish_projectile(entity)


@storage_required
@wifi_required
@server_settings_required
def start(view_manager) -> bool:
    """Start the PGE Adventure view."""
    global _adv

    _adv = _Adventure(view_manager)
    return _adv is not None


def run(view_manager) -> None:
    """Run one PGE Adventure frame."""
    if _adv is None:
        view_manager.back()
        return
    if not _adv.scene_open:
        if not _adv.boot():
            view_manager.back()
        return

    _adv.run()
    if _adv.exit_requested:
        view_manager.back()


def stop(_view_manager) -> None:
    """Stop PGE Adventure and release resources."""
    global _adv

    if _adv is not None:
        _adv.stop()
        del _adv
        _adv = None
    collect()


class _Adventure:
    """Own the world, player, enemies, quests and story state."""

    FIELD_OF_VIEW = 35.0
    CHUNK_LAG = 12.0
    CELL = 25.0
    SCENE_ANCHOR_Z = -1000.0
    BACKGROUND_Z = 1.0e6  # backdrop sorts behind all
    WORLD_HALF_X = 5000.0
    WORLD_HALF_Z = 2500.0
    CAMERA_DISTANCE = 13.0
    CAMERA_DIR_X = 0.0
    CAMERA_DIR_Z = 1.0
    CAMERA_HEIGHT = 3.5
    CAMERA_FIRST_HEIGHT = 1.6
    WALK_SPEED = 1.68
    WALK_BACK = 0.88
    WALK_TURN = 0.28
    # Mesh yaw differs from facing.
    PLAYER_ANGLE = 0.7
    ENEMY_COUNT = 3  # keep as multiple of 3...
    ENEMY_FILES = ("ghoul", "goblin", "soldier")
    ENEMY_CELL = 15.0
    ENEMY_CHANCE = 3  # one enemy cell per N
    RECYCLE_DISTANCE = 72.0
    AGGRO_RANGE = 15.0
    HIT_RANGE = 1.5
    TALK_RANGE = 3.6
    DRAGON_RANGE = 24.0
    EFFECT_FRAMES = 14
    COMBO_WINDOW = 14
    MINIMAP_W = 64.0
    MINIMAP_H = 32.0
    BOSS_LEVEL_GAP = 10
    LAND_FILES = ("grassland", "forestland", "barren-land")
    LAND_COUNT = 3
    LAND_CELL = 20.0
    LAND_SCALE = 2.0
    EFFECT_FILES = ("lightning", "fire-blast", "orb", "fire-ball")
    GUIDE_DISTANCE = 2.3
    HOUSE_POS = (-795.0, -690.0)
    BIRD_HEIGHT = 6.0
    BIRD_FLIGHT = 90   # frames per bird flight
    SPEED_MAX = 2.0    # default multiplier + 2
    SPEED_STEP = 0.2
    SHADOW_COLOR = 0x18E3  # ground shading tint
    CLOCK_START = 8 * 60   # 08:00
    TIME_STEP = 3          # frames per in-game minute
    MENU_ITEMS = ("Map", "Stats", "Camera", "Leave Game")

    COLOR_BLACK = 0x0000
    COLOR_WHITE = 0xFFFF
    COLOR_HP = 0xF800
    COLOR_HP_BACK = 0x3000
    COLOR_XP = 0x07E0
    COLOR_XP_BACK = 0x0320
    COLOR_TEXT = 0xFFE0
    COLOR_ACCENT = 0x07FF
    COLOR_DIM = 0x7BEF
    COLOR_PLAYER = 0x07FF
    COLOR_TRUNK = 0x6B4D
    COLOR_LEAF = 0x07E0
    COLOR_ROCK = 0x9CD3
    COLOR_WOOD = 0xB2C6
    COLOR_ROOF = 0x632C
    COLOR_GHOUL = 0xCE59
    COLOR_GOBLIN = 0x0780
    COLOR_SOLDIER = 0xF800
    COLOR_DRAGON = 0xF81F
    COLOR_WIZARD = 0x781F

    # Zones: Nolands, Ghouls, Goblins, Soldiers.
    ZONE_NAMES = ("Nolands", "Ghouls", "Goblins", "Soldiers")
    ZONE_GROUND = (0x3C67, 0x3186, 0x6A45, 0x3C67)
    ZONE_SKY = (0x2C9F, 0x18C3, 0x1945, 0x2C9F)
    ZONE_FOG = (0x9D3F, 0x4208, 0x2D6B, 0x9D3F)
    ZONE_ENEMY = (0x07E0, 0xCE59, 0x0780, 0xF800)
    ZONE_STRONG = ("", "wooden house", "underground manor", "wooden fortress")

    # Strongholds: x, z, radius.
    STRONGHOLDS = ((0.0, 0.0, 0.0), (3000.0, -1500.0, 300.0),
                   (-3000.0, 1500.0, 300.0), (3200.0, 1400.0, 320.0))
    PLAYER_SPAWN = (-820.0, -770.0)
    WIZARD_POS = (-820.0, -700.0)

    SAVE_PATH = "picoware/settings/pge_adventure.json"


    NET_OFF = 0    # local only
    NET_LOGIN = 1  # login request in flight
    NET_FETCH = 2  # game-stats request in flight
    NET_READY = 3  # logged in, stats syncable
    NET_ERROR = 4  # request failed


    BOOT_LOGIN = 0  # login or register in flight
    BOOT_SCENE = 1  # scene open


    UI_NONE = 0  # playing
    UI_HELP = 1  # controls help
    UI_MENU = 2  # map/stats overlay

    CLASS_PATH = "picoware/apps/games/pge_adventure/classes.json"
    QUEST_PATH = "picoware/apps/games/pge_adventure/quests.json"
    FACTIONS = ("ghouls", "goblins", "soldiers")

    # Mage skills show effect sprites.
    SKILL_FX = {"Lightning": "lightning", "FireBlast": "fire-blast",
                "Orb": "orb"}

    # Projectiles replace instant AOE.
    PROJECTILE_NAMES = ("FireBlast", "Orb")
    PROJECTILE_SPEED = 0.8
    PROJECTILE_HIT_RADIUS = 2.5
    PROJECTILE_ORB_GROWTH = 0.08
    MIGHT_WINDUP = 14
    MIGHT_IMPACT_RADIUS = 3.0
    CONQUER_DISTANCE = 12.0
    CONQUER_FRAMES = 6
    ATTACK_RETURN_FRAMES = 3
    LIGHT_TABLE = tuple(
        (0.25 + 0.75 * max(0.0, sin((hour - 6.0) / 12.0 * pi)),
         cos((hour - 6.0) / 12.0 * pi),
         sin((hour - 6.0) / 12.0 * pi) * 0.5)
        for hour in range(24)
    )
    HALO_HEIGHT = 0.4

    __slots__ = (
        "view_manager",
        "draw",
        "http",
        "net_state",
        "net_pending",
        "net_dirty",
        "net_user",
        "net_pass",
        "net_status",
        "_loaded",
        "scene_open",
        "boot_state",
        "tried_register",
        "game",
        "level",
        "world_mesh",
        "meshes",
        "sprites",
        "enemies",
        "lands",
        "player",
        "wizard",
        "guide",
        "bird",
        "engine",
        "enemy_home",
        "enemy_ready",
        "dragon",
        "effects",
        "world_ready",
        "pending_world",
        "phase",
        "heading",
        "class_index",
        "class_name",
        "class_names",
        "class_cache",
        "class_cache_index",
        "xp_to_next",
        "skills_unlocked",
        "dragon_defeated",
        "armor_earned",
        "intro_done",

        "attack_cd",
        "skill_cd",
        "special_cd",
        "special_active",
        "buff_timer",
        "buff_stat",
        "halos",
        "_halo_entity",
        "combo_timer",
        "prev_button",

        "quest_index",
        "quest_counts",
        "quest_cache",
        "quest_cache_zone",
        "quest_cache_index",
        "q_kills",
        "q_streak",
        "q_timer",
        "q_low",
        "strong_found",
        "strong_kills",
        "faction_done",
        "talked_flag",
        "dragon_spawned",
        "wizard_met",

        "clock",
        "time_step",
        "light",

        "talking",
        "speed_scale",
        "base_speed",
        "bird_used",
        "bird_delay",
        "bird_dx",
        "bird_dz",

        "message",
        "message_timer",
        "dialogue",
        "dialogue_timer",
        "ui",
        "menu_index",
        "exit_requested",
        "anchor_x",
        "anchor_z",
        "land_anchor_x",
        "land_anchor_z",
        "land_type",

        "camera",
        "_loading",
        "old_xp",
        "old_level",
        "_server_level",

        "quest_line_cache",
        "quest_line_key",
        "_target_list",
        "sword_triangles",
        "beast_triangles",
        "beast_right_side",
        "beast_swing_mode",
        "chaos_frames",
        "chaos_yaw",
        "chaos_power",
        "attack_return_x",
        "attack_return_z",
        "attack_return_frames",
        "player_yaw",
        "sword_yaw",
        "sword_swing",
        "sword_swing_frames",
        "conquer_frames",
        "conquer_speed",
        "conquer_dirx",
        "conquer_dirz",
        "conquer_power",
        "conquer_hit",
        "might_windup",
        "might_power",
        "might_radius",
        "cos_h",
        "sin_h",
    )

    def __init__(self, view_manager):
        """Initialize state, load progress and start boot.

        Args:
            view_manager: View manager providing draw, storage and WiFi.
        """
        self.view_manager = view_manager
        self.draw = view_manager.draw
        self.http = None
        self.net_state = self.NET_OFF
        self.net_dirty = False
        self.net_user = ""
        self.net_pass = ""
        self.net_status = ""
        self._loaded = self._load_progress()
        self.scene_open = False
        self.boot_state = self.BOOT_LOGIN
        self.tried_register = False
        self.game = None
        self.level = None
        self.world_mesh = None
        self.meshes = []
        self.sprites = []
        self.enemies = []
        self.lands = []
        self.player = None
        self.wizard = None
        self.guide = None
        self.bird = None
        self.engine = None
        self.camera = None

        self.enemy_home = []
        self.enemy_ready = []
        self.dragon = None
        self.effects = {}
        self.world_ready = False
        self.pending_world = False

        self.phase = 0  # phases: intro, select, play
        self.heading = pi * 0.5
        self.class_index = 0
        self.class_name = ""
        self.class_names = []
        self.class_cache = None
        self.class_cache_index = -1
        self.xp_to_next = 0
        self.skills_unlocked = 1
        self.dragon_defeated = False
        self.armor_earned = False
        self.intro_done = False

        self.attack_cd = 0
        self.skill_cd = [0, 0, 0, 0]
        self.special_cd = 0
        self.special_active = 0
        self.buff_timer = 0
        self.buff_stat = ""
        self.halos = {}
        self._halo_entity = {}
        self.combo_timer = 0
        self.prev_button = -1

        self.quest_index = [0, 0, 0, 0]
        self.quest_counts = [0, 0, 0, 0]
        self.quest_cache = None
        self.quest_cache_zone = 0
        self.quest_cache_index = -1
        self.q_kills = [0, 0, 0, 0]
        self.q_streak = [0, 0, 0, 0]
        self.q_timer = [0, 0, 0, 0]
        self.q_low = [False, False, False, False]
        self.strong_found = [False, False, False, False]
        self.strong_kills = [0, 0, 0, 0]
        self.faction_done = [False, False, False, False]
        self.talked_flag = False
        self.dragon_spawned = False
        self.wizard_met = False

        self.clock = self.CLOCK_START
        self.time_step = 0
        self.light = 1.0

        self.talking = False
        self.speed_scale = 1.0
        self.base_speed = 1.0
        self.bird_used = 0
        self.bird_delay = 300
        self.bird_dx = 0.0
        self.bird_dz = 0.0

        self.message = ""
        self.message_timer = 0
        self.dialogue = ""
        self.dialogue_timer = 0
        self.ui = self.UI_NONE
        self.menu_index = 0
        self.exit_requested = False
        self.anchor_x = self.PLAYER_SPAWN[0]
        self.anchor_z = self.PLAYER_SPAWN[1]
        self.land_anchor_x = self.anchor_x
        self.land_anchor_z = self.anchor_z
        self.land_type = zone_for(self.anchor_x, self.anchor_z)
        if self.land_type >= len(self.LAND_FILES):
            self.land_type = 0

        self._loading = None
        self.old_xp = -1
        self.old_level = 1
        self._server_level = 0

        self.quest_line_cache = None
        self.quest_line_key = None
        self._target_list = []   # Cache targets between frames.
        self.sword_triangles = []
        self.beast_triangles = []
        self.beast_right_side = 1
        self.beast_swing_mode = 0
        self.chaos_frames = 0
        self.chaos_yaw = 0.0
        self.chaos_power = 1.0
        self.attack_return_x = 0.0
        self.attack_return_z = 0.0
        self.attack_return_frames = 0
        self.player_yaw = self.PLAYER_ANGLE
        self.sword_yaw = self.heading
        self.sword_swing = 0.0
        self.sword_swing_frames = 0
        self.conquer_frames = 0
        self.conquer_speed = 0.0
        self.conquer_dirx = 1.0
        self.conquer_dirz = 0.0
        self.conquer_power = 3.0
        self.conquer_hit = set()
        self.might_windup = 0
        self.might_power = 1.0
        self.might_radius = 6.0
        self.cos_h = cos(self.heading)
        self.sin_h = sin(self.heading)

        self._boot_begin()

    def _mesh_entity(self, name, position, size, mesh):
        """Create an entity backed by a custom 3D mesh."""
        entity = Entity(
            name, ENTITY_TYPE_3D_SPRITE, position, size,
            None, None, None, None, None, None, None, None, False,
            SPRITE_3D_CUSTOM, self.COLOR_BLACK,
        )
        mesh.set_wireframe(False)
        entity.sprite_3d = mesh
        entity.sprite_3d_type = SPRITE_3D_CUSTOM
        entity.is_visible = True
        self.meshes.append(mesh)
        self.level.entity_add(entity)
        return entity

    def _triangle(self, mesh, first, second, third, color):
        """Add one triangle to a mesh."""
        mesh.add_triangle(
            first[0], first[1], first[2],
            second[0], second[1], second[2],
            third[0], third[1], third[2],
            color, False,
        )

    def _quad(self, mesh, first, second, third, fourth, color):
        """Add a quad as two triangles."""
        self._triangle(mesh, first, second, third, color)
        self._triangle(mesh, first, fourth, second, color)

    def _squad(self, mesh, first, second, third, fourth, color):
        """Add a double-sided quad, seen from either side."""
        self._quad(mesh, first, second, third, fourth, color)
        self._triangle(mesh, first, third, second, color)
        self._triangle(mesh, first, second, fourth, color)

    def _ground_cell(self, mesh, x, z, half, color):
        """Add one flat ground cell (two triangles)."""
        self._quad(
            mesh,
            (x - half, 0.0, z - half),
            (x + half, 0.0, z + half),
            (x + half, 0.0, z - half),
            (x - half, 0.0, z + half),
            color,
        )

    def _house(self, mesh, x, z, width, depth, height, color):
        """Add a wooden house (body plus roof)."""
        mesh.create_cube(x, height * 0.5, z, width, height, depth, color)
        mesh.create_cube(x, height + 0.12, z, width + 0.16, 0.24, depth + 0.16,
                         self.COLOR_ROOF)

    def _build_stronghold(self, mesh, zone, x, z):
        """Add a faction stronghold structure to the world mesh."""
        if zone == 1:
            self._house(mesh, x, z, 9.0, 8.0, 5.0, self.COLOR_WOOD)
            self._house(mesh, x - 7.0, z + 6.0, 6.0, 6.0, 3.6, self.COLOR_WOOD)
        elif zone == 2:
            # Manor: sunken walls and pit.
            grid = 3
            step = 3.2
            for col in range(grid):
                for row in range(grid):
                    if col == 1 and row == 1:
                        mesh.create_cube(x, -0.35, z, 5.0, 0.7, 5.0, self.COLOR_BLACK)
                        continue
                    mesh.create_cube(
                        x + (col - 1) * step, 1.4, z + (row - 1) * step,
                        3.0, 2.8, 3.0, 0x4208,
                    )
        else:
            # Fortress: corner towers and walls.
            span = 6.0
            mesh.create_cylinder(x - span, 2.6, z - span, 0.9, 5.2, 6, self.COLOR_WOOD)
            mesh.create_cylinder(x + span, 2.6, z - span, 0.9, 5.2, 6, self.COLOR_WOOD)
            mesh.create_cylinder(x - span, 2.6, z + span, 0.9, 5.2, 6, self.COLOR_WOOD)
            mesh.create_cylinder(x + span, 2.6, z + span, 0.9, 5.2, 6, self.COLOR_WOOD)
            for col in range(3):
                mesh.create_cube(x + (col - 1) * span, 1.6, z - span, span, 3.2, 0.5,
                                 self.COLOR_WOOD)
                mesh.create_cube(x + (col - 1) * span, 1.6, z + span, span, 3.2, 0.5,
                                 self.COLOR_WOOD)
            mesh.create_cube(x + span, 1.6, z, 0.5, 3.2, span * 2.0, self.COLOR_WOOD)
            mesh.create_cube(x - span, 1.6, z, 0.5, 3.2, span * 2.0, self.COLOR_WOOD)

    def _build_own_house(self, mesh, x, z):
        """Add the player's hollow walkable house."""
        width = 6.0
        depth = 6.0
        height = 3.4
        scene_z = z - self.SCENE_ANCHOR_Z
        hw = width * 0.5
        hd = depth * 0.5
        floor_y = 0.05
        ceil_y = height - 0.15
        z0 = scene_z - hd + 0.1
        z1 = scene_z + hd - 0.1
        door = 1.2
        mesh.create_cube(x, height + 0.05, scene_z, width + 0.5, 0.18, depth + 0.5,
                         self.COLOR_ROOF)

        self._squad(mesh, (x - hw, floor_y, z0), (x + hw, floor_y, z1),
                    (x + hw, floor_y, z0), (x - hw, floor_y, z1), self.COLOR_WOOD)
        self._squad(mesh, (x - hw, ceil_y, z0), (x + hw, ceil_y, z1),
                    (x + hw, ceil_y, z0), (x - hw, ceil_y, z1), self.COLOR_ROOF)
        # Front wall contains doorway.
        self._squad(mesh, (x - hw, floor_y, z0), (x + hw, ceil_y, z0),
                    (x + hw, floor_y, z0), (x - hw, ceil_y, z0), self.COLOR_WOOD)
        self._squad(mesh, (x - hw, floor_y, z1), (x - door, ceil_y, z1),
                    (x - door, floor_y, z1), (x - hw, ceil_y, z1), self.COLOR_WOOD)
        self._squad(mesh, (x + door, floor_y, z1), (x + hw, ceil_y, z1),
                    (x + hw, floor_y, z1), (x + door, ceil_y, z1), self.COLOR_WOOD)

        self._squad(mesh, (x - hw, floor_y, z0), (x - hw, ceil_y, z1),
                    (x - hw, floor_y, z1), (x - hw, ceil_y, z0), self.COLOR_WOOD)
        self._squad(mesh, (x + hw, floor_y, z0), (x + hw, ceil_y, z1),
                    (x + hw, floor_y, z1), (x + hw, ceil_y, z0), self.COLOR_WOOD)

    def _build_world(self):
        """Create the streamed terrain mesh entity."""
        mesh = Sprite3D()
        self.world_mesh = mesh
        self._mesh_entity(
            "Terrain",
            Vector(0, self.SCENE_ANCHOR_Z),
            Vector(self.WORLD_HALF_X * 2.0, self.WORLD_HALF_Z * 2.0),
            mesh,
        )

    def _fill_world(self, center_x, center_z):
        """Rebuild terrain cells and strongholds near the player."""
        mesh = self.world_mesh
        mesh.clear_triangles()
        half = self.FIELD_OF_VIEW + self.CHUNK_LAG
        cell = self.CELL
        anchor = self.SCENE_ANCHOR_Z
        col0 = int((center_x - half) // cell)
        col1 = int((center_x + half) // cell)
        row0 = int((center_z - half) // cell)
        row1 = int((center_z + half) // cell)
        edge_x = self.WORLD_HALF_X - cell
        edge_z = self.WORLD_HALF_Z - cell
        for col in range(col0, col1 + 1):
            for row in range(row0, row1 + 1):
                x = col * cell + cell * 0.5
                z = row * cell + cell * 0.5
                if x > edge_x or x < -edge_x or z > edge_z or z < -edge_z:
                    continue
                zone = zone_for(x, z)
                self._ground_cell(mesh, x, z - anchor, cell * 0.5, self.ZONE_GROUND[zone])
        for zone in (1, 2, 3):
            sx, sz, _radius = self.STRONGHOLDS[zone]
            if col0 * cell - cell < sx < col1 * cell + cell:
                if row0 * cell - cell < sz < row1 * cell + cell:
                    self._build_stronghold(mesh, zone, sx, sz - anchor)
        hx, hz = self.HOUSE_POS
        if col0 * cell - cell < hx < col1 * cell + cell:
            if row0 * cell - cell < hz < row1 * cell + cell:
                self._build_own_house(mesh, hx, hz)
        mesh.set_wireframe(False)
        mesh.bake_transform()

    def _update_world(self):
        """Refill terrain when the player drifts from the anchor."""
        if not self.player.has_changed_position():
            return
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
            self._fill_world(self.anchor_x, self.anchor_z)
            self._fill_lands(self.anchor_x, self.anchor_z)
            self._fill_enemies(self.anchor_x, self.anchor_z)
        else:
            land_offset_x = position.x - self.land_anchor_x
            land_offset_z = position.y - self.land_anchor_z
            land_lag = self.CHUNK_LAG * 0.5
            if (abs(land_offset_x) > land_lag
                    or abs(land_offset_z) > land_lag):
                self._fill_lands(position.x, position.y)

    def _fill_lands(self, center_x, center_z):
        """Place the nearest land patches around the player."""
        self.land_anchor_x = center_x
        self.land_anchor_z = center_z
        land_type = zone_for(center_x, center_z)
        if land_type >= len(self.LAND_FILES):
            land_type = 0
        if land_type != self.land_type:
            path = "picoware/apps/games/pge_adventure/%s.sprite3d" % self.LAND_FILES[land_type]
            for entity in self.lands:
                sprite = entity.sprite_3d
                if sprite is not None and sprite.from_path(path, False):
                    sprite.scale_factor = self.LAND_SCALE
                    sprite.bake_transform()
            self.land_type = land_type
        cell = self.LAND_CELL
        types = len(self.LAND_FILES)
        reach = self.FIELD_OF_VIEW + self.CHUNK_LAG
        limit = self.FIELD_OF_VIEW * self.FIELD_OF_VIEW
        col0 = int((center_x - reach) // cell)
        col1 = int((center_x + reach) // cell)
        row0 = int((center_z - reach) // cell)
        row1 = int((center_z + reach) // cell)
        edge_x = self.WORLD_HALF_X - cell
        edge_z = self.WORLD_HALF_Z - cell
        bucket = []
        for col in range(col0, col1 + 1):
            for row in range(row0, row1 + 1):
                x = col * cell + cell * 0.5 + ((_hash(col, row, 5) % 100) - 50) * 0.04
                z = row * cell + cell * 0.5 + ((_hash(col, row, 6) % 100) - 50) * 0.04
                if x > edge_x or x < -edge_x or z > edge_z or z < -edge_z:
                    continue
                dx = x - center_x
                dz = z - center_z
                dist_sq = dx * dx + dz * dz
                if dist_sq > limit:
                    continue
                zone = zone_for(x, z)
                kind = zone if zone < types else 0
                if kind == self.land_type:
                    bucket.append((dist_sq, x, z))
        bucket.sort()
        for index, entity in enumerate(self.lands):
            if index < len(bucket):
                _, x, z = bucket[index]
                entity.position_set(x, z)
                entity.is_visible = True
            else:
                entity.is_visible = False

    def _build_background(self):
        """Create the sky and horizon entity."""
        background = Entity(
            "Background", ENTITY_TYPE_3D_SPRITE, Vector(0, self.BACKGROUND_Z), Vector(1, 1),
            None, None, None, None, None, None, _background_render, None, False,
            SPRITE_3D_NONE, self.COLOR_BLACK,
        )
        background.is_visible = True
        self.level.entity_add(background)

    def _build_player(self):
        """Create the player entity."""
        if self.engine is not None and self.player is not None:
            # Remove existing player entity.
            self.engine.entity_remove(self.player)
            self.player = None
        self.player = Entity(
            "Player", ENTITY_TYPE_PLAYER, Vector(self.PLAYER_SPAWN[0], self.PLAYER_SPAWN[1]),
            Vector(0.7, 1.8), None, None, None, None, None, _player_update,
            None, None, False, SPRITE_3D_CUSTOM, self.COLOR_PLAYER,
        )
        self.player.speed = self.base_speed
        self.player.is_player = True
        self.player.is_visible = True
        self.player.direction_set(cos(self.heading), sin(self.heading))
        self.player.set_3d_sprite_rotation(self.heading - pi * 0.5 + self.PLAYER_ANGLE)
        # Intro shows Wizard, not hero.
        sprite = self._load_sprite(
            "picoware/apps/games/pge_adventure/wizard.sprite3d")
        if sprite is None:
            # Provide visible fallback mesh.
            sprite = Sprite3D()
            sprite.create_humanoid(1.8, self.COLOR_PLAYER)
            self.sprites.append(sprite)
        self.player.set_sprite3d(sprite)
        self.level.entity_add(self.player)

    def _build_wizard(self):
        """Create the Wise Wizard NPC in the Nolands hub."""
        self.wizard = Entity(
            "Wise Wizard", ENTITY_TYPE_NPC, Vector(self.WIZARD_POS[0], self.WIZARD_POS[1]),
            Vector(0.8, 2.0), None, None, None, None, None, None, None, None, False,
            SPRITE_3D_CUSTOM, self.COLOR_WIZARD,
        )
        sprite = self._load_sprite(
            "picoware/apps/games/pge_adventure/wizard.sprite3d")
        if sprite is not None:
            self.wizard.set_sprite3d(sprite)
        self.wizard.is_visible = False
        self.level.entity_add(self.wizard)

    def _build_enemies(self):
        """Create the enemy pool with one sprite per type."""
        for index in range(self.ENEMY_COUNT):
            zone = index % len(self.ENEMY_FILES) + 1
            enemy = Entity(
                "Enemy %d" % index, ENTITY_TYPE_ENEMY, Vector(0, 0), Vector(0.7, 1.8),
                None, None, None, None, None, _enemy_update, _enemy_render, None, False,
                SPRITE_3D_CUSTOM, self.ZONE_ENEMY[zone],
            )
            sprite = self._load_sprite(self._enemy_path(zone))
            if sprite is not None:
                enemy.set_sprite3d(sprite)
            enemy.is_visible = False
            enemy.speed = 0.09
            self.enemies.append(enemy)
            self.enemy_home.append(None)
            self.enemy_ready.append(sprite is not None)
            self.level.entity_add(enemy)
        self._target_list = list(self.enemies)

    def _build_dragon(self):
        """Create the hidden Dragon boss."""
        dragon = Entity(
            "Dragon", ENTITY_TYPE_ENEMY, Vector(0, 0), Vector(0.7, 1.8),
            None, None, None, None, None, _enemy_update, _enemy_render, None, False,
            SPRITE_3D_CUSTOM, self.COLOR_DRAGON,
        )
        sprite = self._load_sprite(
            "picoware/apps/games/pge_adventure/dragon.sprite3d")
        if sprite is not None:
            dragon.set_sprite3d(sprite)
        self.dragon = dragon
        self.level.entity_add(dragon)
        if self.dragon is not None:
            self._target_list.append(self.dragon)

    def _build_effects(self):
        """Create the reusable skill effect sprites."""
        for key in self.EFFECT_FILES:
            coll = _on_projectile_collision if key in ("orb", "fire-blast") else None
            update = (_projectile_update if key in ("orb", "fire-blast")
                      else _effect_update)
            effect = Entity(
                "FX %s" % key, ENTITY_TYPE_3D_SPRITE, Vector(0, 0, 1.0), Vector(1, 1),
                None, None, None,      # 5,6,7: sprite_data, sprite_left, sprite_right
                None, None,            # 8,9: start, stop
                update, None,          # 10,11: update, render
                coll,                  # 12: collision
                False,                 # 13: is_8bit
                SPRITE_3D_CUSTOM, self.COLOR_WHITE,   # 14,15: sprite_3d_type, sprite_3d_color
            )
            sprite = self._load_sprite(
                "picoware/apps/games/pge_adventure/%s.sprite3d" % key)
            if sprite is not None:
                effect.set_sprite3d(sprite)
            effect.state = 1 if key == "orb" else 0
            effect.is_visible = False
            self.effects[key] = effect
            self.level.entity_add(effect)

    def _build_halos(self):
        """Create the buff halo sprites that follow the player."""
        self.halos = {}
        self._halo_entity = {}
        for stat, key in (("health", "blue-halo"), ("speed", "green-halo"),
                          ("strength", "red-halo")):
            effect = Entity(
                "Halo %s" % stat, ENTITY_TYPE_3D_SPRITE, Vector(0, 0, 1.0), Vector(1, 1),
                None, None, None,      # 5,6,7: sprite_data, sprite_left, sprite_right
                None, None,            # 8,9: start, stop
                None, None,    # 10,11: update, render
                None,                  # 12: collision
                False,                 # 13: is_8bit
                SPRITE_3D_CUSTOM, self.COLOR_WHITE,   # 14,15: sprite_3d_type, sprite_3d_color
            )
            sprite = self._load_sprite(
                "picoware/apps/games/pge_adventure/%s.sprite3d" % key)
            if sprite is not None:
                effect.set_sprite3d(sprite)
            effect.is_visible = False
            self._halo_entity[effect] = stat
            self.halos[stat] = effect
            self.level.entity_add(effect)

    def _build_lands(self):
        """Create the land patch pool from the world sprite3d assets."""
        for index in range(self.LAND_COUNT):
            entity = Entity(
                "Land %d" % index, ENTITY_TYPE_3D_SPRITE, Vector(0, 0), Vector(1, 1),
                None, None, None, None, None, None, None, None, False,
                SPRITE_3D_CUSTOM, self.COLOR_BLACK,
            )
            sprite = self._load_sprite(
                "picoware/apps/games/pge_adventure/%s.sprite3d"
                % self.LAND_FILES[self.land_type]
            )
            if sprite is not None:
                sprite.scale_factor = self.LAND_SCALE
                sprite.bake_transform()
                entity.set_sprite3d(sprite)
            entity.is_visible = False
            self.lands.append(entity)
            self.level.entity_add(entity)

    def _enemy_path(self, zone):
        """Return the sprite path for a faction's enemy."""
        return ("picoware/apps/games/pge_adventure/%s.sprite3d"
                % self.ENEMY_FILES[zone - 1])

    def _load_sprite(self, path):
        """Load a Sprite3D, collecting once on low memory."""
        sprite = Sprite3D()
        sprite.from_path(path, False)
        self.sprites.append(sprite)
        return sprite

    def _set_class_preview(self, name):
        """Reload the player mesh in place to preview a class."""
        if self.player is None:
            return
        path = "picoware/apps/games/pge_adventure/%s.sprite3d" % name.lower()
        loaded = False
        if self.player.sprite_3d is None:
            sprite_3d = Sprite3D()
            loaded = sprite_3d.from_path(path, False)
            if loaded:
                self.player.set_sprite3d(sprite_3d)
        else:
            loaded = self.player.sprite_3d.from_path(path, False)
        self.sword_triangles = []
        self.beast_triangles = []
        self.beast_right_side = 1

        if (loaded and name == "Knight" and self.player.sprite_3d.triangle_count > 223):
            for index in range(216, 224):
                self.sword_triangles.append(self.player.sprite_3d.get_triangle(index))
        elif loaded and name == "Beast":
            for index in range(self.player.sprite_3d.triangle_count):
                triangle = self.player.sprite_3d.get_triangle(index)
                center_x = (triangle.x1 + triangle.x2 + triangle.x3) / 3.0
                center_y = (triangle.y1 + triangle.y2 + triangle.y3) / 3.0
                if 0.40 <= center_y <= 1.52:
                    if center_x > 0.30:
                        self.beast_triangles.append((index, triangle, 1))
                    elif center_x < -0.30:
                        self.beast_triangles.append((index, triangle, -1))
            if not any(entry[2] == 1 for entry in self.beast_triangles):
                self.beast_right_side = -1
        return loaded

    def _fill_enemies(self, center_x, center_z):
        """Place pooled enemies at the nearest cells for their type."""
        cell = self.ENEMY_CELL
        types = len(self.ENEMY_FILES)
        reach = self.FIELD_OF_VIEW + self.CHUNK_LAG
        limit = self.FIELD_OF_VIEW * self.FIELD_OF_VIEW
        floor = self.AGGRO_RANGE * self.AGGRO_RANGE
        col0 = int((center_x - reach) // cell)
        col1 = int((center_x + reach) // cell)
        row0 = int((center_z - reach) // cell)
        row1 = int((center_z + reach) // cell)
        buckets = [[] for _ in range(types)]
        for col in range(col0, col1 + 1):
            for row in range(row0, row1 + 1):
                if _hash(col, row, 21) % self.ENEMY_CHANCE:
                    continue
                x = col * cell + cell * 0.5
                z = row * cell + cell * 0.5
                if x > self.WORLD_HALF_X - cell or x < -self.WORLD_HALF_X + cell:
                    continue
                if z > self.WORLD_HALF_Z - cell or z < -self.WORLD_HALF_Z + cell:
                    continue
                zone = zone_for(x, z)
                if zone == 0:
                    continue
                dx = x - center_x
                dz = z - center_z
                dist_sq = dx * dx + dz * dz
                if dist_sq > limit or dist_sq < floor:
                    continue
                buckets[zone - 1].append((dist_sq, x, z, col, row))
        for bucket in buckets:
            bucket.sort()
        claimed = [set() for _ in range(types)]
        player_x = self.player.position.x
        player_z = self.player.position.y
        keep_sq = (self.FIELD_OF_VIEW + 10.0) ** 2
        for index, enemy in enumerate(self.enemies):
            home = self.enemy_home[index]
            dx = enemy.position.x - player_x
            dz = enemy.position.y - player_z
            if home is not None and dx * dx + dz * dz <= keep_sq:
                claimed[index % types].add(home)
        for index, enemy in enumerate(self.enemies):
            kind = index % types
            bucket = buckets[kind]
            home = self.enemy_home[index]
            if home is not None:
                dx = enemy.position.x - player_x
                dz = enemy.position.y - player_z
                if dx * dx + dz * dz <= keep_sq:
                    enemy.is_visible = self.enemy_ready[index]
                    continue
                claimed[kind].discard(home)
            placed = False
            for entry in bucket:
                if (entry[3], entry[4]) in claimed[kind]:
                    continue
                claimed[kind].add((entry[3], entry[4]))
                self.enemy_home[index] = (entry[3], entry[4])
                self._enemy_reset(enemy, entry[1], entry[2])
                enemy.is_visible = self.enemy_ready[index]
                placed = True
                break
            if not placed:
                self.enemy_home[index] = None
                enemy.is_visible = False

    def _enemy_reset(self, enemy, x, z):
        """Initialize a pooled enemy at a world cell."""
        level = self.player.level - 5
        level = max(1, level)
        enemy.position_set(x, z)
        enemy.health = health_for_level(level)
        enemy.max_health = enemy.health
        enemy.strength = strength_for_level(level)
        enemy.level = level
        enemy.speed = 0.06 + _next_random(3) * 0.01
        enemy.attack_timer = 0
        enemy.move_timer = 0.0
        enemy.elapsed_move_timer = 0.0
        enemy.sprite_scale = 1.0
        enemy.direction_set(0.0, 1.0)

    def _spawn_dragon(self):
        """Place the Dragon near the player."""
        dragon = self.dragon
        if dragon is None:
            self._build_dragon()
        level = self.player.level + self.BOSS_LEVEL_GAP
        angle = _next_random(628) * 0.01
        distance = self.AGGRO_RANGE * 1.5
        dragon.position_set(
            self.player.position.x + cos(angle) * distance,
            self.player.position.y + sin(angle) * distance,
        )
        dragon.health = health_for_level(level) * 4
        dragon.max_health = dragon.health
        dragon.strength = strength_for_level(level)
        dragon.level = level
        dragon.speed = 0.06
        dragon.attack_timer = 60
        dragon.sprite_scale = 3.0
        dragon.is_visible = True

    def _show_effect(self, key, x, z, height):
        """Place an effect sprite at a world point."""
        effect = self.effects.get(key)
        if effect is None:
            return
        effect.position_set(x, z, height)
        effect.attack_timer = self.EFFECT_FRAMES
        effect.is_visible = True

    def _spawn_projectile(self, name, power, radius):
        """Launch an Orb/FireBlast projectile in the direction the player faces."""
        key = self.SKILL_FX.get(name)
        if key is None:
            return
        effect = self.effects.get(key)
        if effect is None or effect.is_visible:
            return
        dx = self.player.direction.x
        dz = self.player.direction.y
        length = (dx * dx + dz * dz) ** 0.5
        if length < 0.0001:
            dx, dz = 1.0, 0.0
            length = 1.0
        dx /= length
        dz /= length
        speed = self.PROJECTILE_SPEED
        life = int(radius / speed) + 1
        effect.position_set(
            self.player.position.x + dx * 1.0,
            self.player.position.y + dz * 1.0,
            1.0,
        )
        effect.start_position = Vector(dx, dz)
        effect.speed = speed
        effect.attack_timer = life
        effect.elapsed_attack_timer = 0
        effect.strength = int(self.player.strength * power)
        effect.sprite_scale = 1.0
        effect.direction_set(self.player.direction.x, self.player.direction.y)
        effect.sprite.rotation_y = self.player.sprite.rotation_y
        effect.is_visible = True

    def _finish_projectile(self, effect):
        """Hide and reset a projectile entity."""
        effect.is_visible = False
        effect.sprite_scale = 1.0
        effect.elapsed_attack_timer = 0

    def _projectile_hit(self, effect, enemy):
        """Deal damage when a projectile strikes an enemy (idempotent)."""
        if not effect.is_visible or effect.elapsed_attack_timer > 0:
            return
        effect.elapsed_attack_timer = 1
        self._damage(enemy, int(effect.strength))

    def update_enemy(self, enemy):
        """Chase, attack or wander one enemy."""
        if enemy is self.dragon:
            self._update_dragon(enemy)
            return
        if self.ui != self.UI_NONE or self.talking:
            return
        if enemy.attack_timer > 0:
            enemy.attack_timer -= 1

        player = self.player.position
        dx = player.x - enemy.position.x
        dz = player.y - enemy.position.y
        dist_sq = dx * dx + dz * dz

        # Compare squared distances first.
        if self.phase != 2 or dist_sq > self.RECYCLE_DISTANCE * self.RECYCLE_DISTANCE:
            enemy.is_visible = False
            return

        fov = self.FIELD_OF_VIEW + 10.0
        if enemy.elapsed_move_timer > 0:
            enemy.elapsed_move_timer -= 1
            enemy.is_visible = dist_sq < fov * fov
            return

        aggro_sq = self.AGGRO_RANGE * self.AGGRO_RANGE
        hit_sq = self.HIT_RANGE * self.HIT_RANGE
        if 1e-6 < dist_sq < aggro_sq:
            dist = dist_sq ** 0.5
            enemy.direction_set(dx / dist, dz / dist)
            if dist_sq > hit_sq:
                if enemy.elapsed_move_timer <= 0:
                    step = enemy.speed
                    enemy.position_set(
                        enemy.position.x + enemy.direction.x * step,
                        enemy.position.y + enemy.direction.y * step,
                    )
            elif enemy.attack_timer <= 0:
                self._enemy_hit(enemy)
        else:
            self._wander(enemy)

        enemy.sprite_rotation = atan2(enemy.direction.y, enemy.direction.x) - pi * 0.5
        enemy.is_visible = dist_sq < fov * fov

    def _update_dragon(self, enemy):
        """Chase the player and breathe fire."""
        if self.dragon_defeated:
            enemy.is_visible = False
            return
        if enemy.attack_timer > 0:
            enemy.attack_timer -= 1
        if self.ui != self.UI_NONE or self.talking or self.phase != 2:
            return
        player = self.player.position
        dx = player.x - enemy.position.x
        dz = player.y - enemy.position.y
        dist_sq = dx * dx + dz * dz
        fov = self.FIELD_OF_VIEW + 20.0
        enemy.is_visible = dist_sq < fov * fov
        if enemy.elapsed_move_timer > 0:
            enemy.elapsed_move_timer -= 1
            return
        if dist_sq < 1e-6:
            return
        dist = dist_sq ** 0.5
        enemy.direction_set(dx / dist, dz / dist)
        enemy.sprite_rotation = atan2(dz, dx) - pi * 0.5
        if dist_sq > self.DRAGON_RANGE * self.DRAGON_RANGE:
            step = enemy.speed
            enemy.position_set(
                enemy.position.x + enemy.direction.x * step,
                enemy.position.y + enemy.direction.y * step,
            )
            return
        if enemy.attack_timer <= 0:
            self._dragon_skill(enemy)

    def _dragon_skill(self, enemy):
        """Breathe a fireball at the player."""
        px = self.player.position.x
        pz = self.player.position.y
        self._show_effect("fire-ball", (enemy.position.x + px) * 0.5,
                          (enemy.position.y + pz) * 0.5, 1.4)
        loss = int(enemy.strength * 0.5)
        self.player.health -= loss
        enemy.attack_timer = 90
        self.message = "Dragon Fireball!"
        self.message_timer = 40
        if self.player.health <= 0:
            self.player.xp = max(0, self.player.xp - loss)
            self.player.health = self.player.max_health
            self.update_stats()
            self.message = "Defeated! -%d XP" % loss
            self.message_timer = 90

    def _wander(self, enemy):
        """Drift an idle enemy on a short path."""
        if enemy.elapsed_move_timer <= 0:
            angle = _next_random(628) * 0.01
            enemy.direction_set(cos(angle), sin(angle))
            enemy.elapsed_move_timer = 20.0 + _next_random(30)
        enemy.elapsed_move_timer -= 1.0
        step = enemy.speed * 0.5
        ex = enemy.position.x + enemy.direction.x * step
        ez = enemy.position.y + enemy.direction.y * step
        if (
            ex < -self.WORLD_HALF_X or ex > self.WORLD_HALF_X
            or ez < -self.WORLD_HALF_Z or ez > self.WORLD_HALF_Z
        ):
            enemy.direction_set(-enemy.direction.x, -enemy.direction.y)
        else:
            enemy.position_set(ex, ez)

    def _in_stronghold(self, x, z):
        """Return the stronghold zone at a point, or 0."""
        for zone in (1, 2, 3):
            sx, sz, radius = self.STRONGHOLDS[zone]
            dx = x - sx
            dz = z - sz
            if dx * dx + dz * dz <= radius * radius:
                return zone
        return 0

    def _facing(self, enemy):
        """Return whether the player faces an enemy."""
        dx = enemy.position.x - self.player.position.x
        dz = enemy.position.y - self.player.position.y
        length = (dx * dx + dz * dz) ** 0.5
        if length < 0.0001:
            return True
        direction = self.player.direction
        return (direction.x * dx + direction.y * dz) / length > 0.25

    def _damage(self, enemy, amount):
        """Damage an enemy and resolve a kill."""
        enemy.elapsed_move_timer = max(enemy.elapsed_move_timer, 6)
        enemy.health -= amount
        if enemy.health <= 0:
            self._enemy_die(enemy)

    def _enemy_die(self, enemy):
        """Reward a kill, advance quests and respawn the enemy."""
        reward = enemy.strength
        if enemy is self.dragon:
            self.dragon_defeated = True
            self.armor_earned = True
            self.skills_unlocked = 5
            enemy.is_visible = False
            self.update_stats()
            self.message = "Wise Wizard Armor! Special unlocked"
            self.message_timer = 200
            self._mark_progress()
            return
        index = self.enemies.index(enemy)
        zone = index % len(self.ENEMY_FILES) + 1
        self.player.xp += reward
        self.player.health += int(reward * 0.10)
        self.player.health = min(self.player.health, self.player.max_health)
        self._on_kill(zone)
        enemy.health = 0
        self.enemy_home[index] = None
        enemy.is_visible = False
        self._fill_enemies(self.anchor_x, self.anchor_z)

    def _enemy_hit(self, enemy):
        """Apply one enemy strike to the player."""
        self.player.health -= enemy.strength
        enemy.attack_timer = 45
        if self.player.health <= 0:
            loss = enemy.strength
            self.player.xp = max(0, self.player.xp - loss)
            self.player.health = self.player.max_health
            self.update_stats()
            self.message = "Defeated! -%d XP" % loss
            self.message_timer = 90

    def _attack(self):
        """Strike the nearest facing enemy during a special."""
        if self.attack_cd > 0 and self.special_active <= 0:
            return
        best = None
        best_dist = 3.4 * 3.4
        for enemy in self._target_list:
            if not enemy.is_visible:
                continue
            dx = enemy.position.x - self.player.position.x
            dz = enemy.position.y - self.player.position.y
            dist_sq = dx * dx + dz * dz
            if dist_sq < best_dist and self._facing(enemy):
                best = enemy
                best_dist = dist_sq
        if best is not None:
            self._damage(best, int(self.player.strength * self._damage_scale()))
        self.attack_cd = 14

    def _damage_scale(self):
        """Return the current attack multiplier from buffs."""
        return 1.5 if self.buff_stat == "strength" else 1.0

    def _load_class_names(self):
        """Load and cache class names for selection."""
        if not self.class_names:
            data = self.view_manager.storage.deserialize(self.CLASS_PATH)
            self.class_names = list(data.keys())
        return self.class_names

    def _class_entry(self, index=None):
        """Load and cache one class entry."""
        if index is None:
            index = self.class_index
        if self.class_cache_index != index:
            names = self._load_class_names()
            data = self.view_manager.storage.deserialize(self.CLASS_PATH)
            name = names[index]
            entry = data[name]
            self.class_cache = (
                name, entry["attribute"],
                [tuple(skill) for skill in entry["skills"]],
            )
            self.class_cache_index = index
        return self.class_cache

    def _use_skill(self, slot):
        """Cast the class skill in one slot."""
        if slot >= 5 or slot > self.skills_unlocked - 1:
            self.message = "Skill locked"
            self.message_timer = 40
            return
        if slot == 4:
            self._use_special()
            return
        if self.skill_cd[slot] > 0:
            return
        skill = self._class_entry()[2][slot]
        name, kind, power, radius, cooldown = skill[0], skill[1], skill[2], skill[3], skill[4]
        duration = skill[5] if len(skill) > 5 else 0
        if self.class_name == "Knight":
            if kind == "bolt":
                self._knight_bolt(name, power, radius)
            elif kind == "aoe":
                self._knight_might(name, power, radius)
            else:
                self._skill_boost(duration)
        elif self.class_name == "Beast":
            if name in ("Slash", "Maniac"):
                self._beast_bolt(name, power, radius)
            elif name == "Knockout":
                self._beast_knockout(power, radius)
            else:
                self._skill_boost(duration)
        else:
            if kind == "bolt":
                self._skill_bolt(name, power, radius)
            elif kind == "aoe":
                self._skill_aoe(name, power, radius)
            else:
                self._skill_boost(duration)
        self.skill_cd[slot] = cooldown
        self.message = name
        self.message_timer = 40

    def _use_special(self):
        """Cast the class ultimate."""
        if self.special_cd > 0:
            return
        name, _, power, radius, cooldown = self._class_entry()[2][4]
        if self.class_name == "Knight":
            self._knight_conquer(power, radius)
            self.special_cd = cooldown
        elif name == "Chaos":
            self.chaos_frames = 90
            self.chaos_yaw = 0.0
            self.chaos_power = power
            self.beast_swing_mode = 3
            self.attack_cd = 0
            self.special_cd = cooldown
        elif name == "Teleport":
            next_x = self.player.position.x + self.player.direction.x * 12.0
            next_z = self.player.position.y + self.player.direction.y * 12.0
            next_x = max(-self.WORLD_HALF_X + 1.0,
                         min(self.WORLD_HALF_X - 1.0, next_x))
            next_z = max(-self.WORLD_HALF_Z + 1.0,
                         min(self.WORLD_HALF_Z - 1.0, next_z))
            self.player.position_set(next_x, next_z)
            self.special_cd = 0
        else:
            self._skill_aoe(name, power, radius)
            self.special_active = 90
            self.special_cd = cooldown
        self.message = name
        self.message_timer = 20

    def _skill_bolt(self, name, power, radius):
        """Hit the nearest facing enemy within radius."""
        best = None
        best_dist = radius * radius
        for enemy in self._target_list:
            if not enemy.is_visible:
                continue
            dx = enemy.position.x - self.player.position.x
            dz = enemy.position.y - self.player.position.y
            dist_sq = dx * dx + dz * dz
            if dist_sq < best_dist and self._facing(enemy):
                best = enemy
                best_dist = dist_sq
        if best is not None:
            x = best.position.x
            z = best.position.y
            self.player.direction_set(dx, dz)
            self.player.set_3d_sprite_rotation(self.player_yaw)
            self._damage(best, int(self.player.strength * power))
            self._show_skill(name, x, z)

    def _skill_aoe(self, name, power, radius):
        """Damage every enemy inside the radius, or launch a projectile."""
        if name in self.PROJECTILE_NAMES:
            self._spawn_projectile(name, power, radius)
            return
        radius_sq = radius * radius
        damage = int(self.player.strength * power)
        nearest_x = None
        nearest_z = None
        nearest_dist = radius_sq
        for enemy in self._target_list:
            if not enemy.is_visible:
                continue
            dx = enemy.position.x - self.player.position.x
            dz = enemy.position.y - self.player.position.y
            dist_sq = dx * dx + dz * dz
            if dist_sq <= radius_sq:
                if dist_sq < nearest_dist:
                    nearest_x = enemy.position.x
                    nearest_z = enemy.position.y
                    nearest_dist = dist_sq
                self._damage(enemy, damage)
                if self._class_entry()[2][1][0] == "Knockout":
                    enemy.elapsed_move_timer = 60
        if nearest_x is not None:
            self._show_skill(name, nearest_x, nearest_z)
        else:
            self._show_skill(
                name,
                self.player.position.x + self.player.direction.x * radius * 0.5,
                self.player.position.y + self.player.direction.y * radius * 0.5,
            )

    def _show_skill(self, name, x, z):
        """Show a skill's effect sprite at a world point."""
        key = self.SKILL_FX.get(name)
        if key is not None:
            self._show_effect(key, x, z, 1.0)

    def _skill_boost(self, duration):
        """Apply the class boost (speed, health or strength)."""
        if self.buff_timer > 0:
            return # Wait until buff ends.
        stat = self._class_entry()[1]
        self.buff_stat = stat
        if stat == "health":
            bonus = int(self.player.max_health * 0.35)
            self.player.max_health += bonus
            self.player.health += bonus
        elif stat == "strength":
            self.player.strength += int(self.player.strength * 0.35)
        elif stat == "speed":
            self.player.speed = self.base_speed * 1.35
        self.buff_timer = duration
        if stat in self.halos:
            self.halos[stat].position_set(
                self.player.position.x, self.player.position.y, self.HALO_HEIGHT)
            self.halos[stat].is_visible = True

    def _knight_bolt(self, name, power, radius):
        """Dash to just in front of the nearest enemy in range and strike it."""
        best = None
        best_dist = radius * radius
        for enemy in self._target_list:
            if not enemy.is_visible:
                continue
            dx = enemy.position.x - self.player.position.x
            dz = enemy.position.y - self.player.position.y
            dist_sq = dx * dx + dz * dz
            if dist_sq < best_dist:
                best = enemy
                best_dist = dist_sq
        if best is None:
            self.sword_yaw = self.heading
            return
        # Stop one sword-length short.
        dx = best.position.x - self.player.position.x
        dz = best.position.y - self.player.position.y
        length = (dx * dx + dz * dz) ** 0.5
        if length > 0.0001:
            self.attack_return_x = self.player.position.x
            self.attack_return_z = self.player.position.y
            stop = max(length - 1.4, 0.6)
            next_x = self.player.position.x + dx * stop / length
            next_z = self.player.position.y + dz * stop / length
            next_x = max(-self.WORLD_HALF_X + 1.0,
                         min(self.WORLD_HALF_X - 1.0, next_x))
            next_z = max(-self.WORLD_HALF_Z + 1.0,
                         min(self.WORLD_HALF_Z - 1.0, next_z))
            self.player.position_set(next_x, next_z, 0.0)
            self.player.direction_set(dx / length, dz / length)
            self.player.set_3d_sprite_rotation(self.player_yaw)
            self.attack_return_frames = self.ATTACK_RETURN_FRAMES
        self.sword_yaw = atan2(dz, dx)
        self._damage(best, int(self.player.strength * power))
        if name == "Stab":
            self.sword_swing = 0.5
            self.sword_swing_frames = 8
        else:
            self.sword_swing = 0.5
            self.sword_swing_frames = 5

    def _beast_bolt(self, name, power, radius):
        """Dash to an enemy and slash with one or both hands."""
        best = None
        best_dist = radius * radius
        for enemy in self._target_list:
            if not enemy.is_visible:
                continue
            dx = enemy.position.x - self.player.position.x
            dz = enemy.position.y - self.player.position.y
            dist_sq = dx * dx + dz * dz
            if dist_sq < best_dist:
                best = enemy
                best_dist = dist_sq
        self.beast_swing_mode = 2 if name == "Maniac" else 1
        self.sword_swing = 1.0
        self.sword_swing_frames = 10 if name == "Maniac" else 7
        if best is None:
            self.sword_yaw = self.heading
            return
        dx = best.position.x - self.player.position.x
        dz = best.position.y - self.player.position.y
        length = (dx * dx + dz * dz) ** 0.5
        if length > 0.0001:
            self.attack_return_x = self.player.position.x
            self.attack_return_z = self.player.position.y
            approach_distance = max(length - 1.4, 0.6)
            next_x = self.player.position.x + dx * approach_distance / length
            next_z = self.player.position.y + dz * approach_distance / length
            next_x = max(-self.WORLD_HALF_X + 1.0,
                         min(self.WORLD_HALF_X - 1.0, next_x))
            next_z = max(-self.WORLD_HALF_Z + 1.0,
                         min(self.WORLD_HALF_Z - 1.0, next_z))
            self.player.position_set(next_x, next_z, 0.0)
            self.player.direction_set(dx / length, dz / length)
            self.player.set_3d_sprite_rotation(self.player_yaw)
            self.attack_return_frames = self.ATTACK_RETURN_FRAMES
        self.sword_yaw = atan2(dz, dx)
        self._damage(best, int(self.player.strength * power))

    def _beast_knockout(self, power, radius):
        """Stun the nearest enemy with a short-range blow."""
        best = None
        best_dist = radius * radius
        for enemy in self._target_list:
            if not enemy.is_visible:
                continue
            dx = enemy.position.x - self.player.position.x
            dz = enemy.position.y - self.player.position.y
            dist_sq = dx * dx + dz * dz
            if dist_sq < best_dist:
                best = enemy
                best_dist = dist_sq
        self.beast_swing_mode = 1
        self.sword_swing = 0.9
        self.sword_swing_frames = 7
        if best is not None:
            best.elapsed_move_timer = 60
            self._damage(best, int(self.player.strength * power))

    def _knight_might(self, name, power, radius):
        """Overhead swing: wind up, then hit a front cone."""
        self.might_windup = self.MIGHT_WINDUP
        self.might_power = power
        self.might_radius = min(radius, self.MIGHT_IMPACT_RADIUS)
        self.sword_yaw = self.heading
        self.sword_swing = -0.8
        self.sword_swing_frames = self.MIGHT_WINDUP

    def _knight_might_hit(self):
        """Damage every enemy in the front cone."""
        radius_sq = self.might_radius * self.might_radius
        damage = int(self.player.strength * self.might_power)
        for enemy in self._target_list:
            if not enemy.is_visible:
                continue
            dx = enemy.position.x - self.player.position.x
            dz = enemy.position.y - self.player.position.y
            dist_sq = dx * dx + dz * dz
            if dist_sq > radius_sq:
                continue
            dist = dist_sq ** 0.5
            if dist < 0.0001:
                continue
            facing = (self.cos_h * dx + self.sin_h * dz) / dist
            if facing > 0.65:
                self._damage(enemy, damage)
        self.sword_swing = 0.8
        self.sword_swing_frames = 5

    def _knight_conquer(self, power, radius):
        """Charge the player forward like a rhino, hitting enemies in the path."""
        self.conquer_frames = self.CONQUER_FRAMES
        self.conquer_speed = self.CONQUER_DISTANCE / float(self.CONQUER_FRAMES)
        self.conquer_power = power
        self.conquer_dirx = self.cos_h
        self.conquer_dirz = self.sin_h
        self.conquer_hit = set()
        self.sword_yaw = self.heading
        self.sword_swing = 0.5
        self.sword_swing_frames = self.CONQUER_FRAMES
        self.player.set_3d_sprite_rotation(self.player_yaw)
        self.message = "Conquer"
        self.message_timer = 40

    def _knight_conquer_attack(self):
        """Dash one step in the Conquer direction, hitting enemies along the way."""
        step = self.conquer_speed
        px = self.player.position.x + self.conquer_dirx * step
        pz = self.player.position.y + self.conquer_dirz * step
        next_x = max(-self.WORLD_HALF_X + 1.0,
                     min(self.WORLD_HALF_X - 1.0, px))
        next_z = max(-self.WORLD_HALF_Z + 1.0,
                     min(self.WORLD_HALF_Z - 1.0, pz))
        self.player.position_set(next_x, next_z, 0.0)
        for enemy in self._target_list:
            if not enemy.is_visible or enemy in self.conquer_hit:
                continue
            dx = enemy.position.x - next_x
            dz = enemy.position.y - next_z
            if dx * dx + dz * dz <= 4.0:
                self.conquer_hit.add(enemy)
                self._damage(enemy, int(self.player.strength * self.conquer_power))
        self.conquer_frames -= 1
        if self.conquer_frames > 0:
            self.sword_swing = 0.3
        else:
            self.conquer_speed = 0.0

    def _on_kill(self, zone):
        """Record a faction kill and update quest streaks."""
        if zone == 0 or self.faction_done[zone]:
            self.update_stats()
            return
        self.q_kills[zone] += 1
        if self.q_timer[zone] > 0:
            self.q_streak[zone] += 1
        else:
            self.q_streak[zone] = 1
        self.q_low[zone] = self.player.health * 2 < self.player.max_health
        _kind, _a, window = self._current_quest(zone)
        self.q_timer[zone] = window if window else 20
        if self._in_stronghold(self.player.position.x, self.player.position.y) == zone:
            self.strong_kills[zone] += 1
        self._check_quests(zone)
        self.update_stats()

    def _current_quest(self, zone):
        """Return the active quest tuple for a faction."""
        quest = self._quest_entry(zone)
        return quest[0], quest[1], quest[2]

    def _quest_entry(self, zone):
        """Load and cache one faction quest."""
        index = self.quest_index[zone]
        if self.quest_cache_zone != zone or self.quest_cache_index != index:
            data = self.view_manager.storage.deserialize(self.QUEST_PATH)
            for faction_zone, faction in enumerate(self.FACTIONS, 1):
                if self.quest_counts[faction_zone] == 0:
                    self.quest_counts[faction_zone] = len(data[faction])
            quests = data[self.FACTIONS[zone - 1]]
            if index < len(quests):
                quest = quests[index]
                self.quest_cache = (quest[0], quest[1], quest[2], quest[3])
            else:
                self.quest_cache = ("", 0, 0, "")
            self.quest_cache_zone = zone
            self.quest_cache_index = index
        return self.quest_cache

    def _check_quests(self, zone):
        """Advance completed quests and unlock skills."""
        if self.faction_done[zone]:
            return
        kind, a, _b = self._current_quest(zone)
        done = False
        if kind == "kill":
            done = self.q_kills[zone] >= a
        elif kind == "kill_fast":
            done = self.q_timer[zone] > 0 and self.q_streak[zone] >= a
        elif kind == "kill_low":
            done = self.q_timer[zone] > 0 and self.q_streak[zone] >= a and self.q_low[zone]
        elif kind == "find":
            done = self.strong_found[zone]
        elif kind == "clear":
            done = self.strong_kills[zone] >= a
        elif kind == "report":
            done = self.talked_flag
        if done:
            self._advance_quest(zone)

    def _advance_quest(self, zone):
        """Move to the next faction quest and unlock skills."""
        self.quest_index[zone] += 1
        self.q_kills[zone] = 0
        self.q_streak[zone] = 0
        self.q_timer[zone] = 0
        self.talked_flag = False
        self.player.xp += 20
        name = self.ZONE_NAMES[zone]
        if self.quest_index[zone] >= self.quest_counts[zone]:
            self.faction_done[zone] = True
            self.skills_unlocked = max(self.skills_unlocked, zone + 1)
            self.message = "%s cleared! Skill %d unlocked" % (name, zone + 1)
            self.message_timer = 180
            self._check_dragon()
        else:
            self.message = "%s: %s" % (name, self.quest_text(zone))
            self.message_timer = 120
        self._mark_progress()
        self.update_stats()

    def _check_dragon(self):
        """Summon the Dragon once every faction is cleared."""
        if self.faction_done[1] and self.faction_done[2] and self.faction_done[3]:
            if not self.dragon_spawned:
                self.dragon_spawned = True
                self.message = "The Dragon awakens!"
                self.message_timer = 180
                self._spawn_dragon()

    def quest_text(self, zone):
        """Return the current quest description."""
        text = self._quest_entry(zone)[3]
        return text if text else "done"

    def _update_light(self):
        """Point the sun by time of day and set the light level."""
        if self.level is None:
            return
        hour = self.clock // 60
        fraction = (self.clock % 60) / 60.0
        first = self.LIGHT_TABLE[hour]
        second = self.LIGHT_TABLE[(hour + 1) % 24]
        self.light = first[0] + (second[0] - first[0]) * fraction
        self.level.set_light_direction(
            first[1] + (second[1] - first[1]) * fraction, 
            1.0, 
            first[2] + (second[2] - first[2]) * fraction
        )

    def _objective_pos(self):
        """Return the position of the current quest objective."""
        if not self.wizard_met:
            return self.WIZARD_POS
        for zone in (1, 2, 3):
            if self.faction_done[zone]:
                continue
            kind, _target, _window = self._current_quest(zone)
            if kind == "report":
                return self.WIZARD_POS
            return (self.STRONGHOLDS[zone][0], self.STRONGHOLDS[zone][1])
        return self.WIZARD_POS

    def _quest_line_key(self):
        """Tuple of values that affect the HUD quest line text."""
        return (
            self.wizard_met,
            self.quest_index[1], self.quest_index[2], self.quest_index[3],
            self.q_kills[1], self.q_kills[2], self.q_kills[3],
            self.strong_kills[1], self.strong_kills[2], self.strong_kills[3],
            self.faction_done[1], self.faction_done[2], self.faction_done[3],
        )

    def _quest_line(self):
        """Return the tracked quest text for the HUD (cached)."""
        key = self._quest_line_key()
        if key != self.quest_line_key:
            if not self.wizard_met:
                line = "Quest: find the Wise Wizard"
            else:
                line = None
                for zone in (1, 2, 3):
                    if self.faction_done[zone]:
                        continue
                    kind, target, _window = self._current_quest(zone)
                    text = "%s: %s" % (self.ZONE_NAMES[zone], self.quest_text(zone))
                    if kind == "kill":
                        text += " (%d/%d)" % (min(self.q_kills[zone], target), target)
                    elif kind == "clear":
                        text += " (%d/%d)" % (min(self.strong_kills[zone], target), target)
                    line = text
                    break
                if line is None:
                    line = "Quest: slay the Dragon"
            self.quest_line_cache = line
            self.quest_line_key = key
        return self.quest_line_cache

    def _build_guide(self):
        """Create the ground arrow that points to the objective."""
        d = self.GUIDE_DISTANCE  # Match the player's sort key.
        mesh = Sprite3D()
        mesh.add_triangle(-0.70 + d, 0.03, -0.12, 0.25 + d, 0.03, 0.12,
                          0.25 + d, 0.03, -0.12, self.COLOR_ACCENT, False)
        mesh.add_triangle(-0.70 + d, 0.03, -0.12, -0.70 + d, 0.03, 0.12,
                          0.25 + d, 0.03, -0.12, self.COLOR_ACCENT, False)
        mesh.add_triangle(0.95 + d, 0.03, 0.00, 0.25 + d, 0.03, -0.35,
                          0.25 + d, 0.03, 0.35, self.COLOR_ACCENT, False)
        mesh.set_wireframe(False)
        self.guide = Entity(
            "Guide", ENTITY_TYPE_3D_SPRITE, Vector(0, 0), Vector(1, 1),
            None, None, None, None, None, None, None, None, False,
            SPRITE_3D_CUSTOM, self.COLOR_ACCENT,
        )
        self.guide.sprite_3d = mesh
        self.guide.sprite_3d_type = SPRITE_3D_CUSTOM
        self.guide.is_visible = False
        self.meshes.append(mesh)
        self.level.entity_add(self.guide)

    def _update_guide(self, player):
        """Aim the ground arrow at the current objective."""
        ox, oz = self._objective_pos()
        dx = ox - player.position.x
        dz = oz - player.position.y
        if dx * dx + dz * dz < 0.000001:
            self.guide.is_visible = False
            return
        # Arrow draws before player.
        self.guide.position_set(player.position.x, player.position.y)
        self.guide.set_3d_sprite_rotation(atan2(dz, dx))
        self.guide.is_visible = True

    def _build_bird(self):
        """Create the background bird."""
        self.bird = Entity(
            "Bird", ENTITY_TYPE_3D_SPRITE, Vector(0, 0, self.BIRD_HEIGHT),
            Vector(1, 1), None, None, None, None, None, None, None, None, False,
            SPRITE_3D_CUSTOM, self.COLOR_WHITE,
        )
        sprite = self._load_sprite(
            "picoware/apps/games/pge_adventure/bird.sprite3d")
        if sprite is not None:
            self.bird.set_sprite3d(sprite)
        self.bird.is_visible = False
        self.level.entity_add(self.bird)

    def _update_bird(self, player):
        """Fly the background bird up to twice a day."""
        if self.bird.elapsed_move_timer > 0:
            self.bird.elapsed_move_timer -= 1
            p = self.bird.position
            p.x += self.bird_dx
            p.y += self.bird_dz
            p.z = self.BIRD_HEIGHT
            self.bird.position = p
            self.bird.is_visible = True
            return
        self.bird.is_visible = False
        if self.light < 0.6 or self.bird_used >= 2:
            return
        self.bird_delay -= 1
        if self.bird_delay > 0:
            return
        self.bird_delay = 600 + _next_random(1200)
        self.bird_used += 1
        self.bird.elapsed_move_timer = self.BIRD_FLIGHT
        if self.camera.perspective == CAMERA_FIRST_PERSON:
            view_x = self.cos_h
            view_z = self.sin_h
        else:
            view_x = self.CAMERA_DIR_X
            view_z = self.CAMERA_DIR_Z
        side_x = -view_z
        side_z = view_x
        depth = 36.0
        camera_offset = (self.CAMERA_DISTANCE
                         if self.camera.perspective == CAMERA_THIRD_PERSON else 0.0)
        half_width = depth * self.draw.size.x / (2.0 * self.draw.size.y)
        p = self.bird.position
        p.x = (player.position.x + view_x * (depth + camera_offset)
                       - side_x * half_width * 0.8)
        p.y = (player.position.y + view_z * (depth + camera_offset)
                       - side_z * half_width * 0.8)
        self.bird.position = p
        speed = half_width * 1.6 / self.BIRD_FLIGHT
        self.bird_dx = side_x * speed
        self.bird_dz = side_z * speed

    def _update_halos(self):
        """Show the active buff halo on the player, hide the rest."""
        px = self.player.position.x
        pz = self.player.position.y
        active = self.buff_timer > 0
        for stat, halo in self.halos.items():
            if active and stat == self.buff_stat:
                halo.position_set(px, pz, self.HALO_HEIGHT)
                halo.is_visible = True
            else:
                halo.is_visible = False

    def _speed(self):
        """Return the clamped movement speed multiplier."""
        scale = self.speed_scale
        if scale < 1.0:
            return 1.0
        if scale > self.SPEED_MAX:
            return self.SPEED_MAX
        return scale

    def _wizard_talk(self):
        """Start the Wise Wizard conversation with one request."""
        self.wizard_met = True
        self.talked_flag = True
        for zone in (1, 2, 3):
            if not self.faction_done[zone]:
                self._check_quests(zone)
        if self.dragon_defeated:
            self.dialogue = "The Dragon is slain. The armor is yours."
        elif self.dragon_spawned:
            self.dialogue = "The Dragon waits in the wilds. End it."
        else:
            self.dialogue = ""
            for zone in (1, 2, 3):
                if not self.faction_done[zone]:
                    self.dialogue = "%s: %s" % (self.ZONE_NAMES[zone],
                                                self.quest_text(zone))
                    break
            if not self.dialogue:
                self.dialogue = "All lands are safe."
        self.talking = True
        self.dialogue_timer = 0
        self.message = "Wise Wizard"
        self.message_timer = 60

    def _wizard_accept(self):
        """Accept the request and teleport to the area start."""
        self.talking = False
        self.dialogue = ""
        for zone in (1, 2, 3):
            if self.faction_done[zone]:
                continue
            kind, _target, _window = self._current_quest(zone)
            if kind == "report":
                return
            sx, sz, radius = self.STRONGHOLDS[zone]
            dx = sx - self.player.position.x
            dz = sz - self.player.position.y
            length = (dx * dx + dz * dz) ** 0.5
            if length < 1.0:
                return
            step = (radius + 24.0) / length
            next_x = sx - dx * step
            next_z = sz - dz * step
            next_x = max(-self.WORLD_HALF_X + 1.0,
                         min(self.WORLD_HALF_X - 1.0, next_x))
            next_z = max(-self.WORLD_HALF_Z + 1.0,
                         min(self.WORLD_HALF_Z - 1.0, next_z))
            self.player.position_set(next_x, next_z)
            self.anchor_x = self.player.position.x
            self.anchor_z = self.player.position.y
            self._fill_world(self.anchor_x, self.anchor_z)
            self._fill_lands(self.anchor_x, self.anchor_z)
            self._update_camera()
            self._update_guide(self.player)
            self.message = "Wise Wizard: %s" % self.ZONE_NAMES[zone]
            self.message_timer = 90
            return

    def _tick_timers(self):
        """Count down timers and advance the day/night clock."""
        self.time_step += 1
        if self.time_step >= self.TIME_STEP:
            self.time_step = 0
            self.clock += 1
            if self.clock >= 1440:
                self.clock = 0
                self.bird_used = 0
            self._update_light()
        if self.attack_cd > 0:
            self.attack_cd -= 1
        for slot in range(4):
            if self.skill_cd[slot] > 0:
                self.skill_cd[slot] -= 1
        if self.special_cd > 0:
            self.special_cd -= 1
        if self.special_active > 0:
            self.special_active -= 1
        for zone in (1, 2, 3):
            if self.q_timer[zone] > 0:
                self.q_timer[zone] -= 1
        if self.buff_timer > 0:
            self.buff_timer -= 1
            if self.buff_timer == 0:
                halo = self.halos.get(self.buff_stat)
                if halo is not None:
                    halo.is_visible = False
                self.buff_stat = ""
                self.old_xp = -1
                self.update_stats()
        if self.combo_timer > 0:
            self.combo_timer -= 1
        if self.message_timer > 0:
            self.message_timer -= 1
            if self.message_timer == 0:
                self.message = ""
        if self.dialogue_timer > 0:
            self.dialogue_timer -= 1
            if self.dialogue_timer == 0:
                self.dialogue = ""
        if self.might_windup > 0:
            self.might_windup -= 1
            progress = self.MIGHT_WINDUP - self.might_windup
            self.sword_swing = -0.8 + progress * (1.6 / self.MIGHT_WINDUP)
            if self.might_windup == 0:
                self._knight_might_hit()
        if self.sword_swing_frames > 0:
            self.sword_swing_frames -= 1
            if self.sword_swing_frames == 0 and self.chaos_frames <= 0:
                self.beast_swing_mode = 0
        if self.conquer_frames > 0:
            self._knight_conquer_attack()
        if self.chaos_frames > 0:
            self.chaos_frames -= 1
            self.chaos_yaw += 0.35
            self.player_yaw += 0.35
            self.sword_yaw = self.player_yaw
            self.sword_swing = abs(sin(self.chaos_yaw * 3.0))
            if self.attack_cd <= 0:
                radius_sq = (self.HIT_RANGE * 3.0) ** 2
                damage = int(self.player.strength * self.chaos_power)
                for enemy in self._target_list:
                    if not enemy.is_visible:
                        continue
                    dx = enemy.position.x - self.player.position.x
                    dz = enemy.position.y - self.player.position.y
                    if dx * dx + dz * dz <= radius_sq:
                        self._damage(enemy, damage)
                self.attack_cd = 14
            if self.chaos_frames == 0:
                self.player_yaw -= self.chaos_yaw
                self.sword_yaw = self.player_yaw
                self.chaos_yaw = 0.0
                self.beast_swing_mode = 0

    def _button(self, game) -> int:
        """Return the current non-repeat button."""
        button = game.input
        if button == self.prev_button:
            return -1
        self.prev_button = button
        return button

    def _handle_nonplay_phase(self, button):
        """Phase 0/1 (intro / class select) input only; no game-loop work."""
        if self.phase == 0:
            if button in (4, 43):
                self.phase = 1
                self.class_name = self._load_class_names()[self.class_index]
                self._set_class_preview(self.class_name)
            elif button == BUTTON_BACK:
                self.exit_requested = True
            return
        if self.phase == 1:
            if button in (BUTTON_UP, BUTTON_LEFT):
                names = self._load_class_names()
                self.class_index = (self.class_index - 1) % len(names)
                self.class_name = names[self.class_index]
                self._set_class_preview(self.class_name)
            elif button in (BUTTON_DOWN, BUTTON_RIGHT):
                names = self._load_class_names()
                self.class_index = (self.class_index + 1) % len(names)
                self.class_name = names[self.class_index]
                self._set_class_preview(self.class_name)
            elif button in (4, 43):
                self.class_name = self._load_class_names()[self.class_index]
                self._set_class_preview(self.class_name)
                self.intro_done = True
                self._save_progress()
                # Build world after class selection.
                if not self.world_ready:
                    self.pending_world = True
                self.phase = 2
                self.ui = self.UI_HELP
                self.message = "%s chosen" % self.class_name
                self.message_timer = 90
            elif button == BUTTON_BACK:
                self.exit_requested = True

    def update_player(self, player, game):
        """Drive the story phase and the player."""
        button = self._button(game)
        self.player.is_visible = (
            self.ui == self.UI_NONE
            and self.camera.perspective != CAMERA_FIRST_PERSON
        )
        # Skip game updates outside play.
        if self.phase != 2:
            self._handle_nonplay_phase(button)
            return

        self._tick_timers()
        self._net_pump()

        if self.ui == self.UI_HELP:
            if button in (4, 43):
                self.ui = self.UI_NONE
            return
        if self.ui == self.UI_MENU:
            if button == BUTTON_UP:
                self.menu_index = (self.menu_index - 1) % len(self.MENU_ITEMS)
            elif button == BUTTON_DOWN:
                self.menu_index = (self.menu_index + 1) % len(self.MENU_ITEMS)
            elif button == BUTTON_LEFT and self.menu_index == 1:
                self.speed_scale = max(1.0, self._speed() - self.SPEED_STEP)
                self._mark_progress()
            elif button == BUTTON_RIGHT and self.menu_index == 1:
                self.speed_scale = min(self.SPEED_MAX,
                                       self._speed() + self.SPEED_STEP)
                self._mark_progress()
            elif button == BUTTON_BACK:
                self.ui = self.UI_NONE
            elif button in (4, 43) and self.menu_index == 2:
                self.camera.perspective = (
                    CAMERA_FIRST_PERSON
                    if self.camera.perspective == CAMERA_THIRD_PERSON
                    else CAMERA_THIRD_PERSON
                )
                self._update_camera()
                self._mark_progress()
            elif button in (4, 43) and self.menu_index == 3:
                self.exit_requested = True
            return
        if self.talking:
            if button in (4, 43):
                self._wizard_accept()
            return

        if button == BUTTON_CENTER:
            self._interact()
            self.combo_timer = self.COMBO_WINDOW
        elif button == BUTTON_BACK:
            if self.combo_timer > 0:
                self._use_skill(4)
                self.combo_timer = 0
            else:
                self.ui = self.UI_MENU
                self.menu_index = 0
                self.prev_button = -1
            return
        elif self.combo_timer > 0:
            if button == BUTTON_UP:
                self._use_skill(0)
                self.combo_timer = 0
            elif button == BUTTON_RIGHT:
                self._use_skill(1)
                self.combo_timer = 0
            elif button == BUTTON_DOWN:
                self._use_skill(2)
                self.combo_timer = 0
            elif button == BUTTON_LEFT:
                self._use_skill(3)
                self.combo_timer = 0

        self._keyboard_skill(button)
        self._move(player, game)
        if player.has_changed_position():
            self._update_camera()
            self._update_halos()
        if self.class_name == "Knight" and self.sword_triangles:
            swing = self.sword_swing
            if swing > 0.0:
                self.sword_swing = max(0.0, swing - 0.05)
            yaw = self.sword_yaw - self.player_yaw
            yaw_cos = cos(yaw)
            yaw_sin = sin(yaw)
            swing_cos = cos(self.sword_swing)
            swing_sin = sin(self.sword_swing)
            for offset, triangle in enumerate(self.sword_triangles):
                vertices = []
                for vertex in (0, 3, 6):
                    x = 0
                    y = 0
                    z = 0
                    if vertex == 0:
                        x = triangle.x1 - 0.4
                        y = triangle.y1 - 1.283
                        z = triangle.z1 - 0.04
                    elif vertex == 3:
                        x = triangle.x2 - 0.4
                        y = triangle.y2 - 1.283
                        z = triangle.z2 - 0.04
                    elif vertex == 6:
                        x = triangle.x3 - 0.4
                        y = triangle.y3 - 1.283
                        z = triangle.z3 - 0.04

                    rotated_x = x * yaw_cos - z * yaw_sin
                    rotated_z = x * yaw_sin + z * yaw_cos
                    x = rotated_x * swing_cos - y * swing_sin + 0.4
                    y = rotated_x * swing_sin + y * swing_cos + 1.283
                    vertices.extend((x, y, rotated_z + 0.04))
                self.player.sprite_3d.update_triangle(
                    216 + offset, *vertices, triangle.color, triangle.wireframe)
        elif self.class_name == "Beast" and self.beast_triangles:
            if self.chaos_frames <= 0 and self.sword_swing > 0.0:
                self.sword_swing = max(0.0, self.sword_swing - 0.12)
            yaw = self.sword_yaw - self.player_yaw
            yaw_cos = cos(yaw)
            yaw_sin = sin(yaw)
            flap = self.sword_swing
            for index, triangle, side in self.beast_triangles:
                if self.beast_swing_mode == 0:
                    self.player.sprite_3d.update_triangle(
                        index, triangle.x1, triangle.y1, triangle.z1,
                        triangle.x2, triangle.y2, triangle.z2,
                        triangle.x3, triangle.y3, triangle.z3,
                        triangle.color, triangle.wireframe)
                    continue
                if self.beast_swing_mode == 1 and side != self.beast_right_side:
                    self.player.sprite_3d.update_triangle(
                        index, triangle.x1, triangle.y1, triangle.z1,
                        triangle.x2, triangle.y2, triangle.z2,
                        triangle.x3, triangle.y3, triangle.z3,
                        triangle.color, triangle.wireframe)
                    continue
                if self.beast_swing_mode == 3:
                    swing = sin(self.chaos_yaw * 3.0 + (side < 0) * pi) * 0.9
                elif self.beast_swing_mode in (1, 2):
                    swing = flap * side
                else:
                    continue
                pivot_x = side * 0.27
                vertices = []
                for vertex in (0, 3, 6):
                    if vertex == 0:
                        x, y, z = triangle.x1 - pivot_x, triangle.y1 - 1.28, triangle.z1
                    elif vertex == 3:
                        x, y, z = triangle.x2 - pivot_x, triangle.y2 - 1.28, triangle.z2
                    else:
                        x, y, z = triangle.x3 - pivot_x, triangle.y3 - 1.28, triangle.z3
                    rotated_x = x * yaw_cos - z * yaw_sin
                    rotated_z = x * yaw_sin + z * yaw_cos
                    swing_cos = cos(swing)
                    swing_sin = sin(swing)
                    x = rotated_x * swing_cos - y * swing_sin + pivot_x
                    y = rotated_x * swing_sin + y * swing_cos + 1.28
                    vertices.extend((x, y, rotated_z))
                self.player.sprite_3d.update_triangle(
                    index, *vertices, triangle.color, triangle.wireframe)

        if self.special_active > 0:
            self._attack()

        if self.player.health < self.player.max_health:
            self.player.elapsed_health_regen += 1
            if self.player.elapsed_health_regen >= 30:
                self.player.elapsed_health_regen = 0
                self.player.health += self.player.health_regen
                self.player.health = min(self.player.health, self.player.max_health)

        zone = zone_for(player.position.x, player.position.y)
        if zone and self._in_stronghold(player.position.x, player.position.y) == zone:
            if not self.strong_found[zone]:
                self.strong_found[zone] = True
                self.message = "Found the %s!" % self.ZONE_STRONG[zone]
                self.message_timer = 150
                self._check_quests(zone)
        # Show Wizard when nearby.
        dx = self.wizard.position.x - player.position.x
        dz = self.wizard.position.y - player.position.y
        self.wizard.is_visible = dx * dx + dz * dz <= self.FIELD_OF_VIEW * self.FIELD_OF_VIEW
        if player.has_changed_position():
            self._update_guide(player)
        self._update_bird(player)

    def _keyboard_skill(self, button):
        """Handle direct keyboard skill keys."""
        if button in (BUTTON_1, BUTTON_K):
            self._use_skill(0)
        elif button in (BUTTON_2, BUTTON_L):
            self._use_skill(1)
        elif button in (BUTTON_3, BUTTON_O):
            self._use_skill(2)
        elif button in (BUTTON_4, BUTTON_P):
            self._use_skill(3)
        elif button in (BUTTON_5, BUTTON_SPACE):
            self._use_skill(4)

    def _move(self, player, game):
        """Walk and turn the player; skip movement during a Conquer charge."""
        if self.conquer_frames > 0:
            return
        if self.attack_return_frames > 0:
            remaining = self.attack_return_frames
            position = player.position
            next_x = position.x + (self.attack_return_x - position.x) / remaining
            next_z = position.y + (self.attack_return_z - position.y) / remaining
            player.position_set(next_x, next_z, 0.0)
            self.attack_return_frames -= 1
            return
        button = game.input
        speed = 0.0
        scale = self._speed()
        if button == BUTTON_UP:
            scale *= self.player.speed / self.base_speed
            speed = self.WALK_SPEED * scale
        elif button == BUTTON_DOWN:
            speed = -self.WALK_BACK * scale
        if button == BUTTON_LEFT:
            self.heading -= self.WALK_TURN
        elif button == BUTTON_RIGHT:
            self.heading += self.WALK_TURN

        if button in (BUTTON_LEFT, BUTTON_RIGHT):
            self.cos_h = cos(self.heading)
            self.sin_h = sin(self.heading)
            self.player_yaw = self.heading - pi * 0.5 + self.PLAYER_ANGLE
            if self.sword_swing_frames <= 0 and self.conquer_frames <= 0:
                self.sword_yaw = self.heading
        dx = self.cos_h
        dz = self.sin_h
        if speed != 0.0:
            next_x = player.position.x + dx * speed
            next_z = player.position.y + dz * speed
            next_x = max(-self.WORLD_HALF_X + 1.0,
                         min(self.WORLD_HALF_X - 1.0, next_x))
            next_z = max(-self.WORLD_HALF_Z + 1.0,
                         min(self.WORLD_HALF_Z - 1.0, next_z))
            player.position_set(next_x, next_z)
        player.direction_set(dx, dz)
        player.set_3d_sprite_rotation(self.player_yaw)

    def _update_camera(self):
        """Position the camera for the selected perspective."""
        if self.camera is None:
            return
        px = self.player.position.x
        pz = self.player.position.y
        plane = self.camera.plane
        plane_scale = (plane.x * plane.x + plane.y * plane.y) ** 0.5
        if self.camera.perspective == CAMERA_FIRST_PERSON:
            self.player.is_player = True
            direction_x = self.cos_h
            direction_z = self.sin_h
            self.camera.position_set(px, pz)
            self.camera.direction_set(direction_x, direction_z)
            self.camera.plane_set(
                -direction_z * plane_scale, direction_x * plane_scale
            )
            self.camera.height = self.CAMERA_FIRST_HEIGHT
        else:
            self.player.is_player = False
            self.camera.position_set(
                px - self.CAMERA_DIR_X * self.CAMERA_DISTANCE,
                pz - self.CAMERA_DIR_Z * self.CAMERA_DISTANCE,
            )
            self.camera.direction_set(self.CAMERA_DIR_X, self.CAMERA_DIR_Z)
            self.camera.plane_set(
                -self.CAMERA_DIR_Z * plane_scale,
                self.CAMERA_DIR_X * plane_scale,
            )
            self.camera.height = self.CAMERA_HEIGHT
        self.player.is_visible = (
            self.ui == self.UI_NONE
            and self.camera.perspective != CAMERA_FIRST_PERSON
        )

    def _near_wizard(self):
        """Return whether the player is beside the Wise Wizard."""
        dx = self.player.position.x - self.wizard.position.x
        dz = self.player.position.y - self.wizard.position.y
        return dx * dx + dz * dz <= self.TALK_RANGE * self.TALK_RANGE

    def _interact(self):
        """Talk to NPCs or pick up items with CENTER."""
        if self._near_wizard():
            self._wizard_talk()

    def draw_hud(self, draw):
        """Draw health, XP, quest and minimap."""
        if self.engine is None:
            return
        width = draw.size.x

        if self.phase == 0:
            self._draw_intro(draw)
            return
        if self.phase == 1:
            self._draw_class_select(draw, width)
            return
        if self.ui == self.UI_HELP:
            self._draw_help(draw)
            return
        if self.ui == self.UI_MENU:
            if self.menu_index == 1:
                self._draw_stats(draw, width)
            else:
                self._draw_full_map(draw)
            self._draw_view_list(draw, width)
            return

        bar = draw.scale_y(6)
        draw._fill_rectangle(0, 0, width, draw.scale_y(20), self.COLOR_BLACK)

        hp_width = width * self.player.health / self.player.max_health
        hp_width = max(hp_width, 0)
        draw._fill_rectangle(0, 0, width, bar, self.COLOR_HP_BACK)
        draw._fill_rectangle(0, 0, hp_width, bar, self.COLOR_HP)

        xp_width = int(width * self.player.xp / self.xp_to_next) if self.xp_to_next else 0
        xp_width = max(0, min(xp_width, width))
        draw._fill_rectangle(0, bar, width, bar, self.COLOR_XP_BACK)
        draw._fill_rectangle(0, bar, xp_width, bar, self.COLOR_XP)

        line = self._quest_line()
        limit = int((width - draw.scale_y(self.MINIMAP_W) - draw.scale_x(6))
                    // draw.font_size.x)
        twenty_one = draw.scale_y(21)
        draw._text(draw.scale_x(3), twenty_one, line[:max(4, limit)],
                   self.COLOR_TEXT)

        if self.talking or self.dialogue_timer > 0:
            self._draw_dialogue(draw, width)
        elif self.message_timer > 0:
            draw._text((draw.size.x - draw.len(self.message)) // 2, twenty_one + draw.font_size.y + 2,
                       self.message, self.COLOR_ACCENT)
        elif self._near_wizard():
            draw._text((draw.size.x - draw.len("CENTER: talk")) // 2, twenty_one + draw.font_size.y + 2,
                       "CENTER: talk", self.COLOR_ACCENT)

        self._draw_minimap(draw)

    def _project(self, x, z, height, screen_w, screen_h):
        """Project a world point to the screen; -1 when behind."""
        wx = x - self.camera.position.x
        wz = z - self.camera.position.y
        camera_x = wx * -self.camera.direction.y + wz * self.camera.direction.x
        camera_z = wx * self.camera.direction.x + wz * self.camera.direction.y
        if camera_z <= 0.1:
            return -1.0, -1.0
        inv = 1.0 / camera_z
        return (camera_x * inv * screen_h + screen_w * 0.5,
            -(height - self.camera.height) * inv * screen_h + screen_h * 0.5)

    def _draw_intro(self, draw):
        """Draw the opening dragon story beat."""
        height = draw.size.y
        draw.erase()
        lines = (
            "Your sister is taken by the Dragon.",
            "Ghouls, Goblins and Soldiers hold the land.",
            "Slay them, grow strong, take back the Nolands.",
        )
        for index, line in enumerate(lines):
            draw._text(draw.scale_x(6), draw.scale_y(10) + (index * draw.font_size.y), line,
                       self.COLOR_TEXT)
        draw._text(draw.scale_x(6), height - draw.scale_y(16), "CENTER to continue",
                   self.COLOR_ACCENT)

    def _draw_class_select(self, draw, width):
        """Draw the Wise Wizard character select."""
        font_h = draw.font_size.y
        pad = draw.scale_y(4)
        top = draw.scale_y(18)
        names = self._load_class_names()
        box_h = int(pad * 2 + font_h * (len(names) + 2))
        draw._fill_rectangle(draw.scale_x(8), top, width - draw.scale_x(16), box_h,
                             self.COLOR_BLACK)
        draw._rectangle(draw.scale_x(8), top, width - draw.scale_x(16), box_h,
                        self.COLOR_ACCENT)
        draw._text(draw.scale_x(12), top + pad,
                   "Wise Wizard: Who are you?", self.COLOR_ACCENT)
        for index, name in enumerate(names):
            marker = ">" if index == self.class_index else " "
            color = self.COLOR_ACCENT if index == self.class_index else self.COLOR_DIM
            draw._text(draw.scale_x(12), top + pad + (index + 1) * font_h,
                       "%s %s" % (marker, name), color)
        draw._text(draw.scale_x(12), top + pad + (len(names) + 1) * font_h,
                   "UP/DOWN: pick  CENTER: go", self.COLOR_ROCK)

    def _draw_help(self, draw):
        """Draw the controls help screen."""
        height = draw.size.y
        draw.erase()
        draw._text(draw.scale_x(6), draw.scale_y(10), "Controls", self.COLOR_ACCENT)
        lines = (
            "DPAD: move",
            "CENTER: talk / grab",
            "CENTER then DPAD: use skill",
            "CENTER then BACK: special",
            "BACK: map and stats",
        )
        row = draw.scale_y(24)
        for index, line in enumerate(lines):
            draw._text(draw.scale_x(6), row + index * draw.font_size.y, line,
                       self.COLOR_TEXT)
        draw._text(draw.scale_x(6), height - draw.scale_y(16), "CENTER to begin",
                   self.COLOR_ACCENT)

    def _draw_view_list(self, draw, width):
        """Draw the side view list."""
        height = draw.size.y
        left = int(width * 0.62)
        top = int(height * 0.10)
        step = draw.font_size.y + draw.scale_y(2)
        draw._rectangle(left, top, int(width - left - draw.scale_x(4)),
                        int(height * 0.74), self.COLOR_ACCENT)
        for index, label in enumerate(self.MENU_ITEMS):
            if index == 2:
                label = ("1st Person" if self.camera.perspective == CAMERA_FIRST_PERSON
                         else "3rd Person")
            color = self.COLOR_ACCENT if index == self.menu_index else self.COLOR_DIM
            draw._text(left + draw.scale_x(4),
                       int(top + draw.scale_y(6) + index * step), label, color)
        draw._text(left + draw.scale_x(4),
                   int(top + draw.scale_y(6) + len(self.MENU_ITEMS) * step),
                   "%02d:%02d" % (self.clock // 60, self.clock % 60), self.COLOR_TEXT)

    def _draw_full_map(self, draw):
        """Draw the whole-world map screen."""
        width = draw.size.x
        height = draw.size.y
        draw.erase()
        pane = int(width * 0.58)
        pad_y = draw.scale_y(14)
        legend = (
            (self.COLOR_PLAYER, "You"),
            (self.COLOR_WIZARD, "Wizard"),
            (self.COLOR_HP, "Enemy"),
            (self.ZONE_ENEMY[1], "Stronghold"),
        )
        step = draw.font_size.y + draw.scale_y(2)
        legend_h = int(step * len(legend) + draw.scale_y(4))
        avail_w = pane - draw.scale_x(8) * 2
        avail_h = height - pad_y - draw.scale_y(22) - legend_h
        map_w = avail_w
        map_h = map_w * 0.5
        if map_h > avail_h:
            map_h = avail_h
            map_w = map_h * 2.0
        left = (pane - map_w) * 0.5
        top = pad_y + (avail_h - map_h) * 0.5
        half_w = map_w * 0.5
        half_h = map_h * 0.5

        draw._fill_rectangle(int(left), int(top), int(half_w), int(half_h), self.ZONE_GROUND[0])
        draw._fill_rectangle(int(left + half_w), int(top), int(half_w), int(half_h), self.ZONE_GROUND[1])
        draw._fill_rectangle(int(left), int(top + half_h), int(half_w), int(half_h), self.ZONE_GROUND[2])
        draw._fill_rectangle(int(left + half_w), int(top + half_h), int(half_w),
                             int(half_h), self.ZONE_GROUND[3])

        draw._text(int(left + half_w * 0.25), int(top + half_h * 0.45), "Nolands",
                   self.COLOR_TEXT)
        draw._text(int(left + half_w * 1.25), int(top + half_h * 0.45), "Ghouls",
                   self.COLOR_TEXT)
        draw._text(int(left + half_w * 0.25), int(top + half_h * 1.45), "Goblins",
                   self.COLOR_TEXT)
        draw._text(int(left + half_w * 1.25), int(top + half_h * 1.45), "Soldiers",
                   self.COLOR_TEXT)

        for zone in (1, 2, 3):
            sx, sz, _radius = self.STRONGHOLDS[zone]
            mx = left + (sx / self.WORLD_HALF_X * 0.5 + 0.5) * map_w
            mz = top + (sz / self.WORLD_HALF_Z * 0.5 + 0.5) * map_h
            color = self.COLOR_DIM if self.faction_done[zone] else self.ZONE_ENEMY[zone]
            draw._fill_rectangle(int(mx) - 3, int(mz) - 3, 6, 6, color)

        wx = left + (self.WIZARD_POS[0] / self.WORLD_HALF_X * 0.5 + 0.5) * map_w
        wz = top + (self.WIZARD_POS[1] / self.WORLD_HALF_Z * 0.5 + 0.5) * map_h
        draw._fill_rectangle(int(wx) - 3, int(wz) - 3, 7, 7, self.COLOR_WHITE)
        draw._fill_rectangle(int(wx) - 2, int(wz) - 2, 5, 5, self.COLOR_WIZARD)

        for enemy in self._target_list:
            if not enemy.is_visible:
                continue
            ex = left + (enemy.position.x / self.WORLD_HALF_X * 0.5 + 0.5) * map_w
            ez = top + (enemy.position.y / self.WORLD_HALF_Z * 0.5 + 0.5) * map_h
            draw._fill_rectangle(int(ex), int(ez), 3, 3, self.COLOR_HP)

        px = left + (self.player.position.x / self.WORLD_HALF_X * 0.5 + 0.5) * map_w
        pz = top + (self.player.position.y / self.WORLD_HALF_Z * 0.5 + 0.5) * map_h
        draw._fill_rectangle(int(px) - 2, int(pz) - 2, 5, 5, self.COLOR_PLAYER)
        draw._rectangle(int(left), int(top), int(map_w), int(map_h), self.COLOR_WHITE)
        # Legend below the map.
        swatch = int(draw.font_size.y)
        row = top + map_h + draw.scale_y(4)
        for color, label in legend:
            draw._fill_rectangle(draw.scale_x(6), int(row), swatch, swatch, color)
            draw._text(draw.scale_x(6) + swatch + draw.scale_x(3), row, label,
                       self.COLOR_TEXT)
            row += step
        draw._text(draw.scale_x(6), height - draw.scale_y(10),
                   "UP/DOWN: view  BACK: close", self.COLOR_ROCK)

    def _draw_stats(self, draw, width):
        """Draw the stats, skills and class screen."""
        height = draw.size.y
        draw.erase()
        step = draw.font_size.y + draw.scale_y(2)
        row = draw.scale_y(6)
        draw._text(draw.scale_x(6), row,
                   "Class: %s" % self.class_name, self.COLOR_TEXT)
        row += step
        draw._text(draw.scale_x(6), row,
                   "Level %d   XP %d/%d" % (self.player.level, int(self.player.xp),
                                            int(self.xp_to_next)), self.COLOR_TEXT)
        row += step
        draw._text(draw.scale_x(6), row,
                   "HP %d/%d   STR %d" % (int(self.player.health), int(self.player.max_health),
                                          int(self.player.strength)), self.COLOR_TEXT)
        row += step
        draw._text(draw.scale_x(6), row,
                   "Speed x%.1f  (LEFT/RIGHT)" % self._speed(), self.COLOR_TEXT)
        row += step * 2
        draw._text(draw.scale_x(6), row, "Skills", self.COLOR_ACCENT)
        row += step
        skills = self._class_entry()[2]
        for slot in range(5):
            if slot > self.skills_unlocked - 1:
                draw._text(draw.scale_x(10), row + slot * step,
                           "%d: --" % (slot + 1), self.COLOR_DIM)
            else:
                draw._text(draw.scale_x(10), row + slot * step,
                           "%d: %s" % (slot + 1, skills[slot][0]), self.COLOR_TEXT)
        draw._text(draw.scale_x(6), height - draw.scale_y(10),
                   "UP/DOWN: view  BACK: close", self.COLOR_ROCK)

    def _draw_dialogue(self, draw, width):
        """Draw the Wise Wizard dialogue box."""
        font_h = draw.font_size.y
        pad = draw.scale_y(2)
        lines = 3
        rows = lines + 1
        if self.talking:
            rows += 1
        box_h = int(pad * 2 + font_h * rows)
        top = int(draw.size.y) - box_h
        draw._fill_rectangle(0, top, width, box_h, self.COLOR_BLACK)
        draw._rectangle(0, top, width, box_h, self.COLOR_ACCENT)
        draw._text(draw.scale_x(3), top + pad, "Wise Wizard:", self.COLOR_ACCENT)
        wrap = max(1, int((width - draw.scale_x(6)) // draw.font_size.x))
        text = self.dialogue
        line = 0
        while text and line < lines:
            draw._text(draw.scale_x(3), top + pad + (line + 1) * font_h,
                       text[:wrap], self.COLOR_TEXT)
            text = text[wrap:]
            line += 1
        if self.talking:
            draw._text(draw.scale_x(3), top + pad + (lines + 1) * font_h,
                       "CENTER: accept", self.COLOR_ACCENT)

    def _draw_minimap(self, draw):
        """Draw a player-centred field-of-view radar."""
        width = draw.size.x
        size_w = draw.scale_x(self.MINIMAP_W)
        size_h = draw.scale_y(self.MINIMAP_H)
        left = width - size_w - draw.scale_x(3)
        top = draw.scale_y(29)
        center_x = left + size_w * 0.5
        center_y = top + size_h * 0.5
        scale = (size_h * 0.5) / self.FIELD_OF_VIEW
        cos_h = self.cos_h
        sin_h = self.sin_h
        player_x = self.player.position.x
        player_z = self.player.position.y
        zone = zone_for(player_x, player_z)
        draw._fill_rectangle(left, top, size_w, size_h,
                             self.ZONE_GROUND[zone])
        # Nearby strongholds.
        for index in (1, 2, 3):
            sx, sz, _radius = self.STRONGHOLDS[index]
            dx = sx - player_x
            dz = sz - player_z
            if dx * dx + dz * dz > self.FIELD_OF_VIEW * self.FIELD_OF_VIEW:
                continue
            mx = center_x + (-dx * sin_h + dz * cos_h) * scale
            mz = center_y - (dx * cos_h + dz * sin_h) * scale
            color = self.COLOR_DIM if self.faction_done[index] else self.ZONE_ENEMY[index]
            draw._fill_rectangle(mx - 2, mz - 2, 4, 4, color)

        dx = self.WIZARD_POS[0] - player_x
        dz = self.WIZARD_POS[1] - player_z
        if dx * dx + dz * dz <= self.FIELD_OF_VIEW * self.FIELD_OF_VIEW:
            mx = center_x + (-dx * sin_h + dz * cos_h) * scale
            mz = center_y - (dx * cos_h + dz * sin_h) * scale
            draw._fill_rectangle(mx - 1, mz - 1, 3, 3, self.COLOR_WIZARD)

        for enemy in self._target_list:
            dx = enemy.position.x - player_x
            dz = enemy.position.y - player_z
            if dx * dx + dz * dz > self.FIELD_OF_VIEW * self.FIELD_OF_VIEW:
                continue
            mx = center_x + (-dx * sin_h + dz * cos_h) * scale
            mz = center_y - (dx * cos_h + dz * sin_h) * scale
            draw._fill_rectangle(mx, mz, 2, 2, self.COLOR_HP)

        draw._fill_rectangle(center_x - 1, center_y - 1, 3, 3,
                             self.COLOR_PLAYER)
        draw._fill_rectangle(center_x - 1, center_y - 6, 3, 4,
                             self.COLOR_PLAYER)
        draw._rectangle(left, top, size_w, size_h, self.COLOR_WHITE)
        name = self.ZONE_NAMES[zone]
        draw._text(left + size_w - draw.len(name),
                   top + size_h + draw.scale_y(2), name, self.COLOR_TEXT)

    def _load_progress(self):
        """Load the local save dict, or None."""
        return self.view_manager.storage.deserialize(self.SAVE_PATH)

    def _apply_progress(self, data):
        """Restore level, skills and quest progress."""
        try:
            level = max(1, int(data.get("level", 1)))
            self.player.level = level
            self.player.max_health = health_for_level(level)
            self.player.strength = strength_for_level(level)
            self.player.health = float(data.get("health", self.player.max_health))
            self.player.health_regen = 1
            self.player.elapsed_health_regen = 0
            if self.player.health > self.player.max_health or self.player.health <= 0:
                self.player.health = self.player.max_health
            xp_total = max(0, int(data.get("xp", 0)))
            if int(data.get("v", 1)) < 2:
                # v1 XP was level-specific.
                for lv in range(2, level + 1):
                    xp_total += xp_for_level(lv)
            self.player.xp = xp_total
            self.old_xp = -1
            self.old_level = 0
            names = self._load_class_names()
            self.class_index = int(data.get("class", 0)) % len(names)
            self.class_name = names[self.class_index]
            self.intro_done = bool(data.get("intro", 0))
            self.skills_unlocked = max(1, min(5, int(data.get("skills", 1))))
            self.dragon_defeated = bool(data.get("dragon", 0))
            self.armor_earned = bool(data.get("armor", 0))
            qi = data.get("qi", [])
            sf = data.get("sf", [])
            sk = data.get("sk", [])
            fd = data.get("fd", [])
            qk = data.get("qk", [])
            for zone in (1, 2, 3):
                if isinstance(qi, list) and zone < len(qi):
                    self.quest_index[zone] = int(qi[zone])
                if isinstance(sf, list) and zone < len(sf):
                    self.strong_found[zone] = bool(sf[zone])
                if isinstance(sk, list) and zone < len(sk):
                    self.strong_kills[zone] = int(sk[zone])
                if isinstance(fd, list) and zone < len(fd):
                    self.faction_done[zone] = bool(fd[zone])
                if isinstance(qk, list) and zone < len(qk):
                    self.q_kills[zone] = int(qk[zone])
            if self.faction_done[3]:
                self.skills_unlocked = max(self.skills_unlocked, 4)
            if self.dragon_defeated:
                self.skills_unlocked = 5
            self.dragon_spawned = (self.faction_done[1] and self.faction_done[2]
                                   and self.faction_done[3])
            self.wizard_met = bool(data.get("met", 0))
            self.clock = int(data.get("clock", self.CLOCK_START)) % 1440
            self.speed_scale = float(data.get("speed", 1.0))
            self.speed_scale = self._speed()
            self._update_light()
            self.heading = float(data.get("h", self.heading))
            self.cos_h = cos(self.heading)
            self.sin_h = sin(self.heading)
            self.player_yaw = self.heading - pi * 0.5 + self.PLAYER_ANGLE
            self.sword_yaw = self.heading
            x = float(data.get("x", self.PLAYER_SPAWN[0]))
            z = float(data.get("z", self.PLAYER_SPAWN[1]))
            x = max(-self.WORLD_HALF_X + 1.0,
                    min(self.WORLD_HALF_X - 1.0, x))
            z = max(-self.WORLD_HALF_Z + 1.0,
                    min(self.WORLD_HALF_Z - 1.0, z))
            self.player.position_set(x, z)
            self.player.direction_set(self.cos_h, self.sin_h)
            self.player.set_3d_sprite_rotation(self.player_yaw)
            self.anchor_x = x
            self.anchor_z = z
            self.camera.perspective = data.get("camera", CAMERA_THIRD_PERSON)
            self._update_camera()
            self.update_stats()
        except Exception:
            pass

    def _save_progress(self):
        """Persist level, XP and quest progress locally."""
        if self.player is None:
            return
        try:
            self.view_manager.storage.serialize({
                "v": 2,
                "level": self.player.level,
                "xp": int(self.player.xp),
                "health": int(self.player.health),
                "class": self.class_index,
                "skills": self.skills_unlocked,
                "dragon": 1 if self.dragon_defeated else 0,
                "armor": 1 if self.armor_earned else 0,
                "intro": 1 if self.intro_done else 0,
                "qi": self.quest_index,
                "sf": [1 if b else 0 for b in self.strong_found],
                "sk": self.strong_kills,
                "fd": [1 if b else 0 for b in self.faction_done],
                "qk": self.q_kills,
                "met": 1 if self.wizard_met else 0,
                "clock": self.clock,
                "speed": self.speed_scale,
                "x": self.player.position.x,
                "z": self.player.position.y,
                "h": self.heading,
                "camera": self.camera.perspective,
            }, self.SAVE_PATH)
        except Exception:
            pass

    def _mark_progress(self):
        """Flag and persist a progression change."""
        self.net_dirty = True
        self._save_progress()

    def _boot_begin(self):
        """Check stored credentials and log in, or prompt for them."""
        from picoware.system.settings import Settings

        creds = Settings(self.view_manager.storage).server_settings
        self.net_user = creds.get("username")
        self.net_pass = creds.get("password")
        self.boot_state = self.BOOT_LOGIN
        self._start_login()

    def _start_login(self):
        """Create the HTTP client and log in."""
        if not self.net_user or not self.net_pass:
            return
        if self._http_request("https://www.jblanked.com/flipper/api/user/login/", {"username": self.net_user,
                                          "password": self.net_pass}):
            self.net_state = self.NET_LOGIN
            self.net_status = "Logging in..."

    def update_stats(self):
        """Derive level and stats from the player's XP."""
        if self.player is None:
            return
        xp = int(self.player.xp)
        if xp == self.old_xp:
            return
        level = 1
        remaining = xp
        need = xp_for_level(2)
        while level < 50 and remaining >= need:
            remaining -= need
            level += 1
            need = xp_for_level(level + 1)
        self.player.level = level
        self.xp_to_next = need
        self.player.max_health = health_for_level(level)
        self.player.strength = strength_for_level(level)
        self.player.speed = self.base_speed
        self.player.level = level
        self.player.health = min(self.player.health, self.player.max_health)
        if self.buff_stat == "health":
            boost = int(self.player.max_health * 0.35)
            self.player.max_health += boost
        elif self.buff_stat == "strength":
            boost = int(self.player.strength * 0.35)
            self.player.strength += boost
        elif self.buff_stat == "speed":
            self.player.speed = self.base_speed * 1.35
        if level > self.old_level and self.phase == 2:
            self.player.health = self.player.max_health
            self.message = "Level %d!" % level
            self.message_timer = 120
            self._mark_progress()
        self.old_level = level
        self.old_xp = xp

    def boot(self):
        """Drive credential entry and login. Return False to exit."""
        if self.boot_state == self.BOOT_LOGIN:
            self._net_pump()
            # Wait for stats buffers.
            # Free buffers before sprite loading.
            if self.net_state in (self.NET_READY, self.NET_ERROR, self.NET_OFF):
                if self._loading is not None:
                    self._loading.stop()
                    del self._loading
                    self._loading = None
                self._open_scene()
            else:
                self._draw_boot()
            return True
        return True

    def _draw_boot(self):
        """Draw the login status screen while the scene is closed."""
        if self._loading is None:
            from picoware.gui.loading import Loading
            self._loading = Loading(self.draw)
        self._loading.text = self.net_status or "connecting"
        self._loading.animate(swap=True)

    def _open_scene(self):
        """Build the world and start the engine."""
        if self.scene_open:
            return
        if self.http is not None:
            self.http.close()
            del self.http
            self.http = None

        from picoware.engine.camera import CAMERA_THIRD_PERSON, Camera
        from picoware.engine.engine import GameEngine
        from picoware.engine.game import Game
        from picoware.engine.level import Level

        collect()

        self.camera = Camera(
            direction=Vector(self.CAMERA_DIR_X, self.CAMERA_DIR_Z),
            plane=Vector(-0.72, 0),
            height=self.CAMERA_HEIGHT,
            distance=self.CAMERA_DISTANCE,
            perspective=CAMERA_THIRD_PERSON,
        )
        game = Game(
            "PGE Adventure",
            self.draw.size,
            self.draw,
            self.view_manager.input_manager,
            self.COLOR_TEXT,
            self.ZONE_SKY[0],
            self.camera,
        )
        self.game = game
        self.level = Level("Wilds", self.draw.size, game)
        self.level.set_shadow_color(self.SHADOW_COLOR)
        self.level.clear_allowed = False
        self._update_light()
        self._build_background()
        self._build_world()
        # Draw player over guide.
        self._build_guide()
        self._build_player()
        if self._loaded is not None:
            self.intro_done = bool(self._loaded.get("intro", 0))
            names = self._load_class_names()
            self.class_index = int(self._loaded.get("class", 0)) % len(names)
            self.class_name = names[self.class_index]
            # Preserve Wizard during intro.
            if self.intro_done:
                self._set_class_preview(self.class_name)
        self._build_wizard()
        if self._loaded is not None:
            self._apply_progress(self._loaded)
        # First-time intro sequence.
        self.phase = 2 if self.intro_done else 0
        self.ui = self.UI_NONE
        self._fill_world(self.anchor_x, self.anchor_z)
        if self.intro_done:
            self._build_world_content()
        self._adopt_server_level()
        game.level_add(self.level)
        self.engine = GameEngine(game, 60)
        self.boot_state = self.BOOT_SCENE
        self.scene_open = True
        collect()

    def _build_world_content(self):
        """Build the enemy, effect and land pools around the player."""
        if self.world_ready:
            return
        collect()
        self._build_lands()
        self._build_bird()
        collect()
        self._build_enemies()
        self._build_effects()
        self._build_halos()
        collect()
        self._fill_lands(self.anchor_x, self.anchor_z)
        self._fill_enemies(self.anchor_x, self.anchor_z)
        if self.dragon_spawned and not self.dragon_defeated:
            self._spawn_dragon()
        self.world_ready = True

    def _http_request(self, url: str, payload = None, method="POST") -> bool:
        """Start one async request."""
        if self.http is None:
            from picoware.system.http import HTTP

            self.http = HTTP(view_manager=self.view_manager)
        _headers = {
            "Content-Type": "application/json",
            "HTTP_USER_AGENT": "Pico",
            "Setting": "X-Flipper-Redirect",
            "username": self.net_user,
            "password": self.net_pass,
            "User-Agent": "Raspberry Pi Pico W",
        }
        return self.http.request_async(method, url, payload, _headers)

    def _net_pump(self):
        """Advance the async sync state machine."""
        if self.net_state in (self.NET_OFF, self.NET_ERROR):
            return
        if self.http is None or not self.http.is_finished:
            return
        if self.net_state == self.NET_LOGIN:
            self._net_login_done()
        elif self.net_state == self.NET_FETCH:
            self._net_apply_stats(self.http.response.json())
            self.net_state = self.NET_READY
            self.net_status = "synced"
        if self.net_state == self.NET_READY:
            self._net_upload()

    def _net_login_done(self):
        """Finish a login request and fetch stats."""
        if not self.http or not self.http.response:
            return
        if "[SUCCESS]" in self.http.response.text:
            self.net_status = "Welcome %s!" % self.net_user
            if self._http_request("https://www.jblanked.com/flipper/api/user/game-stats/%s/" % self.net_user, None, "GET"):
                self.net_state = self.NET_FETCH
            else:
                self.net_state = self.NET_READY
        elif not self.tried_register:
            # No account: register, re-check.
            self.tried_register = True
            self.net_status = "Registering..."
            if not self._http_request("https://www.jblanked.com/flipper/api/user/register/",
                                  {"username": self.net_user,
                                   "password": self.net_pass}):
                self.net_status = "offline"
                self.net_state = self.NET_OFF
        else:
            self.net_status = "offline"
            self.net_state = self.NET_OFF

    def _net_apply_stats(self, data: dict):
        """Adopt a higher server level if present."""
        stats = data.get("game_stats", data)
        if not isinstance(stats, dict):
            return
        try:
            server_level = int(stats.get("level", 0) or 0)
        except Exception:
            return
        self._server_level = max(self._server_level, server_level)
        self._adopt_server_level()

    def _adopt_server_level(self):
        """Raise the local level to the server level if higher."""
        if self.player is None or self._server_level <= self.player.level:
            return
        xp_total = 0
        for lv in range(2, self._server_level + 1):
            xp_total += xp_for_level(lv)
        self.player.xp = max(self.player.xp, xp_total)
        self.update_stats()
        self.message = "Synced level %d" % self._server_level
        self.message_timer = 120
        self._save_progress()

    def _net_upload(self):
        """Upload stats when progress changed."""
        if not self.net_dirty:
            return
        payload = {
            "username": self.net_user,
            "game_stats": {
                "username": self.net_user,
                "level": self.player.level,
                "xp": int(self.player.xp),
                "health": int(self.player.health),
                "max_health": int(self.player.max_health),
                "strength": self.player.strength,
                "health_regen": 1,
                "attack_timer": 1,
                "class": self.class_name,
                "quests": self.quest_index[1] + self.quest_index[2]
                + self.quest_index[3],
                "dragon": 1 if self.dragon_defeated else 0,
            },
        }
        if self._http_request("https://www.jblanked.com/flipper/api/user/update-game-stats/", payload):
            self.net_dirty = False
            self.net_status = "saved"

    def run(self):
        """Stream terrain and run one engine frame."""
        if self.pending_world:
            self.pending_world = False
            self._build_world_content()
        self._update_world()
        if self.engine is not None:
            self.engine.run_async(False)
            self.draw_hud(self.draw)
        self.draw.swap()

    def stop(self):
        """Stop the engine, save progress and free the world."""
        self._save_progress()
        if self.http is not None:
            self.http.close()
            del self.http
            self.http = None
        if self.engine is not None:
            self.engine.stop()
            self.engine = None
        self.game = None
        self.meshes = []
        self.sprites = []
        self.world_mesh = None
        self.enemies = []
        self.enemy_home = []
        self.enemy_ready = []
        self.dragon = None
        self.effects = {}
        self.world_ready = False
        self.pending_world = False
        self.lands = []
        self.player = None
        self.wizard = None
        self.guide = None
        self.bird = None
        self._loading = None
