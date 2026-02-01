# Classic Pong game
from random import randint
from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_BACK
from picoware.system.colors import TFT_BLACK, TFT_WHITE, TFT_GREEN, TFT_RED
from picoware.system.vector import Vector
from micropython import const

# Game state
screen_size = None
paddle_left = None
paddle_right = None
ball = None
score_left = 0
score_right = 0
game_started = False
score_pos_left = None
score_pos_right = None

PADDLE_WIDTH = const(8)
PADDLE_HEIGHT = const(40)
PADDLE_SPEED = const(8)
BALL_SIZE = const(6)
BALL_SPEED = const(4)
AI_SPEED = const(4)


class Paddle:
    """Paddle object"""

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.width = PADDLE_WIDTH
        self.height = PADDLE_HEIGHT
        self.pos = Vector(self.x, self.y)
        self.size = Vector(self.width, self.height)

    def __del__(self):
        del self.pos
        del self.size
        self.pos = None
        self.size = None

    def move(self, dy: int):
        """Move paddle up or down"""
        self.y += dy
        # Keep within screen bounds
        if self.y < 0:
            self.y = 0
        if self.y + self.height > screen_size.y:
            self.y = screen_size.y - self.height

    def draw(self, draw, color):
        """Draw the paddle"""
        draw.fill_rectangle(self.pos, self.size, color)


class Ball:
    """Ball object"""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset ball to center with random direction"""
        self.x = screen_size.x // 2
        self.y = screen_size.y // 2
        self.vx = BALL_SPEED if randint(0, 1) else -BALL_SPEED
        self.vy = randint(-3, 3)
        self.size = BALL_SIZE

    def update(self):
        """Update ball position"""
        self.x += self.vx
        self.y += self.vy

        # Bounce off top and bottom
        if self.y <= 0 or self.y + self.size >= screen_size.y:
            self.vy = -self.vy

    def draw(self, draw):
        """Draw the ball"""
        pos = Vector(int(self.x), int(self.y))
        size = Vector(self.size, self.size)
        draw.fill_rectangle(pos, size, TFT_WHITE)

    def check_paddle_collision(self, paddle):
        """Check collision with paddle"""
        if (
            self.x < paddle.x + paddle.width
            and self.x + self.size > paddle.x
            and self.y < paddle.y + paddle.height
            and self.y + self.size > paddle.y
        ):
            # Bounce ball
            self.vx = -self.vx
            # Add some variation based on where it hit the paddle
            hit_pos = (self.y - paddle.y) / paddle.height
            self.vy = (hit_pos - 0.5) * 6
            return True
        return False


def start(view_manager) -> bool:
    """Start the app"""
    global screen_size, paddle_left, paddle_right, ball, score_left, score_right, game_started, score_pos_left, score_pos_right

    draw = view_manager.draw
    screen_size = Vector(draw.size.x, draw.size.y)

    # Create paddles
    paddle_left = Paddle(10, screen_size.y // 2 - PADDLE_HEIGHT // 2)
    paddle_right = Paddle(
        screen_size.x - 10 - PADDLE_WIDTH, screen_size.y // 2 - PADDLE_HEIGHT // 2
    )

    # Create ball
    ball = Ball()

    score_left = 0
    score_right = 0
    game_started = True

    score_pos_left = Vector(screen_size.x // 4, 10)
    score_pos_right = Vector(screen_size.x * 3 // 4, 10)

    return True


def run(view_manager) -> None:
    """Run the app"""
    global score_left, score_right, game_started

    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
        return

    draw = view_manager.draw

    # Player controls (left paddle)
    if button == BUTTON_UP:
        inp.reset()
        paddle_left.move(-PADDLE_SPEED)
    elif button == BUTTON_DOWN:
        inp.reset()
        paddle_left.move(PADDLE_SPEED)

    # Simple AI for right paddle
    if ball.y < paddle_right.y + paddle_right.height // 2:
        paddle_right.move(-AI_SPEED)
    elif ball.y > paddle_right.y + paddle_right.height // 2:
        paddle_right.move(AI_SPEED)

    # Update ball
    if game_started:
        ball.update()

        # Check paddle collisions
        ball.check_paddle_collision(paddle_left)
        ball.check_paddle_collision(paddle_right)

        # Check if ball went out of bounds
        if ball.x <= 0:
            score_right += 1
            ball.reset()
        elif ball.x >= screen_size.x:
            score_left += 1
            ball.reset()

    # Draw everything
    draw.fill_screen(TFT_BLACK)

    # Draw center line
    pos = Vector(0, 0)
    size = Vector(4, 10)
    for y in range(0, screen_size.y, 20):
        pos.x, pos.y = (screen_size.x // 2 - 2, y)
        draw.fill_rectangle(pos, size, TFT_WHITE)

    # Draw paddles
    paddle_left.draw(draw, TFT_GREEN)
    paddle_right.draw(draw, TFT_RED)

    # Draw ball
    ball.draw(draw)

    # Draw scores
    draw.text(score_pos_left, str(score_left), TFT_WHITE)
    draw.text(score_pos_right, str(score_right), TFT_WHITE)

    draw.swap()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global screen_size, paddle_left, paddle_right, ball, score_left, score_right, game_started, score_pos_left, score_pos_right

    screen_size = None
    paddle_left = None
    paddle_right = None
    ball = None
    score_left = 0
    score_right = 0
    game_started = False
    score_pos_left = None
    score_pos_right = None

    collect()
