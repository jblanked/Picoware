TOUCH_GESTURE_MODE = 1
TOUCH_POINT_MODE = 2
TOUCH_GESTURE_NONE = 0
TOUCH_GESTURE_UP = 1
TOUCH_GESTURE_DOWN = 2
TOUCH_GESTURE_LEFT = 3
TOUCH_GESTURE_RIGHT = 4
TOUCH_GESTURE_LONG_PRESS = 5
TOUCH_GESTURE_CLICK = 6

_mode = TOUCH_POINT_MODE
_cached_point = (0, 0)


def init(mode=TOUCH_POINT_MODE):
    global _mode
    _mode = mode
    return True


def get_gesture():
    try:
        import sim_runtime

        return sim_runtime.touch_gesture()
    except Exception:
        return TOUCH_GESTURE_NONE


def get_touch_point():
    try:
        import sim_runtime

        return sim_runtime.touch_point()
    except Exception:
        return (0, 0)


def get_cached_point():
    return _cached_point


def read_data(_=None):
    """Refresh the IRQ-safe touch cache from the scripted touch state."""
    global _cached_point
    try:
        import sim_runtime

        _cached_point = sim_runtime.touch_point()
    except Exception:
        _cached_point = (0, 0)
    return None


def reset_state():
    global _cached_point
    _cached_point = (0, 0)
    try:
        import sim_runtime

        sim_runtime.clear_touch()
    except Exception:
        pass
    return True


def reset():
    return reset_state()


def set_touch_point(x, y, gesture=TOUCH_GESTURE_CLICK):
    import sim_runtime

    sim_runtime.set_touch_point(x, y, gesture)
    return True
