"""Host shim for Picoware's optional Motion-JPEG video module."""


class Video:
    """Expose the firmware video object's state without decoding video on host."""

    def __init__(self, path, x=0, y=0, scale=1.0):
        scale = float(scale)
        if scale not in (1.0, 0.5, 0.25, 0.125) or scale <= 0:
            raise RuntimeError("scale must be 1, 0.5, 0.25, or 0.125")
        self.path = str(path)
        self.x = int(x)
        self.y = int(y)
        self.scale = scale
        self.active = False
        self.width = 0
        self.height = 0
        self.frames = 0
        self.frame = 0
        self.fps = 0

    def start(self):
        """Fail closed because the simulator has no MP4/JPEG decoder."""
        raise RuntimeError("video playback is not available in the simulator")

    def run(self):
        """Return False when no simulated video frame is active."""
        return False

    def stop(self):
        """Stop the simulated video state."""
        self.active = False
        self.frame = 0

    def play(self):
        """Fail closed because the simulator has no MP4/JPEG decoder."""
        return self.start()
