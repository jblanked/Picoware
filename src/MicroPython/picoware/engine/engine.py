from time import sleep
import engine


class GameEngine(engine.Engine):
    """
    Represents a game engine.
    """

    def __init__(self, game, fps: int = 30):
        """
        Initialize the game engine.
        :param fps: int - the frames per second of the game engine
        :param game: Game - the game to be run by the engine
        """
        super().__init__(game, fps)

    def __del__(self) -> None:
        self.stop()

    def run(self):
        """Run the game engine"""

        # start the game
        if not self.game.is_active:
            self.game.start()

        # start the game loop
        while self.game.is_active:
            self.game.update()  # update positions, input, etc.
            self.game.render()  # update graphics

            sleep(1 / self.fps)

        self.stop()

    def run_async(self, should_delay: bool = False):
        """Run the game engine asynchronously"""
        # start the game
        if not self.game.is_active:
            self.game.start()

        self.game.update()  # update positions, input, etc.
        self.game.render()  # update graphics

        if should_delay:
            sleep(1 / self.fps)

    def stop(self):
        """Stop the game engine"""
        self.game.stop()
        self.game.draw.erase()

    def update_game_input(self, game_input: int):
        """Update the game input"""
        if self.game:
            self.game.input = game_input
