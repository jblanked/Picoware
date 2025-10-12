class Input:
    """Handles input from the keyboard."""

    def __init__(self):
        from picoware.system.drivers.PicoKeyboard import PicoKeyboard

        self._elapsed_time = 0
        self._last_button = -1
        self._was_pressed = False
        self.keyboard = PicoKeyboard()
        self._shift_held = False
        self._ctrl_held = False
        self._alt_held = False
        self._caps_lock = False
        self._was_capitalized = False
        self._last_shift_time = 0
        self._shift_timeout = 1000

    def __del__(self):
        """Destructor to clean up resources."""
        if self.keyboard:
            del self.keyboard
            self.keyboard = None
        self.reset()

    @property
    def button(self) -> int:
        """Returns the last button pressed."""
        return self._last_button

    def is_alt_held(self) -> bool:
        """Returns True if alt is currently held."""
        return self._alt_held

    def is_caps_lock_active(self) -> bool:
        """Returns True if caps lock is currently active."""
        return self._caps_lock

    def is_ctrl_held(self) -> bool:
        """Returns True if ctrl is currently held."""
        return self._ctrl_held

    def is_shift_held(self) -> bool:
        """Returns True if shift is currently held."""
        return self._shift_held

    def _key_to_button(self, key: int) -> int:
        """Maps a key to a button."""
        import picoware.system.buttons as buttons

        shift_held = self._shift_held

        shifted_char_map = {
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
            58: buttons.BUTTON_COLON,  # :
            60: buttons.BUTTON_LESS_THAN,  # <
            62: buttons.BUTTON_GREATER_THAN,  # >
            63: buttons.BUTTON_QUESTION,  # ?
            64: buttons.BUTTON_AT,  # @
            94: buttons.BUTTON_CARET,  # ^
            95: buttons.BUTTON_UNDERSCORE,  # _
            123: buttons.BUTTON_LEFT_BRACE,  # {
            125: buttons.BUTTON_RIGHT_BRACE,  # }
        }

        if key in shifted_char_map:
            self._shift_held = False
            return shifted_char_map[key]

        if shift_held:
            shifted_number_map = {
                48: buttons.BUTTON_RIGHT_PARENTHESIS,  # Shift + 0 = )
                49: buttons.BUTTON_EXCLAMATION,  # Shift + 1 = !
                50: buttons.BUTTON_AT,  # Shift + 2 = @
                51: buttons.BUTTON_HASH,  # Shift + 3 = #
                52: buttons.BUTTON_DOLLAR,  # Shift + 4 = $
                53: buttons.BUTTON_PERCENT,  # Shift + 5 = %
                54: buttons.BUTTON_CARET,  # Shift + 6 = ^
                55: buttons.BUTTON_AMPERSAND,  # Shift + 7 = &
                56: buttons.BUTTON_ASTERISK,  # Shift + 8 = *
                57: buttons.BUTTON_LEFT_PARENTHESIS,  # Shift + 9 = (
            }
            if key in shifted_number_map:
                self._shift_held = False
                return shifted_number_map[key]

        button_map = {
            #
            8: buttons.BUTTON_BACK,
            10: buttons.BUTTON_CENTER,
            buttons.KEY_UP: buttons.BUTTON_UP,
            buttons.KEY_DOWN: buttons.BUTTON_DOWN,
            buttons.KEY_LEFT: buttons.BUTTON_LEFT,
            buttons.KEY_RIGHT: buttons.BUTTON_RIGHT,
            # modifier keys
            buttons.KEY_ESC: buttons.BUTTON_ESCAPE,
            buttons.KEY_MOD_SHL: buttons.BUTTON_SHIFT,
            buttons.KEY_MOD_SHR: buttons.BUTTON_SHIFT,
            buttons.KEY_MOD_CTRL: buttons.BUTTON_CONTROL,
            buttons.KEY_MOD_ALT: buttons.BUTTON_ALT,
            buttons.KEY_HOME: buttons.BUTTON_HOME,
            buttons.KEY_DEL: buttons.BUTTON_BACKSPACE,
            buttons.KEY_CAPS_LOCK: buttons.BUTTON_CAPS_LOCK,
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
            # alphabet keys (uppercase - for caps lock)
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
            # special keys
            9: buttons.BUTTON_TAB,
            32: buttons.BUTTON_SPACE,
            44: buttons.BUTTON_COMMA,
            45: buttons.BUTTON_MINUS,
            46: buttons.BUTTON_PERIOD,
            47: buttons.BUTTON_SLASH,
            59: buttons.BUTTON_SEMICOLON,
            61: buttons.BUTTON_EQUAL,
            91: buttons.BUTTON_LEFT_BRACKET,
            92: buttons.BUTTON_BACKSLASH,
            93: buttons.BUTTON_RIGHT_BRACKET,
        }

        # set capital letters if shift is held or caps lock is active
        # Check both lowercase (97-122) and uppercase (65-90) key codes
        if (97 <= key <= 122 and (shift_held or self._caps_lock)) or (65 <= key <= 90):
            self._was_capitalized = True

        return button_map.get(key, buttons.BUTTON_NONE)

    def get_last_button(self) -> int:
        """Returns the last button pressed."""
        return self._last_button

    def is_pressed(self) -> bool:
        """Returns True if any key is currently pressed."""
        return self.keyboard.keyCount() > 0

    def is_held(self, duration: int = 3) -> bool:
        """Returns True if the last button was held for the specified duration."""
        return self._was_pressed and self._elapsed_time >= duration

    def read(self) -> int:
        """Returns the key pressed or -1 if no key is pressed."""
        key_event = self.keyboard.keyEvent()
        if key_event:
            state = key_event[0]
            key = key_event[1]
            if state in (1, 2):
                return key
        return -1

    def read_non_blocking(self) -> int:
        """Returns the key pressed or -1 if no key is pressed."""
        if self.keyboard.keyCount() > 0:
            key_event = self.keyboard.keyEvent()
            if key_event:
                state = key_event[0]
                key = key_event[1]
                if state in (1, 2):
                    return key
        return -1

    def reset(self) -> None:
        """Resets the input state."""
        self._elapsed_time = 0
        self._was_pressed = False
        self._last_button = -1
        self._shift_held = False

    def run(self) -> None:
        """Runs the input state machine and sets the current button state."""
        from picoware.system.buttons import (
            KEY_MOD_SHL,
            KEY_MOD_SHR,
            KEY_MOD_CTRL,
            KEY_MOD_ALT,
            KEY_CAPS_LOCK,
        )

        _button = self.read_non_blocking()
        if _button != -1:
            if _button in (KEY_MOD_SHL, KEY_MOD_SHR):
                from utime import ticks_ms, ticks_diff

                current_time_ms = ticks_ms()

                # Check if enough time has passed since the last shift press
                if (
                    ticks_diff(current_time_ms, self._last_shift_time)
                    >= self._shift_timeout
                ):
                    self._shift_held = True
                    self._was_capitalized = False
                    self._last_shift_time = current_time_ms
                return
            if _button == KEY_MOD_CTRL:
                self._ctrl_held = True
                return
            if _button == KEY_MOD_ALT:
                self._alt_held = True
                return
            if _button == KEY_CAPS_LOCK:
                self._caps_lock = not self._caps_lock

            self._last_button = self._key_to_button(_button)
            self._elapsed_time += 1
            self._was_pressed = True

            if _button not in (KEY_MOD_SHL, KEY_MOD_SHR):
                self._shift_held = False
            if _button != KEY_MOD_CTRL:
                self._ctrl_held = False
            if _button != KEY_MOD_ALT:
                self._alt_held = False
        else:
            self._last_button = -1
            self._was_pressed = False
            self._elapsed_time = 0
