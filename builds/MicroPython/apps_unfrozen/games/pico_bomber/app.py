"""Picoware lifecycle adapter for Pico Bomber."""

from gc import collect
from utime import ticks_add, ticks_diff, ticks_ms

from picoware.system.buttons import (
    BUTTON_BACK,
    BUTTON_CENTER,
    BUTTON_DOWN,
    BUTTON_LEFT,
    BUTTON_RIGHT,
    BUTTON_SPACE,
    BUTTON_UP,
)

from .leaderboard import Leaderboard
from .model import (
    MENU_LEADERBOARD,
    STATE_GAME_OVER,
    STATE_LEADERBOARD,
    STATE_MODE_SELECT,
    STATE_PLAYER_DYING,
    STATE_PLAYING,
    STATE_TITLE,
    GameModel,
)
from .render import Renderer


_game = None
_renderer = None
_leaderboard = None
_next_frame = 0
_score_saved = False
FRAME_MS = 50
GAME_CPU_FREQUENCY = 230000000


def start(view_manager):
    """Create a fresh Pico Bomber title screen."""
    global _game, _renderer, _leaderboard, _next_frame, _score_saved

    view_manager.freq(False, GAME_CPU_FREQUENCY)
    _game = GameModel()
    _renderer = Renderer(view_manager.draw)
    _leaderboard = Leaderboard(view_manager.storage)
    _game.leaderboard = _leaderboard.entries
    _score_saved = False
    _next_frame = ticks_ms()
    _renderer.draw_frame(_game)
    return True


def run(view_manager):
    """Handle one Picoware input/update/render cycle."""
    global _next_frame, _score_saved

    if _game is None or _renderer is None:
        return

    input_manager = view_manager.input_manager
    button = input_manager.button
    now = ticks_ms()
    changed = False

    if button == BUTTON_BACK:
        input_manager.reset()
        if _game.state == STATE_LEADERBOARD:
            _game.open_mode_menu()
            changed = True
        elif _game.state == STATE_MODE_SELECT:
            _game.state = STATE_TITLE
            changed = True
        else:
            view_manager.back()
            return
    if button == BUTTON_UP:
        if _game.state == STATE_MODE_SELECT:
            changed = _game.select_mode(-1)
        else:
            changed = _game.move_player(0, -1, now)
    elif button == BUTTON_DOWN:
        if _game.state == STATE_MODE_SELECT:
            changed = _game.select_mode(1)
        else:
            changed = _game.move_player(0, 1, now)
    elif button == BUTTON_LEFT:
        changed = _game.move_player(-1, 0, now)
    elif button == BUTTON_RIGHT:
        changed = _game.move_player(1, 0, now)
    elif button in (BUTTON_CENTER, BUTTON_SPACE):
        if _game.state in (STATE_TITLE, STATE_GAME_OVER):
            _game.open_mode_menu()
            changed = True
        elif _game.state == STATE_LEADERBOARD:
            _game.open_mode_menu()
            changed = True
        elif _game.state == STATE_MODE_SELECT:
            if _game.menu_selection == MENU_LEADERBOARD:
                _game.state = STATE_LEADERBOARD
            else:
                _game.new_game(now, _game.menu_selection)
                _score_saved = False
            changed = True
        else:
            changed = _game.place_bomb(now)

    if button >= 0:
        input_manager.reset()

    if _game.update(now):
        changed = True

    if _game.state == STATE_GAME_OVER and not _score_saved:
        _leaderboard.submit(_game.score, _game.stage, _game.mode)
        _game.leaderboard = _leaderboard.entries
        _score_saved = True
        changed = True

    animated = _game.state in (STATE_PLAYING, STATE_PLAYER_DYING)
    if changed or (animated and ticks_diff(now, _next_frame) >= 0):
        _renderer.draw_frame(_game)
        _next_frame = ticks_add(now, FRAME_MS)


def stop(view_manager):
    """Release the game state when leaving the Picoware view."""
    global _game, _renderer, _leaderboard, _next_frame, _score_saved

    _game = None
    _renderer = None
    _leaderboard = None
    _next_frame = 0
    _score_saved = False
    view_manager.freq()
    collect()
