import engine


class Game(engine.Game):
    """
    Represents a game.
    """

    def __init__(
        self,
        name: str,
        size,
        draw,
        input_manager,
        foreground_color: int = 0xFFFF,
        background_color: int = 0x0000,
        camera_context=None,
        start=None,
        stop=None,
    ) -> None:
        """
        Initializes the game.
        :param name: str - the name of the game
        :param size: Vector - the size of the game
        :param draw: Draw - the draw context used to render the game
        :param input_manager: InputManager - the input manager used to handle input
        :param foreground_color: int - the foreground color of the game
        :param background_color: int - the background color of the game
        :param camera_context: Camera - the camera context used to render the game
        :param start: function(Game) - the function called when the game is started
        :param stop: function(Game) - the function called when the game is stopped
        """
        super().__init__(
            name,
            size,
            foreground_color,
            background_color,
            camera_context,
            start,
            stop,
            self._update,
            draw,
        )
        self.input_manager = input_manager

    def _update(self) -> None:
        """Update the game input and entity positions in a thread-safe manner."""
        if not self.is_active:
            return
        self.set_input(self.input_manager.button)
        self.input_manager.reset()
