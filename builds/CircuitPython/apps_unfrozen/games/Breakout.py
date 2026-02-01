# translated from https://github.com/lazerduck/PicoCalc_Dashboard/blob/main/breakout/breakout.py
# breakout.py - Simple Breakout clone for PicoCalc
# Controls: Left/Right arrows to move paddle, BACK to quit, Up to increase speed, Down to decrease speed
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 320

# Game constants
PADDLE_WIDTH = 50
PADDLE_HEIGHT = 8
PADDLE_Y = SCREEN_HEIGHT - 30
PADDLE_SPEED = 20

BALL_SIZE = 6
BALL_SPEED_X = 3
BALL_SPEED_Y = -3
GAME_SPEED = 1.0  # Multiplier for overall game speed (increase for faster)

BRICK_WIDTH = 38
BRICK_HEIGHT = 12
BRICK_ROWS = 5
BRICK_COLS = 8
BRICK_PADDING = 2
BRICK_OFFSET_TOP = 40


# Game state
class Game:
    """Class to hold game state and logic"""

    def __init__(self):
        """Initialize game state"""
        from picoware.system.colors import (
            TFT_RED,
            TFT_VIOLET,
            TFT_YELLOW,
            TFT_GREEN,
            TFT_CYAN,
        )

        self.paddle_x = SCREEN_WIDTH // 2 - PADDLE_WIDTH // 2
        self.ball_x = SCREEN_WIDTH // 2
        self.ball_y = SCREEN_HEIGHT // 2
        self.ball_dx = BALL_SPEED_X * GAME_SPEED
        self.ball_dy = BALL_SPEED_Y * GAME_SPEED
        self.score = 0
        self.lives = 3
        self.running = True
        self.game_over = False
        self.won = False

        # Store previous positions for erasing
        self.prev_paddle_x = self.paddle_x
        self.prev_ball_x = self.ball_x
        self.prev_ball_y = self.ball_y
        self.prev_score = 0
        self.prev_lives = 3

        # Track if we need full redraw
        self.needs_full_redraw = True

        # Create bricks - list of (x, y, color, active)
        self.bricks = []
        colors = [TFT_RED, TFT_VIOLET, TFT_YELLOW, TFT_GREEN, TFT_CYAN]

        for row in range(BRICK_ROWS):
            for col in range(BRICK_COLS):
                x = col * (BRICK_WIDTH + BRICK_PADDING) + 10
                y = row * (BRICK_HEIGHT + BRICK_PADDING) + BRICK_OFFSET_TOP
                color = colors[row % len(colors)]
                self.bricks.append([x, y, color, True])  # x, y, color, active

    def __del__(self):
        """Cleanup"""
        self.bricks.clear()

    def check_input(self, key: int) -> bool:
        """input check"""
        from picoware.system.buttons import (
            BUTTON_LEFT,
            BUTTON_RIGHT,
            BUTTON_DOWN,
            BUTTON_UP,
        )

        # Arrow keys: 0xAE = left, 0xAF = right (per firmware font table)
        moved: bool = False
        if key == BUTTON_LEFT:  # Left arrow
            self.paddle_x -= PADDLE_SPEED
            moved = True
        elif key == BUTTON_RIGHT:  # Right arrow
            self.paddle_x += PADDLE_SPEED
            moved = True
        elif key == BUTTON_UP:  # Up arrow - increase speed
            if abs(self.ball_dx) < 10:
                self.ball_dx *= 1.1
            if abs(self.ball_dy) < 10:
                self.ball_dy *= 1.1
        elif key == BUTTON_DOWN:  # Down arrow - decrease speed
            if abs(self.ball_dx) > 1:
                self.ball_dx *= 0.9
            if abs(self.ball_dy) > 1:
                self.ball_dy *= 0.9

        # Keep paddle on screen
        if moved:
            self.paddle_x = max(0, self.paddle_x)
            self.paddle_x = min(self.paddle_x, SCREEN_WIDTH - PADDLE_WIDTH)
            return True

        return False

    def update(self):
        """Update game state"""
        if self.game_over or self.won:
            return

        # Move ball
        self.ball_x += self.ball_dx
        self.ball_y += self.ball_dy

        # Ball collision with walls
        if self.ball_x <= 0 or self.ball_x >= SCREEN_WIDTH - BALL_SIZE:
            self.ball_dx = -self.ball_dx
            self.ball_x = max(0, min(SCREEN_WIDTH - BALL_SIZE, self.ball_x))

        if self.ball_y <= 0:
            self.ball_dy = -self.ball_dy
            self.ball_y = 0

        # Ball falls off bottom - lose life
        if self.ball_y >= SCREEN_HEIGHT:
            self.lives -= 1
            self.needs_full_redraw = True  # Redraw everything when life lost
            if self.lives <= 0:
                self.game_over = True
            else:
                # Reset ball
                self.ball_x = SCREEN_WIDTH // 2
                self.ball_y = SCREEN_HEIGHT // 2
                self.ball_dy = -abs(self.ball_dy)

        # Ball collision with paddle
        if (
            self.ball_y + BALL_SIZE >= PADDLE_Y
            and self.ball_y < PADDLE_Y + PADDLE_HEIGHT
            and self.ball_x + BALL_SIZE >= self.paddle_x
            and self.ball_x <= self.paddle_x + PADDLE_WIDTH
        ):

            self.ball_dy = -abs(self.ball_dy)  # Always bounce up
            self.ball_y = PADDLE_Y - BALL_SIZE  # Place ball on top of paddle

            # Add spin based on where ball hits paddle
            hit_pos = (self.ball_x + BALL_SIZE / 2 - self.paddle_x) / PADDLE_WIDTH
            self.ball_dx = int((hit_pos - 0.5) * 6)  # -3 to +3

        # Ball collision with bricks
        for brick in self.bricks:
            if not brick[3]:  # Skip inactive bricks
                continue

            bx, by, color, active = brick

            # Simple AABB collision
            if (
                self.ball_x + BALL_SIZE >= bx
                and self.ball_x <= bx + BRICK_WIDTH
                and self.ball_y + BALL_SIZE >= by
                and self.ball_y <= by + BRICK_HEIGHT
            ):

                # Deactivate brick
                brick[3] = False
                self.score += 10

                # Mark that brick needs to be erased
                self.needs_full_redraw = True

                # Bounce ball
                self.ball_dy = -self.ball_dy

                break  # Only hit one brick per frame

        # Check win condition
        active_bricks = sum(1 for b in self.bricks if b[3])
        if active_bricks == 0:
            self.won = True

    def draw(self, draw):
        """Draw everything with partial updates to reduce flicker"""
        from picoware.system.colors import (
            TFT_BLACK,
            TFT_WHITE,
            TFT_RED,
            TFT_GREEN,
            TFT_YELLOW,
        )
        from picoware.system.vector import Vector

        # Full redraw needed for bricks being destroyed or game state changes
        if self.needs_full_redraw:
            # Clear screen
            draw.fill_screen(TFT_BLACK)

            # Draw all bricks
            brick_pos = Vector(0, 0)
            brick_size = Vector(BRICK_WIDTH, BRICK_HEIGHT)
            for brick in self.bricks:
                if brick[3]:  # Only draw active bricks
                    brick_pos.x = brick[0]
                    brick_pos.y = brick[1]
                    draw.fill_rectangle(brick_pos, brick_size, brick[2])

            # Draw score and lives
            draw.text(Vector(8, 8), f"Score:{self.score}", TFT_WHITE)
            draw.text(Vector(SCREEN_WIDTH - 80, 8), f"Lives:{self.lives}", TFT_WHITE)

            self.needs_full_redraw = False
        else:
            # Partial update - only redraw moving elements

            # Erase previous paddle position if it moved
            paddle_pos = Vector(int(self.prev_paddle_x), PADDLE_Y)
            paddle_size = Vector(PADDLE_WIDTH, PADDLE_HEIGHT)
            if self.prev_paddle_x != self.paddle_x:
                draw.fill_rectangle(
                    paddle_pos,
                    paddle_size,
                    TFT_BLACK,
                )

            # Erase previous ball position
            ball_pos = Vector(int(self.prev_ball_x), int(self.prev_ball_y))
            ball_size = Vector(BALL_SIZE, BALL_SIZE)
            draw.fill_rectangle(
                ball_pos,
                ball_size,
                TFT_BLACK,
            )

            # Update score if changed
            if self.prev_score != self.score:
                draw.fill_rectangle(
                    Vector(8, 8), Vector(80, 8), TFT_BLACK
                )  # Clear old score
                draw.text(Vector(8, 8), f"Score:{self.score}", TFT_WHITE)
                self.prev_score = self.score

            # Update lives if changed
            if self.prev_lives != self.lives:
                draw.fill_rectangle(
                    Vector(SCREEN_WIDTH - 80, 8), Vector(80, 8), TFT_BLACK
                )  # Clear old lives
                draw.text(
                    Vector(SCREEN_WIDTH - 80, 8), f"Lives:{self.lives}", TFT_WHITE
                )
                self.prev_lives = self.lives

        # Draw paddle at new position
        draw.fill_rectangle(
            Vector(int(self.paddle_x), PADDLE_Y),
            Vector(PADDLE_WIDTH, PADDLE_HEIGHT),
            TFT_WHITE,
        )

        # Draw ball at new position
        draw.fill_rectangle(
            Vector(int(self.ball_x), int(self.ball_y)),
            Vector(BALL_SIZE, BALL_SIZE),
            TFT_WHITE,
        )

        # Store positions for next frame
        self.prev_paddle_x = self.paddle_x
        self.prev_ball_x = self.ball_x
        self.prev_ball_y = self.ball_y

        # Draw game over / win message
        if self.game_over:
            self.draw_centered_text(draw, "GAME OVER", 140, TFT_RED)
            self.draw_centered_text(draw, "Press BACK to quit", 160, TFT_WHITE)
            self.running = False
        elif self.won:
            self.draw_centered_text(draw, "YOU WIN!", 140, TFT_GREEN)
            self.draw_centered_text(draw, f"Score: {self.score}", 160, TFT_YELLOW)
            self.draw_centered_text(draw, "Press BACK to quit", 180, TFT_WHITE)
            self.running = False

        draw.swap()

    def draw_centered_text(self, draw, text, y, color):
        """Draw text centered on screen"""
        from picoware.system.vector import Vector

        x = (SCREEN_WIDTH - len(text) * draw.font_size.x) // 2
        draw.text(Vector(x, y), text, color)


