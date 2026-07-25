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

THEME_NATURE = 0
THEME_INDUSTRIAL = 1
THEME_WATER = 2
THEME_NAMES = ("NATURE", "INDUSTRIAL", "WATER")

MODE_GHOST_HUNT = 0
MODE_BLAST_RIVALS = 1
MODE_NAMES = ("GHOST HUNT", "BLAST RIVALS")
MENU_LEADERBOARD = 2
MENU_ITEM_COUNT = 3

ENEMY_BLOB = 0
ENEMY_CHASER = 1
ENEMY_BOMBER = 2

STATE_TITLE = 0
STATE_PLAYING = 1
STATE_STAGE_CLEAR = 2
STATE_GAME_OVER = 3
STATE_PLAYER_DYING = 4
STATE_STAGE_INTRO = 5
STATE_MODE_SELECT = 6
STATE_LEADERBOARD = 7

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
STAGE_CLEAR_MS = 1300
DEATH_ANIMATION_MS = 720
PLAYER_MOVE_ANIMATION_MS = 150
ENEMY_MOVE_ANIMATION_MS = 190
STAGE_INTRO_MS = 900
POSITION_SCALE = 256
MAX_DECALS = 12

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
        self.decals = []
        self.death_effects = []
        self.leaderboard = []
        self.state = STATE_TITLE
        self.state_until = 0
        self.invulnerable_until = 0
        self.animation_time = 0
        self.animation_last = 0
        self.player_frame = 0
        self.player_facing = 0
        self.player_draw_x = POSITION_SCALE
        self.player_draw_y = POSITION_SCALE

    def open_mode_menu(self):
        """Open the mode chooser with the current mode highlighted."""
        self.menu_selection = self.mode
        self.state = STATE_MODE_SELECT

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
        self.flame_range = 2
        self.bomb_limit = 1
        self._build_stage(now)

    def _build_stage(self, now):
        """Create a procedural arena with a guaranteed safe starting pocket."""
        self.theme = self._choose_theme()
        self.grid = []
        for y in range(GRID_HEIGHT):
            row = []
            for x in range(GRID_WIDTH):
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

        self.player_x = 1
        self.player_y = 1
        self.player_draw_x = POSITION_SCALE
        self.player_draw_y = POSITION_SCALE
        self.bombs = []
        self.explosions = []
        self.powerups = []
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
        for y in range(GRID_HEIGHT - 2, 0, -1):
            for x in range(GRID_WIDTH - 2, 0, -1):
                if self.grid[y][x] != TILE_SOLID and x + y > 10:
                    candidates.append((x, y))

        enemy_count = min(2 + self.stage, 7)
        while candidates and len(self.enemies) < enemy_count:
            index = randint(0, len(candidates) - 1)
            x, y = candidates.pop(index)
            too_close = False
            for enemy in self.enemies:
                if abs(enemy[0] - x) + abs(enemy[1] - y) < 2:
                    too_close = True
                    break
            if too_close:
                continue
            self.grid[y][x] = TILE_EMPTY
            delay = randint(100, 350)
            kind = (
                ENEMY_BOMBER
                if self.mode == MODE_BLAST_RIVALS
                else randint(ENEMY_BLOB, ENEMY_CHASER)
            )
            elite_chance = min(35, 8 + self.stage * 3)
            elite = 1 if self.stage >= 3 and randint(0, 99) < elite_chance else 0
            self.enemies.append(
                [
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
                ]
            )

        # This is a fallback for an exceptionally crowded random map.
        if not self.enemies:
            self.grid[GRID_HEIGHT - 2][GRID_WIDTH - 2] = TILE_EMPTY
            self.enemies.append(
                [
                    GRID_WIDTH - 2,
                    GRID_HEIGHT - 2,
                    ticks_add(now, 250),
                    ENEMY_BOMBER
                    if self.mode == MODE_BLAST_RIVALS
                    else ENEMY_BLOB,
                    0,
                    0,
                    (GRID_WIDTH - 2) * POSITION_SCALE,
                    (GRID_HEIGHT - 2) * POSITION_SCALE,
                    0,
                    ticks_add(now, 2200),
                ]
            )

    def _choose_theme(self):
        theme = randint(0, len(THEME_NAMES) - 1)
        if theme == self.theme:
            theme = (theme + 1 + randint(0, len(THEME_NAMES) - 2)) % len(
                THEME_NAMES
            )
        return theme

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

    def _enemy_at(self, x, y, ignored=None):
        for enemy in self.enemies:
            if enemy is not ignored and enemy[0] == x and enemy[1] == y:
                return True
        return False

    @staticmethod
    def _draw_tile(value):
        return (value + POSITION_SCALE // 2) // POSITION_SCALE

    def _enemy_touches_player(self):
        contact_distance = POSITION_SCALE * 3 // 5
        for enemy in self.enemies:
            if (
                abs(enemy[6] - self.player_draw_x) <= contact_distance
                and abs(enemy[7] - self.player_draw_y) <= contact_distance
            ):
                return True
        return False

    def _can_enter(self, x, y, block_enemies=False, ignored_enemy=None):
        if x < 0 or y < 0 or x >= GRID_WIDTH or y >= GRID_HEIGHT:
            return False
        if self.grid[y][x] != TILE_EMPTY or self._has_bomb(x, y):
            return False
        if block_enemies and self._enemy_at(x, y, ignored_enemy):
            return False
        return True

    def move_player(self, dx, dy, now):
        """Attempt to move the player by one grid tile."""
        if self.state != STATE_PLAYING:
            return False
        self.player_facing = self._facing_for_direction(dx, dy)
        x = self.player_x + dx
        y = self.player_y + dy
        if not self._can_enter(x, y):
            return False
        self.player_x = x
        self.player_y = y
        self.player_frame = (self.player_frame + 1) % 4
        self._collect_powerup()
        if self._enemy_touches_player():
            self._lose_life(now)
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
        return True

    def _collect_powerup(self):
        for powerup in self.powerups:
            if powerup[0] == self.player_x and powerup[1] == self.player_y:
                if powerup[2] == POWER_FLAME:
                    self.flame_range = min(6, self.flame_range + 1)
                else:
                    self.bomb_limit = min(5, self.bomb_limit + 1)
                self.score += 25
                self.powerups.remove(powerup)
                return True
        return False

    def _add_explosion(self, x, y, expires, owner=0):
        self._scorch_decals_at(x, y)
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
        if randint(0, 99) >= 24:
            return
        kind = POWER_FLAME if randint(0, 1) == 0 else POWER_BOMB
        self.powerups.append([x, y, kind])

    def _add_decal(self, draw_x, draw_y, kind):
        tile_x = (draw_x + POSITION_SCALE // 2) // POSITION_SCALE
        tile_y = (draw_y + POSITION_SCALE // 2) // POSITION_SCALE
        if kind == DECAL_SCORCH:
            for decal in self.decals:
                decal_x = (decal[0] + POSITION_SCALE // 2) // POSITION_SCALE
                decal_y = (decal[1] + POSITION_SCALE // 2) // POSITION_SCALE
                if decal_x == tile_x and decal_y == tile_y:
                    decal[2] = DECAL_SCORCH
                    decal[3] = self.theme
                    decal[4] = randint(0, 3)
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
            ]
        )

    def _scorch_decals_at(self, x, y):
        for decal in self.decals:
            decal_x = (decal[0] + POSITION_SCALE // 2) // POSITION_SCALE
            decal_y = (decal[1] + POSITION_SCALE // 2) // POSITION_SCALE
            if decal_x == x and decal_y == y:
                decal[2] = DECAL_SCORCH
                decal[3] = self.theme

    def _detonate(self, bomb, now):
        """Turn one bomb into blast tiles and arm bombs caught in the blast."""
        if bomb not in self.bombs:
            return
        self.bombs.remove(bomb)
        expires = ticks_add(now, EXPLOSION_MS)
        owner = bomb[4] if len(bomb) >= 5 else 0
        self._add_explosion(bomb[0], bomb[1], expires, owner)
        self._add_decal(
            bomb[0] * POSITION_SCALE,
            bomb[1] * POSITION_SCALE,
            DECAL_SCORCH,
        )

        for dx, dy in DIRECTIONS:
            for distance in range(1, bomb[3] + 1):
                x = bomb[0] + dx * distance
                y = bomb[1] + dy * distance
                tile = self.grid[y][x]
                if tile == TILE_SOLID:
                    break
                self._add_explosion(x, y, expires, owner)

                chained = None
                for other in self.bombs:
                    if other[0] == x and other[1] == y:
                        chained = other
                        break
                if chained is not None:
                    chained[2] = now

                if tile == TILE_BRICK:
                    self.grid[y][x] = TILE_EMPTY
                    if owner == 0:
                        self.score += 5
                    self._add_decal(
                        x * POSITION_SCALE,
                        y * POSITION_SCALE,
                        DECAL_DEBRIS,
                    )
                    self._reveal_powerup(x, y)
                    break

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
            owner = flame[3] if len(flame) >= 4 else 0
            if enemy[3] == ENEMY_BOMBER and owner == 1:
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
            if enemy[8]:
                death_kind = DEATH_ENEMY_ELITE
                decal_kind = DECAL_ELITE
            elif enemy[3] == ENEMY_BOMBER:
                death_kind = DEATH_ENEMY_BOMBER
                decal_kind = DECAL_BOMBER
            else:
                death_kind = DEATH_ENEMY_BLOB + enemy[3]
                decal_kind = DECAL_BLOB + enemy[3]
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
            )
            self.score += 250 if enemy[8] else 100

        player_x = self._draw_tile(self.player_draw_x)
        player_y = self._draw_tile(self.player_draw_y)
        if self._is_flame(player_x, player_y):
            self._lose_life(now)

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

    def _lose_life(self, now):
        if (
            self.state != STATE_PLAYING
            or ticks_diff(now, self.invulnerable_until) < 0
        ):
            return False

        self._add_death_effect(
            self.player_draw_x,
            self.player_draw_y,
            DEATH_PLAYER,
            now,
        )
        self.lives -= 1
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

    def _enemy_escape_score(self, x, y):
        nearest = 999
        for bomb in self.bombs:
            distance = abs(bomb[0] - x) + abs(bomb[1] - y)
            if distance < nearest:
                nearest = distance
        if not self._tile_in_bomb_danger(x, y):
            return 1000 + nearest
        return nearest

    def _move_enemy(self, enemy, now):
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
                and self._tile_in_bomb_danger(enemy[0], enemy[1])
            ):
                best_score = -1
                for x, y, dx, dy in candidates:
                    score = self._enemy_escape_score(x, y)
                    if score > best_score:
                        chosen = (x, y, dx, dy)
                        best_score = score
            elif enemy[3] in (ENEMY_CHASER, ENEMY_BOMBER) or randint(0, 99) < 55:
                best_distance = 999
                for x, y, dx, dy in candidates:
                    distance = abs(self.player_x - x) + abs(self.player_y - y)
                    if distance < best_distance:
                        chosen = (x, y, dx, dy)
                        best_distance = distance
            if chosen is None:
                chosen = candidates[randint(0, len(candidates) - 1)]
            enemy[0], enemy[1] = chosen[0], chosen[1]
            enemy[4] = (enemy[4] + 1) % 4
            enemy[5] = self._facing_for_direction(chosen[2], chosen[3])

        interval = max(190, 520 - self.stage * 24)
        if enemy[8]:
            interval = max(150, interval * 3 // 4)
        enemy[2] = ticks_add(now, interval + randint(0, 100))

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
        can_escape = False
        for dx, dy in DIRECTIONS:
            if self._can_enter(enemy[0] + dx, enemy[1] + dy, True, enemy):
                can_escape = True
                break

        placed = False
        if (
            enemy_bombs < enemy_limit
            and not self._has_bomb(enemy[0], enemy[1])
            and can_escape
            and (distance <= 6 or randint(0, 99) < 35)
        ):
            self.bombs.append(
                [
                    enemy[0],
                    enemy[1],
                    ticks_add(now, BOMB_FUSE_MS + 300),
                    min(4, 2 + self.stage // 4),
                    1,
                ]
            )
            placed = True
        enemy[9] = ticks_add(now, randint(2600, 4200))
        return placed

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
        player_delta = min(delta, PLAYER_MOVE_ANIMATION_MS)
        player_step = max(
            1,
            (
                POSITION_SCALE * player_delta
                + PLAYER_MOVE_ANIMATION_MS
                - 1
            )
            // PLAYER_MOVE_ANIMATION_MS,
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
        return changed

    def update(self, now):
        """Advance timers, bombs, enemies, damage, and stage transitions."""
        changed = False
        self.animation_time = now
        if self._advance_animation(now):
            changed = True

        if self._cleanup_death_effects(now):
            changed = True

        if self.state == STATE_STAGE_INTRO:
            if ticks_diff(now, self.state_until) >= 0:
                self.state = STATE_PLAYING
                self.state_until = 0
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

        if self._enemy_touches_player():
            if self._lose_life(now):
                changed = True
            if self.state != STATE_PLAYING:
                return True

        if not self.enemies and not self.death_effects:
            self.state = STATE_STAGE_CLEAR
            self.state_until = ticks_add(now, STAGE_CLEAR_MS)
            changed = True

        return changed
