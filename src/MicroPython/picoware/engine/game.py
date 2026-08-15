"""Game - Base game class for the engine."""

import engine


class Game(engine.Game):
    """Represents a game."""

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
        """Initialize the game.

        Args:
            name (str): Name of the game.
            size (Vector): Size of the game.
            draw (Draw): Draw context used to render the game.
            input_manager (InputManager): Input manager used to handle input.
            foreground_color (int): Foreground color of the game. Defaults to 0xFFFF.
            background_color (int): Background color of the game. Defaults to 0x0000.
            camera_context (Camera or None): Camera context used to render the game. Defaults to None.
            start (callable): Function called when the game is started. Defaults to None.
            stop (callable): Function called when the game is stopped. Defaults to None.
        """
        from picoware.engine.camera import Camera

        super().__init__(
            name,
            size,
            foreground_color,
            background_color,
            Camera() if camera_context is None else camera_context,
            start,
            stop,
            self._update,
            draw,
        )
        self.input_manager = input_manager

    def __setattr__(self, name, value):
        """Set a game attribute, routing to the matching setter.

        Args:
            name (str): Attribute name to set.
            value (object): New value for the attribute.
        """
        if name == "name":
            self.set_name(value)
        elif name == "size":
            self.set_size(value)
        elif name == "is_active":
            self.set_is_active(value)
        elif name == "foreground_color":
            self.set_foreground_color(value)
        elif name == "background_color":
            self.set_background_color(value)
        elif name == "input":
            self.set_input(value)
        elif name == "camera":
            self.set_camera(value)
        elif name == "current_level":
            self.set_current_level(value)
        else:
            super().__setattr__(name, value)

    def _update(self) -> None:
        """Update the game input and entity positions in a thread-safe manner."""
        if not self.is_active:
            return
        self.set_input(self.input_manager.button)
        self.input_manager.reset()
