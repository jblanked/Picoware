"""Host keyboard transport for the firmware-native input module and engine."""

import picoware_keyboard
import sim_runtime


def init():
    picoware_keyboard.init()
    return True


def deinit():
    picoware_keyboard.deinit()


def read():
    # Native games poll here without returning to Python Input.button.
    sim_runtime.input_polled()
    key = picoware_keyboard.get_key_nonblocking()
    return -1 if key is None else key
