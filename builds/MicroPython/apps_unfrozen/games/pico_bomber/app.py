"""Picoware lifecycle adapter for Pico Bomber."""

from gc import collect
from utime import ticks_add, ticks_diff, ticks_ms

from picoware.system.buttons import (
    BUTTON_0,
    BUTTON_9,
    BUTTON_A,
    BUTTON_BACK,
    BUTTON_BACKSPACE,
    BUTTON_CENTER,
    BUTTON_DELETE,
    BUTTON_DOWN,
    BUTTON_ENTER,
    BUTTON_LEFT,
    BUTTON_MINUS,
    BUTTON_P,
    BUTTON_RIGHT,
    BUTTON_SPACE,
    BUTTON_UNDERSCORE,
    BUTTON_UP,
    BUTTON_Z,
)

from .leaderboard import DEFAULT_NAME, MAX_NAME_LENGTH, Leaderboard
from .model import (
    MENU_LEADERBOARD,
    STATE_GAME_OVER,
    STATE_LEADERBOARD,
    STATE_MODE_SELECT,
    STATE_NAME_ENTRY,
    STATE_PAUSED,
    STATE_PLAYER_DYING,
    STATE_PLAYING,
    STATE_STAGE_CLEAR,
    STATE_STAGE_INTRO,
    STATE_TITLE,
    GameModel,
)
from .render import Renderer


_game = None
_renderer = None
_leaderboard = None
_next_frame = 0
_score_saved = False
_mode_start_pending = False
_redraw_pending = False
_key_repeat_enabled = False
_runtime_phase = "idle"
_last_button = -1
_run_count = 0
FRAME_MS = 50
STARTUP_SPLASH_MS = 2000
MODE_DEMO_IDLE_MS = 30000
_mode_idle_since = 0


def _log_mode_start_error(view_manager, phase, error):
    """Record the failing cold-start phase without replacing the exception."""
    try:
        view_manager.log(
            "[Pico Bomber] mode-start %s: %r" % (phase, error),
            2,
        )
    except Exception:
        pass


def _set_key_repeat(view_manager, enable, force=False):
    """Use opt-in navigation repeat when the active firmware supports it."""
    global _key_repeat_enabled

    enable = bool(enable)
    if not force and enable == _key_repeat_enabled:
        return
    setter = getattr(view_manager.input_manager, "set_key_repeat", None)
    if setter is not None:
        setter(enable)
    _key_repeat_enabled = enable


def _write_crash_log(view_manager, error):
    """Persist enough state to identify the corrupt-bytecode boundary."""
    try:
        import io
        import sys
        from gc import mem_free

        trace = io.StringIO()
        sys.print_exception(error, trace)
        renderer_phase = -1 if _renderer is None else _renderer.phase
        tile_x = -1 if _renderer is None else _renderer.tile_x
        tile_y = -1 if _renderer is None else _renderer.tile_y
        item_index = -1 if _renderer is None else _renderer.item_index
        game_state = -1 if _game is None else _game.state
        game_theme = -1 if _game is None else _game.theme
        build_phase = -1 if _game is None else _game.build_phase
        build_x = -1 if _game is None else _game.build_x
        build_y = -1 if _game is None else _game.build_y
        build_items = -1 if _game is None else _game.build_items
        text = (
            "phase=%s renderer=%d tile=%d,%d item=%d "
            "state=%d theme=%d build=%d at=%d,%d items=%d "
            "button=%d run=%d free=%d\n%s"
        ) % (
            _runtime_phase,
            renderer_phase,
            tile_x,
            tile_y,
            item_index,
            game_state,
            game_theme,
            build_phase,
            build_x,
            build_y,
            build_items,
            _last_button,
            _run_count,
            mem_free(),
            trace.getvalue(),
        )
        view_manager.storage.write(
            "picoware/pico_bomber_crash.log",
            "\n---\n" + text,
            "a",
        )
    except Exception as log_error:
        try:
            view_manager.log(
                "[Pico Bomber] crash-log failure: %r" % (log_error,),
                2,
            )
        except Exception:
            pass


