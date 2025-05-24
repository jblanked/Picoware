from gc import collect as free
from picogui.vector import Vector
from picogui.draw import Draw
from picoware.system.input_manager import InputManager
from .level import Level


class Game:
    """
    Represents a game.

    Parameters:
    - name: str - the name of the game
    - draw: Draw - the draw object to be used for rendering
    - foreground_color: int - the color of the foreground
    - background_color: int - the color of the background
    - start: function() - the function called when the game is created
    - stop: function() - the function called when the game is destroyed
    """

    def __init__(
        self,
        name: str,
        draw: Draw,
        foreground_color: int,
        background_color: int,
        start=None,
        stop=None,
    ):
        self.name = name
        self._start = start
        self._stop = stop
        self.levels: list[Level] = []  # List of levels in the game
        self.current_level: Level = None  # holds the current level
        self.input_manager = InputManager(draw.board)
        self.input: int = -1  # last button pressed
        self.draw = draw
        self.camera = Vector(0, 0)
        self.position = Vector(0, 0)
        self.size = Vector(draw.size.x, draw.size.y)
        self.world_size = Vector(draw.size.x, draw.size.y)
        self.is_active = False
        self.foreground_color = foreground_color
        self.background_color = background_color
        self.is_uart_input = False

    def clamp(self, value, lower, upper):
        """Clamp a value between a lower and upper bound."""
        return min(max(value, lower), upper)

    @property
    def is_running(self) -> bool:
        """Return the running state of the game"""
        return self.is_active

    @is_running.setter
    def is_running(self, value: bool):
        """Set the running state of the game"""
        self.is_active = value

    def level_add(self, level: Level):
        """Add a level to the game"""
        self.levels.append(level)

    def level_remove(self, level: Level):
        """Remove a level from the game"""
        self.levels.remove(level)

    def level_switch(self, level: Level):
        """Switch to a new level"""
        if not level:
            print("Level is not valid.")
            return
        old_level = self.current_level
        self.current_level = level
        old_level.stop()
        old_level.clear()
        self.current_level.start()

    def render(self):
        """Render the current level"""
        if self.current_level:
            self.current_level.render()

    def start(self) -> bool:
        """Start the game"""
        if not self.levels:
            print("The game has no levels.")
            return False
        self.current_level = self.levels[0]
        if self._start:
            self._start(self)
        self.draw.fill(self.background_color)
        self.current_level.start()
        self.is_running = True
        free()
        return True

    def stop(self):
        """Stop the game"""

        if not self.is_active:
            return

        if self._stop:
            self._stop(self)

        self.is_running = False

        for level in self.levels:
            if level:
                level.clear()
                level = None
        self.levels = []

        self.draw.fill(self.background_color)
        free()

    def update(self):
        """Update the game input and entity positions in a thread-safe manner."""
        self.input_manager.run()
        self.input = self.input_manager.input

        # Run user-defined update functions for each entity.
        for entity in self.current_level.entities:
            if entity.update:
                entity.update(self)

        # Calculate camera offset to center the player.
        self.camera.x = self.position.x - (self.size.x // 2)
        self.camera.y = self.position.y - (self.size.y // 2)

        # Clamp camera position to prevent going outside the world.
        self.camera.x = self.clamp(self.camera.x, 0, self.world_size.x - self.size.x)
        self.camera.y = self.clamp(self.camera.y, 0, self.world_size.y - self.size.y)

        # update the level
        if self.current_level:
            self.current_level.update()
