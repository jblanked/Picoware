import board
from .input import Input
from .buttons import BUTTON_UART, BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT
from .boards import Board, BOARD_TYPE_VGM, JBLANKED_BOARD_CONFIG


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
        if board_type.board_type == BOARD_TYPE_VGM:
            self.inputs.append(Input(button=BUTTON_UART))
            self.is_uart_input = True
        elif board_type.board_type == JBLANKED_BOARD_CONFIG:
            self.inputs.append(Input(BUTTON_UP, board.GP16))
            self.inputs.append(Input(BUTTON_RIGHT, board.GP17))
            self.inputs.append(Input(BUTTON_DOWN, board.GP18))
            self.inputs.append(Input(BUTTON_LEFT, board.GP19))
        else:
            pass  # PicoCalc

    def reset(self):
        """Reset input."""
        self.input = -1
        for inp in self.inputs:
            inp.last_button = -1

    def run(self):
        """
        Run the input manager and check for input events.
        """
        if self.is_uart_input:
            self.inputs[0].run()
            self.input = self.inputs[0].last_button
            return
        for inp in self.inputs:
            inp.run()
            if inp.is_pressed():
                self.input = inp.button
                break
