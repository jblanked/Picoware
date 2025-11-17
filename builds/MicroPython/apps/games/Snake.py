# translated from https://github.com/lazerduck/PicoCalc_Dashboard/blob/main/snake/snake.py

# Display setup
SCREEN_WIDTH = 0
SCREEN_HEIGHT = 0

# Game constants
GRID_SIZE = 0  # Size of each grid cell
GRID_WIDTH = 0
GRID_HEIGHT = 0  # Leave space for score
OFFSET_Y = 0  # Offset for score display


class Snake:
    """Class representing the snake"""

    def __init__(self):
        # Start in the middle
        start_x = GRID_WIDTH // 2
        start_y = GRID_HEIGHT // 2
        self.body = [(start_x, start_y), (start_x - 1, start_y), (start_x - 2, start_y)]
        self.direction = (1, 0)  # Moving right
        self.next_direction = (1, 0)
        self.growing = False

    def __del__(self):
        del self.body
        self.body = None
        del self.direction
        self.direction = None
        del self.next_direction
        self.next_direction = None

    def update(self):
        """Update snake position. Returns False if collision occurs."""
        # Update direction (prevent 180-degree turns)
        if (
            self.next_direction[0] != -self.direction[0]
            or self.next_direction[1] != -self.direction[1]
        ):
            self.direction = self.next_direction

        # Calculate new head position
        head = self.body[0]
        new_head = (head[0] + self.direction[0], head[1] + self.direction[1])

        # Check collision with walls
        if (
            new_head[0] < 0
            or new_head[0] >= GRID_WIDTH
            or new_head[1] < 0
            or new_head[1] >= GRID_HEIGHT
        ):
            return False

        # Check collision with self
        if new_head in self.body:
            return False

        # Add new head
        self.body.insert(0, new_head)

        # Remove tail unless growing
        if not self.growing:
            self.body.pop()
        else:
            self.growing = False

        return True

    def grow(self):
        """Make the snake grow on the next update"""
        self.growing = True

    def set_direction(self, direction):
        """Set the next direction of the snake"""
        self.next_direction = direction


class Game:
    """Class representing the Snake game""" ""

    def __init__(self, display):
        self.display = display
        self.snake = Snake()
        self.food = self.spawn_food()
        self.score = 0
        self.game_over = False

    def __del__(self):
        del self.snake
        self.snake = None
        del self.food
        self.food = None

    def spawn_food(self):
        """Spawn food at a random position not occupied by the snake"""
        from random import randint

        while True:
            x = randint(0, GRID_WIDTH - 1)
            y = randint(0, GRID_HEIGHT - 1)
            if (x, y) not in self.snake.body:
                return (x, y)

    def update(self):
        """Update game state"""
        if self.game_over:
            return

        # Move snake
        if not self.snake.update():
            self.game_over = True
            return

        # Check if snake ate food
        if self.snake.body[0] == self.food:
            self.snake.grow()
            self.score += 10
            self.food = self.spawn_food()

    def draw(self):
        """Draw the game state on the display"""
        from picoware.system.vector import Vector
        from picoware.system.colors import TFT_BLACK, TFT_GREEN, TFT_RED, TFT_WHITE

        self.display.fill_screen(TFT_BLACK)
        # Draw boundary wall
        wall_color = 1  # Blue
        x0 = 0
        y0 = OFFSET_Y
        x1 = GRID_WIDTH * GRID_SIZE
        y1 = OFFSET_Y + GRID_HEIGHT * GRID_SIZE
        # Top and bottom
        self.display.fill_rectangle(Vector(x0, y0), Vector(x1, y0 + 2), wall_color)
        self.display.fill_rectangle(Vector(x0, y1 - 2), Vector(x1, y1), wall_color)
        # Left and right
        self.display.fill_rectangle(Vector(x0, y0), Vector(x0 + 2, y1), wall_color)
        self.display.fill_rectangle(Vector(x1 - 2, y0), Vector(x1, y1), wall_color)

        # Draw score
        self.display.text(
            Vector(int(SCREEN_WIDTH * 0.03125), int(SCREEN_HEIGHT * 0.03125)),
            f"Score: {self.score}",
            TFT_WHITE,
        )
        self.display.text(
            Vector(
                SCREEN_WIDTH - int(SCREEN_WIDTH * 0.21875), int(SCREEN_HEIGHT * 0.03125)
            ),
            "BACK: Quit",
            TFT_WHITE,
        )

        _size_vector = Vector(GRID_SIZE - 1, GRID_SIZE - 1)

        # Draw snake
        snake_vector = Vector(0, 0)
        for segment in self.snake.body:
            snake_vector.x = segment[0] * GRID_SIZE
            snake_vector.y = segment[1] * GRID_SIZE + OFFSET_Y
            self.display.fill_rectangle(snake_vector, _size_vector, TFT_GREEN)

        # Draw food
        food_vector = Vector(
            self.food[0] * GRID_SIZE, self.food[1] * GRID_SIZE + OFFSET_Y
        )
        self.display.fill_rectangle(food_vector, _size_vector, TFT_RED)


def main(view_manager):
    """Main function to run the Snake game"""
    import time
    from picoware.system.buttons import (
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_RIGHT,
        BUTTON_BACK,
    )

    draw = view_manager.draw
    inp = view_manager.input_manager

    game = Game(draw)

    # Game loop
    last_update = time.ticks_ms()
    update_interval = 150  # Move every 150ms

    running = True
    while running:
        current_time = time.ticks_ms()
        _button = inp.button

        # Handle input
        if _button == BUTTON_BACK or game.game_over:
            inp.reset()
            running = False
            view_manager.back()
        elif _button == BUTTON_UP:
            inp.reset()
            game.snake.set_direction((0, -1))
        elif _button == BUTTON_DOWN:
            inp.reset()
            game.snake.set_direction((0, 1))
        elif _button == BUTTON_RIGHT:
            inp.reset()
            game.snake.set_direction((1, 0))
        elif _button == BUTTON_LEFT:
            inp.reset()
            game.snake.set_direction((-1, 0))

        # Update game at fixed interval
        if time.ticks_diff(current_time, last_update) >= update_interval:
            game.update()
            game.draw()
            draw.swap()
            last_update = current_time

            # Speed up as score increases
            update_interval = max(80, 150 - (game.score // 50) * 10)


def start(view_manager) -> bool:
    """Start the app"""

    global SCREEN_WIDTH, SCREEN_HEIGHT, GRID_SIZE, GRID_WIDTH, GRID_HEIGHT, OFFSET_Y

    draw = view_manager.get_draw()

    # Display setup
    SCREEN_WIDTH = draw.size.x
    SCREEN_HEIGHT = draw.size.y

    # Size of each grid cell
    GRID_SIZE = int(SCREEN_WIDTH * 0.05)

    GRID_WIDTH = SCREEN_WIDTH // GRID_SIZE

    # Leave space for score
    GRID_HEIGHT = int((SCREEN_HEIGHT - (SCREEN_WIDTH * 0.125)) // GRID_SIZE)

    # Offset for score display
    OFFSET_Y = int(SCREEN_WIDTH * 0.09375)

    return True


def run(view_manager) -> None:
    """Run the app"""
    main(view_manager)


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    collect()
