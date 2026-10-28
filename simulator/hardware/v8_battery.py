def init():
    return None


def get_voltage():
    return 3300 + get_percentage() * 900 // 100


def get_percentage():
    try:
        import sim_runtime

        return sim_runtime.battery_percentage()
    except Exception:
        return 87
