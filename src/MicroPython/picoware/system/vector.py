class Vector:
    """
    A simple 2D vector class.

    @param x: The x-coordinate of the vector.
    @param y: The y-coordinate of the vector.
    """

    __slots__ = ("x", "y")

    def __init__(self, x=0, y=0):
        # If x is a tuple, unpack it; otherwise, use the two arguments.
        if isinstance(x, tuple):
            self.x, self.y = x
        else:
            self.x = x
            self.y = y

    @classmethod
    def from_val(cls, value):
        """Ensure the value is a Vector. If it's a tuple, convert it."""
        if isinstance(value, tuple):
            return cls(*value)
        if isinstance(value, cls):
            return value
        raise TypeError("Expected a tuple or a Vector.")

    def to_float(self):
        """Convert the vector components to floats."""
        self.x = float(self.x)
        self.y = float(self.y)

    def to_int(self):
        """Convert the vector components to integers."""
        self.x = int(self.x)
        self.y = int(self.y)

    def __add__(self, other):
        other = Vector.from_val(other)
        return Vector(self.x + other.x, self.y + other.y)

    def __mul__(self, scalar):
        return Vector(self.x * scalar, self.y * scalar)

    __rmul__ = __mul__

    def __str__(self):
        return "({}, {})".format(self.x, self.y)

    def __eq__(self, other):
        other = Vector.from_val(other)
        return self.x == other.x and self.y == other.y
