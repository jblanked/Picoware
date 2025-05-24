from time import monotonic
from digitalio import DigitalInOut, Direction
from microcontroller import Pin
from .uart import UART
from .buttons import (
    BUTTON_UP,
    BUTTON_DOWN,
    BUTTON_LEFT,
    BUTTON_RIGHT,
    BUTTON_CENTER,
    BUTTON_BACK,
    BUTTON_START,
    BUTTON_UART,
)


class Input:
    """
    Input class to handle the button presses.

    @param pin: The pin number of the button.
    @param button: The button to be checked.
    """

    def __init__(self, button: int, pin: Pin = None, debounce: float = 0.05):
        self.uart = None
        self.pin = None
        if button == BUTTON_UART:
            self.uart = UART()
        else:
            if pin is None:
                raise ValueError("Pin must be specified for non-UART buttons.")
            self.pin = DigitalInOut(pin)
            self.pin.direction = Direction.OUTPUT

        self.button = button
        self.elapsed_time = 0
        self.was_pressed = False
        self.last_button = 0
        self.start_time = monotonic()
        self.debounce = debounce

    def is_pressed(self) -> bool:
        """
        Return True if the button is pressed.
        Since we are pulling up the button, we need to check for a LOW value.
        """
        return self.pin.value

    def is_held(self, duration: int) -> bool:
        """
        Return True if the button is held for a certain duration.
        """

        return self.elapsed_time >= duration

    def run(self):
        """
        Track the button state and the elapsed time it was pressed.
        This should be looped in the main loop.
        """
        if self.uart:
            # check if it's been more than the debounce time since the last button press
            if monotonic() - self.start_time > self.debounce:
                self.last_button = -1
                self.start_time = monotonic()
                # Check if data is available to read
                if self.uart.available() > 0:
                    # Read the incoming byte as a character
                    incoming_char = ord(self.uart.read())
                    if incoming_char == 48:
                        self.last_button = BUTTON_UP
                    elif incoming_char == 49:
                        self.last_button = BUTTON_DOWN
                    elif incoming_char == 50:
                        self.last_button = BUTTON_LEFT
                    elif incoming_char == 51:
                        self.last_button = BUTTON_RIGHT
                    elif incoming_char == 52:
                        self.last_button = BUTTON_CENTER
                    elif incoming_char == 53:
                        self.last_button = BUTTON_BACK
                    elif incoming_char == 54:
                        self.last_button = BUTTON_START
            return
        if self.is_pressed():
            self.elapsed_time += 1
            self.was_pressed = True
        else:
            self.elapsed_time = 0
            self.was_pressed = False
