from gc import collect as free
from time import sleep
from .game import Game


class GameEngine:
    """
    Represents a game engine.

    Parameters:
    - name: str - the name of the game engine
    - fps: int - the frames per second
    - game: Game - the game to run
    """

    def __init__(self, fps: int, game: Game):
        self.fps = fps
        self.game = game
        self.active = False

    def run(self):
        """Run the game engine"""
        free()

        # start the game
        if not self.game.is_active:
            self.game.start()

            if self.game.is_active:
                self.active = True

        # start the game loop
        while self.active:
            self.game.update()  # update positions, input, etc.
            self.game.render()  # update graphics

            # check if the game is over
            if not self.game.is_running:
                break

            sleep(1 / self.fps)

        self.stop()

    def run_frame(self):
        """Run the game engine frame by frame"""
        free()

        # start the game
        if not self.game.is_active:
            self.game.start()

            if self.game.is_active:
                self.active = True

        # start the game loop
        if self.active:
            self.game.update()  # update positions, input, etc.
            self.game.render()  # update graphics

            # check if the game is over
            if not self.game.is_running:
                self.stop()
                return

            sleep(1 / self.fps)

    def stop(self):
        """Stop the game engine"""
        self.active = False
        self.game.stop()
        self.game.draw.clear()
        free()
