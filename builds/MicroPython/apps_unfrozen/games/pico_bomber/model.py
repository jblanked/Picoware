"""Game rules for Pico Bomber.

The model intentionally has no Picoware display dependencies. Keeping the
rules isolated makes the game cheaper to import, easier to test, and usable on
every MicroPython board supported by Picoware.
"""

from random import randint

try:
    from utime import ticks_add, ticks_diff
except ImportError:
    def ticks_add(value, delta):
        return value + delta

    def ticks_diff(value, reference):
        return value - reference


GRID_WIDTH = 13
GRID_HEIGHT = 13

TILE_EMPTY = 0
TILE_SOLID = 1
TILE_BRICK = 2

POWER_FLAME = 1
POWER_BOMB = 2
POWER_LIFE = 3
POWER_MAGNET = 4
POWER_FLAME_SUIT = 5
POWER_SPEED = 6
POWER_SHIELD = 7

THEME_NATURE = 0
THEME_INDUSTRIAL = 1
THEME_WATER = 2
THEME_BEACH = 3
THEME_HELL = 4
THEME_CLOUD = 5
THEME_FOREST = 6
THEME_CANYON = 7
THEME_NAMES = (
    "NATURE",
    "INDUSTRIAL",
    "WATER",
    "BEACH",
    "HELL",
    "CLOUD",
    "FOREST",
    "CANYON",
)

MODE_GHOST_HUNT = 0
MODE_BLAST_RIVALS = 1
MODE_TREASURE_HUNT = 2
MODE_BOMB_COURIER = 3
MODE_HOT_POTATO = 4
MODE_NAMES = (
    "GHOST HUNT",
    "BLAST RIVALS",
    "TREASURE HUNT",
    "BOMB COURIER",
    "HOT POTATO",
)
MENU_LEADERBOARD = 5
MENU_ITEM_COUNT = 6

EVENT_BOMB_PLACED = 1
EVENT_EXPLOSION = 2
EVENT_CHAIN_REACTION = 4
EVENT_BRICK_BROKEN = 8
EVENT_PICKUP = 16
EVENT_EXTRA_LIFE = 32
EVENT_SHIELD_BLOCK = 64
EVENT_TELEPORT = 128
EVENT_ENEMY_DOWN = 256
EVENT_SLIME_SPLIT = 512
EVENT_TREASURE = 1024
EVENT_COURIER = 2048
EVENT_HOT_POTATO = 4096
EVENT_WARNING = 8192
EVENT_PLAYER_HIT = 16384

ENEMY_BLOB = 0
ENEMY_CHASER = 1
ENEMY_BOMBER = 2
ENEMY_SLIME = 3
ENEMY_SMALL_SLIME = 4
ENEMY_KAMIKAZE = 5
ENEMY_TURRET = 6

STATE_TITLE = 0
STATE_PLAYING = 1
STATE_STAGE_CLEAR = 2
STATE_GAME_OVER = 3
STATE_PLAYER_DYING = 4
STATE_STAGE_INTRO = 5
STATE_MODE_SELECT = 6
STATE_LEADERBOARD = 7
STATE_NAME_ENTRY = 8
STATE_PAUSED = 9

DEATH_PLAYER = 0
DEATH_ENEMY_BLOB = 1
DEATH_ENEMY_CHASER = 2
DEATH_ENEMY_ELITE = 3
DEATH_ENEMY_BOMBER = 4

DECAL_BLOB = 0
DECAL_CHASER = 1
DECAL_ELITE = 2
DECAL_SCORCH = 3
DECAL_DEBRIS = 4
DECAL_BOMBER = 5

BOMB_FUSE_MS = 2100
EXPLOSION_MS = 480
PLAYER_INVULNERABLE_MS = 1400
MAGNET_MS = 10000
FLAME_SUIT_MS = 9000
SPEED_MS = 9000
SHIELD_INVULNERABLE_MS = 700
MAGNET_STEP_MS = 180
TELEPORT_LOCK_MS = 450
SPECIAL_WARNING_MS = 700
SPIKE_CYCLE_MS = 2400
SPIKE_ACTIVE_MS = 700
PROJECTILE_STEP_MS = 120
TREASURE_STAGE_MS = 75000
COURIER_FUSE_MS = 25000
HOT_POTATO_FUSE_MS = 5500
HOT_POTATO_TRANSFER_MS = 650
STAGE_CLEAR_MS = 1300
DEATH_ANIMATION_MS = 720
PLAYER_MOVE_ANIMATION_MS = 150
ENEMY_MOVE_ANIMATION_MS = 190
ENEMY_ESCAPE_PLAN_STEPS = 4
DEMO_ACTION_MS = 260
DEMO_ESCAPE_PLAN_STEPS = 4
STAGE_INTRO_MS = 900
POSITION_SCALE = 256
PLAYER_MOVE_QUEUE_THRESHOLD = POSITION_SCALE // 3
MAX_DECALS = 12
DECAL_SCORCH_MS = 3200
DECAL_DEBRIS_MS = 1800
DECAL_ENEMY_MS = 2400

DIRECTIONS = ((0, -1), (0, 1), (-1, 0), (1, 0))
SAFE_TILES = (
    (1, 1),
    (2, 1),
    (3, 1),
    (3, 2),
    (1, 2),
    (1, 3),
    (2, 3),
)


