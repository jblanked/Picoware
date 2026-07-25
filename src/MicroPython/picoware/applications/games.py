_games = None
_games_index = 0
_app_loader = None
_pending_game = None


def _thread_idle(view_manager):
    """Return whether an SD import can run without a background worker."""
    thread_manager = getattr(view_manager, "thread_manager", None)
    return thread_manager is None or thread_manager.is_idle


def _launch_game(view_manager, game_index, selected_game):
    """Load and switch to a selected game after background work drains."""
    from picoware.system.view import View

    if game_index == 0:
        from picoware.applications import ghouls

        ghouls_view_name = "game_ghouls"
        if view_manager.get_view(ghouls_view_name) is None:
            ghouls_view = View(
                ghouls_view_name,
                ghouls.run,
                ghouls.start,
                ghouls.stop,
            )
            view_manager.add(ghouls_view)
        view_manager.switch_to(ghouls_view_name)
        return

    if not selected_game or not _app_loader:
        return

    game_module = _app_loader.load_app(selected_game, "games")
    if game_module is None:
        view_manager.alert('Failed to load game "{}".'.format(selected_game))
        return

    game_view_name = "game_{}".format(selected_game)
    from utime import ticks_ms

    start_time = ticks_ms()
    if view_manager.get_view(game_view_name) is None:
        game_view = View(
            game_view_name,
            game_module.run,
            game_module.start,
            game_module.stop,
        )
        view_manager.log(
            "[Games]: Created view for app {} after {} ms".format(
                selected_game,
                ticks_ms() - start_time,
            ),
        )
        view_manager.add(game_view)

    view_manager.switch_to(game_view_name)
    view_manager.log(
        '[Games]: Switched to view for app "{}" after {} ms'.format(
            selected_game,
            ticks_ms() - start_time,
        ),
    )


def start(view_manager) -> bool:
    """Start the games app"""
    from picoware.gui.menu import Menu
    from picoware.system.app_loader import AppLoader

    if not view_manager.has_sd_card:
        view_manager.alert(
            "Games app requires an SD card.",
            False,
        )
        return False

    # create games folder if it doesn't exist
    view_manager.storage.mkdir("picoware/apps/games")

    global _games
    global _app_loader
    global _pending_game

    _pending_game = None

    if _app_loader:
        del _app_loader
        _app_loader = None

    if _games:
        del _games
        _games = None

    _games = Menu(
        view_manager.draw,
        "Games",
        0,
        view_manager.draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
        view_manager.foreground_color,
        2,
    )
    _app_loader = AppLoader(view_manager)

    _games.add_item("Ghouls")  # Add Ghouls as a built-in game

    for game in _app_loader.list_available_apps("games"):
        _games.add_item(game)

    _games.set_selected(_games_index)

    _games.draw()
    return True


def run(view_manager) -> None:
    """Run the games app."""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_CENTER,
        BUTTON_RIGHT,
    )

    global _games_index
    global _pending_game

    if not _games:
        return

    button: int = view_manager.button

    if _pending_game is not None:
        if button == BUTTON_BACK:
            _pending_game = None
            _games_index = 0
            view_manager.back()
            return
        if _thread_idle(view_manager):
            pending = _pending_game
            _pending_game = None
            _launch_game(view_manager, pending[0], pending[1])
        return

    if button in (BUTTON_UP, BUTTON_LEFT):
        _games.scroll_up()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        _games.scroll_down()
    elif button == BUTTON_BACK:
        _games_index = 0
        view_manager.back()
    elif button == BUTTON_CENTER:
        _games_index = _games.selected_index
        selected_game = _games.current_item
        if _thread_idle(view_manager):
            _launch_game(view_manager, _games_index, selected_game)
        else:
            _pending_game = (_games_index, selected_game)
            view_manager.log(
                '[Games]: Waiting for background work before loading "{}".'.format(
                    selected_game,
                ),
            )


def stop(view_manager) -> None:
    """Stop the games app"""
    from gc import collect

    global _games, _app_loader, _pending_game
    _pending_game = None
    if _games is not None:
        del _games
        _games = None
    if _app_loader is not None:
        _app_loader.cleanup_modules()
        del _app_loader
        _app_loader = None
    collect()
