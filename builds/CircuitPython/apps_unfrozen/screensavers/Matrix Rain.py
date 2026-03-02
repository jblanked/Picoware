# Matrix-style falling characters screensaver
from random import randint, choice
from picoware.system.buttons import BUTTON_BACK
from picoware.system.colors import TFT_BLACK, TFT_DARKGREEN
from picoware.system.vector import Vector

# Matrix rain columns
rain_columns = []
screen_size = None
font_size = None


class RainColumn:
    """A single column of falling characters"""

    def __init__(self, x: int):
        self.x = x
        self.y = randint(-20, 0)
        self.speed = randint(1, 4)
        self.length = randint(8, 20)
        self._chars = (
            "01234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!?#$%@&*[]"
        )
        self.chars = [choice(self._chars) for _ in range(self.length)]
        self.brightness = [255 - (i * 15) for i in range(self.length)]
        self.pos = Vector(0, 0)

    def __del__(self):
        self.chars = []
        self.brightness = []
        del self.pos
        self.pos = None

    def update(self):
        """Update column position"""
        self.y += self.speed
        # Randomize one character in the column
        if randint(0, 10) < 3:
            idx = randint(0, self.length - 1)
            self.chars[idx] = choice(self._chars)

    def draw(self, draw):
        """Draw the column"""
        for i in range(self.length):
            char_y = self.y + (i * font_size.y)
            if 0 <= char_y < screen_size.y:
                self.pos.x = self.x
                self.pos.y = char_y
                # Brightest at head, darker towards tail
                if i == 0:
                    color = 0x07E0  # Bright green
                elif i < 3:
                    color = 0x05C0  # Medium green
                else:
                    color = TFT_DARKGREEN
                draw.char(self.pos, self.chars[i], color)

    def is_offscreen(self) -> bool:
        """Check if column is completely off screen"""
        return self.y - (self.length * font_size.y) > screen_size.y


def start(view_manager) -> bool:
    """Start the app"""
    global rain_columns, screen_size, font_size

    draw = view_manager.draw
    screen_size = Vector(draw.size.x, draw.size.y)
    font_size = Vector(draw.font_size.x, draw.font_size.y)

    # Create initial columns
    rain_columns = []
    num_columns = screen_size.x // font_size.x
    for i in range(num_columns):
        if randint(0, 100) < 30:  # 30% chance for initial column
            rain_columns.append(RainColumn(i * font_size.x))

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

    draw.fill_screen(TFT_BLACK)

    # Update and draw columns
    for col in rain_columns[:]:
        col.update()
        col.draw(draw)

        # Remove offscreen columns
        if col.is_offscreen():
            rain_columns.remove(col)

    # Spawn new columns randomly
    if randint(0, 100) < 15:  # 15% chance each frame
        x = randint(0, (screen_size.x // font_size.x) - 1) * font_size.x
        rain_columns.append(RainColumn(x))

    draw.swap()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global rain_columns, screen_size, font_size

    rain_columns = []
    screen_size = None
    font_size = None

    collect()
