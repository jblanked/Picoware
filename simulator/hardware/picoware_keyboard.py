import sim_runtime

_initialized = False
_last_key = -1
_game_mode = False
_buffered_input = False


def init():
    global _initialized, _game_mode, _last_key, _buffered_input
    if _initialized:
        return
    _initialized = True
    _game_mode = False
    _last_key = -1
    import picoware_boards

    _buffered_input = picoware_boards.BOARD_ID in (
        picoware_boards.BOARD_PICOCALC_PICO,
        picoware_boards.BOARD_PICOCALC_PICOW,
        picoware_boards.BOARD_PICOCALC_PICO_2,
        picoware_boards.BOARD_PICOCALC_PICO_2W,
        picoware_boards.BOARD_PICOCALC_PIMORONI_2W,
        picoware_boards.BOARD_DESKTOP,
        picoware_boards.BOARD_PICOCALC_ESP32_P4,
    )
    if _buffered_input:
        set_key_available_callback(_capture_key)
        set_background_poll(True)


def deinit():
    global _initialized, _game_mode, _last_key
    _game_mode = False
    _last_key = -1
    sim_runtime.set_background_key_poll(False)
    sim_runtime.register_key_callback(None)
    if _initialized:
        _initialized = False
        sim_runtime._keys = []


def set_background_poll(enable):
    sim_runtime.set_background_key_poll(bool(enable))


def set_key_available_callback(callback):
    if callback is not None and not callable(callback):
        raise TypeError("callback must be callable or None")
    sim_runtime.register_key_callback(callback)


def poll():
    if _initialized:
        sim_runtime.loop_polled()


def key_available():
    if not _initialized:
        return False
    sim_runtime.loop_polled()
    return sim_runtime.has_key()


def get_key():
    while not key_available():
        sim_runtime.loop_polled()
    return sim_runtime.pop_key()


def get_key_nonblocking():
    if not key_available():
        return None
    key = sim_runtime.pop_key()
    return None if key == -1 else key


def _capture_key(_=None):
    global _last_key
    key = get_key_nonblocking()
    _last_key = -1 if key is None else key


def _get_input():
    global _last_key
    if not _initialized:
        return -1
    if _game_mode or not _buffered_input:
        poll()
        key = get_key_nonblocking()
        return -1 if key is None else key
    key = _last_key
    _last_key = -1
    return key


def _set_game_mode(enable):
    global _game_mode
    enable = bool(enable)
    if not _initialized or not _buffered_input or _game_mode == enable:
        return
    _game_mode = enable
    set_background_poll(not enable)
    set_key_available_callback(None if enable else _capture_key)
