# Space Invaders style game
from random import randint
from picoware.system.buttons import (
    BUTTON_LEFT,
    BUTTON_RIGHT,
    BUTTON_CENTER,
    BUTTON_BACK,
)
from picoware.system.colors import TFT_BLACK, TFT_WHITE, TFT_GREEN, TFT_RED, TFT_YELLOW
from picoware.system.vector import Vector

# Game state
screen_size = None
player_x = 0
bullets = []
enemies = []
enemy_bullets = []
score = 0
lives = 3
game_over = False
enemy_direction = 1
enemy_move_counter = 0

PLAYER_WIDTH = 12
PLAYER_HEIGHT = 8
BULLET_WIDTH = 2
BULLET_HEIGHT = 6
ENEMY_WIDTH = 10
ENEMY_HEIGHT = 8
ENEMY_ROWS = 4
ENEMY_COLS = 8
ENEMY_SPACING = 20


class Bullet:
    """Bullet object"""

    def __init__(self, x: int, y: int, vy: int):
        self.x = x
        self.y = y
        self.vy = vy
        self.active = True
        self.pos = Vector(int(self.x), int(self.y))
        self.size = Vector(BULLET_WIDTH, BULLET_HEIGHT)

    def __del__(self):
        del self.pos
        del self.size
        self.pos = None
        self.size = None

    def update(self):
        """Update bullet position"""
        self.y += self.vy
        if self.y < 0 or self.y > screen_size.y:
            self.active = False

    def draw(self, draw, color):
        """Draw the bullet"""
        if self.active:
            self.pos.x, self.pos.y = int(self.x), int(self.y)
            draw.fill_rectangle(self.pos, self.size, color)


class Enemy:
    """Enemy alien object"""

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.active = True
        self.pos = Vector(int(self.x), int(self.y))
        self.size = Vector(ENEMY_WIDTH, ENEMY_HEIGHT)
        self.eye_pos = Vector(int(self.x) + 2, int(self.y) + 2)

    def __del__(self):
        del self.pos
        del self.size
        del self.eye_pos
        self.pos = None
        self.size = None
        self.eye_pos = None

    def draw(self, draw):
        """Draw the enemy"""
        if self.active:
            self.pos.x, self.pos.y = int(self.x), int(self.y)
            draw.fill_rectangle(self.pos, self.size, TFT_GREEN)
            # Draw eyes
            self.eye_pos.x, self.eye_pos.y = int(self.x) + 2, int(self.y) + 2
            draw.pixel(self.eye_pos, TFT_BLACK)
            self.eye_pos.x = int(self.x) + ENEMY_WIDTH - 3
            draw.pixel(self.eye_pos, TFT_BLACK)


def start(view_manager) -> bool:
    """Start the app"""
    global screen_size, player_x, bullets, enemies, enemy_bullets, score, lives, game_over
    global enemy_direction, enemy_move_counter

    draw = view_manager.draw
    screen_size = draw.size

    player_x = screen_size.x // 2 - PLAYER_WIDTH // 2
    bullets = []
    enemy_bullets = []
    score = 0
    lives = 3
    game_over = False
    enemy_direction = 1
    enemy_move_counter = 0

    # Create enemies
    enemies = []
    start_x = 40
    start_y = 40
    for row in range(ENEMY_ROWS):
        for col in range(ENEMY_COLS):
            x = start_x + col * ENEMY_SPACING
            y = start_y + row * (ENEMY_HEIGHT + 10)
            enemies.append(Enemy(x, y))

    return True


