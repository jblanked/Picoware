from picoware.system.vector import Vector
import engine


class Game(engine.Game):
    """
    Represents a game.
    """

    def __init__(
        self,
        name: str,
        size: Vector,
        draw,
        input_manager,
        foreground_color: int = 0xFFFF,
        background_color: int = 0x0000,
        perspective: int = 0,  # Default perspective (first person)
        start=None,
        stop=None,
    ):
        """
        Initializes the game.
        :param name: str - the name of the game
        :param size: Vector - the size of the game
        :param draw: Draw - the draw object used to render the game
        :param input_manager: InputManager - the input manager used to handle input
        :param foreground_color: int - the foreground color of the game
        :param background_color: int - the background color of the game
        :param perspective: int - the camera perspective (first person or third person)
        :param start: function(Game) - the function called when the game is started
        :param stop: function(Game) - the function called when the game is stopped
        """
        super().__init__(
            name,
            size,
            foreground_color,
            background_color,
            perspective,
        )
        self._start = start
        self._stop = stop
        self.current_level = None
        self.draw = draw
        self.input_manager = input_manager

    def __del__(self):
        self.stop()

        if self.current_level:
            del self.current_level
            self.current_level = None

    @property
    def perspective(self) -> int:
        """Get the camera perspective"""
        return self.camera_perspective

    @perspective.setter
    def perspective(self, perspective: int):
        """Set the camera perspective"""
        self.camera_perspective = perspective

    def clamp(self, value, lower, upper):
        """Clamp a value between a lower and upper bound."""
        return min(max(value, lower), upper)

    def level_add(self, level):
        """Add a level to the game"""
        self.levels.append(level)

    def level_exists(self, level_name: str) -> bool:
        """Check if a level exists in the game"""
        return level_name in [level.name for level in self.levels]

    def level_remove(self, level):
        """Remove a level from the game"""
        self.levels.remove(level)

    def level_switch(self, level):
        """Switch to a new level"""
        if isinstance(level, int):
            if level > len(self.levels) - 1:
                print("Level index out of range")
                return
            if self.current_level:
                self.current_level.stop()

            self.current_level = self.levels[level]
            self.current_level.start()
        elif isinstance(level, str):
            for l in self.levels:
                if l.name == level:
                    if self.current_level:
                        self.current_level.stop()

                    self.current_level = l
                    self.current_level.start()
                    return
        else:
            print("Invalid level type. Must be int or str.")

    def render(self):
        """Render the current level"""
        if self.current_level:
            self.current_level.render(self.camera_perspective)

    def start(self) -> bool:
        """Start the game"""
        if not self.levels:
            print("The game has no levels.")
            return False
        self.current_level = self.levels[0]
        if self._start:
            self._start(self)
        self.current_level.start()
        self.is_active = True
        return True

    def stop(self):
        """Stop the game"""

        if not self.is_active:
            return

        if self._stop:
            self._stop(self)

        self.is_active = False

        for level in self.levels:
            if level:
                level.clear()
                level = None
        self.levels = []

        self.draw.clear(Vector(0, 0), self.size, self.background_color)

    def update(self):
        """Update the game input and entity positions in a thread-safe manner."""
        if not self.is_active:
            return

        self.input = self.input_manager.button
        self.input_manager.reset()
        # update the level
        if self.current_level:
            self.current_level.update()