def _write_start_marker(view_manager, phase):
    """Persist the last completed startup step for hard-freeze diagnosis."""
    try:
        from gc import mem_free
        from machine import freq

        thread_manager = view_manager.thread_manager
        thread = None if thread_manager is None else thread_manager.thread
        thread_running = (
            1
            if thread is not None and thread.is_running
            else 0
        )
        queued_tasks = (
            0
            if thread_manager is None
            else len(thread_manager._tasks)
        )
        view_manager.storage.write(
            "picoware/pico_bomber_start.log",
            "phase=%s freq=%d free=%d thread=%d queued=%d\n"
            % (
                phase,
                freq(),
                mem_free(),
                thread_running,
                queued_tasks,
            ),
            "w",
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


def _open_mode_menu(now):
    """Open mode selection and restart its attract-mode idle timer."""
    global _mode_idle_since

    _game.open_mode_menu()
    _mode_idle_since = now


def _handle_name_input(_input_manager, button):
    """Edit a short arcade name using the physical keyboard."""
    if button < 0:
        return False
    if button in (BUTTON_CENTER, BUTTON_ENTER):
        _submit_name(_game.player_name)
        return True
    if button in (BUTTON_BACK, BUTTON_BACKSPACE, BUTTON_DELETE):
        if _game.player_name:
            _game.player_name = _game.player_name[:-1]
            return True
        if button == BUTTON_BACK:
            _submit_name(DEFAULT_NAME)
            return True
        return False
    if len(_game.player_name) >= MAX_NAME_LENGTH:
        return False

    if BUTTON_A <= button <= BUTTON_Z:
        char = chr(65 + button - BUTTON_A)
    elif BUTTON_0 <= button <= BUTTON_9:
        char = chr(48 + button - BUTTON_0)
    elif button == BUTTON_SPACE:
        char = " "
    elif button == BUTTON_MINUS:
        char = "-"
    elif button == BUTTON_UNDERSCORE:
        char = "_"
    else:
        return False

    if char:
        _game.player_name += char
        return True
    return False


def _finish_start(view_manager):
    """Create a fresh Pico Bomber startup splash."""
    global _game, _renderer, _leaderboard, _next_frame, _score_saved
    global _mode_start_pending, _redraw_pending

    _game = GameModel()
    _write_start_marker(view_manager, "model")
    _renderer = Renderer(view_manager.draw, view_manager.storage)
    _write_start_marker(view_manager, "renderer")
    _leaderboard = Leaderboard(view_manager.storage)
    _write_start_marker(view_manager, "leaderboard")
    _game.leaderboard = _leaderboard.entries
    _score_saved = False
    _renderer.draw_frame(_game)
    # The raw splash buffer is temporary; reclaim it before the timed screen
    # and later demo/game allocations begin.
    collect()
    now = ticks_ms()
    _game.state_until = ticks_add(now, STARTUP_SPLASH_MS)
    _write_start_marker(view_manager, "title-render")
    _next_frame = ticks_add(now, FRAME_MS)
    _write_start_marker(view_manager, "complete")


def start(view_manager):
    """Create a fresh Pico Bomber startup splash."""
    global _mode_start_pending, _redraw_pending, _mode_idle_since

    _mode_start_pending = False
    _redraw_pending = False
    _mode_idle_since = 0
    _write_start_marker(view_manager, "entered")
    _set_key_repeat(view_manager, False, True)
    _write_start_marker(view_manager, "repeat-off")
    _finish_start(view_manager)
    return True


def _run_once(view_manager):
    """Handle one Picoware input/update/render cycle."""
    global _next_frame, _score_saved, _mode_start_pending, _redraw_pending
    global _runtime_phase, _last_button, _mode_idle_since

    if _game is None or _renderer is None:
        return

    _runtime_phase = "repeat"
    _set_key_repeat(view_manager, _game.state == STATE_PLAYING)
    input_manager = view_manager.input_manager
    button = view_manager.button
    _last_button = button
    now = ticks_ms()
    changed = False

    if _game.state == STATE_TITLE:
        if button >= 0:
            input_manager.reset()
        if ticks_diff(now, _game.state_until) >= 0:
            _open_mode_menu(now)
            _renderer.draw_frame(_game)
            _next_frame = ticks_add(now, FRAME_MS)
        return

    if _game.demo_mode and button >= 0:
        input_manager.reset()
        _open_mode_menu(now)
        button = -1
        changed = True

    if _game.state == STATE_MODE_SELECT:
        if _mode_idle_since == 0 or button >= 0:
            _mode_idle_since = now
        idle_elapsed = max(0, ticks_diff(now, _mode_idle_since))
        remaining = max(
            0,
            (MODE_DEMO_IDLE_MS - idle_elapsed + 999) // 1000,
        )
        if remaining != _game.demo_countdown:
            _game.demo_countdown = remaining
            changed = True
        if button < 0 and idle_elapsed >= MODE_DEMO_IDLE_MS:
            demo_mode = (
                _game.menu_selection
                if _game.menu_selection < MENU_LEADERBOARD
                else _game.mode
            )
            _runtime_phase = "demo-build"
            _game.start_demo(now, demo_mode)
            collect()
            _score_saved = True
            _mode_start_pending = True
            changed = True

    if _game.state == STATE_NAME_ENTRY:
        _runtime_phase = "name-input"
        if button >= 0:
            changed = _handle_name_input(input_manager, button)
            input_manager.reset()
        if changed:
            _redraw_pending = True
        if _redraw_pending and ticks_diff(now, _next_frame) >= 0:
            _runtime_phase = "name-render"
            _renderer.draw_frame(_game)
            _redraw_pending = False
            _next_frame = ticks_add(now, FRAME_MS)
        return

    _runtime_phase = "input"
    if button == BUTTON_BACK:
        input_manager.reset()
        if _game.state == STATE_LEADERBOARD:
            _open_mode_menu(now)
            changed = True
        elif _game.state in (
            STATE_PLAYING,
            STATE_PAUSED,
            STATE_PLAYER_DYING,
            STATE_GAME_OVER,
        ):
            _open_mode_menu(now)
            _mode_start_pending = False
            changed = True
        elif _game.state == STATE_MODE_SELECT:
            view_manager.back()
            return
        else:
            view_manager.back()
            return
    if button == BUTTON_P:
        if _game.state == STATE_PLAYING:
            changed = _game.pause(now)
        elif _game.state == STATE_PAUSED:
            changed = _game.resume(now)
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
        if _game.state == STATE_GAME_OVER:
            _open_mode_menu(now)
            changed = True
        elif _game.state == STATE_LEADERBOARD:
            _open_mode_menu(now)
            changed = True
        elif _game.state == STATE_MODE_SELECT:
            if _game.menu_selection == MENU_LEADERBOARD:
                _game.state = STATE_LEADERBOARD
            else:
                _mode_start_pending = True
                try:
                    _runtime_phase = "stage-build"
                    _game.new_game(now, _game.menu_selection)
                    # Release the stage builder's temporary candidate tuples
                    # before the first full arena frame.
                    collect()
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

    updated = False
    if _game.update_demo(now):
        changed = True
    if _game.state in (
        STATE_PLAYING,
        STATE_PLAYER_DYING,
        STATE_STAGE_CLEAR,
        STATE_STAGE_INTRO,
    ):
        _runtime_phase = "update"
        try:
            updated = _game.update(now)
        except Exception as error:
            if _mode_start_pending:
                _log_mode_start_error(view_manager, "first-update", error)
                _mode_start_pending = False
            raise
    if updated:
        changed = True

    _runtime_phase = "score"
    if _game.state == STATE_GAME_OVER and _game.demo_mode:
        _open_mode_menu(now)
        _score_saved = True
        changed = True
    elif _game.state == STATE_GAME_OVER and not _score_saved:
        if _leaderboard.qualifies(_game.score):
            _game.player_name = ""
            _game.state = STATE_NAME_ENTRY
        else:
            _score_saved = True
        changed = True

    _set_key_repeat(view_manager, _game.state == STATE_PLAYING)
    animated = _game.state in (STATE_PLAYING, STATE_PLAYER_DYING)
    if changed:
        _redraw_pending = True
    if (
        ticks_diff(now, _next_frame) >= 0
        and (_redraw_pending or animated)
    ):
        try:
            _runtime_phase = "render"
            _renderer.draw_frame(_game)
        except Exception as error:
            if _mode_start_pending:
                _log_mode_start_error(view_manager, "first-render", error)
                _mode_start_pending = False
            raise
        _redraw_pending = False
        _mode_start_pending = False
        _next_frame = ticks_add(now, FRAME_MS)
    _runtime_phase = "idle"


def run(view_manager):
    """Run one guarded cycle and persist the original crash traceback."""
    global _run_count

    _run_count += 1
    try:
        _run_once(view_manager)
    except Exception as error:
        _write_crash_log(view_manager, error)
        raise


def stop(view_manager):
    """Release the game state when leaving the Picoware view."""
    global _game, _renderer, _leaderboard, _next_frame, _score_saved
    global _mode_start_pending, _redraw_pending, _mode_idle_since

    _set_key_repeat(view_manager, False, True)
    _game = None
    _renderer = None
    _leaderboard = None
    _next_frame = 0
    _score_saved = False
    _mode_start_pending = False
    _redraw_pending = False
    _mode_idle_since = 0
    collect()
