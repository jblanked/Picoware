from picoware.gui.textbox import TextBox


class TextEditor(TextBox):
    """
    A simple text editor built for Picoware.

    The callback is useful for saving to a file or updating a preview in real-time.
    """

    TYPE_ADD = 0
    TYPE_DELETE = 1

    def __init__(self, view_manager, callback: callable = None):
        """
        Initializes the TextEditor with a view manager and an optional callback for text changes.
        :param view_manager: The view manager to handle drawing and input.
        :param callback: A callable that takes two arguments (action_type, char) where action_type is either TYPE_ADD or TYPE_DELETE, and char is the character added (or None if deleted).
        """
        self._vm = view_manager
        self._callback = callback
        draw = view_manager.draw
        super().__init__(
            draw, 0, draw.height, draw.foreground, draw.background, True, True
        )

    @property
    def callback(self) -> callable:
        """Gets the current callback function."""
        return self._callback

    @callback.setter
    def callback(self, func: callable) -> None:
        """Sets the callback function for text changes."""
        self._callback = func

    def __process_text_input(self, button: int) -> None:
        """Process text input and update the textbox"""
        from picoware.system import buttons

        button_pressed = False
        inp = self._vm.input_manager
        char: str = inp.button_to_char(button)

        if char:
            self.current_text += char
            button_pressed = True
            if self._callback:
                self._callback(self.TYPE_ADD, char)
        elif button == buttons.BUTTON_BACKSPACE:
            self.current_text = self.current_text[:-1]
            button_pressed = True
            if self._callback:
                self._callback(self.TYPE_DELETE, None)

        if button_pressed:
            self.refresh()

    def run(self) -> bool:
        """Runs the text editor - call this every frame/tick."""
        from picoware.system.buttons import BUTTON_BACK

        inp = self._vm.input_manager
        but = inp.button

        if but == BUTTON_BACK:
            inp.reset()
            return False
        if but != -1:
            self.__process_text_input(but)
            inp.reset()
        return True
