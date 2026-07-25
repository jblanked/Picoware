"""Picoware lifecycle adapter for Pico Bomber."""

from gc import collect
from utime import ticks_add, ticks_diff, ticks_ms

from picoware.system.buttons import (
    BUTTON_BACK,
    BUTTON_BACKSPACE,
    BUTTON_CENTER,
    BUTTON_DELETE,
    BUTTON_DOWN,
    BUTTON_ENTER,
    BUTTON_LEFT,
    BUTTON_RIGHT,
    BUTTON_SPACE,
    BUTTON_UP,
)

from .leaderboard import DEFAULT_NAME, MAX_NAME_LENGTH, Leaderboard
from .model import (
    MENU_LEADERBOARD,
    STATE_GAME_OVER,
    STATE_LEADERBOARD,
    STATE_MODE_SELECT,
    STATE_NAME_ENTRY,
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
_frequency_changed = False
_mode_start_pending = False
FRAME_MS = 50
GAME_CPU_FREQUENCY = 230000000


def _thread_idle(view_manager):
    """Return whether changing the global CPU clock is currently safe."""
    thread_manager = getattr(view_manager, "thread_manager", None)
    return thread_manager is None or thread_manager.thread is None


def _log_mode_start_error(view_manager, phase, error):
    """Record the failing cold-start phase without replacing the exception."""
    try:
        view_manager.log(
            "[Pico Bomber] mode-start %s: %r" % (phase, error),
            2,
        )
    except Exception:
        pass


def _submit_name(name):
    """Save the finished score and return to the game-over screen."""
    global _score_saved

    clean_name = Leaderboard.clean_name(name)
    _leaderboard.submit(
        _game.score,
        _game.stage,
        _game.mode,
        clean_name,
    )
    _game.player_name = clean_name
    _game.leaderboard = _leaderboard.entries
    _game.state = STATE_GAME_OVER
    _score_saved = True


def _handle_name_input(input_manager, button):
    """Edit a short arcade name using the physical keyboard."""
    if button == BUTTON_BACK:
        _submit_name(DEFAULT_NAME)
        return True
    if button in (BUTTON_CENTER, BUTTON_ENTER):
        _submit_name(_game.player_name)
        return True
    if button in (BUTTON_BACKSPACE, BUTTON_DELETE):
        if _game.player_name:
            _game.player_name = _game.player_name[:-1]
            return True
        return False
    if len(_game.player_name) >= MAX_NAME_LENGTH:
        return False

    char = input_manager.button_to_char(button).upper()
    if len(char) == 1 and (
        "A" <= char <= "Z"
        or "0" <= char <= "9"
        or char in (" ", "-", "_")
    ):
        _game.player_name += char
        return True
    return False


def start(view_manager):
    """Create a fresh Pico Bomber title screen."""
    global _game, _renderer, _leaderboard, _next_frame, _score_saved
    global _frequency_changed, _mode_start_pending

    _frequency_changed = False
    _mode_start_pending = False
    if _thread_idle(view_manager):
        view_manager.freq(False, GAME_CPU_FREQUENCY)
        _frequency_changed = True
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
    global _next_frame, _score_saved, _mode_start_pending

    if _game is None or _renderer is None:
        return

    input_manager = view_manager.input_manager
    button = view_manager.button
    now = ticks_ms()
    changed = False

    if _game.state == STATE_NAME_ENTRY:
        changed = _handle_name_input(input_manager, button)
        if button >= 0:
            input_manager.reset()
        if changed:
            _renderer.draw_frame(_game)
        return

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
                _mode_start_pending = True
                try:
                    _game.new_game(now, _game.menu_selection)
                except Exception as error:
                    _log_mode_start_error(view_manager, "stage-build", error)
                    _mode_start_pending = False
                    raise
                _score_saved = False
            changed = True
        else:
            changed = _game.place_bomb(now)

    if button >= 0:
        input_manager.reset()

    try:
        updated = _game.update(now)
    except Exception as error:
        if _mode_start_pending:
            _log_mode_start_error(view_manager, "first-update", error)
            _mode_start_pending = False
        raise
    if updated:
        changed = True

    if _game.state == STATE_GAME_OVER and not _score_saved:
        if _leaderboard.qualifies(_game.score):
            _game.player_name = ""
            _game.state = STATE_NAME_ENTRY
        else:
            _score_saved = True
        changed = True

    animated = _game.state in (STATE_PLAYING, STATE_PLAYER_DYING)
    if changed or (animated and ticks_diff(now, _next_frame) >= 0):
        try:
            _renderer.draw_frame(_game)
        except Exception as error:
            if _mode_start_pending:
                _log_mode_start_error(view_manager, "first-render", error)
                _mode_start_pending = False
            raise
        _mode_start_pending = False
        _next_frame = ticks_add(now, FRAME_MS)


def stop(view_manager):
    """Release the game state when leaving the Picoware view."""
    global _game, _renderer, _leaderboard, _next_frame, _score_saved
    global _frequency_changed, _mode_start_pending

    _game = None
    _renderer = None
    _leaderboard = None
    _next_frame = 0
    _score_saved = False
    _mode_start_pending = False
    if _frequency_changed and _thread_idle(view_manager):
        view_manager.freq()
    _frequency_changed = False
    collect()
