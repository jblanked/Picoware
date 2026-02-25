from vector import Vector as vector_mp


class Vector(vector_mp):
    """
    A simple 3D vector class.

    @param x: The x-coordinate of the vector.
    @param y: The y-coordinate of the vector.
    @param z: The z-coordinate of the vector.
    """

    def __init__(self, x=0, y=0, z=0):
        super().__init__(
            x, y, z, isinstance(x, int) and isinstance(y, int) and isinstance(z, int)
        )

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
        return Vector(self.x + other.x, self.y + other.y, self.z + other.z)

    def __mul__(self, scalar):
        return Vector(self.x * scalar, self.y * scalar, self.z * scalar)

    __rmul__ = __mul__

    def __eq__(self, other):
        other = Vector.from_val(other)
        return self.x == other.x and self.y == other.y and self.z == other.z
