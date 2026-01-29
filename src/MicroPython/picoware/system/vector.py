from vector import Vector as vector_mp


class Vector:
    """
    A simple 2D vector class.

    @param x: The x-coordinate of the vector.
    @param y: The y-coordinate of the vector.
    """

    __slots__ = ("_vector",)

    def __init__(self, x=0, y=0):
        self._vector = None
        if isinstance(x, tuple):
            self._vector = vector_mp(x[0], x[1], isinstance(x[0], int))
        else:
            self._vector = vector_mp(x, y, isinstance(x, int))

    def __del__(self):
        del self._vector
        self._vector = None

    def __str__(self) -> str:
        return str(self._vector)

    @property
    def x(self):
        """The x-coordinate of the vector (float or int)."""
        return self._vector.x

    @x.setter
    def x(self, value):
        """Set the x-coordinate of the vector."""
        try:
            self._vector.x = value
        except TypeError:
            self._vector.x = int(value)

    @property
    def y(self):
        """The y-coordinate of the vector (float or int)."""
        return self._vector.y

    @y.setter
    def y(self, value):
        """Set the y-coordinate of the vector."""
        try:
            self._vector.y = value
        except TypeError:
            self._vector.y = int(value)

    @classmethod
    def from_val(cls, value):
        """Ensure the value is a Vector. If it's a tuple, convert it."""
        if isinstance(value, tuple):
            return cls(*value)
        if isinstance(value, cls):
            return value
        raise TypeError("Expected a tuple or a Vector.")

    def __add__(self, other):
        other = Vector.from_val(other)
        return Vector(self.x + other.x, self.y + other.y)

    def __mul__(self, scalar):
        return Vector(self.x * scalar, self.y * scalar)

    __rmul__ = __mul__

    def __eq__(self, other):
        other = Vector.from_val(other)
        return self.x == other.x and self.y == other.y
