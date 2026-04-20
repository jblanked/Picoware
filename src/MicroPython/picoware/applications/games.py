_games = None
_games_index = 0
_app_loader = None


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
    from picoware.system.view import View
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_CENTER,
        BUTTON_RIGHT,
    )

    global _games_index

    if not _games:
        return

    button: int = view_manager.button

    if button in (BUTTON_UP, BUTTON_LEFT):
        _games.scroll_up()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        _games.scroll_down()
    elif button == BUTTON_BACK:
        _games_index = 0
        view_manager.back()
    elif button == BUTTON_CENTER:
        _games_index = _games.selected_index

        if _games_index == 0:
            # Start Ghouls
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

        # Get the selected game name
        selected_game = _games.current_item

        if selected_game and _app_loader:
            # Try to load the game
            game_module = _app_loader.load_app(selected_game, "games")
            if game_module is None:
                view_manager.alert(f'Failed to load game "{selected_game}".')
                return
            # Create a view for the game and switch to it
            game_view_name = f"game_{selected_game}"
            from utime import ticks_ms

            start_time = ticks_ms()

            # Check if view already exists
            if view_manager.get_view(game_view_name) is None:
                game_view = View(
                    game_view_name,
                    game_module.run,
                    game_module.start,
                    game_module.stop,
                )
                view_manager.log(
                    f"[Games]: Created view for app {selected_game} after {ticks_ms() - start_time} ms",
                )
                view_manager.add(game_view)

            view_manager.switch_to(game_view_name)
            view_manager.log(
                f'[Games]: Switched to view for app "{selected_game}" after {ticks_ms() - start_time} ms',
            )


def stop(view_manager) -> None:
    """Stop the games app"""
    from gc import collect

    global _games, _app_loader
    if _games is not None:
        del _games
        _games = None
    if _app_loader is not None:
        _app_loader.cleanup_modules()
        del _app_loader
        _app_loader = None
    collect()
