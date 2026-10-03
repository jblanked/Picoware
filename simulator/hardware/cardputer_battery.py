def init():
    return None


def get_voltage():
    try:
        import sim_runtime

        percentage = sim_runtime.battery_percentage()
    except Exception:
        percentage = 87
    return 3.3 + int(percentage) * 0.8 / 100


def get_percentage():
    try:
        import sim_runtime

        return sim_runtime.battery_percentage()
    except Exception:
        return 87


def set_percentage(value):
    import sim_runtime

    sim_runtime.set_battery_percentage(value)
    return True
