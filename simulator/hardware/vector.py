class Vector:
    def __init__(self, x=0, y=0, z=0, integer=True):
        object.__setattr__(self, "_integer", integer)
        object.__setattr__(self, "x", int(x) if integer else x)
        object.__setattr__(self, "y", int(y) if integer else y)
        object.__setattr__(self, "z", int(z) if integer else z)

    def set_x(self, value):
        object.__setattr__(self, "x", int(value) if self._integer else value)

    def set_y(self, value):
        object.__setattr__(self, "y", int(value) if self._integer else value)

    def set_z(self, value):
        object.__setattr__(self, "z", int(value) if self._integer else value)
