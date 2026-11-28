"""Input - Keyboard and touch input handling."""

import input_mp
from picoware.system import buttons
from picoware.system.boards import (
    BOARD_ID,
    BOARD_HAS_TOUCH,
    BOARD_PICO_DUO,
)


class Input(input_mp.Input):
    """Handles input from the keyboard."""

    __slots__ = (
        "_button_map",
        "_last_button",
        "_was_capitalized",
        "_uart",
    )

    def __init__(self, back_button=buttons.BUTTON_BACK):
        """Initialize the input manager for the current board.

        Args:
            back_button (int): The button code used as back. Defaults to buttons.BUTTON_BACK.
        """
        super().__init__(back_button)

        self._button_map = None
        self._last_button = -1
        self._was_capitalized = False
        self._uart = None

        if BOARD_ID == BOARD_PICO_DUO:
            from picoware.system.uart import UART

            self._uart = UART(0, 0, 1)
            self._uart.set_callback(self.__uart_callback)

            self._button_map = {
                b"\x04": buttons.BUTTON_UP,  # 4
                b"\x07": buttons.BUTTON_DOWN,  # 7
                b"\x08": buttons.BUTTON_LEFT,  # 8
                b"\x02": buttons.BUTTON_RIGHT,  # 2
                b"\x11": buttons.BUTTON_UP,  # 17
                b"\x12": buttons.BUTTON_DOWN,  # 18
                b"\x10": buttons.BUTTON_LEFT,  # 16
                b"\x0f": buttons.BUTTON_RIGHT,  # 15
                b"\x0d": buttons.BUTTON_CENTER,  # 13
                b"\x0c": buttons.BUTTON_BACK,  # 12
            }

    def __del__(self):
        """Destructor to clean up resources."""
        self.__deinit()

    @property
    def button(self) -> int:
        """Returns the last button pressed."""
        key = self.read()
        self._was_capitalized = 65 <= key <= 90
        return self.key_to_button(key)

    @property
    def has_touch_support(self) -> bool:
        """Returns True if touch input is supported on the current board."""
        return BOARD_HAS_TOUCH == 1

    @property
    def point(self) -> tuple:
        """Returns and clears the last touch point as (x, y)."""
        return self.get_point()

    @property
    def was_capitalized(self) -> bool:
        """Returns True if the last key pressed was a capital letter."""
        return self._was_capitalized

    def __deinit(self):
        """Deinitialize the input system."""
        self.reset()

        del self._button_map
        self._button_map = None

        self.deinit()

    def read(self) -> int:
        """Returns the key code as an integer.

        Returns:
            int: The button code corresponding to the last input.
        """
        if BOARD_ID == BOARD_PICO_DUO:
            return self._last_button

        return self.get_input()

    def reset(self) -> None:
        """Resets the input state."""
        self._last_button = -1
        self._was_capitalized = False

    def __uart_callback(self, uart_instance) -> None:
        """UART callback to handle incoming data.

        Args:
            uart_instance: The UART instance triggering the callback.
        """
        _data = uart_instance.read()
        if _data is None:
            return

        self._last_button = self._button_map.get(_data, buttons.BUTTON_NONE)