game = None


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.system.colors import TFT_BLACK, TFT_CYAN, TFT_WHITE, TFT_YELLOW
    from picoware.system.buttons import BUTTON_BACK, BUTTON_NONE

    global game

    game = Game()

    draw = view_manager.draw

    # Title screen
    draw.fill_screen(TFT_BLACK)
    game.draw_centered_text(draw, "BREAKOUT", 100, TFT_CYAN)
    game.draw_centered_text(draw, "Use Arrow Keys", 140, TFT_WHITE)
    game.draw_centered_text(draw, "Press any key to start", 180, TFT_YELLOW)
    draw.swap()

    # Wait for any key using keyboard.readinto
    inp = view_manager.input_manager
    while True:
        button = inp.button
        if button == BUTTON_BACK:
            inp.reset()
            return False
        if button != BUTTON_NONE:
            inp.reset()
            break

    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK

    inp = view_manager.input_manager
    button = inp.button

    if any([button == BUTTON_BACK, game is None, not game.running]):
        inp.reset()
        view_manager.back()
        if game is not None:
            game.running = False
        return

    if game:
        # Check input
        if game.check_input(button):
            inp.reset()

        # Update game state
        game.update()

        # Draw everything
        game.draw(view_manager.draw)


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global game

    if game is not None:
        del game
        game = None

    collect()
