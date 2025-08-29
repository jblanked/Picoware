import board
from .input import Input
from .buttons import (
    BUTTON_UART,
    BUTTON_UP,
    BUTTON_DOWN,
    BUTTON_LEFT,
    BUTTON_RIGHT,
    BUTTON_KEYBOARD,
)
from .boards import Board, BOARD_TYPE_VGM, JBLANKED_BOARD_CONFIG, BOARD_TYPE_PICO_CALC


class InputManager:
    """
    InputManager class to handle the input events.

    @param inputs: The list of inputs to be managed.
    """

    def __init__(self, board_type: Board):
        self.input: int = -1
        self.inputs: list[Input] = []
        self.board: Board = board_type
        self.is_uart_input: bool = False
        self.is_keyboard_input: bool = False

        if board_type.board_type == BOARD_TYPE_VGM:
            self.inputs.append(Input(button=BUTTON_UART))
            self.is_uart_input = True
        elif board_type.board_type == JBLANKED_BOARD_CONFIG:
            self.inputs.append(Input(BUTTON_UP, board.GP16))
            self.inputs.append(Input(BUTTON_RIGHT, board.GP17))
            self.inputs.append(Input(BUTTON_DOWN, board.GP18))
            self.inputs.append(Input(BUTTON_LEFT, board.GP19))
        elif board_type.board_type == BOARD_TYPE_PICO_CALC:
            self.inputs.append(Input(button=BUTTON_KEYBOARD))
            self.is_keyboard_input = True
        else:
            pass  # Unknown board type

    def reset(self):
        """Reset input."""
        self.input = -1
        for inp in self.inputs:
            inp.last_button = -1
            if hasattr(inp, "keyboard_buffer"):
                inp.keyboard_buffer.clear()

    def run(self):
        """
        Run the input manager and check for input events.
        """
        if self.is_uart_input:
            self.inputs[0].run()
            self.input = self.inputs[0].last_button
            return
        elif self.is_keyboard_input:
            self.inputs[0].run()
            self.input = self.inputs[0].last_button
            return

        for inp in self.inputs:
            inp.run()
            if inp.is_pressed():
                self.input = inp.button
                break

    def get_keyboard_input(self) -> str:
        """
        Get keyboard input as a string. Only available for BOARD_TYPE_PICO_CALC.
        Returns empty string if no keyboard input or not a keyboard board.
        """
        if self.is_keyboard_input and len(self.inputs) > 0:
            return self.inputs[0].get_keyboard_string()
        return ""

    def has_keyboard_input(self) -> bool:
        """
        Check if there's keyboard input available. Only for BOARD_TYPE_PICO_CALC.
        """
        if self.is_keyboard_input and len(self.inputs) > 0:
            return self.inputs[0].has_keyboard_data()
        return False
