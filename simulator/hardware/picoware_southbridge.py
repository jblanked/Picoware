_battery_percentage = 87
_power_off_delay = None
_initialized = True


def deinit():
    """Deinitialize the southbridge."""
    global _initialized
    _initialized = False
    return True


def init():
    """Initialize the southbridge."""
    global _initialized
    _initialized = True
    return True


def get_battery_percentage():
    """Return simulated battery percentage."""
    try:
        import sim_runtime

        return sim_runtime.battery_percentage()
    except Exception:
        pass
    return _battery_percentage


def set_battery_percentage(value):
    """Set simulated battery percentage (0-100)."""
    global _battery_percentage
    _battery_percentage = max(0, min(100, int(value)))
    try:
        import sim_runtime

        sim_runtime.set_battery_percentage(_battery_percentage)
    except Exception:
        pass
    return True


def is_power_off_supported():
    """Return True; power-off is always supported in simulator."""
    return True


def write_power_off_delay(delay):
    """Set the power-off delay in seconds."""
    global _power_off_delay
    _power_off_delay = int(delay)
    return True


def get_power_off_delay():
    """Return the current power-off delay."""
    return _power_off_delay
