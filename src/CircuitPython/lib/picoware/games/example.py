from pico_game_engine.game import Game
from pico_game_engine.engine import GameEngine
from pico_game_engine.entity import Entity
from pico_game_engine.level import Level
from picoware.system.input import BUTTON_UP, BUTTON_DOWN, BUTTON_RIGHT, BUTTON_LEFT
from picogui.vector import Vector
from picogui.draw import Draw, TFT_BLACK, TFT_WHITE


class ExampleGame:
    """
    A game example using the modified Pico Game Engine
    """

    def __init__(self, draw: Draw):
        self.screen = draw
        self.game: Game = None
        self.current_level: Level = None
        self.engine = None

    def add_level(self):
        """Add a new level"""
        self.current_level = Level(
            name="Level", size=Vector(self.screen.size), game=self.game
        )
        self.game.level_add(self.current_level)

    def add_player(self):
        """Add a new player entity"""

        player_entity = Entity(
            name="Player",
            position=Vector(160, 120),
            sprite_file_path="/sd/Dino.bmp",
            sprite_size=Vector(16, 16),
            update=self.player_update,
            render=self.player_render,
            is_player=True,
        )

        self.current_level.entity_add(player_entity)

    def game_input(self, player: Entity, game: Game):
        """Move the player entity based on input"""
        if game.input == BUTTON_UP:
            player.position += Vector(0, -5)
        elif game.input == BUTTON_RIGHT:
            player.position += Vector(5, 0)
        elif game.input == BUTTON_DOWN:
            player.position += Vector(0, 5)
        elif game.input == BUTTON_LEFT:
            player.position += Vector(-5, 0)

        # check if the player is out of bounds
        if player.position.x < 0 or player.position.x > self.screen.size.x:
            player.position.x = 0 if player.position.x < 0 else self.screen.size.x
        if player.position.y < 0 or player.position.y > self.screen.size.y:
            player.position.y = 0 if player.position.y < 0 else self.screen.size.y

    def game_start(self, game: Game):
        """Handle your game start logic here"""

    def game_stop(self, game: Game):
        """Handle your game stop logic here"""

    def player_update(self, player: Entity, game: Game):
        """Update the player entity"""

        # move the player entity based on input
        self.game_input(player, game)

    def player_render(self, player: Entity, draw: Draw, game: Game):
        """Render the player entity"""

        # draw name of the game
        draw.text(Vector(110, 10), game.name, TFT_BLACK)

    def setup(self):
        """Setup the game environment and create a new game instance"""
        # create a new game
        self.game = Game(
            name="Example",
            start=self.game_start,
            stop=self.game_stop,
            draw=self.screen,
            foreground_color=TFT_BLACK,
            background_color=TFT_WHITE,
        )

        # add controls, level, and player
        self.add_level()
        self.add_player()

        # create a new game engine
        self.engine = GameEngine(
            fps=30,
            game=self.game,
        )

    def run(self):
        """Run the game engine"""
        try:
            self.engine.run_frame()
        except KeyboardInterrupt:
            self.game.is_running = False


example_view: ExampleGame = None


def main(draw: Draw):
    """Main function to run the game engine"""
    global example_view
    if not example_view:
        example_view = ExampleGame(draw)
        example_view.setup()
    example_view.run()
