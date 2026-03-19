import engine


class Triangle3D(engine.Triangle3D):
    """3D triangle structure"""

    def __setattr__(self, name, value):
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
