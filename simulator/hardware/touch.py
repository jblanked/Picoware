class Touch:
    def __init__(self):
        self.x = 0
        self.y = 0

    def read(self):
        try:
            import sim_runtime
        except ImportError:
            point = (0, 0)
        else:
            sim_runtime.loop_polled()
            point = sim_runtime.touch_point()
            if point == (0, 0) and sim_runtime.has_key():
                point = self._point_for_key(sim_runtime.pop_key())
                if point != (0, 0):
                    # Firmware touch input is debounced against wall-clock time.
                    # Give an injected key enough separation to be accepted.
                    import time

                    time.sleep_ms(121)
        self.x = int(point[0])
        self.y = int(point[1])
        return point != (0, 0)

    def _point_for_key(self, key):
        """Translate scripted directional keys into board touch zones."""
        import sim_runtime

        name = str(sim_runtime.board).lower().replace("_", "-")
        if name == "pancake":
            points = {
                0xB5: (160, 48),
                0xB6: (160, 432),
                0xB4: (20, 240),
                0xB7: (300, 240),
                0xB1: (32, 32),
                13: (160, 240),
            }
        elif name in (
            "waveshare-2.06",
            "waveshare-2.06-esp32s3",
            "waveshare-2-06-esp32s3",
        ):
            points = {
                0xB5: (205, 60),
                0xB6: (205, 442),
                0xB4: (25, 251),
                0xB7: (390, 251),
                0xB1: (20, 25),
                13: (205, 251),
            }
        else:
            points = {
                0xB5: (512, 60),
                0xB6: (512, 540),
                0xB4: (62, 300),
                0xB7: (962, 300),
                0xB1: (51, 30),
                13: (512, 300),
            }
        return points.get(int(key), (0, 0))

    def reset(self):
        try:
            import sim_runtime

            sim_runtime.clear_touch()
        except Exception:
            pass
        self.x = 0
        self.y = 0
        return True
