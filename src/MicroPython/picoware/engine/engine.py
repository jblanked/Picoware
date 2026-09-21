"""Engine - Core game engine."""

import engine


class GameEngine(engine.Engine):
    """Run a game through the native engine loop.

    Args:
        game (Game): Game instance to run.
        fps (int): Target frame rate.

    Attributes:
        game (Game): Game instance managed by the engine.

    Methods:
        - run(): Run the blocking game loop until the game stops.
        - run_async(should_delay=True): Run one update and render tick.
        - stop(): Stop the game, clear the display, and release native resources.
        - update_game_input(input): Update the game input while the game is active.
        - __del__(): Release the native engine resources.
    """

    def __setattr__(self, name, value):
        """Set an engine attribute, routing to the matching setter.

        Args:
            name (str): Attribute name to set.
            value (object): New value for the attribute.
        """
        if name == "input":
            self.update_game_input(value)
        else:
            super().__setattr__(name, value)
