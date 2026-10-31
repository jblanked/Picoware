# Aquarium-like Screensaver, made with Swift-1.5-Qwen3.8:27b
from random import randint, uniform
from math import sin
from time import ticks_ms, ticks_diff, sleep_ms
from picoware.system.buttons import BUTTON_BACK
from picoware.system.colors import (
    TFT_ORANGE,
    TFT_PINK,
    TFT_CYAN,
    TFT_YELLOW,
    TFT_GREEN,
    TFT_DARKGREEN,
    TFT_SKYBLUE,
)

WATER_TOP = 0x001F
WATER_1 = 0x020F
WATER_2 = 0x0513
WATER_3 = 0x0C11
SAND = 0x6B4F
FOAM = 0xE7DF
FRAME_MS = 33

fish = []
bubbles = []
last_frame = 0
screen_w = 320
screen_h = 320
sand_top = 290
view_manager = None


def make_fish():
    '''Create one random fish'''
    direction = 1 if randint(0, 1) else -1
    size = randint(6, 12)
    return {
        'x': uniform(0, screen_w),
        'y': uniform(30, sand_top - 30),
        'base_y': 0.0,
        'dir': direction,
        'speed': uniform(0.4, 1.4) * direction,
        'size': size,
        'color': randint(0, 5),
        'phase': uniform(0, 6.28),
    }


def colors_for(index):
    '''Map index to a fish color'''
    table = (
        TFT_ORANGE,
        TFT_PINK,
        TFT_CYAN,
        TFT_YELLOW,
        TFT_SKYBLUE,
        TFT_GREEN,
    )
    return table[index]


def draw_water():
    '''Draw the water gradient'''
    draw = view_manager.draw
    bands = ((WATER_TOP, 0), (WATER_1, 60), (WATER_2, 140), (WATER_3, 220))
    for color, y in bands:
        draw._fill_rectangle(0, y, screen_w, screen_h - y, color)
    draw._fill_rectangle(0, sand_top, screen_w, screen_h - sand_top, SAND)
    for x in range(0, screen_w, 8):
        draw._line(
            x, sand_top, x + 4, sand_top - 2, SAND
        )


def draw_weeds():
    '''Draw swaying seaweed'''
    draw = view_manager.draw
    for i, base_x in enumerate((18, 46, 250, 285)):
        sway = sin(ticks_ms() / 900 + i) * 6
        color = TFT_GREEN if i % 2 else TFT_DARKGREEN
        draw._line(base_x, sand_top, base_x + sway / 2, sand_top - 26, color)
        draw._line(base_x + sway / 2, sand_top - 26, base_x + sway, sand_top - 50, color)


def draw_bubbles():
    '''Draw and advance bubbles'''
    draw = view_manager.draw
    for bubble in bubbles[:]:
        bubble['y'] -= bubble['v']
        bubble['x'] += sin(bubble['y'] / 9) * 0.3
        if bubble['y'] < 4:
            bubbles.remove(bubble)
            continue
        draw._circle(int(bubble['x']), int(bubble['y']), bubble['r'], FOAM)


def draw_fish(f):
    '''Draw one fish with tail and eye'''
    draw = view_manager.draw
    x = int(f['x'])
    y = int(f['base_y'] + sin(f['phase']) * 5)
    r = f['size']
    d = f['dir']
    color = colors_for(f['color'])
    draw._fill_circle(x, y, r, color)
    draw._fill_triangle(
        x - d * r, y,
        x - d * (r * 2), y - r,
        x - d * (r * 2), y + r,
        color,
    )
    draw._fill_circle(x + d * (r + 1), y - 2, 2, 0xFFFF)
    draw._pixel(x + d * (r + 1), y - 2, 0x0000)


def update():
    '''Advance fish and bubbles'''
    for f in fish:
        f['x'] += f['speed']
        f['phase'] += 0.12 + abs(f['speed']) * 0.05
        limit = 25
        if f['x'] > screen_w + limit:
            f['x'] = -limit
        elif f['x'] < -limit:
            f['x'] = screen_w + limit
    if len(bubbles) < 20 and randint(1, 4) == 1:
        bubbles.append({
            'x': uniform(10, screen_w - 10),
            'y': sand_top - 5,
            'v': uniform(0.5, 1.2),
            'r': randint(1, 3),
        })


def start(view_manager):
    '''Start the app'''
    global fish, bubbles, last_frame, screen_w, screen_h, sand_top
    globals()['view_manager'] = view_manager
    draw = view_manager.draw
    screen_w = draw.size.x
    screen_h = draw.size.y
    sand_top = screen_h - 26
    fish = [make_fish() for _ in range(6)]
    for f in fish:
        f['base_y'] = f['y']
    bubbles = []
    last_frame = ticks_ms()
    draw_water()
    draw_weeds()
    draw.swap()
    sleep_ms(50)
    return True


def run(view_manager):
    '''Run the app'''
    global last_frame
    draw = view_manager.draw
    if view_manager.button == BUTTON_BACK:
        view_manager.back()
        return
    now = ticks_ms()
    if ticks_diff(now, last_frame) < FRAME_MS:
        return
    last_frame = now
    draw_water()
    draw_weeds()
    draw_bubbles()
    for f in fish:
        draw_fish(f)
    update()
    draw.swap()


def stop(view_manager):
    '''Stop the app'''
    from gc import collect
    fish.clear()
    bubbles.clear()
    collect()