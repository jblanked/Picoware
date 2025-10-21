from picoware.system.vector import Vector


class Game:
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
        self.name = name
        self._start = start
        self._stop = stop
        self.levels = []  # List of levels in the game
        self.current_level = None  # holds the current level
        self.input_manager = input_manager
        self.input: int = -1  # last button pressed
        self.draw = draw
        self.camera = Vector(0, 0)
        self.position = Vector(0, 0)
        self.size = size
        self.world_size = size
        self.is_active = False
        self.foreground_color = foreground_color
        self.background_color = background_color
        self.camera_perspective = perspective  # first person or third person

    def __del__(self):
        self.stop()

        if self.current_level:
            del self.current_level
            self.current_level = None

        if self.camera:
            del self.camera
            self.camera = None
        if self.position:
            del self.position
            self.position = None
        if self.size:
            del self.size
            self.size = None
        if self.world_size:
            del self.world_size
            self.world_size = None

        self.name = ""
        self.input = -1

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

    def level_remove(self, level):
        """Remove a level from the game"""
        self.levels.remove(level)

    def level_switch(self, level):
        """Switch to a new level"""
        if not level:
            print("Level is not valid.")
            return
        if self.current_level:
            self.current_level.stop()

        self.current_level = level
        self.current_level.start()

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

        self.input = self.input_manager.get_last_button()
        self.input_manager.reset()
        # update the level
        if self.current_level:
            self.current_level.update()
