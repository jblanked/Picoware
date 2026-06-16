_battery_percentage = 87
_power_off_delay = None
_initialized = True


def deinit():
    global _initialized
    _initialized = False
    return True


def init():
    global _initialized
    _initialized = True
    return True


def get_battery_percentage():
    return _battery_percentage


def set_battery_percentage(value):
    global _battery_percentage
    _battery_percentage = max(0, min(100, int(value)))
    return True


def is_power_off_supported():
    return True


def write_power_off_delay(delay):
    global _power_off_delay
    _power_off_delay = int(delay)
    return True


def get_power_off_delay():
    return _power_off_delay
