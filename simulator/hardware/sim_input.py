"""Host keyboard transport for the firmware-native input module and engine."""

import picoware_keyboard
import sim_runtime
import picoware_boards

_touch_pressed = False
_touch_sample = (0, 0, 0, False)


def init():
    global _touch_pressed, _touch_sample
    _touch_pressed = False
    _touch_sample = (0, 0, 0, False)
    picoware_keyboard.init()
    return True


def deinit():
    picoware_keyboard.deinit()


def touch_state():
    return _touch_sample


def _touch_button(x, y):
    width, height = picoware_boards.get_display_size(picoware_boards.BOARD_ID)
    if x <= width * 15 // 100 and y <= height * 12 // 100:
        return 5
    if x >= width * 85 // 100 and height * 30 // 100 <= y <= height * 70 // 100:
        return 2
    if x <= width * 15 // 100 and height * 30 // 100 <= y <= height * 70 // 100:
        return 3
    if width * 20 // 100 <= x <= width * 80 // 100 and y <= height * 20 // 100:
        return 0
    if width * 20 // 100 <= x <= width * 80 // 100 and y >= height * 80 // 100:
        return 1
    if width * 40 // 100 <= x <= width * 60 // 100 and height * 40 // 100 <= y <= height * 60 // 100:
        return 4
    return -1


def read():
    global _touch_pressed, _touch_sample
    # Native games poll here without returning to Python Input.button.
    sim_runtime.input_polled()
    if picoware_boards.BOARD_HAS_TOUCH:
        x, y = sim_runtime.touch_point()
        gesture_board = picoware_boards.BOARD_ID == picoware_boards.BOARD_WAVESHARE_1_28_RP2350
        gesture = sim_runtime.touch_gesture() if gesture_board else 0
        pressed = (x, y) != (0, 0)
        _touch_sample = (x, y, gesture, pressed)
        if not pressed:
            _touch_pressed = False
        elif not _touch_pressed:
            _touch_pressed = True
            if gesture_board:
                from waveshare_touch import (TOUCH_GESTURE_UP, TOUCH_GESTURE_DOWN,
                    TOUCH_GESTURE_RIGHT, TOUCH_GESTURE_LEFT, TOUCH_GESTURE_CLICK,
                    TOUCH_GESTURE_LONG_PRESS)
                return {TOUCH_GESTURE_UP: 0, TOUCH_GESTURE_DOWN: 1,
                    TOUCH_GESTURE_RIGHT: 2, TOUCH_GESTURE_LEFT: 3,
                    TOUCH_GESTURE_CLICK: 4, TOUCH_GESTURE_LONG_PRESS: 5}.get(gesture, -1)
            return _touch_button(x, y)
    else:
        _touch_sample = (0, 0, 0, False)
    key = picoware_keyboard.get_key_nonblocking()
    return -1 if key is None else key
