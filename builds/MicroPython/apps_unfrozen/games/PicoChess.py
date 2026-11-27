"""SD-installed PicoChess launcher.

Import the package at start: the Games view cleans its AppLoader modules while
switching away, after discovering this launcher but before starting the game.
"""
_game = None


def start(view_manager):
    global _game
    import chess_game
    _game = chess_game
    return _game.start(view_manager)


def run(view_manager):
    if _game is not None:
        _game.run(view_manager)


def stop(view_manager):
    global _game
    if _game is not None:
        _game.stop(view_manager)
        _game = None
