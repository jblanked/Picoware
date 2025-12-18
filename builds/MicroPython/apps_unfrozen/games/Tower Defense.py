# translated from https://github.com/lazerduck/PicoCalc_Dashboard/blob/main/tower_defense.py
# tower_defense.py - Tower Defense game for PicoCalc
# Controls: Arrow keys to move cursor, ENTER to place tower/cycle tower type, Q to quit
from micropython import const

# Tower types
TOWER_BASIC = const(0)
TOWER_FAST = const(1)
TOWER_SPLASH = const(2)

# Tower properties: (cost, damage, fire_rate, range, name)
TOWER_PROPS = {
    TOWER_BASIC: (50, 20, 30, 2.5, "Basic"),
    TOWER_FAST: (40, 8, 10, 2.0, "Fast"),
    TOWER_SPLASH: (80, 15, 40, 2.0, "Splash"),
}

# Mob properties
MOB_HP_BASE = const(30)
MOB_SPEED_BASE = const(0.5)  # cells per update
MOB_REWARD = const(15)


class Mob:
    """Class representing a mob"""

    def __init__(self, wave_num, path):
        self.path = path
        self.path_idx = 0
        self.hp = MOB_HP_BASE + wave_num * 10
        self.max_hp = self.hp
        self.speed = MOB_SPEED_BASE + wave_num * 0.05
        self.reward = MOB_REWARD + wave_num * 5
        # Position on path (fractional)
        self.progress = 0.0
        self.alive = True
        self.reached_end = False

    def get_position(self):
        """Get current grid position"""
        if self.path_idx >= len(self.path):
            return self.path[-1]
        return self.path[self.path_idx]

    def update(self):
        """Move along the path"""
        if not self.alive:
            return

        self.progress += self.speed
        while self.progress >= 1.0 and self.path_idx < len(self.path) - 1:
            self.progress -= 1.0
            self.path_idx += 1

        if self.path_idx >= len(self.path) - 1 and self.progress >= 1.0:
            self.reached_end = True
            self.alive = False

    def take_damage(self, damage):
        """Apply damage to mob"""
        self.hp -= damage
        if self.hp <= 0:
            self.alive = False
            return True
        return False


class Tower:
    """Class representing a tower"""

    def __init__(self, x, y, tower_type):
        self.x = x
        self.y = y
        self.type = tower_type
        cost, damage, fire_rate, range_val, name = TOWER_PROPS[tower_type]
        self.damage = damage
        self.fire_rate = fire_rate
        self.range = range_val
        self.name = name
        self.cooldown = 0

    def update(self):
        """Update tower cooldown"""
        if self.cooldown > 0:
            self.cooldown -= 1

    def can_fire(self):
        """Check if tower can fire"""
        return self.cooldown == 0

    def fire(self, target):
        """Fire at target"""
        self.cooldown = self.fire_rate
        return self.damage

    def in_range(self, target_x, target_y):
        """Check if target is in range"""
        dx = target_x - self.x
        dy = target_y - self.y
        dist = (dx * dx + dy * dy) ** 0.5
        return dist <= self.range


