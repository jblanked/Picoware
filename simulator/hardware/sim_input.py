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
    return picoware_keyboard._get_input()


def game_mode(enable):
    picoware_keyboard._set_game_mode(enable)
