# Matrix-style falling characters screensaver
from random import randint, choice
from picoware.system.buttons import BUTTON_BACK
from picoware.system.colors import TFT_BLACK, TFT_DARKGREEN
from gc import collect

# Matrix rain columns
rain_columns = []
is_flipper = None
CHARS = "01234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!?#$%@&*[]"


class RainColumn:
    """A single column of falling characters"""

    __slots__ = ("x", "y", "speed", "length", "chars")

    def __init__(self, x: int):
        self.x = x
        self.y = randint(-20, 0)
        self.speed = randint(1, 4)
        self.length = randint(8, 20)
        self.chars = [choice(CHARS) for _ in range(self.length)]

    def update(self):
        """Update column position"""
        self.y += self.speed
        # Randomize one character in the column
        if randint(0, 10) < 3:
            idx = randint(0, self.length - 1)
            self.chars[idx] = choice(CHARS)

    def draw(self, draw_char, font_width, font_height, screen_width, screen_height):
        """Draw the column"""
        for i in range(self.length):
            char_y = self.y + (i * font_height)
            if (
                0 <= self.x
                and self.x + font_width <= screen_width
                and 0 <= char_y
                and char_y + font_height <= screen_height
            ):
                # Brightest at head, darker towards tail
                if is_flipper:
                    color = 0xFFFF  # White on Flipper
                elif i == 0:
                    color = 0x07E0  # Bright green
                elif i < 3:
                    color = 0x05C0  # Medium green
                else:
                    color = TFT_DARKGREEN
                draw_char(self.x, char_y, self.chars[i], color)

    def is_offscreen(self, screen_height) -> bool:
        """Check if column is completely off screen"""
        return self.y > screen_height


def start(view_manager) -> bool:
    """Start the app"""
    global rain_columns, is_flipper
    from picoware.system.boards import BOARD_ID, BOARD_FLIPPER_ZERO

    is_flipper = BOARD_ID == BOARD_FLIPPER_ZERO

    draw = view_manager.draw

    # Create initial columns
    rain_columns = []
    num_columns = draw.size.x // draw.len("a")
    for i in range(num_columns):
        if randint(0, 100) < 30:  # 30% chance for initial column
            rain_columns.append(RainColumn(i * draw.font_size.x))

    draw.fill_screen(TFT_BLACK)
    draw.swap()

    return True


def run(view_manager) -> None:
    """Run the app"""
    global rain_columns

    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
        return

    draw = view_manager.draw
    draw_char = draw._char
    font = draw.get_font()
    font_width = font.width
    font_height = font.height
    screen_width = draw.size.x
    screen_height = draw.size.y

    draw.fill_screen(TFT_BLACK)

    # Update and draw columns
    for i in range(len(rain_columns) - 1, -1, -1):
        col = rain_columns[i]
        col.update()
        col.draw(draw_char, font_width, font_height, screen_width, screen_height)

        # Remove offscreen columns
        if col.is_offscreen(screen_height):
            rain_columns.pop(i)

    # Spawn new columns randomly
    if randint(0, 100) < 15:  # 15% chance each frame
        x = randint(0, (draw.size.x // draw.font_size.x) - 1) * draw.font_size.x
        rain_columns.append(RainColumn(x))

    draw.swap()


def stop(view_manager) -> None:
    """Stop the app"""

    global rain_columns, is_flipper

    rain_columns = []
    is_flipper = None

    collect()
