import sim_runtime


def init():
    return True


def deinit():
    return True


def poll():
    sim_runtime.loop_polled()
    return True


def key_available():
    sim_runtime.loop_polled()
    return sim_runtime.has_key()


def get_key():
    while not key_available():
        sim_runtime.loop_polled()
    return sim_runtime.pop_key()


def get_key_nonblocking():
    sim_runtime.loop_polled()
    key = sim_runtime.pop_key()
    return 0 if key == -1 else key
