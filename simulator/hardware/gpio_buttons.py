"""Waveshare GPIO buttons backed by Enter and Backspace host keys."""

import sim_runtime

_initialized = False
_callback = None


def init():
    global _initialized
    _initialized = True


def deinit():
    global _initialized, _callback
    _initialized = False
    _callback = None


def set_key_available_callback(callback):
    global _callback
    if callback is not None and not callable(callback):
        raise TypeError("callback must be callable or None")
    # Firmware stores this callback but does not invoke it; Input polls instead.
    _callback = callback


def key_available():
    return _initialized and sim_runtime.peek_key() in (8, 13)


def get_key():
    if key_available():
        return sim_runtime.pop_key()
    return 0
