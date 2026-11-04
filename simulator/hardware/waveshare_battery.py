def init():
    return None


def get_percentage():
    try:
        import sim_runtime

        return sim_runtime.battery_percentage()
    except Exception:
        return 87


def get_voltage():
    return 3300 + get_percentage() * 900 // 100


def read():
    return get_voltage() * 4096 // 6600


def set_percentage(value):
    import sim_runtime

    sim_runtime.set_battery_percentage(value)
    return True
