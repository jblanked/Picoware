"""Game - Base game class for the engine."""

import engine


class Game(engine.Game):
    """Represent the top-level game state and its native render context.

    Args:
        name (str): Name of the game.
        size (Vector): Game world size.
        draw (Draw): Drawing context used to render the game.
        input_manager (InputManager): Input manager used to handle input.
        foreground_color (int): Foreground color. Defaults to 0xFFFF.
        background_color (int): Background color. Defaults to 0x0000.
        camera_context (Camera or None): Camera used to render the game. Defaults to None.
        start (callable or None): Callback called when the game starts. Defaults to None.
        stop (callable or None): Callback called when the game stops. Defaults to None.

    Attributes:
        name (str): Game name. Writable.
        position (Vector): Current game position. Writable.
        size (Vector): Game world size. Writable.
        is_active (bool): Whether the game is active. Writable.
        foreground_color (int): Foreground color. Writable.
        background_color (int): Background color. Writable.
        camera (Camera or None): Current camera context. Writable.
        input (int): Most recent input value. Writable.
        draw (Draw): Native drawing context. Read-only.
        current_level (Level or None): Current level. Writable.
        MAX_LEVELS (int): Maximum number of tracked levels.

    Methods:
        - set_camera(camera): Set the camera context.
        - set_input(input): Set the current input value.
        - level_add(level): Add a level to the game.
        - level_remove(level): Remove a level from the game.
        - level_switch(index_or_name): Switch to a level by index or name.
        - set_name(name): Set the game name.
        - set_position(position): Set the game position.
        - set_size(size): Set the game world size.
        - set_is_active(is_active): Set the active flag.
        - set_foreground_color(foreground_color): Set the foreground color.
        - set_background_color(background_color): Set the background color.
        - set_current_level(level): Set the current level or None.
        - level_exists(name): Return whether a level name is registered.
        - __del__(): Release the native game resources.
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
