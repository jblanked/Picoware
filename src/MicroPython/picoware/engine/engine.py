import engine


class GameEngine(engine.Engine):
    """
    Represents a game engine.
    """

    def __setattr__(self, name, value):
        if name == "input":
            self.update_game_input(value)
        else:
            super().__setattr__(name, value)
