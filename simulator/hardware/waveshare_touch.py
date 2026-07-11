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


def reset_state():
    try:
        import sim_runtime

        sim_runtime.clear_touch()
    except Exception:
        pass
    return True


def set_touch_point(x, y, gesture=TOUCH_GESTURE_CLICK):
    import sim_runtime

    sim_runtime.set_touch_point(x, y, gesture)
    return True
