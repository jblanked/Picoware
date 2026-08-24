"""FlipWorld dragon — boss + cameo fly-bys, ported from the Arduino build.

Modes:
  "boss"   - patrols the last world, lobs up to 5 fireballs at the player, bites when
             crowded, and wheels back to face the player at each third of health lost.
  "attack" - undefeatable cameo that streaks across making N passes firing at the player.
  "burn"   - undefeatable cameo that streaks across torching flammable scenery.

Rendered with the mono sprite for speed (colour comes with the full-colour pass).
"""

from math import sqrt, sin, atan2
from picoware.system.vector import Vector
from picoware.engine.image import Image
from picoware.engine.entity import (
    Entity,
    ENTITY_TYPE_ENEMY,
    ENTITY_TYPE_NPC,
    ENTITY_TYPE_PLAYER,
    ENTITY_STATE_DEAD,
    ENTITY_STATE_ATTACKED,
)
from picoware.system.buttons import BUTTON_CENTER, BUTTON_NONE
from flip_world.dragon_assets import (
    enemy_left_dragon_59x44px,
    enemy_right_dragon_59x44px,
)
from flip_world.colorize import ink_byte

# health fractions at which the boss turns to face the player (3 defensive turns)
_TURN_AT = (0.667, 0.334, 0.08)
_DT = 1.0 / 30.0
_RAD2DEG = 57.29578

# Panel is not inverted, so shape colours are passed straight through.
_FB_ORANGE = 0xFD20  # orange body
_FB_CORE = 0xFFE0    # hot yellow core

# flammable icon ids (must match general.py)
_FLAMMABLE = (0, 1, 2, 4)  # house, plant, tree, flower


def _fire_arc(facing_right, dx, dy):
    """True if (dx,dy) is inside the dragon's forward fire arc (clock positions)."""
    ang = atan2(dy, dx) * _RAD2DEG
    if facing_right:
        return -60.0 <= ang <= 120.0
    return ang >= 60.0 or ang <= -120.0


# ── multi-colour body (built once, cached) ─────────────────────────────────────
_DRAGON_W = 59
_DRAGON_H = 44


def _grad565(t):
    """Smooth head->tail colour: red -> orange -> yellow -> (green only near the tail)."""
    if t < 0:
        t = 0
    elif t > 1:
        t = 1
    if t < 0.40:
        r, g, b = 255, int(t / 0.40 * 150), 0
    elif t < 0.72:
        r, g, b = 255, int(150 + (t - 0.40) / 0.32 * 105), 0
    elif t < 0.90:
        r, g, b = 255, 255, 0
    else:
        k = (t - 0.90) / 0.10
        r, g, b = int(255 - k * 210), int(255 - k * 35), int(k * 70)
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def _build_dragon_buffer(mask, head_right):
    """Colour an 8-bit dragon mask into a framebuffer (RGB332) buffer, once."""
    w, h = _DRAGON_W, _DRAGON_H
    wing_cut = h - 12
    foot_cut = h - 3
    green = _grad565(1.0)
    yellow_ink = ink_byte(0xFFE0)
    mottle_ink = ink_byte(0xF800)
    out = bytearray(len(mask))
    for y in range(h):
        row = y * w
        for x in range(w):
            i = row + x
            if mask[i] != 0x00:
                out[i] = 0x00  # transparent (black, blends into the background)
                continue
            front_cols = (w - 1 - x) if head_right else x
            if y < wing_cut and front_cols >= 8:
                # wings: yellow, lightly mottled, top row kept clean
                if y > 0 and ((x ^ y) & 3) == 0:
                    out[i] = mottle_ink
                else:
                    out[i] = yellow_ink
            else:
                t = (w - 1 - x) / (w - 1) if head_right else x / (w - 1)
                out[i] = ink_byte(green if y >= foot_cut else _grad565(t))
    return bytes(out)


_dragon_buf_cache = {}


def _dragon_buffer(head_right):
    """Cached coloured dragon body for the given facing."""
    if head_right not in _dragon_buf_cache:
        mask = enemy_left_dragon_59x44px if head_right else enemy_right_dragon_59x44px
        _dragon_buf_cache[head_right] = _build_dragon_buffer(mask, head_right)
    return _dragon_buf_cache[head_right]


