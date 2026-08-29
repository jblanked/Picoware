# micropython implementation of FlipWorld: https://github.com/jblanked/FlipWorld/tree/main
from picoware.system.decorator import wifi_required, storage_required
_game = None

@storage_required
@wifi_required
def start(view_manager) -> bool:
    """Start the app"""
    global _game

    view_manager.freq(True)  # set to lower frequency

    from flip_world.run import FlipWorldRun

    _game = FlipWorldRun(view_manager)

    return _game is not None


def run(view_manager) -> None:
    """Run the app"""
    button = view_manager.button

    if not _game or not _game.is_active:
        view_manager.back()
        return

    _game.update_input(button)
    _game.update_draw()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _game

    if _game:
        del _game
        _game = None

    view_manager.freq()  # set to default frequency

    collect()
