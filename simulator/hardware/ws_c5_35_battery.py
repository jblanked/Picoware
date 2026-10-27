def init():
    return True


def get_voltage():
    return 3.3 + get_percentage() * 0.9 / 100


def get_percentage():
    try:
        import sim_runtime

        return sim_runtime.battery_percentage()
    except Exception:
        return 87