def run(view_manager) -> None:
    """Run the app"""
    global player_x, bullets, enemies, enemy_bullets, score, lives, game_over
    global enemy_direction, enemy_move_counter

    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
        return

    draw = view_manager.draw

    if not game_over:
        # Player controls
        if button == BUTTON_LEFT:
            inp.reset()
            player_x -= 5
            player_x = max(player_x, 0)
        elif button == BUTTON_RIGHT:
            inp.reset()
            player_x += 5
            player_x = min(player_x, screen_size.x - PLAYER_WIDTH)
        elif button == BUTTON_CENTER:
            inp.reset()
            # Fire bullet
            if len(bullets) < 3:  # Limit bullets on screen
                bullet_x = player_x + PLAYER_WIDTH // 2 - BULLET_WIDTH // 2
                bullet_y = screen_size.y - PLAYER_HEIGHT - BULLET_HEIGHT - 5
                bullets.append(Bullet(bullet_x, bullet_y, -6))
            inp.reset()

        # Update bullets
        for bullet in bullets[:]:
            bullet.update()
            if not bullet.active:
                bullets.remove(bullet)

        # Update enemy bullets
        for bullet in enemy_bullets[:]:
            bullet.update()
            if not bullet.active:
                enemy_bullets.remove(bullet)

        # Move enemies
        enemy_move_counter += 1
        if enemy_move_counter > 20:
            enemy_move_counter = 0
            should_descend = False

            # Check if any enemy hit the edge
            for enemy in enemies:
                if enemy.active:
                    if (enemy.x <= 0 and enemy_direction < 0) or (
                        enemy.x >= screen_size.x - ENEMY_WIDTH and enemy_direction > 0
                    ):
                        should_descend = True
                        enemy_direction = -enemy_direction
                        break

            # Move all enemies
            for enemy in enemies:
                if enemy.active:
                    if should_descend:
                        enemy.y += 10
                    else:
                        enemy.x += enemy_direction * 5

        # Enemies randomly shoot
        if randint(0, 100) < 2 and len(enemy_bullets) < 5:
            active_enemies = [e for e in enemies if e.active]
            if active_enemies:
                shooter = active_enemies[randint(0, len(active_enemies) - 1)]
                bullet_x = int(shooter.x) + ENEMY_WIDTH // 2
                bullet_y = int(shooter.y) + ENEMY_HEIGHT
                enemy_bullets.append(Bullet(bullet_x, bullet_y, 4))

        # Check bullet collisions with enemies
        for bullet in bullets[:]:
            for enemy in enemies:
                if enemy.active and bullet.active:
                    if (
                        bullet.x < enemy.x + ENEMY_WIDTH
                        and bullet.x + BULLET_WIDTH > enemy.x
                        and bullet.y < enemy.y + ENEMY_HEIGHT
                        and bullet.y + BULLET_HEIGHT > enemy.y
                    ):
                        enemy.active = False
                        bullet.active = False
                        score += 10
                        break

        # Check enemy bullet collisions with player
        player_y = screen_size.y - PLAYER_HEIGHT - 5
        for bullet in enemy_bullets[:]:
            if bullet.active:
                if (
                    bullet.x < player_x + PLAYER_WIDTH
                    and bullet.x + BULLET_WIDTH > player_x
                    and bullet.y < player_y + PLAYER_HEIGHT
                    and bullet.y + BULLET_HEIGHT > player_y
                ):
                    bullet.active = False
                    lives -= 1
                    if lives <= 0:
                        game_over = True

        # Check if all enemies defeated
        if all(not e.active for e in enemies):
            game_over = True

        # Check if enemies reached bottom
        for enemy in enemies:
            if enemy.active and enemy.y > screen_size.y - 50:
                game_over = True

    # Draw everything
    draw.fill_screen(TFT_BLACK)

    if not game_over:
        # Draw player
        player_pos = Vector(player_x, screen_size.y - PLAYER_HEIGHT - 5)
        player_size = Vector(PLAYER_WIDTH, PLAYER_HEIGHT)
        draw.fill_rectangle(player_pos, player_size, TFT_WHITE)

        # Draw bullets
        for bullet in bullets:
            bullet.draw(draw, TFT_YELLOW)

        # Draw enemy bullets
        for bullet in enemy_bullets:
            bullet.draw(draw, TFT_RED)

        # Draw enemies
        for enemy in enemies:
            enemy.draw(draw)

        # Draw score and lives
        score_pos = Vector(5, 5)
        draw.text(score_pos, f"Score:{score}", TFT_WHITE)
        lives_pos = Vector(5, 20)
        draw.text(lives_pos, f"Lives:{lives}", TFT_WHITE)
    else:
        # Game over screen
        msg = "YOU WIN!" if all(not e.active for e in enemies) else "GAME OVER"
        msg_pos = Vector(screen_size.x // 2 - 40, screen_size.y // 2 - 20)
        draw.text(msg_pos, msg, TFT_WHITE)
        score_pos = Vector(screen_size.x // 2 - 40, screen_size.y // 2)
        draw.text(score_pos, f"Score:{score}", TFT_WHITE)

    draw.swap()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global screen_size, player_x, bullets, enemies, enemy_bullets, score, lives, game_over
    global enemy_direction, enemy_move_counter

    screen_size = None
    player_x = 0
    bullets = []
    enemies = []
    enemy_bullets = []
    score = 0
    lives = 3
    game_over = False
    enemy_direction = 1
    enemy_move_counter = 0

    collect()
