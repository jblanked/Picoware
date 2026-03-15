from picoware.gui.textbox import TextBox


class TextEditor(TextBox):
    """
    A simple text editor built for Picoware.
    """

    TYPE_ADD = 0
    TYPE_DELETE = 1

    def __init__(self, view_manager, callback: callable = None):
        self._vm = view_manager
        self._callback = callback
        self._is_shift = False
        self._is_caps = False
        draw = view_manager.draw
        super().__init__(
            draw, 0, draw.height, draw.foreground, draw.background, True, True
        )

    @property
    def callback(self) -> callable:
        return self._callback

    @callback.setter
    def callback(self, func: callable) -> None:
        self._callback = func

    def __process_text_input(self, button: int) -> None:
        """Process text input and update the textbox"""
        from picoware.system import buttons

        inp = self._vm.input_manager
        
        # 1. Handle Navigation Keys
        if button == buttons.BUTTON_UP:
            self._scroll_up()
            return
        elif button == buttons.BUTTON_DOWN:
            self._scroll_down()
            return
        elif button == buttons.BUTTON_LEFT:
            c_pos = self._get_cursor()
            self._set_cursor(max(0, c_pos - 1))
            self.refresh()
            return
        elif button == buttons.BUTTON_RIGHT:
            c_pos = self._get_cursor()
            self._set_cursor(min(len(self.current_text), c_pos + 1))
            self.refresh()
            return

        # 2. Handle Modifiers (Shift / Caps Lock)
        if button in (buttons.BUTTON_SHIFT, getattr(buttons, 'KEY_MOD_SHL', -1), getattr(buttons, 'KEY_MOD_SHR', -1)):
            self._is_shift = not self._is_shift
            return
        elif button in (buttons.BUTTON_CAPS_LOCK, getattr(buttons, 'KEY_CAPS_LOCK', -1)):
            self._is_caps = not self._is_caps
            self._is_shift = False
            return

        # 3. Handle Text Input
        button_pressed = False
        char: str = inp.button_to_char(button)
        
        if button == buttons.BUTTON_CENTER:
            char = '\n'
        elif char == '\t':
            char = '    ' # Trap tabs and convert to spaces to preserve pixel grid

        # Pull TRUE cursor position from the C module
        c_pos = self._get_cursor()
        curr_text = self.current_text

        if char:
            if getattr(inp, 'was_capitalized', False) or self._is_shift or self._is_caps:
                char = char.upper()
                
            self.current_text = curr_text[:c_pos] + char + curr_text[c_pos:]
            # Force C to advance the cursor past the newly inserted character
            self._set_cursor(c_pos + len(char))
            button_pressed = True
            
            if self._is_shift:
                self._is_shift = False

            if self._callback:
                self._callback(self.TYPE_ADD, char)
                
        elif button == buttons.BUTTON_BACKSPACE:
            if c_pos > 0:
                self.current_text = curr_text[:c_pos-1] + curr_text[c_pos:]
                # Force C to pull the cursor back one space
                self._set_cursor(c_pos - 1)
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