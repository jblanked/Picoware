import engine


class GameEngine(engine.Engine):
    """Represents a game engine."""

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
