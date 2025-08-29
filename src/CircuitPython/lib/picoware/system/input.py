from time import monotonic
from digitalio import DigitalInOut, Direction
from microcontroller import Pin
from .uart import UART
from .keyboard import Keyboard
from .buttons import (
    BUTTON_UP,
    BUTTON_DOWN,
    BUTTON_LEFT,
    BUTTON_RIGHT,
    BUTTON_CENTER,
    BUTTON_BACK,
    BUTTON_START,
    BUTTON_UART,
    BUTTON_KEYBOARD,
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
        self.keyboard = None
        self.keyboard_buffer = bytearray(32)  # Buffer for keyboard input
        self.keyboard_string_buffer = ""

        if button == BUTTON_UART:
            self.uart = UART()
        elif button == BUTTON_KEYBOARD:
            self.keyboard = Keyboard()
        else:
            if pin is None:
                raise ValueError(
                    "Pin must be specified for non-UART/non-keyboard buttons."
                )
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

    def has_keyboard_data(self) -> bool:
        """
        Check if there's keyboard data available.
        """
        return len(self.keyboard_string_buffer) > 0

    def get_keyboard_string(self) -> str:
        """
        Get the accumulated keyboard input as a string and clear the buffer.
        """
        if self.keyboard_string_buffer:
            result = self.keyboard_string_buffer
            self.keyboard_string_buffer = ""
            return result
        return ""

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

        elif self.keyboard:
            # Handle keyboard input
            if monotonic() - self.start_time > self.debounce:
                self.last_button = -1
                self.start_time = monotonic()

                # Clear the buffer first
                for i in range(len(self.keyboard_buffer)):
                    self.keyboard_buffer[i] = 0

                # Try to read keyboard input
                keys_read = self.keyboard.readinto(self.keyboard_buffer)
                if keys_read and keys_read > 0:
                    # Convert bytes to string and add to buffer
                    try:
                        # Process the keyboard input
                        for i in range(keys_read):
                            key_byte = self.keyboard_buffer[i]
                            if key_byte != 0:
                                # Handle special keys and escape sequences
                                if (
                                    key_byte == 0x1B
                                ):  # ESC character - start of escape sequence
                                    # Look ahead to see if this is an escape sequence
                                    if (
                                        i + 1 < keys_read
                                        and self.keyboard_buffer[i + 1] == 0x1B
                                    ):
                                        # Double ESC = actual ESC key
                                        self.last_button = BUTTON_BACK
                                        break
                                    elif i + 2 < keys_read and self.keyboard_buffer[
                                        i + 1
                                    ] == ord("["):
                                        # Arrow key or other escape sequence
                                        third_char = self.keyboard_buffer[i + 2]
                                        if third_char == ord("A"):  # Up arrow
                                            self.last_button = BUTTON_UP
                                            break
                                        elif third_char == ord("B"):  # Down arrow
                                            self.last_button = BUTTON_DOWN
                                            break
                                        elif third_char == ord("C"):  # Right arrow
                                            self.last_button = BUTTON_RIGHT
                                            break
                                        elif third_char == ord("D"):  # Left arrow
                                            self.last_button = BUTTON_LEFT
                                            break
                                elif (
                                    key_byte == 0x0D or key_byte == 0x0A
                                ):  # Enter/Return
                                    self.last_button = BUTTON_CENTER
                                    break
                                elif (
                                    32 <= key_byte <= 126
                                ):  # Printable ASCII characters
                                    self.keyboard_string_buffer += chr(key_byte)
                                elif (
                                    key_byte == 0x7F or key_byte == 0x08
                                ):  # Backspace/DEL
                                    if self.keyboard_string_buffer:
                                        self.keyboard_string_buffer = (
                                            self.keyboard_string_buffer[:-1]
                                        )
                    except Exception as e:
                        # Handle any conversion errors
                        print(f"Keyboard input error: {e}")
                        pass
            return

        # Handle regular GPIO buttons
        if self.is_pressed():
            self.elapsed_time += 1
            self.was_pressed = True
        else:
            self.elapsed_time = 0
            self.was_pressed = False
