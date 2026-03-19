import engine


class Image(engine.Image):
    """Image structure"""

    def __setattr__(self, name, value):
        if name == "size":
            self.set_size(value)
        else:
            super().__setattr__(name, value)
