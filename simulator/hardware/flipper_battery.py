def init():
    return True


def get_voltage_mv():
    return 3300 + get_percentage() * 860 // 100


def get_percentage():
    try:
        import sim_runtime

        return sim_runtime.battery_percentage()
    except Exception:
        return 87
