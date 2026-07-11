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