class Game:
    """Class representing the Tower Defense game"""

    def __init__(self, width=320, height=320):
        from picoware.system.vector import Vector

        # Game constants
        self.ten_x = width // 32
        self.ten_y = height // 32
        self.twenty_x = self.ten_x * 2
        self.twenty_y = self.ten_y * 2
        self.grid_size = self.twenty_x
        self.grid_width = width // self.grid_size
        self.grid_height = (height - self.twenty_y) // self.grid_size
        self.space_text_vec = Vector(self.ten_x * 9, 2)
        self.game_over_text_vec = Vector(self.ten_x * 10, self.ten_y * 15)
        self.score_text_vec = Vector(self.ten_x * 11, self.ten_y * 17)
        self.you_win_text_vec = Vector(self.ten_x * 11, self.ten_y * 15)
        self.tower_size = Vector(6, 6)

        # Create path for mobs (snake pattern)
        self.path = self.create_path()

        # Game state
        self.money = 100
        self.lives = 20
        self.wave = 0
        self.score = 0

        # Game objects
        self.towers = []
        self.mobs = []
        self.projectiles = []

        # UI state
        self.cursor_x = 5
        self.cursor_y = 5
        self.selected_tower_type = TOWER_BASIC
        self.game_over = False
        self.won = False

        # Wave management
        self.wave_active = False
        self.mobs_spawned = 0
        self.mobs_to_spawn = 0
        self.spawn_timer = 0

        # Create occupied grid for tower placement
        self.occupied = [[False] * self.grid_width for _ in range(self.grid_height)]
        for x, y in self.path:
            self.occupied[y][x] = True

    def __del__(self):
        """Cleanup"""
        del self.towers
        self.towers = None
        del self.mobs
        self.mobs = None
        del self.projectiles
        self.projectiles = None
        del self.occupied
        self.occupied = None
        del self.path
        self.path = None
        del self.space_text_vec
        self.space_text_vec = None
        del self.game_over_text_vec
        self.game_over_text_vec = None
        del self.score_text_vec
        self.score_text_vec = None
        del self.you_win_text_vec
        self.you_win_text_vec = None
        del self.tower_size
        self.tower_size = None

    def create_path(self):
        """Create a snake-like path for mobs"""
        path = []
        # Start from left edge
        x, y = 0, 2
        path.append((x, y))

        # Move right
        for _ in range(12):
            x += 1
            path.append((x, y))

        # Move down
        for _ in range(3):
            y += 1
            path.append((x, y))

        # Move left
        for _ in range(10):
            x -= 1
            path.append((x, y))

        # Move down
        for _ in range(3):
            y += 1
            path.append((x, y))

        # Move right to exit
        for _ in range(13):
            x += 1
            path.append((x, y))

        return path

    def start_wave(self):
        """Start a new wave"""
        if self.wave_active:
            return

        self.wave += 1
        self.wave_active = True
        self.mobs_to_spawn = 5 + self.wave * 3
        self.mobs_spawned = 0
        self.spawn_timer = 0

    def spawn_mob(self):
        """Spawn a new mob"""
        mob = Mob(self.wave, self.path)
        self.mobs.append(mob)
        self.mobs_spawned += 1

    def update(self):
        """Update game state"""
        if self.game_over or self.won:
            return

        # Check for wave completion
        if not self.wave_active and len(self.mobs) == 0:
            if self.wave >= 10:
                self.won = True
                return

        # Wave spawning
        if self.wave_active:
            if self.mobs_spawned < self.mobs_to_spawn:
                self.spawn_timer += 1
                if self.spawn_timer >= 30:  # Spawn every 30 frames
                    self.spawn_mob()
                    self.spawn_timer = 0
            elif len(self.mobs) == 0:
                self.wave_active = False

        # Update towers
        for tower in self.towers:
            tower.update()

            # Find target and fire
            if tower.can_fire():
                target = None
                for mob in self.mobs:
                    if mob.alive:
                        mx, my = mob.get_position()
                        if tower.in_range(mx, my):
                            target = mob
                            break

                if target:
                    damage = tower.fire(target)

                    # Apply damage
                    if tower.type == TOWER_SPLASH:
                        # Splash damage to nearby mobs
                        tx, ty = target.get_position()
                        for mob in self.mobs:
                            if mob.alive:
                                mx, my = mob.get_position()
                                dx = mx - tx
                                dy = my - ty
                                dist = (dx * dx + dy * dy) ** 0.5
                                if dist <= 1.5:
                                    if mob.take_damage(damage):
                                        self.money += mob.reward
                                        self.score += mob.reward
                    else:
                        # Single target damage
                        if target.take_damage(damage):
                            self.money += target.reward
                            self.score += target.reward

        # Update mobs
        for mob in self.mobs[:]:
            mob.update()
            if mob.reached_end:
                self.lives -= 1
                self.mobs.remove(mob)
                if self.lives <= 0:
                    self.game_over = True
            elif not mob.alive:
                self.mobs.remove(mob)

    def place_tower(self, x, y, tower_type):
        """Try to place a tower at (x, y)"""
        # Check if valid position
        if x < 0 or x >= self.grid_width or y < 0 or y >= self.grid_height:
            return False

        if self.occupied[y][x]:
            return False

        # Check if can afford
        cost = TOWER_PROPS[tower_type][0]
        if self.money < cost:
            return False

        # Place tower
        tower = Tower(x, y, tower_type)
        self.towers.append(tower)
        self.occupied[y][x] = True
        self.money -= cost
        return True

    def handle_input(self, key: int) -> bool:
        """Handle keyboard input"""
        from picoware.system.buttons import (
            BUTTON_UP,
            BUTTON_DOWN,
            BUTTON_LEFT,
            BUTTON_RIGHT,
            BUTTON_CENTER,
            BUTTON_TAB,
            BUTTON_SPACE,
        )

        if key == BUTTON_UP:  # A - Up
            self.cursor_y = max(0, self.cursor_y - 1)
        elif key == BUTTON_DOWN:  # B - Down
            self.cursor_y = min(self.grid_height - 1, self.cursor_y + 1)
        elif key == BUTTON_RIGHT:  # C - Right
            self.cursor_x = min(self.grid_width - 1, self.cursor_x + 1)
        elif key == BUTTON_LEFT:  # D - Left
            self.cursor_x = max(0, self.cursor_x - 1)
        elif key == BUTTON_CENTER:  # Enter
            self.place_tower(self.cursor_x, self.cursor_y, self.selected_tower_type)
        elif key == BUTTON_TAB:  # Tab - cycle tower type
            self.selected_tower_type = (self.selected_tower_type + 1) % 3
        elif key == BUTTON_SPACE:  # Space - start wave
            self.start_wave()
        else:
            return False  # Unhandled key
        return True  # Key handled

    def draw(self, fb):
        """Draw the game"""
        from picoware.system.vector import Vector
        from picoware.system.colors import (
            TFT_BLACK,
            TFT_BLUE,
            TFT_RED,
            TFT_GREEN,
            TFT_CYAN,
            TFT_VIOLET,
            TFT_YELLOW,
            TFT_WHITE,
        )

        fb.fill_screen(TFT_BLACK)

        # Draw path
        rec_pos = Vector(0, self.twenty_y)
        rec_size = Vector(self.grid_size, self.grid_size)
        for x, y in self.path:
            rec_pos.x = x * self.grid_size
            rec_pos.y = y * self.grid_size + self.twenty_y
            fb.fill_rectangle(rec_pos, rec_size, TFT_YELLOW)

        # Draw towers
        tow_pos = Vector(0, 0)
        for tower in self.towers:
            tow_pos.x = tower.x * self.grid_size + self.grid_size // 2 - 3
            tow_pos.y = (
                tower.y * self.grid_size + self.twenty_y + self.grid_size // 2 - 3
            )
            if tower.type == TOWER_BASIC:
                fb.fill_rectangle(tow_pos, self.tower_size, TFT_BLUE)
            elif tower.type == TOWER_FAST:
                fb.fill_rectangle(tow_pos, self.tower_size, TFT_GREEN)
            elif tower.type == TOWER_SPLASH:
                fb.fill_rectangle(tow_pos, self.tower_size, TFT_VIOLET)
        # Draw mobs
        mob_vec = Vector(0, 0)
        health_vec = Vector(0, 0)
        health_vec_size = Vector(0, 2)
        for mob in self.mobs:
            if mob.alive:
                mx, my = mob.get_position()
                mob_vec.x = mx * self.grid_size + self.grid_size // 2 - 3
                mob_vec.y = (
                    my * self.grid_size + self.twenty_y + self.grid_size // 2 - 3
                )
                fb.fill_rectangle(mob_vec, self.tower_size, TFT_RED)

                # HP bar
                hp_pct = mob.hp / mob.max_hp
                bar_w = int(self.grid_size * 0.8 * hp_pct)
                if bar_w > 0:
                    health_vec.x = mx * self.grid_size + 2
                    health_vec.y = my * self.grid_size + self.twenty_y + 2
                    health_vec_size.x = bar_w
                    fb.fill_rectangle(health_vec, health_vec_size, TFT_GREEN)

        # Draw cursor
        cursor_vec = Vector(
            self.cursor_x * self.grid_size,
            self.cursor_y * self.grid_size + self.twenty_y,
        )
        fb.rect(cursor_vec, rec_size, TFT_WHITE)

        # Draw UI
        cost = TOWER_PROPS[self.selected_tower_type][0]
        name = TOWER_PROPS[self.selected_tower_type][4]

        ui_text = "W:{} $:{} L:{}".format(self.wave, self.money, self.lives)
        fb.text(Vector(2, 2), ui_text, TFT_WHITE)

        # Draw tower info
        tower_info = "[{}:${}] TAB:Switch".format(name, cost)
        fb.text(Vector(2, 12), tower_info, TFT_CYAN)

        # Draw instructions
        if not self.wave_active and len(self.mobs) == 0:
            fb.text(self.space_text_vec, "SPACE: Start Wave", TFT_YELLOW)
        # Game over / won
        if self.game_over:
            fb.text(self.game_over_text_vec, "GAME OVER!", TFT_RED)
            fb.text(
                self.score_text_vec,
                "Score: {}".format(self.score),
                TFT_WHITE,
            )
        elif self.won:
            fb.text(self.you_win_text_vec, "YOU WIN!", TFT_GREEN)
            fb.text(
                self.score_text_vec,
                "Score: {}".format(self.score),
                TFT_WHITE,
            )

        fb.swap()


game = None


def start(view_manager) -> bool:
    """Start the app"""
    global game

    game = Game()

    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK

    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
        return

    if game:
        # Handle input
        if game.handle_input(button):
            inp.reset()

        # Update game
        game.update()

        # Draw
        game.draw(view_manager.draw)


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global game

    if game is not None:
        del game
        game = None

    collect()