class GameModel:
    """Mutable state and rules for one Pico Bomber session."""

    def __init__(self):
        self.grid = []
        self.player_x = 1
        self.player_y = 1
        self.lives = 3
        self.score = 0
        self.stage = 1
        self.mode = MODE_GHOST_HUNT
        self.menu_selection = MODE_GHOST_HUNT
        self.theme = -1
        self.flame_range = 2
        self.bomb_limit = 1
        self.bombs = []
        self.explosions = []
        self.enemies = []
        self.powerups = []
        self.life_powerup_x = -1
        self.life_powerup_y = -1
        self.magnet_until = 0
        self.flame_suit_until = 0
        self.speed_until = 0
        self.shield_hits = 0
        self.shield_flash_until = 0
        self.magnet_next = 0
        self.teleport_lock_until = 0
        self.barrels = []
        self.teleporters = []
        self.spike_traps = []
        self.flame_emitters = []
        self.cannons = []
        self.mines = []
        self.projectiles = []
        self.background_creatures = []
        self.shake_until = 0
        self.flash_until = 0
        self.chain_strength = 0
        self.treasure_hidden = []
        self.treasures = []
        self.treasure_collected = 0
        self.treasure_target = 0
        self.objective_until = 0
        self.courier_bomb_x = -1
        self.courier_bomb_y = -1
        self.courier_exit_x = -1
        self.courier_exit_y = -1
        self.courier_carrying = False
        self.courier_fuse_until = 0
        self.hot_potato_player = False
        self.hot_potato_enemy = None
        self.hot_potato_until = 0
        self.hot_potato_transfer_until = 0
        self.decals = []
        self.death_effects = []
        self.leaderboard = []
        self.player_name = ""
        self.state = STATE_TITLE
        self.state_until = 0
        self.invulnerable_until = 0
        self.animation_time = 0
        self.animation_last = 0
        self.player_frame = 0
        self.player_facing = 0
        self.player_draw_x = POSITION_SCALE
        self.player_draw_y = POSITION_SCALE
        self.paused_at = 0
        self.build_phase = 0
        self.build_x = -1
        self.build_y = -1
        self.build_items = 0
        self.demo_mode = False
        self.demo_next_action = 0
        self.demo_countdown = 30
        self.pending_events = 0
        # Demo and bomber AI run this search many times per minute. Reusing a
        # packed queue and visit map avoids steadily churning hundreds of
        # short-lived lists on MicroPython's constrained heap.
        self._escape_queue = [0] * (GRID_WIDTH * GRID_HEIGHT)
        self._escape_visited = bytearray(GRID_WIDTH * GRID_HEIGHT)
        self._escape_visit_generation = 0

    def open_mode_menu(self):
        """Open the mode chooser with the current mode highlighted."""
        self.menu_selection = self.mode
        self.paused_at = 0
        self.demo_mode = False
        self.demo_next_action = 0
        self.demo_countdown = 30
        self.state = STATE_MODE_SELECT

    def pause(self, now):
        """Freeze active gameplay until the player resumes."""
        if self.state != STATE_PLAYING:
            return False
        self.paused_at = now
        self.state = STATE_PAUSED
        return True

    def resume(self, now):
        """Resume gameplay without advancing any active timers."""
        if self.state != STATE_PAUSED:
            return False

        paused_for = max(0, ticks_diff(now, self.paused_at))
        self.invulnerable_until = ticks_add(
            self.invulnerable_until,
            paused_for,
        )
        self.magnet_until = ticks_add(self.magnet_until, paused_for)
        self.flame_suit_until = ticks_add(self.flame_suit_until, paused_for)
        self.speed_until = ticks_add(self.speed_until, paused_for)
        self.shield_flash_until = ticks_add(
            self.shield_flash_until,
            paused_for,
        )
        self.magnet_next = ticks_add(self.magnet_next, paused_for)
        self.teleport_lock_until = ticks_add(
            self.teleport_lock_until,
            paused_for,
        )
        self.shake_until = ticks_add(self.shake_until, paused_for)
        self.flash_until = ticks_add(self.flash_until, paused_for)
        if self.objective_until:
            self.objective_until = ticks_add(
                self.objective_until,
                paused_for,
            )
        if self.courier_fuse_until:
            self.courier_fuse_until = ticks_add(
                self.courier_fuse_until,
                paused_for,
            )
        if self.hot_potato_until:
            self.hot_potato_until = ticks_add(
                self.hot_potato_until,
                paused_for,
            )
        if self.hot_potato_transfer_until:
            self.hot_potato_transfer_until = ticks_add(
                self.hot_potato_transfer_until,
                paused_for,
            )
        for bomb in self.bombs:
            bomb[2] = ticks_add(bomb[2], paused_for)
        for flame in self.explosions:
            flame[2] = ticks_add(flame[2], paused_for)
        for enemy in self.enemies:
            enemy[2] = ticks_add(enemy[2], paused_for)
            enemy[9] = ticks_add(enemy[9], paused_for)
            if len(enemy) >= 13:
                if enemy[11]:
                    enemy[11] = ticks_add(enemy[11], paused_for)
                enemy[12] = ticks_add(enemy[12], paused_for)
            if len(enemy) >= 14 and enemy[13]:
                enemy[13] = ticks_add(enemy[13], paused_for)
        for emitter in self.flame_emitters:
            emitter[3] = ticks_add(emitter[3], paused_for)
            if emitter[4]:
                emitter[4] = ticks_add(emitter[4], paused_for)
        for cannon in self.cannons:
            cannon[4] = ticks_add(cannon[4], paused_for)
            if cannon[5]:
                cannon[5] = ticks_add(cannon[5], paused_for)
        for mine in self.mines:
            mine[2] = ticks_add(mine[2], paused_for)
            mine[3] = ticks_add(mine[3], paused_for)
        for projectile in self.projectiles:
            projectile[4] = ticks_add(projectile[4], paused_for)
        for creature in self.background_creatures:
            creature[3] = ticks_add(creature[3], paused_for)
        for decal in self.decals:
            if len(decal) >= 6:
                decal[5] = ticks_add(decal[5], paused_for)
        for effect in self.death_effects:
            effect[3] = ticks_add(effect[3], paused_for)
            effect[4] = ticks_add(effect[4], paused_for)

        self.animation_last = now
        self.paused_at = 0
        self.state = STATE_PLAYING
        return True

    def select_mode(self, direction):
        """Move the mode chooser selection."""
        if self.state != STATE_MODE_SELECT:
            return False
        count = MENU_ITEM_COUNT
        self.menu_selection = (self.menu_selection + direction) % count
        return True

    def new_game(self, now, mode=None):
        """Start a new run from stage one."""
        if mode is not None:
            self.mode = mode
        else:
            self.mode = self.menu_selection
        self.lives = 3
        self.score = 0
        self.stage = 1
        self.player_name = ""
        self.flame_range = 2
        self.bomb_limit = 1
        self.magnet_until = 0
        self.flame_suit_until = 0
        self.speed_until = 0
        self.shield_hits = 0
        self.shield_flash_until = 0
        self.treasure_collected = 0
        self.treasure_target = 0
        self.objective_until = 0
        self.courier_carrying = False
        self.courier_fuse_until = 0
        self.hot_potato_player = False
        self.hot_potato_enemy = None
        self.hot_potato_until = 0
        self.hot_potato_transfer_until = 0
        self.paused_at = 0
        self.demo_mode = False
        self.demo_next_action = 0
        self.demo_countdown = 0
        self.pending_events = 0
        self._build_stage(now)

    def start_demo(self, now, mode):
        """Start an autonomous attract-mode run without leaderboard scoring."""
        self.new_game(now, mode)
        self.demo_mode = True
        self.demo_next_action = ticks_add(now, STAGE_INTRO_MS)
        self.demo_countdown = 0

    def _build_stage(self, now):
        """Create a procedural arena with a guaranteed safe starting pocket."""
        self.build_phase = 1
        self.build_x = -1
        self.build_y = -1
        self.build_items = 0
        self.theme = self._choose_theme()
        self.grid = []
        self.build_phase = 2
        for y in range(GRID_HEIGHT):
            self.build_y = y
            row = []
            for x in range(GRID_WIDTH):
                self.build_x = x
                if (
                    x == 0
                    or y == 0
                    or x == GRID_WIDTH - 1
                    or y == GRID_HEIGHT - 1
                    or (x % 2 == 0 and y % 2 == 0)
                ):
                    row.append(TILE_SOLID)
                elif (x, y) in SAFE_TILES:
                    row.append(TILE_EMPTY)
                elif randint(0, 99) < 52:
                    row.append(TILE_BRICK)
                else:
                    row.append(TILE_EMPTY)
            self.grid.append(row)

        self.build_phase = 3
        self.build_x = -1
        self.build_y = -1
        self.player_x = 1
        self.player_y = 1
        self.player_draw_x = POSITION_SCALE
        self.player_draw_y = POSITION_SCALE
        self.bombs = []
        self.explosions = []
        self.powerups = []
        self.barrels = []
        self.teleporters = []
        self.spike_traps = []
        self.flame_emitters = []
        self.cannons = []
        self.mines = []
        self.projectiles = []
        self.background_creatures = []
        self.shake_until = 0
        self.flash_until = 0
        self.chain_strength = 0
        self.treasure_hidden = []
        self.treasures = []
        self.treasure_collected = 0
        self.treasure_target = 0
        self.objective_until = 0
        self.courier_bomb_x = -1
        self.courier_bomb_y = -1
        self.courier_exit_x = -1
        self.courier_exit_y = -1
        self.courier_carrying = False
        self.courier_fuse_until = 0
        self.hot_potato_player = False
        self.hot_potato_enemy = None
        self.hot_potato_until = 0
        self.hot_potato_transfer_until = 0
        self.pending_events = 0
        self.magnet_next = ticks_add(now, MAGNET_STEP_MS)
        self.teleport_lock_until = 0
        self.decals = []
        self.enemies = []
        self.death_effects = []
        self.invulnerable_until = ticks_add(now, PLAYER_INVULNERABLE_MS)
        self.animation_time = now
        self.animation_last = now
        self.player_frame = 0
        self.player_facing = 0
        self.state = STATE_STAGE_INTRO
        self.state_until = ticks_add(now, STAGE_INTRO_MS)

        candidates = []
        self.build_phase = 4
        for y in range(GRID_HEIGHT - 2, 0, -1):
            self.build_y = y
            for x in range(GRID_WIDTH - 2, 0, -1):
                self.build_x = x
                if self.grid[y][x] != TILE_SOLID and x + y > 10:
                    candidates.append((x, y))
                    self.build_items = len(candidates)

        enemy_count = min(2 + self.stage, 7)
        self.build_phase = 5
        while candidates and len(self.enemies) < enemy_count:
            self.build_items = len(candidates)
            index = randint(0, len(candidates) - 1)
            x, y = candidates.pop(index)
            self.build_x = x
            self.build_y = y
            too_close = False
            for enemy in self.enemies:
                if abs(enemy[0] - x) + abs(enemy[1] - y) < 2:
                    too_close = True
                    break
            if too_close:
                continue
            self.grid[y][x] = TILE_EMPTY
            delay = randint(100, 350)
            kind = self._choose_enemy_kind()
            elite_chance = min(35, 8 + self.stage * 3)
            elite = (
                1
                if kind not in (ENEMY_SMALL_SLIME, ENEMY_TURRET)
                and self.stage >= 3
                and randint(0, 99) < elite_chance
                else 0
            )
            self.enemies.append(self._make_enemy(x, y, now, kind, elite, delay))

        # This is a fallback for an exceptionally crowded random map.
        self.build_phase = 6
        if not self.enemies:
            self.grid[GRID_HEIGHT - 2][GRID_WIDTH - 2] = TILE_EMPTY
            self.enemies.append(
                self._make_enemy(
                    GRID_WIDTH - 2,
                    GRID_HEIGHT - 2,
                    now,
                    ENEMY_BOMBER
                    if self.mode == MODE_BLAST_RIVALS
                    else ENEMY_BLOB,
                    0,
                    250,
                )
            )
        self._hide_stage_life()
        self._spawn_stage_assets(now)
        self._setup_mode_objective(now)
        self.build_phase = 7
        self.build_x = -1
        self.build_y = -1
        self.build_items = len(self.enemies)

    def _choose_enemy_kind(self):
        roll = randint(0, 99)
        if self.stage >= 4 and roll < 12:
            return ENEMY_TURRET
        if self.stage >= 3 and roll < 28:
            return ENEMY_KAMIKAZE
        if self.stage >= 2 and roll < 48:
            return ENEMY_SLIME
        if self.mode == MODE_BLAST_RIVALS:
            return ENEMY_BOMBER
        return ENEMY_BLOB if randint(0, 1) == 0 else ENEMY_CHASER

    def _make_enemy(self, x, y, now, kind, elite=0, delay=0):
        return [
            x,
            y,
            ticks_add(now, delay),
            kind,
            randint(0, 3),
            0,
            x * POSITION_SCALE,
            y * POSITION_SCALE,
            elite,
            ticks_add(now, randint(1600, 3000)),
            randint(-70, 100),
            0,
            ticks_add(now, randint(900, 1900)),
            0,
        ]

    def _hide_stage_life(self):
        """Hide exactly one extra-life pickup in a brick for this stage."""
        self.life_powerup_x = -1
        self.life_powerup_y = -1
        brick_count = 0
        for y in range(1, GRID_HEIGHT - 1):
            for x in range(1, GRID_WIDTH - 1):
                if self.grid[y][x] != TILE_BRICK:
                    continue
                brick_count += 1
                # Reservoir sampling keeps the placement random without
                # allocating another stage-sized coordinate list.
                if randint(1, brick_count) == 1:
                    self.life_powerup_x = x
                    self.life_powerup_y = y

        if self.life_powerup_x >= 0:
            return

        # A brick-free random arena is extremely unlikely, but the one-life
        # promise must still hold. Add a distant brick on an unoccupied tile.
        for y in range(GRID_HEIGHT - 2, 0, -1):
            for x in range(GRID_WIDTH - 2, 0, -1):
                if (
                    self.grid[y][x] == TILE_EMPTY
                    and (x, y) not in SAFE_TILES
                    and not self._enemy_at(x, y)
                ):
                    self.grid[y][x] = TILE_BRICK
                    self.life_powerup_x = x
                    self.life_powerup_y = y
                    return

    def _asset_at(self, x, y):
        for item in self.barrels:
            if item[0] == x and item[1] == y:
                return True
        for item in self.teleporters:
            if item[0] == x and item[1] == y:
                return True
        for item in self.spike_traps:
            if item[0] == x and item[1] == y:
                return True
        for item in self.mines:
            if item[0] == x and item[1] == y:
                return True
        for item in self.background_creatures:
            if item[0] == x and item[1] == y:
                return True
        if self.courier_bomb_x == x and self.courier_bomb_y == y:
            return True
        if self.courier_exit_x == x and self.courier_exit_y == y:
            return True
        return False

    def _random_open_tile(self, min_distance=0):
        """Choose an unoccupied floor tile without allocating candidates."""
        chosen_x = -1
        chosen_y = -1
        count = 0
        for y in range(1, GRID_HEIGHT - 1):
            for x in range(1, GRID_WIDTH - 1):
                if (
                    self.grid[y][x] != TILE_EMPTY
                    or (x, y) in SAFE_TILES
                    or x + y < min_distance
                    or self._enemy_at(x, y)
                    or self._asset_at(x, y)
                ):
                    continue
                count += 1
                if randint(1, count) == 1:
                    chosen_x = x
                    chosen_y = y
        return chosen_x, chosen_y

    def _random_reachable_tile(self, start_x, start_y, min_distance=0):
        """Choose an objective tile reachable without placing another bomb."""
        if start_x < 0 or start_y < 0:
            return -1, -1
        queue = self._escape_queue
        visited = self._escape_visited
        generation = self._escape_visit_generation + 1
        if generation > 255:
            for index in range(len(visited)):
                visited[index] = 0
            generation = 1
        self._escape_visit_generation = generation

        start_key = start_y * GRID_WIDTH + start_x
        queue[0] = start_key
        visited[start_key] = generation
        cursor = 0
        queue_end = 1
        chosen_x = -1
        chosen_y = -1
        count = 0
        while cursor < queue_end:
            key = queue[cursor]
            cursor += 1
            x = key % GRID_WIDTH
            y = key // GRID_WIDTH
            if (
                (x != start_x or y != start_y)
                and abs(x - start_x) + abs(y - start_y) >= min_distance
                and not self._asset_at(x, y)
                and not self._enemy_at(x, y)
                and (x, y) not in SAFE_TILES
            ):
                count += 1
                if randint(1, count) == 1:
                    chosen_x = x
                    chosen_y = y
            for dx, dy in DIRECTIONS:
                next_x = x + dx
                next_y = y + dy
                if (
                    next_x < 0
                    or next_y < 0
                    or next_x >= GRID_WIDTH
                    or next_y >= GRID_HEIGHT
                ):
                    continue
                next_key = next_y * GRID_WIDTH + next_x
                if visited[next_key] == generation or not self._can_enter(
                    next_x,
                    next_y,
                ):
                    continue
                visited[next_key] = generation
                queue[queue_end] = next_key
                queue_end += 1
        return chosen_x, chosen_y

    def _spawn_stage_assets(self, now):
        """Populate bounded interactive scenery and hazards for one stage."""
        barrel_count = min(3, 1 + self.stage // 3)
        for _ in range(barrel_count):
            x, y = self._random_open_tile(8)
            if x >= 0:
                self.barrels.append([x, y])

        # Teleporters always appear as one clearly paired set.
        for _ in range(2):
            x, y = self._random_open_tile(6)
            if x >= 0:
                self.teleporters.append([x, y])
        if len(self.teleporters) != 2:
            self.teleporters = []

        for index in range(min(3, 1 + self.stage // 3)):
            x, y = self._random_open_tile(7)
            if x >= 0:
                self.spike_traps.append(
                    [x, y, (index * 730 + randint(0, 500)) % SPIKE_CYCLE_MS]
                )

        if self.stage >= 2:
            for _ in range(min(2, 1 + self.stage // 5)):
                x, y = self._random_open_tile(8)
                if x >= 0:
                    self.mines.append(
                        [
                            x,
                            y,
                            ticks_add(now, 1100),
                            ticks_add(now, randint(5200, 7600)),
                        ]
                    )

            # Emitters sit on existing permanent pillars, so they never alter
            # route connectivity or consume another floor allocation.
            emitter_count = 2 if self.stage >= 6 else 1
            for index in range(emitter_count):
                pillar_x = 2 + 2 * randint(0, (GRID_WIDTH - 4) // 2)
                pillar_y = 2 + 2 * randint(0, (GRID_HEIGHT - 4) // 2)
                duplicate = False
                for emitter in self.flame_emitters:
                    if emitter[0] == pillar_x and emitter[1] == pillar_y:
                        duplicate = True
                        break
                if not duplicate:
                    self.flame_emitters.append(
                        [
                            pillar_x,
                            pillar_y,
                            randint(0, 3),
                            ticks_add(now, 1500 + index * 600),
                            0,
                        ]
                    )

            cannon_y = 1 + randint(0, (GRID_HEIGHT - 3) // 2) * 2
            if randint(0, 1) == 0:
                self.cannons.append(
                    [0, cannon_y, 1, 0, ticks_add(now, 1900), 0]
                )
            else:
                self.cannons.append(
                    [
                        GRID_WIDTH - 1,
                        cannon_y,
                        -1,
                        0,
                        ticks_add(now, 1900),
                        0,
                    ]
                )

        for index in range(2):
            x, y = self._random_open_tile(4)
            if x >= 0:
                self.background_creatures.append(
                    [x, y, index % 2, 0, 0, 1]
                )

    def _treasure_hidden_at(self, x, y):
        for treasure in self.treasure_hidden:
            if treasure[0] == x and treasure[1] == y:
                return treasure
        return None

    def _setup_mode_objective(self, now):
        if self.mode == MODE_TREASURE_HUNT:
            wanted = min(5, 2 + (self.stage - 1) // 2)
            while len(self.treasure_hidden) < wanted:
                chosen_x = -1
                chosen_y = -1
                count = 0
                for y in range(1, GRID_HEIGHT - 1):
                    for x in range(1, GRID_WIDTH - 1):
                        if (
                            self.grid[y][x] != TILE_BRICK
                            or (
                                x == self.life_powerup_x
                                and y == self.life_powerup_y
                            )
                            or self._treasure_hidden_at(x, y) is not None
                        ):
                            continue
                        count += 1
                        if randint(1, count) == 1:
                            chosen_x = x
                            chosen_y = y
                if chosen_x < 0:
                    break
                self.treasure_hidden.append([chosen_x, chosen_y])

            self.treasure_target = len(self.treasure_hidden)
            if self.treasure_target == 0:
                x, y = self._random_open_tile(7)
                if x < 0:
                    x, y = self._random_open_tile(0)
                if x >= 0:
                    self.treasures.append([x, y])
                    self.treasure_target = 1
            self.objective_until = ticks_add(
                now,
                STAGE_INTRO_MS + TREASURE_STAGE_MS,
            )
            return

        if self.mode == MODE_BOMB_COURIER:
            self.courier_bomb_x, self.courier_bomb_y = (
                self._random_open_tile(7)
            )
            if self.courier_bomb_x < 0:
                self.courier_bomb_x, self.courier_bomb_y = (
                    self._random_open_tile(0)
                )
            self.courier_exit_x, self.courier_exit_y = (
                self._random_reachable_tile(
                    self.courier_bomb_x,
                    self.courier_bomb_y,
                    6,
                )
            )
            if self.courier_exit_x < 0:
                self.courier_exit_x, self.courier_exit_y = (
                    self._random_reachable_tile(
                        self.courier_bomb_x,
                        self.courier_bomb_y,
                        0,
                    )
                )
            if self.courier_exit_x < 0:
                # Reaching the pickup necessarily opens a route back to the
                # starting pocket, making this a safe last-resort destination.
                self.courier_exit_x = 1
                self.courier_exit_y = 1
            return

        if self.mode == MODE_HOT_POTATO:
            self.hot_potato_player = True
            self.hot_potato_enemy = None
            self.hot_potato_until = ticks_add(
                now,
                STAGE_INTRO_MS + HOT_POTATO_FUSE_MS,
            )
            self.hot_potato_transfer_until = ticks_add(
                now,
                STAGE_INTRO_MS,
            )

    def _choose_theme(self):
        theme = randint(0, len(THEME_NAMES) - 1)
        if theme == self.theme:
            theme = (theme + 1 + randint(0, len(THEME_NAMES) - 2)) % len(
                THEME_NAMES
            )
        return theme

    def _emit(self, event):
        """Record a bounded gameplay event for optional presentation layers."""
        self.pending_events |= event

    def take_events(self):
        """Return and clear gameplay events accumulated since the last frame."""
        events = self.pending_events
        self.pending_events = 0
        return events

    def bombs_available(self):
        """Return how many additional bombs the player may place."""
        player_bombs = 0
        for bomb in self.bombs:
            if len(bomb) < 5 or bomb[4] == 0:
                player_bombs += 1
        return max(0, self.bomb_limit - player_bombs)

    def _has_bomb(self, x, y):
        for bomb in self.bombs:
            if bomb[0] == x and bomb[1] == y:
                return True
        return False

    def _barrel_at(self, x, y):
        for barrel in self.barrels:
            if barrel[0] == x and barrel[1] == y:
                return barrel
        return None

    def _mine_at(self, x, y):
        for mine in self.mines:
            if mine[0] == x and mine[1] == y:
                return mine
        return None

    def _enemy_at(self, x, y, ignored=None):
        for enemy in self.enemies:
            if enemy is not ignored and enemy[0] == x and enemy[1] == y:
                return True
        return False

    @staticmethod
    def _draw_tile(value):
        return (value + POSITION_SCALE // 2) // POSITION_SCALE

    def _enemy_touching_player(self):
        contact_distance = POSITION_SCALE * 3 // 5
        for enemy in self.enemies:
            if (
                abs(enemy[6] - self.player_draw_x) <= contact_distance
                and abs(enemy[7] - self.player_draw_y) <= contact_distance
            ):
                return enemy
        return None

    def _enemy_touches_player(self):
        return self._enemy_touching_player() is not None

    def _can_enter(self, x, y, block_enemies=False, ignored_enemy=None):
        if x < 0 or y < 0 or x >= GRID_WIDTH or y >= GRID_HEIGHT:
            return False
        if (
            self.grid[y][x] != TILE_EMPTY
            or self._has_bomb(x, y)
            or self._barrel_at(x, y) is not None
        ):
            return False
        if block_enemies and self._enemy_at(x, y, ignored_enemy):
            return False
        return True

    def move_player(self, dx, dy, now):
        """Attempt to queue one grid tile of player movement."""
        if self.state != STATE_PLAYING:
            return False
        self.player_facing = self._facing_for_direction(dx, dy)
        target_draw_x = self.player_x * POSITION_SCALE
        target_draw_y = self.player_y * POSITION_SCALE
        if (
            abs(self.player_draw_x - target_draw_x)
            > PLAYER_MOVE_QUEUE_THRESHOLD
            or abs(self.player_draw_y - target_draw_y)
            > PLAYER_MOVE_QUEUE_THRESHOLD
        ):
            return False
        x = self.player_x + dx
        y = self.player_y + dy
        if not self._can_enter(x, y):
            return False
        self.player_x = x
        self.player_y = y
        self.player_frame = (self.player_frame + 1) % 4
        self._collect_powerup(now)
        self._collect_mode_objective(now)
        self._teleport_player(now)
        self._collect_powerup(now)
        self._collect_mode_objective(now)
        touching = self._enemy_touching_player()
        if touching is not None and not self._hot_potato_contact(
            touching,
            now,
        ):
            self._lose_life(now)
        return True

    def _collect_mode_objective(self, now):
        if self.mode == MODE_TREASURE_HUNT:
            for treasure in self.treasures:
                if (
                    treasure[0] == self.player_x
                    and treasure[1] == self.player_y
                ):
                    self.treasures.remove(treasure)
                    self.treasure_collected += 1
                    self.score += 200
                    self._emit(EVENT_TREASURE)
                    return True
            return False

        if self.mode != MODE_BOMB_COURIER:
            return False
        if (
            not self.courier_carrying
            and self.player_x == self.courier_bomb_x
            and self.player_y == self.courier_bomb_y
        ):
            self.courier_carrying = True
            self.courier_bomb_x = -1
            self.courier_bomb_y = -1
            self.courier_fuse_until = ticks_add(now, COURIER_FUSE_MS)
            self.score += 50
            self._emit(EVENT_COURIER)
            return True
        if (
            self.courier_carrying
            and self.player_x == self.courier_exit_x
            and self.player_y == self.courier_exit_y
        ):
            self.courier_carrying = False
            self.courier_fuse_until = 0
            self.score += 500
            self.state = STATE_STAGE_CLEAR
            self.state_until = ticks_add(now, STAGE_CLEAR_MS)
            self._emit(EVENT_COURIER)
            return True
        return False

    def _hot_potato_contact(self, enemy, now):
        if self.mode != MODE_HOT_POTATO:
            return False
        if ticks_diff(now, self.hot_potato_transfer_until) < 0:
            return True
        if self.hot_potato_player:
            self.hot_potato_player = False
            self.hot_potato_enemy = enemy
            self.hot_potato_transfer_until = ticks_add(
                now,
                HOT_POTATO_TRANSFER_MS,
            )
            self.score += 25
            self._emit(EVENT_HOT_POTATO)
            return True
        if self.hot_potato_enemy is enemy:
            self.hot_potato_player = True
            self.hot_potato_enemy = None
            self.hot_potato_transfer_until = ticks_add(
                now,
                HOT_POTATO_TRANSFER_MS,
            )
            self._emit(EVENT_HOT_POTATO)
            return True
        return False

    def _teleport_player(self, now):
        if (
            len(self.teleporters) != 2
            or ticks_diff(now, self.teleport_lock_until) < 0
        ):
            return False
        source = -1
        for index, pad in enumerate(self.teleporters):
            if pad[0] == self.player_x and pad[1] == self.player_y:
                source = index
                break
        if source < 0:
            return False
        target = self.teleporters[1 - source]
        if self._has_bomb(target[0], target[1]) or self._enemy_at(
            target[0],
            target[1],
        ):
            return False
        self.player_x = target[0]
        self.player_y = target[1]
        self.player_draw_x = target[0] * POSITION_SCALE
        self.player_draw_y = target[1] * POSITION_SCALE
        self.teleport_lock_until = ticks_add(now, TELEPORT_LOCK_MS)
        self._emit(EVENT_TELEPORT)
        return True

    @staticmethod
    def _facing_for_direction(dx, dy):
        if dy < 0:
            return 3
        if dx < 0:
            return 1
        if dx > 0:
            return 2
        return 0

    def place_bomb(self, now):
        """Place a bomb on the player's current tile if capacity allows."""
        if (
            self.state != STATE_PLAYING
            or (
                self.mode == MODE_BOMB_COURIER
                and self.courier_carrying
            )
            or self.bombs_available() <= 0
            or self._has_bomb(self.player_x, self.player_y)
        ):
            return False
        self.bombs.append(
            [
                self.player_x,
                self.player_y,
                ticks_add(now, BOMB_FUSE_MS),
                self.flame_range,
                0,
            ]
        )
        self._emit(EVENT_BOMB_PLACED)
        return True

    def _collect_powerup(self, now=None):
        if now is None:
            now = self.animation_time
        for powerup in self.powerups:
            if powerup[0] == self.player_x and powerup[1] == self.player_y:
                if powerup[2] == POWER_FLAME:
                    self.flame_range = min(6, self.flame_range + 1)
                elif powerup[2] == POWER_BOMB:
                    self.bomb_limit = min(5, self.bomb_limit + 1)
                elif powerup[2] == POWER_LIFE:
                    self.lives += 1
                elif powerup[2] == POWER_MAGNET:
                    self.magnet_until = ticks_add(now, MAGNET_MS)
                    self.magnet_next = now
                elif powerup[2] == POWER_FLAME_SUIT:
                    self.flame_suit_until = ticks_add(now, FLAME_SUIT_MS)
                elif powerup[2] == POWER_SPEED:
                    self.speed_until = ticks_add(now, SPEED_MS)
                elif powerup[2] == POWER_SHIELD:
                    self.shield_hits = min(2, self.shield_hits + 1)
                self.score += 25
                self._emit(
                    EVENT_EXTRA_LIFE
                    if powerup[2] == POWER_LIFE
                    else EVENT_PICKUP
                )
                self.powerups.remove(powerup)
                return True
        return False

    def _update_magnet(self, now):
        if (
            ticks_diff(self.magnet_until, now) <= 0
            or ticks_diff(now, self.magnet_next) < 0
        ):
            return False
        self.magnet_next = ticks_add(now, MAGNET_STEP_MS)
        moved = False
        for powerup in self.powerups:
            dx = self.player_x - powerup[0]
            dy = self.player_y - powerup[1]
            if abs(dx) + abs(dy) > 4:
                continue
            step_x = 0
            step_y = 0
            if abs(dx) >= abs(dy) and dx:
                step_x = 1 if dx > 0 else -1
            elif dy:
                step_y = 1 if dy > 0 else -1
            next_x = powerup[0] + step_x
            next_y = powerup[1] + step_y
            if (
                self.grid[next_y][next_x] != TILE_EMPTY
                or self._has_bomb(next_x, next_y)
                or self._barrel_at(next_x, next_y) is not None
            ):
                continue
            powerup[0] = next_x
            powerup[1] = next_y
            moved = True
        if self._collect_powerup(now):
            moved = True
        return moved

    def _add_explosion(self, x, y, expires, now, owner=0):
        self._scorch_decals_at(x, y, now)
        for flame in self.explosions:
            if flame[0] == x and flame[1] == y:
                flame[2] = expires
                flame_owner = flame[3] if len(flame) >= 4 else 0
                if flame_owner != owner:
                    if len(flame) >= 4:
                        flame[3] = 2
                    else:
                        flame.append(2)
                return
        self.explosions.append([x, y, expires, owner])

    def _reveal_powerup(self, x, y):
        hidden_treasure = self._treasure_hidden_at(x, y)
        if hidden_treasure is not None:
            self.treasure_hidden.remove(hidden_treasure)
            self.treasures.append([x, y])
            return
        if x == self.life_powerup_x and y == self.life_powerup_y:
            self.powerups.append([x, y, POWER_LIFE])
            self.life_powerup_x = -1
            self.life_powerup_y = -1
            return
        if randint(0, 99) >= 24:
            return
        roll = randint(0, 11)
        if roll < 3:
            kind = POWER_FLAME
        elif roll < 6:
            kind = POWER_BOMB
        elif roll < 8:
            kind = POWER_MAGNET
        elif roll < 10:
            kind = POWER_SPEED
        elif roll == 10:
            kind = POWER_FLAME_SUIT
        else:
            kind = POWER_SHIELD
        self.powerups.append([x, y, kind])

    @staticmethod
    def _decal_lifetime(kind):
        if kind == DECAL_SCORCH:
            return DECAL_SCORCH_MS
        if kind == DECAL_DEBRIS:
            return DECAL_DEBRIS_MS
        return DECAL_ENEMY_MS

    def _add_decal(self, draw_x, draw_y, kind, now):
        tile_x = (draw_x + POSITION_SCALE // 2) // POSITION_SCALE
        tile_y = (draw_y + POSITION_SCALE // 2) // POSITION_SCALE
        expires = ticks_add(now, self._decal_lifetime(kind))
        if kind == DECAL_SCORCH:
            for decal in self.decals:
                decal_x = (decal[0] + POSITION_SCALE // 2) // POSITION_SCALE
                decal_y = (decal[1] + POSITION_SCALE // 2) // POSITION_SCALE
                if decal_x == tile_x and decal_y == tile_y:
                    decal[2] = DECAL_SCORCH
                    decal[3] = self.theme
                    decal[4] = randint(0, 3)
                    if len(decal) >= 6:
                        decal[5] = expires
                    else:
                        decal.append(expires)
                    return
        if len(self.decals) >= MAX_DECALS:
            replace_index = -1
            for index, decal in enumerate(self.decals):
                if decal[2] in (DECAL_SCORCH, DECAL_DEBRIS):
                    replace_index = index
                    break
            if replace_index >= 0:
                self.decals.pop(replace_index)
            elif kind in (DECAL_SCORCH, DECAL_DEBRIS):
                return
            else:
                self.decals.pop(0)
        self.decals.append(
            [
                draw_x,
                draw_y,
                kind,
                self.theme,
                randint(0, 3),
                expires,
            ]
        )

    def _scorch_decals_at(self, x, y, now):
        expires = ticks_add(now, DECAL_SCORCH_MS)
        for decal in self.decals:
            decal_x = (decal[0] + POSITION_SCALE // 2) // POSITION_SCALE
            decal_y = (decal[1] + POSITION_SCALE // 2) // POSITION_SCALE
            if decal_x == x and decal_y == y:
                decal[2] = DECAL_SCORCH
                decal[3] = self.theme
                if len(decal) >= 6:
                    decal[5] = expires
                else:
                    decal.append(expires)

    def _cleanup_decals(self, now):
        changed = False
        for decal in self.decals[:]:
            if len(decal) >= 6 and ticks_diff(now, decal[5]) >= 0:
                self.decals.remove(decal)
                changed = True
        return changed

    def _trigger_barrel(self, barrel, now, owner):
        if barrel not in self.barrels:
            return False
        self.barrels.remove(barrel)
        self.bombs.append([barrel[0], barrel[1], now, 3, owner, 1])
        return True

    def _trigger_mine(self, mine, now):
        if mine not in self.mines:
            return False
        mine[3] = now
        return True

    def _react_background_creatures(self, x, y, now):
        for creature in self.background_creatures:
            dx = creature[0] - x
            dy = creature[1] - y
            if abs(dx) + abs(dy) > 4:
                continue
            creature[3] = ticks_add(now, 1100)
            if abs(dx) >= abs(dy):
                creature[4] = 1 if dx >= 0 else -1
                creature[5] = 0
            else:
                creature[4] = 0
                creature[5] = 1 if dy >= 0 else -1

    def _detonate(self, bomb, now):
        """Turn one bomb into blast tiles and arm bombs caught in the blast."""
        if bomb not in self.bombs:
            return
        self.bombs.remove(bomb)
        expires = ticks_add(now, EXPLOSION_MS)
        owner = bomb[4] if len(bomb) >= 5 else 0
        bomb_kind = bomb[5] if len(bomb) >= 6 else 0
        if self.explosions or bomb_kind:
            self._emit(EVENT_CHAIN_REACTION)
            self.chain_strength = min(3, self.chain_strength + 1)
            self.flash_until = ticks_add(now, 120 + self.chain_strength * 35)
            self.shake_until = ticks_add(now, 150 + self.chain_strength * 55)
        else:
            self.chain_strength = 1
            self._emit(EVENT_EXPLOSION)
        self._add_explosion(bomb[0], bomb[1], expires, now, owner)
        self._add_decal(
            bomb[0] * POSITION_SCALE,
            bomb[1] * POSITION_SCALE,
            DECAL_SCORCH,
            now,
        )

        for dx, dy in DIRECTIONS:
            for distance in range(1, bomb[3] + 1):
                x = bomb[0] + dx * distance
                y = bomb[1] + dy * distance
                tile = self.grid[y][x]
                if tile == TILE_SOLID:
                    break
                self._add_explosion(x, y, expires, now, owner)

                chained = None
                for other in self.bombs:
                    if other[0] == x and other[1] == y:
                        chained = other
                        break
                if chained is not None:
                    chained[2] = now

                barrel = self._barrel_at(x, y)
                if barrel is not None:
                    self._trigger_barrel(barrel, now, owner)
                    break

                mine = self._mine_at(x, y)
                if mine is not None:
                    self._trigger_mine(mine, now)

                if tile == TILE_BRICK:
                    self.grid[y][x] = TILE_EMPTY
                    self._emit(EVENT_BRICK_BROKEN)
                    if owner == 0:
                        self.score += 5
                    self._add_decal(
                        x * POSITION_SCALE,
                        y * POSITION_SCALE,
                        DECAL_DEBRIS,
                        now,
                    )
                    self._reveal_powerup(x, y)
                    break
        self._react_background_creatures(bomb[0], bomb[1], now)

    def _is_flame(self, x, y):
        for flame in self.explosions:
            if flame[0] == x and flame[1] == y:
                return True
        return False

    def _enemy_hit_by_flame(self, enemy):
        enemy_x = self._draw_tile(enemy[6])
        enemy_y = self._draw_tile(enemy[7])
        for flame in self.explosions:
            if flame[0] != enemy_x or flame[1] != enemy_y:
                continue
            return True
        return False

    def _apply_explosion_damage(self, now):
        killed = []
        for enemy in self.enemies:
            if self._enemy_hit_by_flame(enemy):
                killed.append(enemy)
        for enemy in killed:
            self.enemies.remove(enemy)
            self._emit(EVENT_ENEMY_DOWN)
            if enemy is self.hot_potato_enemy:
                self.hot_potato_enemy = None
                self.hot_potato_player = True
                self.hot_potato_until = ticks_add(
                    now,
                    HOT_POTATO_FUSE_MS,
                )
                self.hot_potato_transfer_until = ticks_add(
                    now,
                    HOT_POTATO_TRANSFER_MS,
                )
            if enemy[8]:
                death_kind = DEATH_ENEMY_ELITE
                decal_kind = DECAL_ELITE
            elif enemy[3] in (ENEMY_BOMBER, ENEMY_KAMIKAZE):
                death_kind = DEATH_ENEMY_BOMBER
                decal_kind = DECAL_BOMBER
            elif enemy[3] == ENEMY_TURRET:
                death_kind = DEATH_ENEMY_CHASER
                decal_kind = DECAL_CHASER
            else:
                death_kind = (
                    DEATH_ENEMY_BLOB
                    if enemy[3] in (ENEMY_BLOB, ENEMY_SLIME, ENEMY_SMALL_SLIME)
                    else DEATH_ENEMY_CHASER
                )
                decal_kind = (
                    DECAL_BLOB
                    if enemy[3] in (ENEMY_BLOB, ENEMY_SLIME, ENEMY_SMALL_SLIME)
                    else DECAL_CHASER
                )
            self._add_death_effect(
                enemy[6],
                enemy[7],
                death_kind,
                now,
            )
            self._add_decal(
                enemy[6],
                enemy[7],
                decal_kind,
                now,
            )
            self.score += 250 if enemy[8] else 100
            if enemy[3] == ENEMY_SLIME:
                self._emit(EVENT_SLIME_SPLIT)
                self._split_slime(enemy, now)
            elif enemy[3] == ENEMY_KAMIKAZE:
                carried_bomb = [
                    enemy[0],
                    enemy[1],
                    now,
                    2,
                    1,
                    1,
                ]
                self.bombs.append(carried_bomb)
                self._detonate(carried_bomb, now)

        player_x = self._draw_tile(self.player_draw_x)
        player_y = self._draw_tile(self.player_draw_y)
        if self._is_flame(player_x, player_y):
            self._lose_life(now, True)

    def _split_slime(self, enemy, now):
        spawned = 0
        for dx, dy in DIRECTIONS:
            x = enemy[0] + dx
            y = enemy[1] + dy
            if not self._can_enter(x, y, True):
                continue
            child = self._make_enemy(
                x,
                y,
                now,
                ENEMY_SMALL_SLIME,
                0,
                180 + spawned * 80,
            )
            child[10] = -110
            self.enemies.append(child)
            spawned += 1
            if spawned >= 2:
                break

    def _add_death_effect(self, draw_x, draw_y, kind, now):
        self.death_effects.append(
            [
                draw_x,
                draw_y,
                kind,
                now,
                ticks_add(now, DEATH_ANIMATION_MS),
            ]
        )

    def _cleanup_death_effects(self, now):
        changed = False
        for effect in self.death_effects[:]:
            if ticks_diff(now, effect[4]) >= 0:
                self.death_effects.remove(effect)
                changed = True
        return changed

    def _drop_courier_bomb(self):
        if not self.courier_carrying:
            return False
        self.courier_carrying = False
        self.courier_bomb_x = self.player_x
        self.courier_bomb_y = self.player_y
        self.courier_fuse_until = 0
        return True

    def _lose_life(self, now, flame_damage=False):
        if (
            self.state != STATE_PLAYING
            or ticks_diff(now, self.invulnerable_until) < 0
        ):
            return False

        if flame_damage and ticks_diff(self.flame_suit_until, now) > 0:
            return False
        if self.shield_hits > 0:
            self.shield_hits -= 1
            self._emit(EVENT_SHIELD_BLOCK)
            self.shield_flash_until = ticks_add(now, SHIELD_INVULNERABLE_MS)
            self.invulnerable_until = self.shield_flash_until
            return True

        if self.mode == MODE_BOMB_COURIER:
            self._drop_courier_bomb()
        if self.mode == MODE_HOT_POTATO and self.hot_potato_player:
            self.hot_potato_player = False
            self.hot_potato_enemy = None
            self.hot_potato_until = 0

        self._add_death_effect(
            self.player_draw_x,
            self.player_draw_y,
            DEATH_PLAYER,
            now,
        )
        self.lives -= 1
        self._emit(EVENT_PLAYER_HIT)
        self.bombs = []
        self.state = STATE_PLAYER_DYING
        self.state_until = ticks_add(now, DEATH_ANIMATION_MS)
        return True

    def _finish_player_death(self, now):
        self.explosions = []
        if self.lives <= 0:
            self.state = STATE_GAME_OVER
            self.state_until = 0
            return

        self.player_x = 1
        self.player_y = 1
        self.player_draw_x = POSITION_SCALE
        self.player_draw_y = POSITION_SCALE
        self.player_frame = 0
        self.player_facing = 0
        for x, y in SAFE_TILES:
            self.grid[y][x] = TILE_EMPTY
        self.invulnerable_until = ticks_add(now, PLAYER_INVULNERABLE_MS)

        if (
            self.mode == MODE_HOT_POTATO
            and not self.hot_potato_player
            and self.hot_potato_enemy is None
        ):
            self.hot_potato_player = True
            self.hot_potato_until = ticks_add(now, HOT_POTATO_FUSE_MS)
            self.hot_potato_transfer_until = ticks_add(
                now,
                HOT_POTATO_TRANSFER_MS,
            )

        # Keep surviving enemies out of the respawn pocket.
        for enemy in self.enemies:
            if (enemy[0], enemy[1]) in SAFE_TILES:
                enemy[0] = GRID_WIDTH - 2
                enemy[1] = GRID_HEIGHT - 2
                enemy[6] = enemy[0] * POSITION_SCALE
                enemy[7] = enemy[1] * POSITION_SCALE
                self.grid[enemy[1]][enemy[0]] = TILE_EMPTY
        self.state = STATE_PLAYING
        self.state_until = 0

    def _bomb_reaches(self, bomb, x, y):
        if bomb[0] != x and bomb[1] != y:
            return False
        distance = abs(bomb[0] - x) + abs(bomb[1] - y)
        if distance > bomb[3]:
            return False
        dx = 0 if bomb[0] == x else (1 if x > bomb[0] else -1)
        dy = 0 if bomb[1] == y else (1 if y > bomb[1] else -1)
        check_x = bomb[0] + dx
        check_y = bomb[1] + dy
        while check_x != x or check_y != y:
            if self.grid[check_y][check_x] != TILE_EMPTY:
                return False
            check_x += dx
            check_y += dy
        return self.grid[y][x] == TILE_EMPTY

    def _tile_in_bomb_danger(self, x, y):
        for bomb in self.bombs:
            if self._bomb_reaches(bomb, x, y):
                return True
        return False

    def _tile_is_dangerous(self, x, y):
        if self._is_flame(x, y) or self._tile_in_bomb_danger(x, y):
            return True
        for trap in self.spike_traps:
            if trap[0] == x and trap[1] == y and self._spike_active(
                trap,
                self.animation_time,
            ):
                return True
        for mine in self.mines:
            if mine[0] == x and mine[1] == y:
                return True
        return False

    def _enemy_escape_step(self, enemy, max_steps=0):
        """Find a safe first step using a compact reusable breadth-first search."""
        start_x = enemy[0]
        start_y = enemy[1]
        queue = self._escape_queue
        visited = self._escape_visited
        generation = self._escape_visit_generation + 1
        if generation > 255:
            for index in range(len(visited)):
                visited[index] = 0
            generation = 1
        self._escape_visit_generation = generation

        start_key = start_y * GRID_WIDTH + start_x
        # Packed node layout: tile key (8 bits), first direction (3 bits),
        # then step count. Direction 4 marks the root node.
        queue[0] = start_key | (4 << 8)
        visited[start_key] = generation
        cursor = 0
        queue_end = 1

        while cursor < queue_end:
            node = queue[cursor]
            cursor += 1
            key = node & 0xFF
            first_direction = (node >> 8) & 0x07
            steps = node >> 11
            x = key % GRID_WIDTH
            y = key // GRID_WIDTH
            if steps and not self._tile_is_dangerous(x, y):
                first_dx, first_dy = DIRECTIONS[first_direction]
                return (
                    start_x + first_dx,
                    start_y + first_dy,
                    first_dx,
                    first_dy,
                    steps,
                )
            if max_steps and steps >= max_steps:
                continue

            for direction in range(len(DIRECTIONS)):
                dx, dy = DIRECTIONS[direction]
                next_x = x + dx
                next_y = y + dy
                if (
                    next_x < 0
                    or next_y < 0
                    or next_x >= GRID_WIDTH
                    or next_y >= GRID_HEIGHT
                ):
                    continue
                key = next_y * GRID_WIDTH + next_x
                if visited[key] == generation or not self._can_enter(
                    next_x,
                    next_y,
                    True,
                    enemy,
                ):
                    continue
                visited[key] = generation
                next_first_direction = (
                    direction if steps == 0 else first_direction
                )
                queue[queue_end] = (
                    key
                    | (next_first_direction << 8)
                    | ((steps + 1) << 11)
                )
                queue_end += 1
        return None

    def _demo_bomb_plan(self, now):
        """Return a safe simulated player bomb, or None when escape is unclear."""
        if (
            (
                self.mode == MODE_BOMB_COURIER
                and self.courier_carrying
            )
            or self.bombs_available() <= 0
            or self._has_bomb(
            self.player_x,
            self.player_y,
            )
        ):
            return None
        planned_bomb = [
            self.player_x,
            self.player_y,
            ticks_add(now, BOMB_FUSE_MS),
            self.flame_range,
            0,
        ]
        self.bombs.append(planned_bomb)
        escape = self._enemy_escape_step(
            [self.player_x, self.player_y],
            DEMO_ESCAPE_PLAN_STEPS,
        )
        self.bombs.pop()
        return planned_bomb if escape is not None else None

    def _demo_should_bomb(self, planned_bomb):
        """Prefer bombs that pressure enemies or exploit arena assets."""
        for dx, dy in DIRECTIONS:
            x = self.player_x + dx
            y = self.player_y + dy
            if self.grid[y][x] == TILE_BRICK:
                return True
        for enemy in self.enemies:
            if self._bomb_reaches(planned_bomb, enemy[0], enemy[1]):
                return True
        for barrel in self.barrels:
            if self._bomb_reaches(planned_bomb, barrel[0], barrel[1]):
                return True
        for mine in self.mines:
            if self._bomb_reaches(planned_bomb, mine[0], mine[1]):
                return True
        return randint(0, 99) < 12

    def _demo_powerup_target(self):
        """Choose a useful visible pickup without abandoning urgent goals."""
        if (
            (self.mode == MODE_BOMB_COURIER and self.courier_carrying)
            or (self.mode == MODE_HOT_POTATO and self.hot_potato_player)
        ):
            return None

        best = None
        best_score = 999
        for powerup in self.powerups:
            kind = powerup[2]
            distance = abs(powerup[0] - self.player_x) + abs(
                powerup[1] - self.player_y
            )
            if kind == POWER_LIFE:
                value = 0
            elif kind == POWER_SHIELD and self.shield_hits == 0:
                value = 1
            elif kind == POWER_BOMB and self.bomb_limit < 4:
                value = 2
            elif kind == POWER_FLAME and self.flame_range < 5:
                value = 2
            elif kind in (POWER_MAGNET, POWER_FLAME_SUIT, POWER_SPEED):
                value = 3
            else:
                value = 6
            score = value * 12 + distance
            if score < best_score:
                best = powerup
                best_score = score

        if best is None:
            return None
        distance = abs(best[0] - self.player_x) + abs(
            best[1] - self.player_y
        )
        if self.mode == MODE_TREASURE_HUNT and distance > 5:
            return None
        return best[0], best[1]

    def _asset_route_distance(self, x, y, target_x, target_y):
        """Score a route using either direct travel or a teleporter shortcut."""
        best = abs(target_x - x) + abs(target_y - y)
        if len(self.teleporters) != 2:
            return best
        for source_index in range(2):
            source = self.teleporters[source_index]
            destination = self.teleporters[1 - source_index]
            via = (
                abs(source[0] - x)
                + abs(source[1] - y)
                + abs(target_x - destination[0])
                + abs(target_y - destination[1])
            )
            if via < best:
                best = via
        return best

    def update_demo(self, now):
        """Choose one fallible but danger-aware action for attract mode."""
        if (
            not self.demo_mode
            or self.state != STATE_PLAYING
            or ticks_diff(now, self.demo_next_action) < 0
        ):
            return False
        self.demo_next_action = ticks_add(now, DEMO_ACTION_MS)

        actor = [self.player_x, self.player_y]
        if self._tile_is_dangerous(self.player_x, self.player_y):
            escape = self._enemy_escape_step(actor)
            if escape is not None:
                return self.move_player(escape[2], escape[3], now)

        planned_bomb = self._demo_bomb_plan(now)
        if planned_bomb is not None and self._demo_should_bomb(planned_bomb):
            return self.place_bomb(now)

        candidates = []
        risky = []
        for dx, dy in DIRECTIONS:
            x = self.player_x + dx
            y = self.player_y + dy
            if not self._can_enter(x, y) or self._enemy_at(x, y):
                continue
            item = (x, y, dx, dy)
            risky.append(item)
            if not self._tile_is_dangerous(x, y):
                candidates.append(item)

        # Usually stay safe, but retain enough fallibility for a real demo.
        choices = candidates if candidates and randint(0, 99) < 92 else risky
        if not choices:
            return False

        chosen = None
        target_x = -1
        target_y = -1
        powerup_target = self._demo_powerup_target()
        if powerup_target is not None:
            target_x, target_y = powerup_target
        elif self.mode == MODE_TREASURE_HUNT and self.treasures:
            target_x = self.treasures[0][0]
            target_y = self.treasures[0][1]
        elif self.mode == MODE_BOMB_COURIER:
            if self.courier_carrying:
                target_x = self.courier_exit_x
                target_y = self.courier_exit_y
            else:
                target_x = self.courier_bomb_x
                target_y = self.courier_bomb_y
        elif self.mode == MODE_HOT_POTATO and self.hot_potato_player:
            if self.enemies:
                target_x = self.enemies[0][0]
                target_y = self.enemies[0][1]

        if target_x >= 0:
            best_distance = 999
            for x, y, dx, dy in choices:
                distance = self._asset_route_distance(
                    x,
                    y,
                    target_x,
                    target_y,
                )
                if distance < best_distance:
                    chosen = (x, y, dx, dy)
                    best_distance = distance
        elif (
            self.mode == MODE_HOT_POTATO
            and self.hot_potato_enemy is not None
        ):
            best_distance = -1
            for x, y, dx, dy in choices:
                distance = abs(self.hot_potato_enemy[0] - x) + abs(
                    self.hot_potato_enemy[1] - y
                )
                if distance > best_distance:
                    chosen = (x, y, dx, dy)
                    best_distance = distance
        elif self.enemies and randint(0, 99) < 78:
            best_distance = 999
            for x, y, dx, dy in choices:
                distance = 999
                for enemy in self.enemies:
                    candidate = abs(enemy[0] - x) + abs(enemy[1] - y)
                    if candidate < distance:
                        distance = candidate
                if distance < best_distance:
                    chosen = (x, y, dx, dy)
                    best_distance = distance
        if chosen is None:
            chosen = choices[randint(0, len(choices) - 1)]
        return self.move_player(chosen[2], chosen[3], now)

    def _enemy_escape_score(self, x, y):
        nearest = 999
        for bomb in self.bombs:
            distance = abs(bomb[0] - x) + abs(bomb[1] - y)
            if distance < nearest:
                nearest = distance
        if not self._tile_in_bomb_danger(x, y):
            return 1000 + nearest
        return nearest

    def _teleport_enemy(self, enemy, now):
        """Let mobile enemies intentionally use an unoccupied teleporter."""
        if len(self.teleporters) != 2:
            return False
        if len(enemy) < 14:
            enemy.append(0)
        if ticks_diff(now, enemy[13]) < 0:
            return False

        source = -1
        for index, pad in enumerate(self.teleporters):
            if enemy[0] == pad[0] and enemy[1] == pad[1]:
                source = index
                break
        if source < 0:
            return False

        target = self.teleporters[1 - source]
        if (
            self._has_bomb(target[0], target[1])
            or self._enemy_at(target[0], target[1], enemy)
            or (
                self.player_x == target[0]
                and self.player_y == target[1]
            )
        ):
            return False
        enemy[0] = target[0]
        enemy[1] = target[1]
        enemy[6] = target[0] * POSITION_SCALE
        enemy[7] = target[1] * POSITION_SCALE
        enemy[13] = ticks_add(now, TELEPORT_LOCK_MS)
        self._emit(EVENT_TELEPORT)
        return True

    def _move_enemy(self, enemy, now):
        if enemy[3] == ENEMY_TURRET:
            enemy[2] = ticks_add(now, 500)
            return
        candidates = []
        for dx, dy in DIRECTIONS:
            x = enemy[0] + dx
            y = enemy[1] + dy
            if self._can_enter(x, y, True, enemy):
                candidates.append((x, y, dx, dy))

        if candidates:
            chosen = None
            if (
                enemy[3] == ENEMY_BOMBER
                and self._tile_is_dangerous(enemy[0], enemy[1])
            ):
                escape = self._enemy_escape_step(enemy)
                if escape is not None:
                    chosen = escape[:4]
                else:
                    best_score = -1
                    for x, y, dx, dy in candidates:
                        score = self._enemy_escape_score(x, y)
                        if score > best_score:
                            chosen = (x, y, dx, dy)
                            best_score = score
            elif (
                enemy[3] in (ENEMY_CHASER, ENEMY_BOMBER, ENEMY_KAMIKAZE)
                or randint(0, 99) < 55
            ):
                best_distance = 999
                for x, y, dx, dy in candidates:
                    if (
                        enemy[3] == ENEMY_BOMBER
                        and self._tile_is_dangerous(x, y)
                    ):
                        continue
                    distance = self._asset_route_distance(
                        x,
                        y,
                        self.player_x,
                        self.player_y,
                    )
                    if distance < best_distance:
                        chosen = (x, y, dx, dy)
                        best_distance = distance
            if chosen is None:
                chosen = candidates[randint(0, len(candidates) - 1)]
            enemy[0], enemy[1] = chosen[0], chosen[1]
            enemy[4] = (enemy[4] + 1) % 4
            enemy[5] = self._facing_for_direction(chosen[2], chosen[3])
            self._teleport_enemy(enemy, now)

        pace = enemy[10] if len(enemy) >= 11 else 0
        interval = max(190, 520 - self.stage * 24 + pace)
        if enemy[8]:
            interval = max(150, interval * 3 // 4)
        enemy[2] = ticks_add(now, interval + randint(20, 120))

    def _stagger_enemy_moves(self, now):
        """Give every enemy a fresh, visibly separate first move deadline."""
        for index, enemy in enumerate(self.enemies):
            enemy[2] = ticks_add(
                now,
                80 + index * 105 + randint(0, 55),
            )

    def _enemy_try_bomb(self, enemy, now):
        if (
            self.mode != MODE_BLAST_RIVALS
            or enemy[3] != ENEMY_BOMBER
            or ticks_diff(now, enemy[9]) < 0
            or enemy[6] != enemy[0] * POSITION_SCALE
            or enemy[7] != enemy[1] * POSITION_SCALE
        ):
            return False

        enemy_bombs = 0
        for bomb in self.bombs:
            if len(bomb) >= 5 and bomb[4] == 1:
                enemy_bombs += 1
        enemy_limit = min(4, 1 + self.stage // 2)
        distance = abs(self.player_x - enemy[0]) + abs(self.player_y - enemy[1])
        flame_range = min(4, 2 + self.stage // 4)
        can_escape = False
        asset_pressure = False
        if not self._tile_is_dangerous(enemy[0], enemy[1]):
            planned_bomb = [
                enemy[0],
                enemy[1],
                ticks_add(now, BOMB_FUSE_MS + 300),
                flame_range,
                1,
            ]
            self.bombs.append(planned_bomb)
            can_escape = (
                self._enemy_escape_step(
                    enemy,
                    ENEMY_ESCAPE_PLAN_STEPS,
                )
                is not None
            )
            for barrel in self.barrels:
                if self._bomb_reaches(
                    planned_bomb,
                    barrel[0],
                    barrel[1],
                ):
                    asset_pressure = True
                    break
            if not asset_pressure:
                for mine in self.mines:
                    if self._bomb_reaches(
                        planned_bomb,
                        mine[0],
                        mine[1],
                    ):
                        asset_pressure = True
                        break
            self.bombs.pop()

        placed = False
        if (
            enemy_bombs < enemy_limit
            and not self._has_bomb(enemy[0], enemy[1])
            and can_escape
            and (
                distance <= 6
                or asset_pressure
                or randint(0, 99) < 35
            )
        ):
            self.bombs.append(
                [
                    enemy[0],
                    enemy[1],
                    ticks_add(now, BOMB_FUSE_MS + 300),
                    flame_range,
                    1,
                ]
            )
            enemy[2] = now
            placed = True
        enemy[9] = ticks_add(now, randint(2600, 4200))
        return placed

    @staticmethod
    def _direction_for_facing(facing):
        if facing == 1:
            return -1, 0
        if facing == 2:
            return 1, 0
        if facing == 3:
            return 0, -1
        return 0, 1

    def _aim_enemy_at_player(self, enemy):
        dx = self.player_x - enemy[0]
        dy = self.player_y - enemy[1]
        if abs(dx) >= abs(dy):
            step_x = 1 if dx >= 0 else -1
            step_y = 0
        else:
            step_x = 0
            step_y = 1 if dy >= 0 else -1
        enemy[5] = self._facing_for_direction(step_x, step_y)
        return step_x, step_y

    def _spawn_projectile(self, x, y, dx, dy, now, kind):
        self.projectiles.append(
            [x, y, dx, dy, ticks_add(now, PROJECTILE_STEP_MS), kind]
        )

    def _update_enemy_specials(self, now):
        changed = False
        for enemy in self.enemies[:]:
            kind = enemy[3]
            if kind not in (ENEMY_KAMIKAZE, ENEMY_TURRET):
                continue
            warning_until = enemy[11]
            if warning_until:
                if ticks_diff(now, warning_until) < 0:
                    continue
                enemy[11] = 0
                if kind == ENEMY_KAMIKAZE:
                    if enemy not in self.enemies:
                        continue
                    self.enemies.remove(enemy)
                    self._add_death_effect(
                        enemy[6],
                        enemy[7],
                        DEATH_ENEMY_BOMBER,
                        now,
                    )
                    carried_bomb = [
                        enemy[0],
                        enemy[1],
                        now,
                        3 if enemy[8] else 2,
                        1,
                        1,
                    ]
                    self.bombs.append(carried_bomb)
                    self._detonate(carried_bomb, now)
                else:
                    dx, dy = self._direction_for_facing(enemy[5])
                    self._spawn_projectile(
                        enemy[0], enemy[1], dx, dy, now, 0
                    )
                    enemy[12] = ticks_add(now, randint(2100, 3000))
                changed = True
                continue

            if ticks_diff(now, enemy[12]) < 0:
                continue
            distance = abs(self.player_x - enemy[0]) + abs(
                self.player_y - enemy[1]
            )
            if kind == ENEMY_KAMIKAZE and distance > 3:
                enemy[12] = ticks_add(now, 400)
                continue
            self._aim_enemy_at_player(enemy)
            enemy[11] = ticks_add(now, SPECIAL_WARNING_MS)
            self._emit(EVENT_WARNING)
            changed = True
        return changed

    @staticmethod
    def _spike_active(trap, now):
        phase = (now + trap[2]) % SPIKE_CYCLE_MS
        return phase >= SPIKE_CYCLE_MS - SPIKE_ACTIVE_MS

    def _fire_emitter(self, emitter, now):
        dx, dy = DIRECTIONS[emitter[2]]
        expires = ticks_add(now, EXPLOSION_MS + 180)
        for distance in range(1, 5):
            x = emitter[0] + dx * distance
            y = emitter[1] + dy * distance
            if x < 0 or y < 0 or x >= GRID_WIDTH or y >= GRID_HEIGHT:
                break
            if self.grid[y][x] == TILE_SOLID:
                break
            self._add_explosion(x, y, expires, now, 3)
            barrel = self._barrel_at(x, y)
            if barrel is not None:
                self._trigger_barrel(barrel, now, 3)
                break
            mine = self._mine_at(x, y)
            if mine is not None:
                self._trigger_mine(mine, now)
            if self.grid[y][x] == TILE_BRICK:
                break
        self._react_background_creatures(emitter[0], emitter[1], now)

    def _update_projectiles(self, now):
        changed = False
        for projectile in self.projectiles[:]:
            if ticks_diff(now, projectile[4]) < 0:
                continue
            x = projectile[0] + projectile[2]
            y = projectile[1] + projectile[3]
            if (
                x < 0
                or y < 0
                or x >= GRID_WIDTH
                or y >= GRID_HEIGHT
                or self.grid[y][x] != TILE_EMPTY
            ):
                self.projectiles.remove(projectile)
                changed = True
                continue
            projectile[0] = x
            projectile[1] = y
            projectile[4] = ticks_add(now, PROJECTILE_STEP_MS)
            barrel = self._barrel_at(x, y)
            mine = self._mine_at(x, y)
            if barrel is not None:
                self._trigger_barrel(barrel, now, 3)
                self.projectiles.remove(projectile)
            elif mine is not None:
                self._trigger_mine(mine, now)
                self.projectiles.remove(projectile)
            elif x == self.player_x and y == self.player_y:
                self._lose_life(now)
                self.projectiles.remove(projectile)
            changed = True
        return changed

    def _update_hazards(self, now):
        changed = False
        for trap in self.spike_traps:
            if (
                trap[0] == self.player_x
                and trap[1] == self.player_y
                and self._spike_active(trap, now)
            ):
                if self._lose_life(now):
                    changed = True

        for mine in self.mines[:]:
            if ticks_diff(now, mine[3]) < 0:
                continue
            self.mines.remove(mine)
            mine_bomb = [mine[0], mine[1], now, 2, 3, 2]
            self.bombs.append(mine_bomb)
            self._detonate(mine_bomb, now)
            changed = True

        for emitter in self.flame_emitters:
            if emitter[4]:
                if ticks_diff(now, emitter[4]) >= 0:
                    self._fire_emitter(emitter, now)
                    emitter[2] = (emitter[2] + 1) % len(DIRECTIONS)
                    emitter[3] = ticks_add(now, 2400)
                    emitter[4] = 0
                    changed = True
            elif ticks_diff(now, emitter[3]) >= 0:
                emitter[4] = ticks_add(now, 550)
                self._emit(EVENT_WARNING)
                changed = True

        for cannon in self.cannons:
            if cannon[5]:
                if ticks_diff(now, cannon[5]) >= 0:
                    self._spawn_projectile(
                        cannon[0],
                        cannon[1],
                        cannon[2],
                        cannon[3],
                        now,
                        1,
                    )
                    cannon[4] = ticks_add(now, 2800)
                    cannon[5] = 0
                    changed = True
            elif ticks_diff(now, cannon[4]) >= 0:
                cannon[5] = ticks_add(now, 650)
                self._emit(EVENT_WARNING)
                changed = True

        if self._update_projectiles(now):
            changed = True
        return changed

    @staticmethod
    def _approach(value, target, step):
        if value < target:
            return min(target, value + step)
        if value > target:
            return max(target, value - step)
        return value

    def _advance_animation(self, now):
        delta = ticks_diff(now, self.animation_last)
        self.animation_last = now
        if delta <= 0:
            return False
        delta = min(delta, ENEMY_MOVE_ANIMATION_MS)
        speed_active = ticks_diff(self.speed_until, now) > 0
        if self.mode == MODE_BOMB_COURIER and self.courier_carrying:
            player_move_ms = 135 if speed_active else 215
        else:
            player_move_ms = 90 if speed_active else PLAYER_MOVE_ANIMATION_MS
        player_delta = min(delta, player_move_ms)
        player_step = max(
            1,
            (
                POSITION_SCALE * player_delta
                + player_move_ms
                - 1
            )
            // player_move_ms,
        )
        enemy_step = max(
            1,
            (POSITION_SCALE * delta + ENEMY_MOVE_ANIMATION_MS - 1)
            // ENEMY_MOVE_ANIMATION_MS,
        )
        changed = False

        target_x = self.player_x * POSITION_SCALE
        target_y = self.player_y * POSITION_SCALE
        next_x = self._approach(self.player_draw_x, target_x, player_step)
        next_y = self._approach(self.player_draw_y, target_y, player_step)
        if next_x != self.player_draw_x or next_y != self.player_draw_y:
            self.player_draw_x = next_x
            self.player_draw_y = next_y
            changed = True

        for enemy in self.enemies:
            target_x = enemy[0] * POSITION_SCALE
            target_y = enemy[1] * POSITION_SCALE
            next_x = self._approach(enemy[6], target_x, enemy_step)
            next_y = self._approach(enemy[7], target_y, enemy_step)
            if next_x != enemy[6] or next_y != enemy[7]:
                enemy[6] = next_x
                enemy[7] = next_y
                changed = True
        return changed

    def _cleanup_explosions(self, now):
        changed = False
        for flame in self.explosions[:]:
            if ticks_diff(now, flame[2]) >= 0:
                self.explosions.remove(flame)
                changed = True
        if not self.explosions:
            self.chain_strength = 0
        return changed

    def _update_mode_objective(self, now):
        if self.mode == MODE_TREASURE_HUNT:
            if (
                self.treasure_target > 0
                and self.treasure_collected >= self.treasure_target
            ):
                self.score += 300
                self.state = STATE_STAGE_CLEAR
                self.state_until = ticks_add(now, STAGE_CLEAR_MS)
                return True
            if ticks_diff(now, self.objective_until) >= 0:
                self.objective_until = ticks_add(now, 30000)
                self._lose_life(now)
                return True
            return False

        if self.mode == MODE_BOMB_COURIER:
            if (
                self.courier_carrying
                and ticks_diff(now, self.courier_fuse_until) >= 0
            ):
                x = self.player_x
                y = self.player_y
                self._drop_courier_bomb()
                unstable_bomb = [x, y, now, 3, 0, 1]
                self.bombs.append(unstable_bomb)
                self._detonate(unstable_bomb, now)
                return True
            return False

        if self.mode != MODE_HOT_POTATO:
            return False
        if (
            self.hot_potato_enemy is not None
            and self.hot_potato_enemy not in self.enemies
        ):
            self.hot_potato_enemy = None
            self.hot_potato_player = True
            self.hot_potato_until = ticks_add(now, HOT_POTATO_FUSE_MS)
            return True
        if ticks_diff(now, self.hot_potato_until) < 0:
            return False

        if self.hot_potato_player:
            x = self.player_x
            y = self.player_y
        elif self.hot_potato_enemy is not None:
            holder = self.hot_potato_enemy
            x = holder[0]
            y = holder[1]
            if holder in self.enemies:
                self.enemies.remove(holder)
                self._add_death_effect(
                    holder[6],
                    holder[7],
                    DEATH_ENEMY_BOMBER,
                    now,
                )
                self.score += 200
        else:
            x = self.player_x
            y = self.player_y

        self.hot_potato_enemy = None
        self.hot_potato_player = True
        self.hot_potato_until = ticks_add(now, HOT_POTATO_FUSE_MS)
        self.hot_potato_transfer_until = ticks_add(
            now,
            HOT_POTATO_TRANSFER_MS,
        )
        potato_bomb = [x, y, now, 2, 3, 1]
        self.bombs.append(potato_bomb)
        self._detonate(potato_bomb, now)
        return True

    def update(self, now):
        """Advance timers, bombs, enemies, damage, and stage transitions."""
        changed = False
        self.animation_time = now
        if self._advance_animation(now):
            changed = True

        if self._cleanup_death_effects(now):
            changed = True
        if self._cleanup_decals(now):
            changed = True

        if self.state == STATE_STAGE_INTRO:
            if ticks_diff(now, self.state_until) >= 0:
                self.state = STATE_PLAYING
                self.state_until = 0
                self._stagger_enemy_moves(now)
                return True
            return changed

        if self.state == STATE_PLAYER_DYING:
            if self._cleanup_explosions(now):
                changed = True
            if ticks_diff(now, self.state_until) >= 0:
                self._finish_player_death(now)
                return True
            return changed

        if self.state == STATE_STAGE_CLEAR:
            if ticks_diff(now, self.state_until) >= 0:
                self.stage += 1
                self.score += 250
                self._build_stage(now)
                return True
            return False

        if self.state != STATE_PLAYING:
            return changed

        if self._cleanup_explosions(now):
            changed = True

        if self._update_magnet(now):
            changed = True

        if self._update_mode_objective(now):
            changed = True
        if self.state != STATE_PLAYING:
            return True

        while True:
            due = None
            for bomb in self.bombs:
                if ticks_diff(now, bomb[2]) >= 0:
                    due = bomb
                    break
            if due is None:
                break
            self._detonate(due, now)
            changed = True

        if self._update_enemy_specials(now):
            changed = True
        if self._update_hazards(now):
            changed = True
        if self.state != STATE_PLAYING:
            return True

        if self.explosions:
            previous_lives = self.lives
            previous_enemies = len(self.enemies)
            self._apply_explosion_damage(now)
            if previous_lives != self.lives or previous_enemies != len(self.enemies):
                changed = True
            if self.state != STATE_PLAYING:
                return True

        for enemy in self.enemies:
            if ticks_diff(now, enemy[2]) >= 0:
                self._move_enemy(enemy, now)
                changed = True
            if self._enemy_try_bomb(enemy, now):
                changed = True

        touching = self._enemy_touching_player()
        if touching is not None:
            if self._hot_potato_contact(touching, now):
                changed = True
            elif self._lose_life(now):
                changed = True
            if self.state != STATE_PLAYING:
                return True

        enemies_cleared = not self.enemies and not self.death_effects
        if (
            enemies_cleared
            and self.mode
            not in (MODE_TREASURE_HUNT, MODE_BOMB_COURIER)
        ):
            self.state = STATE_STAGE_CLEAR
            self.state_until = ticks_add(now, STAGE_CLEAR_MS)
            changed = True

        return changed
