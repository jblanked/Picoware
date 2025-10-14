_games = None
_games_index = 0
_app_loader = None


def start(view_manager) -> bool:
    """Start the games app"""
    from picoware.gui.menu import Menu
    from picoware.system.app_loader import AppLoader

    # create games folder if it doesn't exist
    view_manager.get_storage().mkdir("picoware/apps/games")

    global _games
    global _games_index
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
        320,
        view_manager.get_foreground_color(),
        view_manager.get_background_color(),
        view_manager.get_selected_color(),
        view_manager.get_foreground_color(),
        2,
    )
    _app_loader = AppLoader(view_manager)

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

    global _games_index, _app_loader

    if not _games:
        return

    input_manager = view_manager.input_manager
    button: int = input_manager.get_last_button()

    if button == BUTTON_UP:
        input_manager.reset()
        _games.scroll_up()
    elif button == BUTTON_DOWN:
        input_manager.reset()
        _games.scroll_down()
    elif button in (BUTTON_BACK, BUTTON_LEFT):
        _games_index = 0
        input_manager.reset()
        view_manager.back()
    elif button in (BUTTON_CENTER, BUTTON_RIGHT):
        input_manager.reset()
        _games_index = _games.get_selected_index()

        # Get the selected game name
        selected_game = _games.get_current_item()

        if selected_game and _app_loader:
            # Try to load the game
            game_module = _app_loader.load_app(selected_game, "games")
            if game_module:
                # Create a view for the game and switch to it
                game_view_name = f"game_{selected_game}"

                # Check if view already exists
                if view_manager.get_view(game_view_name) is None:
                    game_view = View(
                        game_view_name,
                        game_module.run,
                        game_module.start,
                        game_module.stop,
                    )
                    view_manager.add(game_view)

                view_manager.switch_to(game_view_name)


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
