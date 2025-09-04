class Input:
    """Handles input from the keyboard."""

    def __init__(self):
        from picoware.system.drivers.PicoKeyboard import PicoKeyboard

        self._elapsed_time = 0
        self._last_button = -1
        self._was_pressed = False
        self.debounce = 0.01
        self.keyboard = PicoKeyboard()

    def _key_to_button(self, key: int) -> int:
        """Maps a key to a button."""
        import picoware.system.buttons as buttons

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
            # alphabet keys
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

    def reset(self, should_delay, delay_ms: int = 150) -> None:
        """Resets the input state."""
        self._elapsed_time = 0
        self._was_pressed = False
        self._last_button = -1
        if should_delay:
            # sleep_ms(delay_ms);
            pass

    def run(self) -> None:
        """Runs the input state machine and sets the current button state."""
        _button = self.read_non_blocking()
        if _button != -1:
            self._last_button = self._key_to_button(_button)
            self._elapsed_time += 1
            self._was_pressed = True
        else:
            self._last_button = -1
            self._was_pressed = False
            self._elapsed_time = 0
