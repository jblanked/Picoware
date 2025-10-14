class Input:
    """
    Handles input from the keyboard.
    """

    def __init__(self):
        """Initializes the Input class."""
        from picoware_keyboard import (
            init,
            set_background_poll,
            set_key_available_callback,
        )

        init()
        set_background_poll(True)
        set_key_available_callback(self.on_key_callback)

        self._elapsed_time = 0
        self._last_button = -1
        self._was_pressed = False
        self._was_capitalized = False

    def __del__(self):
        """Destructor to clean up resources."""
        self.reset()

    @property
    def battery(self) -> int:
        """Returns the current battery level as a percentage (0-100)."""
        from picoware_southbridge import read_battery

        return read_battery()

    @property
    def button(self) -> int:
        """Returns the last button pressed."""
        return self._last_button

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
            125: buttons.BUTTON_RIGHT_BRACE,  # }
        }

        if 65 <= key <= 90:
            self._was_capitalized = True

        return button_map.get(key, buttons.BUTTON_NONE)

    def get_last_button(self) -> int:
        """Returns the last button pressed."""
        return self._last_button

    def is_pressed(self) -> bool:
        """Returns True if any key is currently pressed."""
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
        __button = self.read_non_blocking()

        if __button == -1:
            self.reset()
            return

        self._was_capitalized = False
        self._last_button = self._key_to_button(__button)
        self._elapsed_time += 1
        self._was_pressed = True

    def read(self) -> int:
        """Returns the key code as an integer (blocking call).

        Returns:
            int: Key code (0-255)

        Warning:
            This is a blocking call and should not be used in callback contexts.
        """
        from picoware_keyboard import get_key

        return get_key()

    def read_non_blocking(self) -> int:
        """Returns the key code as integer, or -1 if no key is pressed."""
        from picoware_keyboard import get_key_nonblocking

        key = get_key_nonblocking()
        return key if key else -1

    def reset(self) -> None:
        """Resets the input state."""
        self._elapsed_time = 0
        self._was_pressed = False
        self._last_button = -1
        self._was_capitalized = False
