class Input:
    """
    Handles input from the keyboard.
    """

    def __init__(self):
        """Initializes the Input class."""
        from picoware_boards import get_current_id
        from picoware.system.boards import (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
        )

        self._current_board_id = get_current_id()
        self.pin = None
        self._last_point = (0, 0)
        self._last_gesture = 0  # 0 is TOUCH_GESTURE_NONE

        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            from waveshare_touch import init, TOUCH_GESTURE_MODE, TOUCH_GESTURE_NONE
            from machine import Pin

            # Initialize touch in gesture mode
            init(TOUCH_GESTURE_MODE)
            # set pin
            self.pin = Pin(21, Pin.IN, Pin.PULL_UP)
            # set callback
            self.pin.irq(handler=self.__touch_callback, trigger=Pin.IRQ_FALLING)

            self._last_point = (0, 0)
            self._last_gesture = TOUCH_GESTURE_NONE
        elif self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_touch import init
            from machine import Pin

            # Initialize touch in gesture mode
            init()
            # set pin
            self.pin = Pin(20, Pin.IN, Pin.PULL_UP)
            # set callback
            self.pin.irq(handler=self.__touch_callback, trigger=Pin.IRQ_FALLING)

            self._last_point = (0, 0)

        else:
            from picoware_keyboard import (
                init,
                set_background_poll,
                set_key_available_callback,
            )

            init()
            set_background_poll(True)
            set_key_available_callback(self.on_key_callback)

        self._elapsed_time = 0
        self._elapsed_touch_start = 0
        self._elapsed_touch_now = 0
        self._delay_ms = 100  # milliseconds (for Touch input polling)
        self._last_button = -1
        self._was_pressed = False
        self._was_capitalized = False

    def __del__(self):
        """Destructor to clean up resources."""
        self.reset()
        if self.pin is not None:
            self.pin.irq(handler=None)
            del self.pin
            self.pin = None

    @property
    def battery(self) -> int:
        """Returns the current battery level as a percentage (0-100)."""
        from picoware.system.boards import (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
        )

        if self._current_board_id in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
        ):
            from waveshare_battery import get_percentage

            return get_percentage()

        from picoware_southbridge import get_battery_percentage

        return get_battery_percentage()

    @property
    def button(self) -> int:
        """Returns the last button pressed."""
        return self._last_button

    @property
    def gesture(self):
        """Returns the last touch gesture."""
        return self._last_gesture

    @property
    def has_touch_support(self) -> bool:
        """Returns True if touch input is supported on the current board."""
        from picoware.system.boards import (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
        )

        return self._current_board_id in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
        )

    @property
    def point(self) -> tuple:
        """Returns the last touch point as (x, y)."""
        return self._last_point

    @property
    def was_capitalized(self) -> bool:
        """Returns True if the last key pressed was a capital letter."""
        return self._was_capitalized

    def _key_to_button(self, key) -> int:
        """Maps a key to a button.

        Args:
            key: Key code as integer (from C module) or string (for compatibility)
        """
        import picoware.system.buttons as buttons

        button_map = {
            buttons.KEY_UP: buttons.BUTTON_UP,
            buttons.KEY_DOWN: buttons.BUTTON_DOWN,
            buttons.KEY_LEFT: buttons.BUTTON_LEFT,
            buttons.KEY_RIGHT: buttons.BUTTON_RIGHT,
            buttons.KEY_ESC: buttons.BUTTON_ESCAPE,
            buttons.KEY_HOME: buttons.BUTTON_HOME,
            buttons.KEY_DEL: buttons.BUTTON_BACKSPACE,
            8: buttons.BUTTON_BACK,
            9: buttons.BUTTON_TAB,
            13: buttons.BUTTON_CENTER,
            # special keys
            32: buttons.BUTTON_SPACE,
            33: buttons.BUTTON_EXCLAMATION,  # !
            34: buttons.BUTTON_DOUBLE_QUOTE,  # "
            35: buttons.BUTTON_HASH,  # #
            36: buttons.BUTTON_DOLLAR,  # $
            37: buttons.BUTTON_PERCENT,  # %
            38: buttons.BUTTON_AMPERSAND,  # &
            39: buttons.BUTTON_SINGLE_QUOTE,  # '
            40: buttons.BUTTON_LEFT_PARENTHESIS,  # (
            41: buttons.BUTTON_RIGHT_PARENTHESIS,  # )
            42: buttons.BUTTON_ASTERISK,  # *
            43: buttons.BUTTON_PLUS,  # +
            44: buttons.BUTTON_COMMA,
            45: buttons.BUTTON_MINUS,
            46: buttons.BUTTON_PERIOD,
            47: buttons.BUTTON_SLASH,
            # numbers
            48: buttons.BUTTON_0,
            49: buttons.BUTTON_1,
            50: buttons.BUTTON_2,
            51: buttons.BUTTON_3,
            52: buttons.BUTTON_4,
            53: buttons.BUTTON_5,
            54: buttons.BUTTON_6,
            55: buttons.BUTTON_7,
            56: buttons.BUTTON_8,
            57: buttons.BUTTON_9,
            # special characters
            58: buttons.BUTTON_COLON,  # :
            59: buttons.BUTTON_SEMICOLON,
            60: buttons.BUTTON_LESS_THAN,  # <
            61: buttons.BUTTON_EQUAL,
            62: buttons.BUTTON_GREATER_THAN,  # >
            63: buttons.BUTTON_QUESTION,  # ?
            64: buttons.BUTTON_AT,  # @
            # alphabet keys
            65: buttons.BUTTON_A,
            66: buttons.BUTTON_B,
            67: buttons.BUTTON_C,
            68: buttons.BUTTON_D,
            69: buttons.BUTTON_E,
            70: buttons.BUTTON_F,
            71: buttons.BUTTON_G,
            72: buttons.BUTTON_H,
            73: buttons.BUTTON_I,
            74: buttons.BUTTON_J,
            75: buttons.BUTTON_K,
            76: buttons.BUTTON_L,
            77: buttons.BUTTON_M,
            78: buttons.BUTTON_N,
            79: buttons.BUTTON_O,
            80: buttons.BUTTON_P,
            81: buttons.BUTTON_Q,
            82: buttons.BUTTON_R,
            83: buttons.BUTTON_S,
            84: buttons.BUTTON_T,
            85: buttons.BUTTON_U,
            86: buttons.BUTTON_V,
            87: buttons.BUTTON_W,
            88: buttons.BUTTON_X,
            89: buttons.BUTTON_Y,
            90: buttons.BUTTON_Z,
            # special characters
            91: buttons.BUTTON_LEFT_BRACKET,
            92: buttons.BUTTON_BACKSLASH,
            93: buttons.BUTTON_RIGHT_BRACKET,
            94: buttons.BUTTON_CARET,  # ^
            95: buttons.BUTTON_UNDERSCORE,  # _
            96: buttons.BUTTON_BACK_TICK,  # `
            # alphabet keys (lowercase)
            97: buttons.BUTTON_A,
            98: buttons.BUTTON_B,
            99: buttons.BUTTON_C,
            100: buttons.BUTTON_D,
            101: buttons.BUTTON_E,
            102: buttons.BUTTON_F,
            103: buttons.BUTTON_G,
            104: buttons.BUTTON_H,
            105: buttons.BUTTON_I,
            106: buttons.BUTTON_J,
            107: buttons.BUTTON_K,
            108: buttons.BUTTON_L,
            109: buttons.BUTTON_M,
            110: buttons.BUTTON_N,
            111: buttons.BUTTON_O,
            112: buttons.BUTTON_P,
            113: buttons.BUTTON_Q,
            114: buttons.BUTTON_R,
            115: buttons.BUTTON_S,
            116: buttons.BUTTON_T,
            117: buttons.BUTTON_U,
            118: buttons.BUTTON_V,
            119: buttons.BUTTON_W,
            120: buttons.BUTTON_X,
            121: buttons.BUTTON_Y,
            122: buttons.BUTTON_Z,
            123: buttons.BUTTON_LEFT_BRACE,  # {
            124: buttons.BUTTON_PIPE,  # |
            125: buttons.BUTTON_RIGHT_BRACE,  # }
            126: buttons.BUTTON_TILDE,  # ~
        }

        if 65 <= key <= 90:
            self._was_capitalized = True

        return button_map.get(key, buttons.BUTTON_NONE)

    def button_to_char(self, button: int) -> str:
        """Converts a button code to its corresponding character.

        Args:
            button (int): Button code.

        Returns:
            str: Corresponding character or empty string if no mapping exists.
        """
        import picoware.system.buttons as buttons

        character_map = {
            buttons.BUTTON_A: "a",
            buttons.BUTTON_B: "b",
            buttons.BUTTON_C: "c",
            buttons.BUTTON_D: "d",
            buttons.BUTTON_E: "e",
            buttons.BUTTON_F: "f",
            buttons.BUTTON_G: "g",
            buttons.BUTTON_H: "h",
            buttons.BUTTON_I: "i",
            buttons.BUTTON_J: "j",
            buttons.BUTTON_K: "k",
            buttons.BUTTON_L: "l",
            buttons.BUTTON_M: "m",
            buttons.BUTTON_N: "n",
            buttons.BUTTON_O: "o",
            buttons.BUTTON_P: "p",
            buttons.BUTTON_Q: "q",
            buttons.BUTTON_R: "r",
            buttons.BUTTON_S: "s",
            buttons.BUTTON_T: "t",
            buttons.BUTTON_U: "u",
            buttons.BUTTON_V: "v",
            buttons.BUTTON_W: "w",
            buttons.BUTTON_X: "x",
            buttons.BUTTON_Y: "y",
            buttons.BUTTON_Z: "z",
            #
            buttons.BUTTON_0: "0",
            buttons.BUTTON_1: "1",
            buttons.BUTTON_2: "2",
            buttons.BUTTON_3: "3",
            buttons.BUTTON_4: "4",
            buttons.BUTTON_5: "5",
            buttons.BUTTON_6: "6",
            buttons.BUTTON_7: "7",
            buttons.BUTTON_8: "8",
            buttons.BUTTON_9: "9",
            #
            buttons.BUTTON_CENTER: "\n",
            buttons.BUTTON_SPACE: " ",
            buttons.BUTTON_PERIOD: ".",
            buttons.BUTTON_QUESTION: "?",
            buttons.BUTTON_COMMA: ",",
            buttons.BUTTON_SEMICOLON: ";",
            buttons.BUTTON_MINUS: "-",
            buttons.BUTTON_EQUAL: "=",
            buttons.BUTTON_LEFT_BRACKET: "[",
            buttons.BUTTON_LEFT_BRACE: "{",
            buttons.BUTTON_RIGHT_BRACKET: "]",
            buttons.BUTTON_RIGHT_BRACE: "}",
            buttons.BUTTON_SLASH: "/",
            buttons.BUTTON_BACKSLASH: "\\",
            buttons.BUTTON_UNDERSCORE: "_",
            buttons.BUTTON_COLON: ":",
            buttons.BUTTON_SINGLE_QUOTE: "'",
            buttons.BUTTON_DOUBLE_QUOTE: '"',
            buttons.BUTTON_PLUS: "+",
            #
            buttons.BUTTON_EXCLAMATION: "!",
            buttons.BUTTON_AT: "@",
            buttons.BUTTON_HASH: "#",
            buttons.BUTTON_DOLLAR: "$",
            buttons.BUTTON_PERCENT: "%",
            buttons.BUTTON_CARET: "^",
            buttons.BUTTON_AMPERSAND: "&",
            buttons.BUTTON_ASTERISK: "*",
            buttons.BUTTON_LEFT_PARENTHESIS: "(",
            buttons.BUTTON_RIGHT_PARENTHESIS: ")",
            buttons.BUTTON_LESS_THAN: "<",
            buttons.BUTTON_GREATER_THAN: ">",
            buttons.BUTTON_BACK_TICK: "`",
            buttons.BUTTON_TILDE: "~",
            buttons.BUTTON_PIPE: "|",
        }

        if button in character_map:
            char_to_add = character_map[button]
            if self._was_capitalized and char_to_add.isalpha():
                char_to_add = char_to_add.upper()
            return char_to_add
        return ""

    def is_pressed(self) -> bool:
        """Returns True if any key is currently pressed."""
        from picoware.system.boards import (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
        )

        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return self._last_gesture != 0  # 0 is TOUCH_GESTURE_NONE
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            return self._last_point != (0, 0)
        from picoware_keyboard import key_available

        return key_available()

    def is_held(self, duration: int = 3) -> bool:
        """Returns True if the last button was held for the specified duration."""
        return self._was_pressed and self._elapsed_time >= duration

    def on_key_callback(self, _=None) -> None:
        """Callback invoked when a key becomes available.

        Args:
            _: Unused argument (required by mp_sched_schedule)
        """
        try:
            __button = self.read_non_blocking()

            if __button == -1:
                self.reset()
                return

            self._was_capitalized = False
            self._last_button = self._key_to_button(__button)
            self._elapsed_time += 1
            self._was_pressed = True
        except Exception as e:
            raise e

    def read(self) -> int:
        """Returns the key code as an integer (blocking call).

        Returns:
            int: Key code (0-255)

        Warning:
            This is a blocking call and should not be used in callback contexts.
        """
        if self.has_touch_support:
            return -1  # Not applicable for touch input
        from picoware_keyboard import get_key

        return get_key()

    def read_non_blocking(self) -> int:
        """Returns the key code as integer, or -1 if no key is pressed."""
        if self.has_touch_support:
            return -1  # Not applicable for touch input
        from picoware_keyboard import get_key_nonblocking

        key = get_key_nonblocking()
        return key if key else -1

    def reset(self) -> None:
        """Resets the input state."""
        from picoware.system.boards import (
            BOARD_WAVESHARE_1_43_RP2350,
        )

        self._elapsed_time = 0
        self._was_pressed = False
        self._last_button = -1
        self._was_capitalized = False
        self._last_point = (0, 0)
        self._last_gesture = 0  # 0 is TOUCH_GESTURE_NONE

        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_touch import reset_state

            reset_state()

    def __touch_callback(self, pin):
        """Touch interrupt callback function"""
        from picoware.system.boards import (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
        )

        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            from waveshare_touch import (
                get_gesture,
                TOUCH_GESTURE_NONE,
                TOUCH_GESTURE_UP,
                TOUCH_GESTURE_DOWN,
                TOUCH_GESTURE_LEFT,
                TOUCH_GESTURE_RIGHT,
                TOUCH_GESTURE_LONG_PRESS,
                TOUCH_GESTURE_CLICK,
                get_touch_point,
            )

            self._last_gesture = get_gesture()
            if self._last_gesture != TOUCH_GESTURE_NONE:

                from utime import ticks_ms

                self._elapsed_touch_now = int(ticks_ms())

                if self._elapsed_touch_now - self._elapsed_touch_start < self._delay_ms:
                    self._last_gesture = TOUCH_GESTURE_NONE
                    return

                self._elapsed_touch_start = self._elapsed_touch_now

                import picoware.system.buttons as buttons

                self._last_point = get_touch_point()

                # set last button based on gesture
                gesture_to_button = {
                    TOUCH_GESTURE_UP: buttons.BUTTON_UP,
                    TOUCH_GESTURE_DOWN: buttons.BUTTON_DOWN,
                    TOUCH_GESTURE_LEFT: buttons.BUTTON_LEFT,
                    TOUCH_GESTURE_RIGHT: buttons.BUTTON_RIGHT,
                    TOUCH_GESTURE_LONG_PRESS: buttons.BUTTON_BACK,
                    TOUCH_GESTURE_CLICK: buttons.BUTTON_CENTER,
                }
                self._last_button = gesture_to_button.get(
                    self._last_gesture, buttons.BUTTON_NONE
                )
                self._elapsed_time += 1
                self._was_pressed = True

        elif self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_touch import get_touch_point

            self._last_point = get_touch_point()

            if self._last_point != (0, 0):

                from utime import ticks_ms

                self._elapsed_touch_now = int(ticks_ms())

                if self._elapsed_touch_now - self._elapsed_touch_start < self._delay_ms:
                    self._last_point = (0, 0)
                    return

                self._elapsed_touch_start = self._elapsed_touch_now

                x, y = self._last_point
                import picoware.system.buttons as buttons

                # Right:
                # x: 430-466
                # y: 150-350

                # Left:
                # x: 0 - 36
                # y: 150-350

                # Up:
                # x: 150-300
                # y: 0-36

                # Down:
                # x: 150-300
                # y: 430-466

                if 430 <= x <= 466 and 150 <= y <= 350:
                    self._last_button = buttons.BUTTON_RIGHT
                elif 0 <= x <= 36 and 150 <= y <= 350:
                    self._last_button = buttons.BUTTON_LEFT
                elif 150 <= x <= 300 and 0 <= y <= 36:
                    self._last_button = buttons.BUTTON_UP
                elif 150 <= x <= 300 and 430 <= y <= 466:
                    self._last_button = buttons.BUTTON_DOWN
                else:
                    self._last_button = buttons.BUTTON_CENTER

                self._elapsed_time += 1
                self._was_pressed = True
