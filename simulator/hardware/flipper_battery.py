_initialized = False


def init():
    """Initialize the simulated Flipper battery interface."""
    global _initialized
    if _initialized:
        return True
    _initialized = True
    return True


def deinit():
    """Deinitialize the battery interface; repeated calls are harmless."""
    global _initialized
    if not _initialized:
        return True
    _initialized = False
    return True


def is_initialized():
    """Return whether the simulated battery interface is initialized."""
    return _initialized


def _require_initialized():
    if not _initialized:
        raise RuntimeError("battery not initialized")


def get_voltage_mv():
    _require_initialized()
    return 3300 + get_percentage() * 860 // 100


def get_percentage():
    _require_initialized()
    try:
        import sim_runtime

        return sim_runtime.battery_percentage()
    except Exception:
        return 87


def shutdown():
    """Power off the simulated Flipper by terminating the simulation."""
    import sim_runtime

    deinit()
    raise sim_runtime.StopSimulation()
