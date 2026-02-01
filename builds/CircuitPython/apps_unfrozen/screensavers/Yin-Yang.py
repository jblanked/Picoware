# original from https://github.com/seltee/bloody_yin_yang/tree/main
# Authors: Deriv'era
# BSD License 2.0 Deriv'era(C)2026

from picoware.system.vector import Vector
from picoware.system.colors import TFT_BLACK
from picoware.system.buttons import BUTTON_BACK
from micropython import const

try:
    from urandom import getrandbits
except ImportError:
    from random import getrandbits

# Constants
FLOAT_SHIFT = const(8)
FIELD_WIDTH = const(10)
FIELD_HEIGHT = const(10)
FIELD_CELL_SIZE = const(32)
YIN = const(0)
YANG = const(1)
BALL_RADIUS = const(16)

# Global state
_yin_yang_data = None
_ball_black = None
_ball_white = None
_speed = 256
_adder = 4


class Ball:
    """Ball object with position and direction"""

    __slots__ = ("type", "pos_x", "pos_y", "dir_x", "dir_y")

    def __init__(self, ball_type, pos_x, pos_y, dir_x, dir_y):
        self.type = ball_type
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.dir_x = dir_x
        self.dir_y = dir_y


def i_sqrt(n):
    """Integer square root using Newton's method"""
    if n == 0:
        return 0

    root = 0
    bit = 1 << 30

    while bit > n:
        bit >>= 2

    while bit != 0:
        if n >= root + bit:
            n -= root + bit
            root = (root >> 1) + bit
        else:
            root >>= 1
        bit >>= 2

    return root


def i_sqrt_fixed(fn):
    """Square root for fixed-point numbers"""
    return i_sqrt(fn << FLOAT_SHIFT)


def i_normalize(f_vector_x, f_vector_y):
    """Normalize a vector (returns tuple of normalized x, y)"""
    f_dist2 = ((f_vector_x * f_vector_x) >> FLOAT_SHIFT) + (
        (f_vector_y * f_vector_y) >> FLOAT_SHIFT
    )
    f_dist = i_sqrt_fixed(f_dist2)
    if f_dist <= 0:
        f_dist = 1
    f_out_x = (f_vector_x << FLOAT_SHIFT) // f_dist
    f_out_y = (f_vector_y << FLOAT_SHIFT) // f_dist
    return f_out_x, f_out_y


def i_dot(f_vector_ax, f_vector_ay, f_vector_bx, f_vector_by):
    """Dot product of two vectors"""
    return ((f_vector_ax * f_vector_bx) >> FLOAT_SHIFT) + (
        (f_vector_ay * f_vector_by) >> FLOAT_SHIFT
    )


def get_random_none_zero_direction():
    """Get a random non-zero direction"""
    random = 0
    while random == 0:
        random = (getrandbits(8) % 256) - 128
    return random


