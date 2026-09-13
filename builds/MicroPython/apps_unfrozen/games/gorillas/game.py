"""Engine-backed Gorillas artillery game."""

from math import cos, pi, sin

from micropython import const
from picoware.engine.engine import GameEngine
from picoware.engine.entity import (
    ENTITY_TYPE_ICON,
    ENTITY_TYPE_NPC,
    ENTITY_TYPE_PLAYER,
    Entity,
)
from picoware.engine.game import Game
from picoware.engine.level import Level
from picoware.system.buttons import (
    BUTTON_BACK,
    BUTTON_CENTER,
    BUTTON_DOWN,
    BUTTON_LEFT,
    BUTTON_RIGHT,
    BUTTON_UP,
)
from picoware.system.colors import (
    TFT_BLACK,
    TFT_BLUE,
    TFT_CYAN,
    TFT_GREEN,
    TFT_ORANGE,
    TFT_RED,
    TFT_WHITE,
    TFT_YELLOW,
)
from picoware.system.vector import Vector

from .assets import BANANA, EXPLOSION, GORILLA_LEFT, GORILLA_RIGHT

PHASE_AIMING = const(0)
PHASE_FLYING = const(1)
PHASE_EXPLODING = const(2)
PHASE_GAME_OVER = const(3)

_engine = None
_game = None
_level = None
_state = None


def __banana_collision(entity, other, game) -> None:
    """Resolve a banana collision with a building or gorilla."""
    if _state is None or _state["phase"] != PHASE_FLYING:
        return
    if other is None or other.type not in (ENTITY_TYPE_NPC, ENTITY_TYPE_PLAYER):
        return

    __resolve_shot(other.type == ENTITY_TYPE_PLAYER)


def __banana_update(entity, game) -> None:
    """Advance the banana projectile using simple gravity and wind."""
    if _state is None or _state["phase"] != PHASE_FLYING:
        entity.is_visible = False
        return

    scale = _state["physics_scale"]
    _state["banana_vx"] += _state["wind"] * 0.004 * scale
    _state["banana_vy"] += 0.42 * scale
    _state["banana_x"] += _state["banana_vx"]
    _state["banana_y"] += _state["banana_vy"]

    entity.position = Vector(_state["banana_x"], _state["banana_y"])
    entity.is_visible = True

    if (
        _state["banana_x"] < -16
        or _state["banana_x"] > _state["width"] + 16
        or _state["banana_y"] > _state["height"]
    ):
        __resolve_shot(False)


