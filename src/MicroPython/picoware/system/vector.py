"""Vector - 3D vector math."""

import vector


class Vector(vector.Vector):
    """A simple 3D vector class.

    Args:
        x (int or float): The x-coordinate of the vector. Defaults to 0.
        y (int or float): The y-coordinate of the vector. Defaults to 0.
        z (int or float): The z-coordinate of the vector. Defaults to 0.
    Attributes:
        x (int or float): The x-coordinate of the vector.
        y (int or float): The y-coordinate of the vector.
        z (int or float): The z-coordinate of the vector.
    """

    __slots__ = ("x", "y", "z")

    def __init__(self, x=0, y=0, z=0):
        """Initialize the vector coordinates.

        Args:
            x (int or float): The x-coordinate. Defaults to 0.
            y (int or float): The y-coordinate. Defaults to 0.
            z (int or float): The z-coordinate. Defaults to 0.
        """
        super().__init__(
            x, y, z, isinstance(x, int) and isinstance(y, int) and isinstance(z, int)
        )

    def __setattr__(self, name, value):
        """Route attribute assignment through the underlying setters.

        Args:
            name (str): The attribute name being set (``"x"``, ``"y"``, or ``"z"``).
            value (int or float): The new value for the attribute.
        """
        if name == "x":
            self.set_x(value)
        elif name == "y":
            self.set_y(value)
        elif name == "z":
            self.set_z(value)
        else:
            super().__setattr__(name, value)

    @classmethod
    def from_val(cls, value):
        """Ensure the value is a Vector, converting from a tuple if needed.

        Args:
            value (tuple or Vector): The value to coerce into a Vector.

        Returns:
            Vector: The coerced vector instance.

        Raises:
            TypeError: If ``value`` is neither a tuple nor a Vector.
        """
        if isinstance(value, tuple):
            return cls(*value)
        if isinstance(value, cls):
            return value
        raise TypeError("Expected a tuple or a Vector.")

    def __add__(self, other):
        """Add another vector or tuple to this vector.

        Args:
            other (tuple or Vector): The vector (or tuple) to add.

        Returns:
            Vector: A new vector representing the sum.
        """
        other = Vector.from_val(other)
        return Vector(self.x + other.x, self.y + other.y, self.z + other.z)

    def __mul__(self, scalar):
        """Scale this vector by a scalar value.

        Args:
            scalar (int or float): The scalar to multiply each component by.

        Returns:
            Vector: A new scaled vector.
        """
        return Vector(self.x * scalar, self.y * scalar, self.z * scalar)

    __rmul__ = __mul__

    def __eq__(self, other):
        """Check equality with another vector or tuple.

        Args:
            other (tuple or Vector): The value to compare against.

        Returns:
            bool: True if all components are equal, False otherwise.
        """
        other = Vector.from_val(other)
        return self.x == other.x and self.y == other.y and self.z == other.z