def process_ball(ball, yin_yang_data, f_speed_factor, screen_width, screen_height):
    """Process ball physics and collisions"""
    ball.pos_x += (ball.dir_x * f_speed_factor) >> FLOAT_SHIFT
    ball.pos_y += (ball.dir_y * f_speed_factor) >> FLOAT_SHIFT
    screen_pos_x = ball.pos_x >> FLOAT_SHIFT
    screen_pos_y = ball.pos_y >> FLOAT_SHIFT

    screen_pos_block_x = screen_pos_x // FIELD_CELL_SIZE
    screen_pos_block_y = screen_pos_y // FIELD_CELL_SIZE
    check_start_x = max(screen_pos_block_x - 1, 0)
    check_end_x = min(screen_pos_block_x + 1, FIELD_WIDTH - 1)
    check_start_y = max(screen_pos_block_y - 1, 0)
    check_end_y = min(screen_pos_block_y + 1, FIELD_HEIGHT - 1)
    hit = False

    # Control quad hits
    for iy in range(check_start_y, check_end_y + 1):
        if hit:
            break
        box_center_y = iy * FIELD_CELL_SIZE + FIELD_CELL_SIZE // 2
        diff_y = screen_pos_y - box_center_y
        point_y = box_center_y + max(
            min(diff_y, FIELD_CELL_SIZE // 2), -FIELD_CELL_SIZE // 2
        )
        diff_point_y = screen_pos_y - point_y

        for ix in range(check_start_x, check_end_x + 1):
            if hit:
                break
            if yin_yang_data[iy * FIELD_WIDTH + ix] == ball.type:
                box_center_x = ix * FIELD_CELL_SIZE + FIELD_CELL_SIZE // 2
                diff_x = screen_pos_x - box_center_x
                point_x = box_center_x + max(
                    min(diff_x, FIELD_CELL_SIZE // 2), -FIELD_CELL_SIZE // 2
                )
                diff_point_x = screen_pos_x - point_x

                dist2 = diff_point_x * diff_point_x + diff_point_y * diff_point_y
                if dist2 < BALL_RADIUS * BALL_RADIUS:
                    dist = i_sqrt(dist2)
                    if dist <= 0:
                        dist = 1

                    # Classic bounce with 1.0 restitution
                    f_penetration = (BALL_RADIUS << FLOAT_SHIFT) - (dist << FLOAT_SHIFT)
                    f_normal_x = (diff_point_x << FLOAT_SHIFT) // dist
                    f_normal_y = (diff_point_y << FLOAT_SHIFT) // dist
                    f_shift_x = (f_normal_x * f_penetration) >> FLOAT_SHIFT
                    f_shift_y = (f_normal_y * f_penetration) >> FLOAT_SHIFT
                    ball.pos_x += f_shift_x
                    ball.pos_y += f_shift_y

                    # v - n * (2.0f * dot(v, n))
                    ball.dir_x -= (
                        f_normal_x
                        * (2 * i_dot(ball.dir_x, ball.dir_y, f_normal_x, f_normal_y))
                    ) >> FLOAT_SHIFT
                    ball.dir_y -= (
                        f_normal_y
                        * (2 * i_dot(ball.dir_x, ball.dir_y, f_normal_x, f_normal_y))
                    ) >> FLOAT_SHIFT
                    ball.dir_x += get_random_none_zero_direction() // 64
                    ball.dir_y += get_random_none_zero_direction() // 64
                    ball.dir_x, ball.dir_y = i_normalize(ball.dir_x, ball.dir_y)

                    if ball.type == YIN:
                        yin_yang_data[iy * FIELD_WIDTH + ix] = YANG
                    else:
                        yin_yang_data[iy * FIELD_WIDTH + ix] = YIN
                    hit = True

    screen_pos_x = ball.pos_x >> FLOAT_SHIFT
    screen_pos_y = ball.pos_y >> FLOAT_SHIFT

    # Control screen bounds
    if screen_pos_x - BALL_RADIUS < 0 and ball.dir_x < 0:
        ball.pos_x = BALL_RADIUS << FLOAT_SHIFT
        ball.dir_x = -ball.dir_x
        ball.dir_x += get_random_none_zero_direction() // 64
        ball.dir_y += get_random_none_zero_direction() // 64
        ball.dir_x, ball.dir_y = i_normalize(ball.dir_x, ball.dir_y)

    if screen_pos_x + BALL_RADIUS >= screen_width and ball.dir_x > 0:
        ball.pos_x = (screen_width - BALL_RADIUS) << FLOAT_SHIFT
        ball.dir_x = -ball.dir_x
        ball.dir_x += get_random_none_zero_direction() // 64
        ball.dir_y += get_random_none_zero_direction() // 64
        ball.dir_x, ball.dir_y = i_normalize(ball.dir_x, ball.dir_y)

    if screen_pos_y - BALL_RADIUS < 0 and ball.dir_y < 0:
        ball.pos_y = BALL_RADIUS << FLOAT_SHIFT
        ball.dir_y = -ball.dir_y
        ball.dir_x += get_random_none_zero_direction() // 64
        ball.dir_y += get_random_none_zero_direction() // 64
        ball.dir_x, ball.dir_y = i_normalize(ball.dir_x, ball.dir_y)

    if screen_pos_y + BALL_RADIUS >= screen_height and ball.dir_y > 0:
        ball.pos_y = (screen_height - BALL_RADIUS) << FLOAT_SHIFT
        ball.dir_y = -ball.dir_y
        ball.dir_x += get_random_none_zero_direction() // 128
        ball.dir_y += get_random_none_zero_direction() // 128
        ball.dir_x, ball.dir_y = i_normalize(ball.dir_x, ball.dir_y)


def start(view_manager) -> bool:
    """Start the app"""
    global _yin_yang_data, _ball_black, _ball_white, _speed, _adder

    # Initialize yin-yang data
    _yin_yang_data = bytearray(FIELD_WIDTH * FIELD_HEIGHT)
    for i in range(FIELD_WIDTH * FIELD_HEIGHT):
        _yin_yang_data[i] = YIN

    # Initialize right half as YANG
    for x in range(FIELD_WIDTH // 2, FIELD_WIDTH):
        for y in range(FIELD_HEIGHT):
            _yin_yang_data[y * FIELD_WIDTH + x] = YANG

    # Initialize black ball (YIN)
    dir_x = get_random_none_zero_direction()
    dir_y = get_random_none_zero_direction()
    dir_x, dir_y = i_normalize(dir_x, dir_y)
    _ball_black = Ball(
        YIN,
        (((FIELD_WIDTH // 4) * 3) * FIELD_CELL_SIZE) * (1 << FLOAT_SHIFT),
        (((FIELD_HEIGHT * FIELD_CELL_SIZE) // 2)) * (1 << FLOAT_SHIFT),
        dir_x,
        dir_y,
    )

    # Initialize white ball (YANG)
    dir_x = get_random_none_zero_direction()
    dir_y = get_random_none_zero_direction()
    dir_x, dir_y = i_normalize(dir_x, dir_y)
    _ball_white = Ball(
        YANG,
        ((FIELD_WIDTH // 4) * FIELD_CELL_SIZE) * (1 << FLOAT_SHIFT),
        ((FIELD_HEIGHT * FIELD_CELL_SIZE) // 2) * (1 << FLOAT_SHIFT),
        dir_x,
        dir_y,
    )

    _speed = 256
    _adder = 4

    view_manager.freq(True)  # set to lower frequency

    return True


def run(view_manager) -> None:
    """Run the app"""
    global _speed, _adder

    inp = view_manager.input_manager
    button = inp.button
    draw = view_manager.draw

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
        return

    # Get screen dimensions
    screen_width = draw.size.x
    screen_height = draw.size.y

    # Logic processing
    if _speed > 100000:
        _adder = -4
    if _speed < 256:
        _adder = 4
    _speed += _adder

    color_minus = max(min((_speed - 10000) >> 10, 15), 0)
    color_white = 0b111111111111 - ((color_minus << 8) + (color_minus << 4))

    repeats = _speed // 1024
    for _ in range(repeats):
        process_ball(_ball_white, _yin_yang_data, 1024, screen_width, screen_height)
        process_ball(_ball_black, _yin_yang_data, 1024, screen_width, screen_height)

    left = _speed - repeats * 1024
    if left > 0:
        process_ball(_ball_white, _yin_yang_data, left, screen_width, screen_height)
        process_ball(_ball_black, _yin_yang_data, left, screen_width, screen_height)

    # Rendering
    draw.clear(color=TFT_BLACK)

    pos_vec = Vector(0, 0)
    size_vec = Vector(FIELD_CELL_SIZE, FIELD_CELL_SIZE)
    for x in range(FIELD_WIDTH):
        for y in range(FIELD_HEIGHT):
            if _yin_yang_data[y * FIELD_WIDTH + x] == YANG:
                pos_vec.x, pos_vec.y = x * FIELD_CELL_SIZE, y * FIELD_CELL_SIZE
                draw.fill_rectangle(
                    pos_vec,
                    size_vec,
                    color_white,
                )

    # Draw balls
    pos_vec.x, pos_vec.y = (
        _ball_black.pos_x >> FLOAT_SHIFT,
        _ball_black.pos_y >> FLOAT_SHIFT,
    )
    draw.fill_circle(
        pos_vec,
        BALL_RADIUS,
        TFT_BLACK,
    )
    pos_vec.x, pos_vec.y = (
        _ball_white.pos_x >> FLOAT_SHIFT,
        _ball_white.pos_y >> FLOAT_SHIFT,
    )
    draw.fill_circle(
        pos_vec,
        BALL_RADIUS,
        color_white,
    )

    draw.swap()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _yin_yang_data, _ball_black, _ball_white, _speed, _adder

    _yin_yang_data = None
    _ball_black = None
    _ball_white = None
    _speed = 256
    _adder = 4

    view_manager.freq()  # set to default frequency

    # Initial cleanup
    collect()
