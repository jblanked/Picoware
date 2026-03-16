import textbox


class TextEditor(textbox.TextBox):
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
        :param callback: A callable that takes three arguments (action_type, char, cursor_pos) where action_type is either TYPE_ADD or TYPE_DELETE, char is the character added (or None if deleted), and cursor_pos is the position of the cursor when the change occurred.
        """
        self._vm = view_manager
        self._callback = callback
        draw = view_manager.draw
        super().__init__(
            0,
            draw.height,
            draw.size.x,
            int(draw.size.x // draw.font_size.x),  # chars per line
            int(draw.size.x * 0.03125),  # spacing
            draw.foreground,  # foreground_color
            draw.background,  # background_color
            True,  # show_scrollbar
            True,  # show_cursor
        )

    def __setattr__(self, name, value):
        if name == "text":
            self._set_text(value)
        elif name == "cursor":
            self._set_cursor(value)
        elif name == "current_line":
            self._set_current_line(value)
        else:
            super().__setattr__(name, value)

    @property
    def callback(self) -> callable:
        """Gets the current callback function."""
        return self._callback

    @callback.setter
    def callback(self, func: callable) -> None:
        """Sets the callback function for text changes."""
        self._callback = func

    @property
    def current_text(self) -> str:
        """Returns the current text content of the text box."""
        return self.text

    @current_text.setter
    def current_text(self, value: str) -> None:
        self._set_text(value)

    def __process_text_input(self, button: int) -> None:
        """Process text input and update the textbox"""
        from picoware.system import buttons

        inp = self._vm.input_manager
        char: str = inp.button_to_char(button)

        if char:
            _pos = self.cursor
            self._insert_char(char)
            if self._callback:
                self._callback(self.TYPE_ADD, char, _pos)
        elif button == buttons.BUTTON_BACKSPACE:
            _pos = self.cursor
            self._delete_char()
            if self._callback:
                self._callback(self.TYPE_DELETE, None, _pos)

    def refresh(self) -> None:
        """Refresh the text editor display."""
        self.render()

    def run(self) -> bool:
        """Runs the text editor - call this every frame/tick."""
        from picoware.system import buttons

        inp = self._vm.input_manager
        but = inp.button

        if but == buttons.BUTTON_BACK:
            inp.reset()
            return False
        if but == buttons.BUTTON_UP:
            inp.reset()
            self._cursor_up()
        elif but == buttons.BUTTON_DOWN:
            inp.reset()
            self._cursor_down()
        elif but == buttons.BUTTON_LEFT:
            inp.reset()
            self.cursor -= 1
        elif but == buttons.BUTTON_RIGHT:
            inp.reset()
            self.cursor += 1
        elif but != buttons.BUTTON_NONE:
            self.__process_text_input(but)
            inp.reset()
        return True

    def set_text(self, text: str) -> None:
        """Sets the text content of the text box."""
        self._set_text(text)
