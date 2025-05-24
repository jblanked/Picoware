from picogui.vector import Vector
from displayio import TileGrid, OnDiskBitmap


class Entity:
    """
    Represents an entity in the game.

    Parameters:
    - name: str - the name of the entity
    - sprite: Image - the image representing the entity
    - position: Vector - the position of the entity
    - start: function(Entity, Game) - the function called when the entity is created
    - stop: function(Entity, Game) - the function called when the entity is destroyed
    - update: function(Entity, Game) - the function called every frame
    - render: function(Entity, Draw, Game) - the function called every frame to render the entity
    - collision: function(Entity, Entity, Game) - the function called when the entity collides with another entity
    - is_player: bool - whether the entity is the player
    """

    def __init__(
        self,
        name: str,  # name is a string that represents the name of the entity
        position: Vector,  # position is a Vector that represents the x and y coordinates of the entity
        sprite_file_path: str,  # sprite_file_path is a string that represents the path to the image or the image data
        sprite_size: Vector,  # sprite_size is a Vector that represents the width and height of the image
        start=None,  # start is a function that is called when the entity is created
        stop=None,  # stop is a function that is called when the entity is destroyed
        update=None,  # update is a function that is called every frame
        render=None,  # render is a function that is called every frame
        collision=None,  # collision is a function that is called when the entity collides with another entity
        is_player: bool = False,  # is_player is a boolean that specifies whether the entity is the player
    ):
        self.name = name
        self.__position = position
        self.position_old = position
        self.sprite_path = sprite_file_path
        self.tile_grid = None
        if sprite_file_path != "":
            bitmap = OnDiskBitmap(sprite_file_path)
            self.tile_grid = TileGrid(
                bitmap,
                pixel_shader=bitmap.pixel_shader,
                x=int(position.x),
                y=int(position.y),
            )
            del bitmap
        self.size = sprite_size
        self._start = start
        self._stop = stop
        self._update = update
        self._render = render
        self._collision = collision
        self.is_player = is_player
        self.is_active = False

    def collision(self, other, game):
        """Called when the entity collides with another entity."""
        if self._collision:
            self._collision(self, other, game)

    @property
    def position(self) -> Vector:
        """Used by the engine to get the position of the entity."""
        return Vector(self.__position.x, self.__position.y)

    @position.setter
    def position(self, value: Vector):
        """Used by the engine to set the position of the entity."""
        self.position_old = Vector(self.__position.x, self.__position.y)
        self.__position = Vector(value.x, value.y)
        self.tile_grid.x = int(self.__position.x)
        self.tile_grid.y = int(self.__position.y)

    def render(self, draw, game):
        """Called every frame to render the entity."""
        if self._render:
            self._render(self, draw, game)

    def start(self, game):
        """Called when the entity is created."""
        if self._start:
            self._start(self, game)

    def stop(self, game):
        """Called when the entity is destroyed."""
        if self._stop:
            self._stop(self, game)

    def update(self, game):
        """Called every frame."""
        if self._update:
            self._update(self, game)