def __center_text(draw, text, y, color) -> None:
    """Draw text centered on the current display."""
    x = max(0, (int(draw.size.x) - draw.len(text)) // 2)
    draw.text(Vector(x, y), text, color)


def __create_entity(name, entity_type, position, size, update=None, render=None, collision=None):
    """Create an engine entity with optional Python callbacks."""
    return Entity(
        name,
        entity_type,
        position,
        size,
        None,
        None,
        None,
        None,
        None,
        update,
        render,
        collision,
    )


def __create_scene(view_manager) -> None:
    """Create the engine game, level, entities, and deterministic skyline."""
    global _engine, _game, _level, _state

    draw = view_manager.draw
    width = int(draw.size.x)
    height = int(draw.size.y)
    minimum = min(width, height)
    font_height = max(6, int(draw.font_size.y))
    footer_y = max(font_height + 8, height - font_height - 2)
    baseline = max(font_height + 20, footer_y - 8)
    play_top = font_height + 12
    pixel_scale = max(1, minimum // 160)
    physics_scale = max(0.2, minimum / 320.0)
    compact = width < 180

    _state = {
        "baseline": baseline,
        "banana": None,
        "banana_vx": 0.0,
        "banana_vy": 0.0,
        "banana_x": -32.0,
        "banana_y": -32.0,
        "compact": compact,
        "explosion_frames": 0,
        "explosion_x": 0.0,
        "explosion_y": 0.0,
        "font_height": font_height,
        "gorillas": [],
        "height": height,
        "message": "Aim and fire!",
        "phase": PHASE_AIMING,
        "physics_scale": physics_scale,
        "pixel_scale": pixel_scale,
        "power": 68,
        "round": 1,
        "turn": 0,
        "width": width,
        "wind": 0,
        "angle": 45,
        "buildings": [],
    }

    _game = Game(
        "Gorillas",
        Vector(width, height),
        draw,
        view_manager.input_manager,
        TFT_WHITE,
        TFT_BLACK,
        None,
        None,
        None,
    )
    _level = Level("City", Vector(width, height), _game, None, None)

    banana = __create_entity(
        "banana",
        ENTITY_TYPE_ICON,
        Vector(-32, -32),
        Vector(max(2, pixel_scale * 5), max(2, pixel_scale * 5)),
        __banana_update,
        None,
        __banana_collision,
    )
    _state["banana"] = banana
    _level.entity_add(banana)

    count = max(3, min(10, width // 24))
    gap = max(1, width // 160)
    margin = max(2, width // 40)
    building_width = max(8, (width - (2 * margin) - ((count - 1) * gap)) // count)

    for index in range(count):
        building_x = margin + index * (building_width + gap)
        building_height = max(
            6,
            min(
                max(7, baseline - play_top - 8),
                10 + ((index * 17 + width + height) % max(11, baseline - play_top - 5)),
            ),
        )
        building = __create_entity(
            "building_{}".format(index),
            ENTITY_TYPE_NPC,
            Vector(building_x, baseline - building_height),
            Vector(building_width, building_height),
            None,
            __draw_building,
            None,
        )
        _state["buildings"].append(building)
        _level.entity_add(building)

    gorilla_width = max(6, pixel_scale * 12)
    gorilla_height = max(6, pixel_scale * 12)
    left_building = _state["buildings"][0]
    right_building = _state["buildings"][-1]
    for index, building in enumerate((left_building, right_building)):
        x = int(building.position.x + (building.size.x - gorilla_width) / 2)
        y = int(building.position.y - gorilla_height + 1)
        gorilla = __create_entity(
            "gorilla_{}".format(index),
            ENTITY_TYPE_PLAYER,
            Vector(x, y),
            Vector(gorilla_width, gorilla_height),
            None,
            __draw_gorilla,
            None,
        )
        gorilla.is_player = True
        _state["gorillas"].append(gorilla)
        _level.entity_add(gorilla)

    hud = __create_entity(
        "hud",
        ENTITY_TYPE_ICON,
        Vector(0, 0),
        Vector(0, 0),
        None,
        __draw_hud,
        None,
    )
    _level.entity_add(hud)
    _game.level_add(_level)
    _engine = GameEngine(_game, 30)


def __draw_building(entity, draw, game) -> None:
    """Render one skyline building from the generated scene data."""
    if not entity.is_visible:
        return

    index = int(entity.name.split("_")[-1])
    colors = (TFT_BLUE, TFT_CYAN, TFT_GREEN, TFT_RED, TFT_ORANGE)
    color = TFT_WHITE if _state["compact"] else colors[index % len(colors)]
    position = entity.position
    size = entity.size
    draw.fill_rectangle(
        Vector(int(position.x), int(position.y)),
        Vector(int(size.x), int(size.y)),
        color,
    )

    window_color = TFT_BLACK
    window_size = max(1, _state["pixel_scale"])
    window_gap = max(2, window_size * 3)
    window_y = int(position.y + window_gap)
    while window_y < _state["baseline"] - window_size:
        window_x = int(position.x + window_gap)
        while window_x < position.x + size.x - window_size:
            draw.fill_rectangle(
                Vector(window_x, window_y),
                Vector(window_size, window_size),
                window_color,
            )
            window_x += window_gap + window_size
        window_y += window_gap + window_size


def __draw_gorilla(entity, draw, game) -> None:
    """Render a pixel-art gorilla entity."""
    pattern = GORILLA_LEFT if entity.name.endswith("_0") else GORILLA_RIGHT
    color = TFT_WHITE if _state["compact"] else (TFT_GREEN if entity.name.endswith("_0") else TFT_RED)
    __draw_pattern(draw, pattern, entity.position.x, entity.position.y, _state["pixel_scale"], color)


def __draw_hud(entity, draw, game) -> None:
    """Render the HUD, projectile, explosion, and control instructions."""
    if _state is None:
        return

    width = int(draw.size.x)
    height = int(draw.size.y)
    font_height = _state["font_height"]
    title = "GORILLAS"
    __center_text(draw, title, 2, TFT_WHITE)

    if _state["phase"] == PHASE_GAME_OVER:
        status = _state["message"]
    elif _state["phase"] == PHASE_FLYING:
        status = "BANANA IN FLIGHT"
    elif _state["phase"] == PHASE_EXPLODING:
        status = _state["message"]
    else:
        side = "P1" if _state["turn"] == 0 else "P2"
        status = "{} A{} P{} W{:+d}".format(
            side,
            _state["angle"],
            _state["power"],
            _state["wind"],
        )
    __center_text(draw, status, font_height + 3, TFT_YELLOW)

    if _state["phase"] == PHASE_FLYING:
        __draw_pattern(
            draw,
            BANANA,
            _state["banana_x"] - (_state["pixel_scale"] * 3),
            _state["banana_y"] - (_state["pixel_scale"] * 2),
            _state["pixel_scale"],
            TFT_WHITE if _state["compact"] else TFT_YELLOW,
        )
    elif _state["phase"] == PHASE_EXPLODING:
        explosion_color = TFT_WHITE if _state["compact"] else TFT_ORANGE
        radius = max(2, _state["pixel_scale"] * 4)
        draw.fill_circle(
            Vector(int(_state["explosion_x"]), int(_state["explosion_y"])),
            radius,
            explosion_color,
        )
        __draw_pattern(
            draw,
            EXPLOSION,
            _state["explosion_x"] - (_state["pixel_scale"] * 4),
            _state["explosion_y"] - (_state["pixel_scale"] * 3),
            _state["pixel_scale"],
            explosion_color,
        )

    draw.line(
        Vector(0, _state["baseline"]),
        Vector(width, _state["baseline"]),
        TFT_WHITE if _state["compact"] else TFT_CYAN,
    )

    if _state["phase"] == PHASE_GAME_OVER:
        footer = "CENTER: New game | BACK: Exit"
    elif _state["compact"]:
        footer = "L/R Ang U/D Pow C Fire B Exit"
    else:
        footer = "LEFT/RIGHT: Angle  UP/DOWN: Power  CENTER: Fire  BACK: Exit"
    if draw.len(footer) > width:
        footer = "L/R Angle U/D Power C Fire B Exit"
    draw.text(Vector(max(0, (width - draw.len(footer)) // 2), height - font_height - 2), footer)


def __draw_pattern(draw, pattern, x, y, scale, color) -> None:
    """Draw a transparent pixel-art pattern using engine primitives."""
    scale = max(1, int(scale))
    for row, line in enumerate(pattern):
        for column, pixel in enumerate(line):
            if pixel == "1":
                draw.fill_rectangle(
                    Vector(int(x + column * scale), int(y + row * scale)),
                    Vector(scale, scale),
                    color,
                )


def __finish_turn() -> None:
    """Advance to the next player or show the winner after an explosion."""
    if _state["hit_player"]:
        winner = "P2 WINS" if _state["turn"] == 0 else "P1 WINS"
        _state["message"] = winner
        _state["phase"] = PHASE_GAME_OVER
        return

    _state["turn"] = 1 - _state["turn"]
    _state["round"] += 1
    _state["wind"] = ((_state["wind"] * 3) + _state["round"] + _state["turn"]) % 11 - 5
    _state["phase"] = PHASE_AIMING
    _state["message"] = "Aim and fire!"


def __reset_round() -> None:
    """Reset the match while retaining the generated skyline."""
    _state["angle"] = 45
    _state["banana_x"] = -32.0
    _state["banana_y"] = -32.0
    _state["explosion_frames"] = 0
    _state["hit_player"] = False
    _state["message"] = "Aim and fire!"
    _state["phase"] = PHASE_AIMING
    _state["power"] = 68
    _state["round"] = 1
    _state["turn"] = 0
    _state["wind"] = 0


def __resolve_shot(hit_player) -> None:
    """Start the short explosion phase for a hit or missed throw."""
    if _state["phase"] != PHASE_FLYING:
        return

    _state["explosion_x"] = _state["banana_x"]
    _state["explosion_y"] = _state["banana_y"]
    _state["explosion_frames"] = 12
    _state["hit_player"] = hit_player
    _state["message"] = "HIT!" if hit_player else "BOOM!"
    _state["phase"] = PHASE_EXPLODING
    _state["banana"].is_visible = False


def __set_message(message) -> None:
    """Set the transient game message."""
    if _state is not None:
        _state["message"] = message


def __throw() -> None:
    """Launch a banana for the active player."""
    if _state["phase"] != PHASE_AIMING:
        return

    gorilla = _state["gorillas"][_state["turn"]]
    radians = _state["angle"] * pi / 180.0
    direction = 1 if _state["turn"] == 0 else -1
    velocity = _state["power"] * 0.11 * _state["physics_scale"]
    _state["banana_x"] = gorilla.position.x + gorilla.size.x / 2
    _state["banana_y"] = gorilla.position.y
    _state["banana_vx"] = cos(radians) * velocity * direction
    _state["banana_vy"] = -sin(radians) * velocity
    _state["banana"].position = Vector(_state["banana_x"], _state["banana_y"])
    _state["banana"].is_visible = True
    _state["phase"] = PHASE_FLYING


def __update_aim(button) -> None:
    """Adjust angle or power from the directional controls."""
    if button == BUTTON_LEFT:
        _state["angle"] = max(15, _state["angle"] - 2)
    elif button == BUTTON_RIGHT:
        _state["angle"] = min(80, _state["angle"] + 2)
    elif button == BUTTON_UP:
        _state["power"] = min(100, _state["power"] + 4)
    elif button == BUTTON_DOWN:
        _state["power"] = max(20, _state["power"] - 4)


def run(view_manager) -> None:
    """Run one Gorillas input and engine frame."""
    if _engine is None or _state is None:
        view_manager.back()
        return

    button = view_manager.button
    if button == BUTTON_BACK:
        view_manager.back()
        return

    if _state["phase"] == PHASE_GAME_OVER:
        if button == BUTTON_CENTER:
            __reset_round()
    elif _state["phase"] == PHASE_AIMING:
        if button == BUTTON_CENTER:
            __throw()
        elif button in (BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP, BUTTON_DOWN):
            __update_aim(button)

    if _state["phase"] == PHASE_EXPLODING:
        _state["explosion_frames"] -= 1
        if _state["explosion_frames"] <= 0:
            __finish_turn()

    _engine.run_async(False)


def start(view_manager) -> bool:
    """Start the Gorillas engine game."""
    if _engine is not None:
        return True

    try:
        __create_scene(view_manager)
        _engine.run_async(False)
        return True
    except Exception:
        stop(view_manager)
        return False


def stop(view_manager) -> None:
    """Stop the Gorillas engine game and release its native objects."""
    global _engine, _game, _level, _state

    if _game is not None:
        try:
            _game.stop()
        except Exception:
            pass
    if _engine is not None:
        del _engine
    if _game is not None:
        del _game
    _engine = None
    _game = None
    _level = None
    _state = None
