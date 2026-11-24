def init():
    return None


def read_grove_adc():
    """Read GPIO1 with the firmware's 12-bit Grove ADC range."""
    from machine import ADC, Pin

    return ADC(Pin(1)).read_u16() >> 4


def get_voltage():
    try:
        import sim_runtime

        percentage = sim_runtime.battery_percentage()
    except Exception:
        percentage = 87
    return 3300 + int(percentage) * 800 // 100


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