class Dragon(Entity):
    """The boss dragon and its cameo fly-by cousins."""

    def __init__(self, mode="boss", passes=1, burn_count=0):
        size = Vector(59, 44)
        etype = ENTITY_TYPE_ENEMY if mode == "boss" else ENTITY_TYPE_NPC
        pos = Vector(360, 100) if mode == "boss" else Vector(-60, 70)
        super().__init__(
            "Dragon",
            etype,
            pos,
            size,
            None,           # sprite (set below)
            None,           # sprite_left
            None,           # sprite_right
            None,           # start
            None,           # stop
            self.update,    # update
            self.render,    # render
            self.collision, # collision
            True,           # is 8-bit
        )
        self.mode = mode
        self.flip_world_run = None
        self.size = size
        # left/right facing images (art faces the opposite way, so they're swapped)
        self.sprite = Image(size, True, enemy_right_dragon_59x44px)
        self.sprite_left = Image(size, True, enemy_right_dragon_59x44px)
        self.sprite_right = Image(size, True, enemy_left_dragon_59x44px)

        # movement / combat state
        self.direction = Vector(-1, 0)
        self.speed = 80.0 if mode == "boss" else 90.0
        self.strength = 40.0
        self.health = 1000.0
        self.max_health = 1000.0
        self.start_position = Vector(pos.x, pos.y)

        # boss internals
        self._base_y = pos.y
        self._phase = 0.0
        self._fire_cd = 1.5
        self._turns = 0
        self._move_dir = -1.0
        self._melee_cd = 0.0
        # up to 5 fireballs in flight: [active, x, y, dx, dy]
        self._fb = [[False, 0.0, 0.0, 0.0, 0.0] for _ in range(5)]

        # fly-by internals
        self._passes = passes
        self._burn_n = burn_count
        self._burn_i = 0
        self._fly_dir = 1.0
        self._fly_y = pos.y
        self._fly_cd = 0.6
        self._fly_tx = 0.0
        self._fly_ty = 0.0
        self._fly_fb = [False, 0.0, 0.0, 0.0, 0.0]
        self._done = False
        self._draw_pos = Vector(0, 0)

    # ── helpers ──────────────────────────────────────────────────────────────
    def _find_player(self, game):
        lvl = game.current_level
        if not lvl:
            return None
        for i in range(lvl.entity_count):
            e = lvl.get_entity(i)
            if e and e.type == ENTITY_TYPE_PLAYER:
                return e
        return None

    def _hurt_player(self, player, dmg):
        player.health -= dmg
        if player.health <= 0:
            player.state = ENTITY_STATE_DEAD
            player.health = player.max_health
            player.position = player.start_position
        else:
            player.state = ENTITY_STATE_ATTACKED

    def _flammables(self):
        """Yield (cx, cy) centres of flammable scenery from the icon group."""
        run = self.flip_world_run
        out = []
        if not run or not run.current_icon_group:
            return out
        for spec in run.current_icon_group.icons:
            if spec.id in _FLAMMABLE:
                out.append((spec.x + spec.width * 0.5, spec.y + spec.height * 0.5))
        return out

    def collision(self, other, game):
        """The boss can be worn down by the player; cameo dragons are undefeatable."""
        if self.mode != "boss" or self.state == ENTITY_STATE_DEAD:
            return
        if other.type != ENTITY_TYPE_PLAYER:
            return

        dpos = self.position
        ppos = other.position
        dragon_facing = (
            (self.direction.x == -1 and ppos.x < dpos.x)
            or (self.direction.x == 1 and ppos.x > dpos.x)
        )
        player_facing = (
            (other.direction.x == -1 and dpos.x < ppos.x)
            or (other.direction.x == 1 and dpos.x > ppos.x)
            or (other.direction.y == -1 and dpos.y < ppos.y)
            or (other.direction.y == 1 and dpos.y > ppos.y)
        )

        # player lands a hit
        if player_facing and game.input == BUTTON_CENTER and not dragon_facing:
            game.input = BUTTON_NONE
            if other.elapsed_attack_timer >= other.attack_timer:
                other.elapsed_attack_timer = 0
                other.xp += self.strength
                other.health = min(other.health + self.strength * 0.1, 100)
                self.health -= other.strength
                if self.health <= 0:
                    self.state = ENTITY_STATE_DEAD
                    self.position = Vector(-100, -100)
                    self.health = 0

    # ── update ───────────────────────────────────────────────────────────────
    def update(self, game):
        if self.mode == "boss":
            self._update_boss(game)
        else:
            self._update_flyby(game)

    def _update_boss(self, game):
        if self.state == ENTITY_STATE_DEAD:
            for fb in self._fb:
                fb[0] = False
            return
        lvl = game.current_level
        if not lvl:
            return
        player = self._find_player(game)

        # defensive turns toward the player at each third of health lost
        while self._turns < 3 and self.health <= self.max_health * _TURN_AT[self._turns]:
            if player:
                self._move_dir = -1.0 if player.position.x < self.position.x else 1.0
            self._turns += 1

        # patrol back and forth, bouncing off the edges
        buffer = 40
        min_x = buffer
        max_x = lvl.size.x - buffer - self.size.x
        if max_x < min_x:
            max_x = min_x
        nx = self.position.x + self._move_dir * self.speed * _DT
        if nx <= min_x:
            nx = min_x
            self._move_dir = 1.0
        elif nx >= max_x:
            nx = max_x
            self._move_dir = -1.0
        self.direction = Vector(1, 0) if self._move_dir >= 0 else Vector(-1, 0)

        # ease the path height toward the player (aggression)
        if player:
            want = player.position.y + player.size.y * 0.5 - self.size.y * 0.5
            self._base_y += (want - self._base_y) * 0.04
            self._base_y = max(8, min(self._base_y, lvl.size.y - self.size.y - 8))

        self._phase += _DT
        ny = self._base_y + sin(self._phase * 1.6) * 16.0
        self.position = Vector(nx, ny)

        facing_right = self.direction.x >= 0
        cx = self.position.x + self.size.x * 0.5
        cy = self.position.y + self.size.y * 0.5
        mx = (self.position.x + self.size.x - 2) if facing_right else (self.position.x + 2)
        my = self.position.y + 37

        # melee bite when the player is right in front of the jaws
        if self._melee_cd > 0:
            self._melee_cd -= _DT
        if player and self._melee_cd <= 0:
            px = player.position.x + player.size.x * 0.5
            py = player.position.y + player.size.y * 0.5
            in_front = (px >= self.position.x + self.size.x * 0.4) if facing_right \
                else (px <= self.position.x + self.size.x * 0.6)
            ddx = px - mx
            ddy = py - my
            if in_front and ddx * ddx + ddy * ddy < 52.0 * 52.0:
                self._hurt_player(player, self.strength)
                self._melee_cd = 0.6

        # loose another fireball (up to 5 aloft) on a cooldown so they spread out
        if self._fire_cd > 0:
            self._fire_cd -= _DT
        free = -1
        count = 0
        for i in range(5):
            if self._fb[i][0]:
                count += 1
            elif free < 0:
                free = i
        if free >= 0 and count < 5 and self._fire_cd <= 0 and player:
            px = player.position.x + player.size.x * 0.5
            py = player.position.y + player.size.y * 0.5
            dx = px - mx
            dy = py - my
            dist = sqrt(dx * dx + dy * dy)
            if _fire_arc(facing_right, px - cx, py - cy) and 30 < dist < 500:
                sp = 3.3
                self._fb[free] = [True, mx, my, dx / dist * sp, dy / dist * sp]
                self._fire_cd = 0.7

        # advance fireballs, resolve hits
        for fb in self._fb:
            if not fb[0]:
                continue
            fb[1] += fb[3]
            fb[2] += fb[4]
            if fb[1] < 0 or fb[2] < 0 or fb[1] > lvl.size.x or fb[2] > lvl.size.y:
                fb[0] = False
            elif player:
                px = player.position.x + player.size.x * 0.5
                py = player.position.y + player.size.y * 0.5
                ddx = fb[1] - px
                ddy = fb[2] - py
                if ddx * ddx + ddy * ddy < 100:
                    self._hurt_player(player, 25)
                    fb[0] = False

    def _update_flyby(self, game):
        if self._done:
            self.is_visible = False
            self._fly_fb[0] = False
            return
        lvl = game.current_level
        if not lvl:
            return
        player = self._find_player(game)

        self.direction = Vector(-1, 0) if self._fly_dir < 0 else Vector(1, 0)
        nx = self.position.x + self._fly_dir * self.speed * _DT
        ny = self._fly_y + sin(self._phase) * 8.0
        self._phase += _DT * 0.12
        self.position = Vector(nx, ny)
        facing_right = self._fly_dir >= 0
        cx = nx + self.size.x * 0.5
        cy = ny + self.size.y * 0.5
        mx = (nx + self.size.x - 2) if facing_right else (nx + 2)
        my = ny + 37

        if self._fly_cd > 0:
            self._fly_cd -= _DT

        # launch a fireball
        if not self._fly_fb[0] and self._fly_cd <= 0:
            if self.mode == "attack" and player:
                px = player.position.x + player.size.x * 0.5
                py = player.position.y + player.size.y * 0.5
                dx = px - mx
                dy = py - my
                dd = sqrt(dx * dx + dy * dy)
                if dd > 1 and _fire_arc(facing_right, px - cx, py - cy):
                    sp = 3.1
                    self._fly_fb = [True, mx, my, dx / dd * sp, dy / dd * sp]
                    self._fly_cd = 1.3
            elif self.mode == "burn" and self._burn_i < self._burn_n:
                tgt = self._nearest_flammable(cx, cy, 260, self._fly_dir)
                if tgt is None:
                    tgt = self._nearest_flammable(cx, cy, 260, 0)
                if tgt:
                    self._fly_tx, self._fly_ty = tgt
                    dx = self._fly_tx - mx
                    dy = self._fly_ty - my
                    dd = sqrt(dx * dx + dy * dy)
                    if dd > 1:
                        sp = 4.0
                        self._fly_fb = [True, mx, my, dx / dd * sp, dy / dd * sp]
                        self._fly_cd = 0.85

        # advance the fireball
        if self._fly_fb[0]:
            self._fly_fb[1] += self._fly_fb[3]
            self._fly_fb[2] += self._fly_fb[4]
            fx, fy = self._fly_fb[1], self._fly_fb[2]
            off = fx < 0 or fy < 0 or fx > lvl.size.x or fy > lvl.size.y
            if self.mode == "attack" and player:
                px = player.position.x + player.size.x * 0.5
                py = player.position.y + player.size.y * 0.5
                if (fx - px) ** 2 + (fy - py) ** 2 < 100:
                    self._hurt_player(player, 25)
                    self._fly_fb[0] = False
                elif off:
                    self._fly_fb[0] = False
            else:
                if (fx - self._fly_tx) ** 2 + (fy - self._fly_ty) ** 2 < 220:
                    self._fly_fb[0] = False
                    self._mark_burnt(self._fly_tx, self._fly_ty)
                    self._burn_i += 1
                elif off:
                    self._fly_fb[0] = False

        # Burn run: once it's torched its quota it stops firing (the fire condition gates
        # on _burn_i < _burn_n) and finishes the pass it's on, then flies off the edge —
        # cap the remaining passes to 1 so it doesn't turn back or vanish mid-map.
        if self.mode == "burn" and self._burn_n > 0 and self._burn_i >= self._burn_n and self._passes > 1:
            self._passes = 1

        # count passes; leave (undefeated) after the last one
        margin = self.size.x + 20
        if (self._fly_dir > 0 and nx > lvl.size.x + 20) or (self._fly_dir < 0 and nx < -margin):
            self._passes -= 1
            if self._passes <= 0:
                self._done = True
                self.is_visible = False
            else:
                self._fly_dir = -self._fly_dir

    def _nearest_flammable(self, x, y, max_dist, dir_x):
        best = None
        bd = max_dist * max_dist
        for (ex, ey) in self._flammables():
            if (ex, ey) in self._burnt():
                continue
            if dir_x != 0 and (ex - x) * dir_x < 20:
                continue
            d = (ex - x) ** 2 + (ey - y) ** 2
            if d < bd:
                bd = d
                best = (ex, ey)
        return best

    def _burnt(self):
        run = self.flip_world_run
        return run.burnt_icons if run is not None else ()

    def _mark_burnt(self, x, y):
        # tag the nearest flammable centre as burnt (so the colour pass can char it)
        best = None
        bd = 1e18
        for c in self._flammables():
            if c in self._burnt():
                continue
            d = (c[0] - x) ** 2 + (c[1] - y) ** 2
            if d < bd:
                bd = d
                best = c
        if best is not None:
            self._burnt().add(best)

    # ── render ───────────────────────────────────────────────────────────────
    def render(self, draw, game):
        if self.mode == "boss" and self.state == ENTITY_STATE_DEAD:
            self.is_visible = False
            return

        sx = int(self.position.x - game.position.x)
        sy = int(self.position.y - game.position.y)
        # cull if fully off-screen
        if not (sx + self.size.x < 0 or sx > game.draw.size.x or
                sy + self.size.y < 0 or sy > game.draw.size.y):
            data = _dragon_buffer(self.direction.x >= 0)  # full-colour body
            self._draw_pos.x = sx
            self._draw_pos.y = sy
            draw.image_bytearray(self._draw_pos, self.size, data)

        # fireballs (orange with a hot core)
        if self.mode == "boss":
            for fb in self._fb:
                if fb[0]:
                    self._fireball(draw, game, fb[1], fb[2])
        elif self._fly_fb[0]:
            self._fireball(draw, game, self._fly_fb[1], self._fly_fb[2])

        self.is_visible = False  # we drew it ourselves

    def _fireball(self, draw, game, wx, wy):
        px = int(wx - game.position.x)
        py = int(wy - game.position.y)
        draw.fill_circle(Vector(px, py), 4, _FB_ORANGE)  # orange
        draw.fill_circle(Vector(px, py), 2, _FB_CORE)    # hot core
