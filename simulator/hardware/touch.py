class Touch:
    def __init__(self):
        self.x = 0
        self.y = 0

    def read(self):
        try:
            import sim_runtime

            point = sim_runtime.touch_point()
        except Exception:
            point = (0, 0)
        self.x = int(point[0])
        self.y = int(point[1])
        return point != (0, 0)

    def reset(self):
        try:
            import sim_runtime

            sim_runtime.clear_touch()
        except Exception:
            pass
        self.x = 0
        self.y = 0
        return True
