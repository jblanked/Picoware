import sim_runtime

_initialized = False


def init():
    global _initialized
    _initialized = True
    return True


def deinit():
    global _initialized
    _initialized = False
    sim_runtime.set_background_key_poll(False)
    sim_runtime.register_key_callback(None)
    return True


def set_background_poll(enable):
    sim_runtime.set_background_key_poll(bool(enable))


def set_key_available_callback(callback):
    if callback is not None and not callable(callback):
        raise TypeError("callback must be callable or None")
    sim_runtime.register_key_callback(callback)


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
