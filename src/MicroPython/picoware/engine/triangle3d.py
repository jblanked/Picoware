"""Triangle3D - 3D triangles for the game engine."""

import engine


class Triangle3D(engine.Triangle3D):
    """Represent a colored triangle used by the 3D renderer.

    Args:
        x1 (float): First vertex X coordinate. Defaults to 0.0.
        y1 (float): First vertex Y coordinate. Defaults to 0.0.
        z1 (float): First vertex Z coordinate. Defaults to 0.0.
        x2 (float): Second vertex X coordinate. Defaults to 0.0.
        y2 (float): Second vertex Y coordinate. Defaults to 0.0.
        z2 (float): Second vertex Z coordinate. Defaults to 0.0.
        x3 (float): Third vertex X coordinate. Defaults to 0.0.
        y3 (float): Third vertex Y coordinate. Defaults to 0.0.
        z3 (float): Third vertex Z coordinate. Defaults to 0.0.
        color (int): Triangle color. Defaults to 0x0000.

    Attributes:
        x1 (float): First vertex X coordinate. Writable.
        y1 (float): First vertex Y coordinate. Writable.
        z1 (float): First vertex Z coordinate. Writable.
        x2 (float): Second vertex X coordinate. Writable.
        y2 (float): Second vertex Y coordinate. Writable.
        z2 (float): Second vertex Z coordinate. Writable.
        x3 (float): Third vertex X coordinate. Writable.
        y3 (float): Third vertex Y coordinate. Writable.
        z3 (float): Third vertex Z coordinate. Writable.
        visible (bool): Whether the triangle is visible. Writable.
        distance (float): Depth-sorting distance. Writable.
        color (int): Triangle color. Writable.

    Methods:
        - get_center(): Return the triangle center.
        - is_facing_camera(camera_pos): Return whether the triangle faces a camera position.
        - set_x1(x1): Set the first vertex X coordinate.
        - set_y1(y1): Set the first vertex Y coordinate.
        - set_z1(z1): Set the first vertex Z coordinate.
        - set_x2(x2): Set the second vertex X coordinate.
        - set_y2(y2): Set the second vertex Y coordinate.
        - set_z2(z2): Set the second vertex Z coordinate.
        - set_x3(x3): Set the third vertex X coordinate.
        - set_y3(y3): Set the third vertex Y coordinate.
        - set_z3(z3): Set the third vertex Z coordinate.
        - set_visible(visible): Set whether the triangle is visible.
        - set_distance(distance): Set the depth-sorting distance.
        - set_color(color): Set the triangle color.
        - __del__(): Release the native triangle resources.
    """

    def __setattr__(self, name, value):
        """Set a triangle attribute, routing to the matching setter.

        Args:
            name (str): Attribute name to set.
            value (object): New value for the attribute.
        """
        if name == "x1":
            self.set_x1(value)
        elif name == "y1":
            self.set_y1(value)
        elif name == "z1":
            self.set_z1(value)
        elif name == "x2":
            self.set_x2(value)
        elif name == "y2":
            self.set_y2(value)
        elif name == "z2":
            self.set_z2(value)
        elif name == "x3":
            self.set_x3(value)
        elif name == "y3":
            self.set_y3(value)
        elif name == "z3":
            self.set_z3(value)
        elif name == "visible":
            self.set_visible(value)
        elif name == "distance":
            self.set_distance(value)
        elif name == "color":
            self.set_color(value)
        else:
            super().__setattr__(name, value)
