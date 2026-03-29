import textbox


class TextBox(textbox.TextBox):
    '''Class for a text box with scrolling functionality."""'''

    def __init__(
        self,
        draw,
        y: int,
        height: int,
        foreground_color: int = 0xFFFF,
        background_color: int = 0x0000,
        show_scrollbar: bool = True,
        show_cursor: bool = False,
    ) -> None:
        self.use_lvgl = draw.use_lvgl
        self._lvgl_textbox = None
        self._draw = draw
        super().__init__(
            y,
            height,
            draw.size.x,
            int(draw.size.x // draw.font_size.x),  # chars per line
            int(draw.size.x * 0.03125),  # spacing
            foreground_color,
            background_color,
            show_scrollbar,
            show_cursor,
        )

        # LVGL path
        if self.use_lvgl:
            try:
                from picoware_lvgl import init, TextBox as LVGLTextBox

                init()

                class LVGLTextBoxWrapper(LVGLTextBox):
                    def __setattr__(self, name, value):
                        if name == "text":
                            self.set_text(value)
                        elif name == "current_line":
                            self.set_current_line(value)
                        else:
                            super().__setattr__(name, value)

                self._lvgl_textbox = LVGLTextBoxWrapper(
                    y, height, foreground_color, background_color, show_scrollbar
                )
            except (ImportError, RuntimeError, ValueError):
                self.use_lvgl = False

    def __del__(self):
        if self._lvgl_textbox is not None:
            from picoware_lvgl import deinit

            del self._lvgl_textbox
            self._lvgl_textbox = None
            deinit()

    def __setattr__(self, name, value):
        if name == "text":
            self.set_text(value)
        elif name == "cursor":
            self._set_cursor(value)
        elif name == "current_line":
            self.set_current_line(value)
        else:
            super().__setattr__(name, value)

    @property
    def current_text(self) -> str:
        """Returns the current text content of the text box."""
        if self.use_lvgl and self._lvgl_textbox is not None:
            return self._lvgl_textbox.text()
        return self.text

    @current_text.setter
    def current_text(self, value: str) -> None:
        if self.use_lvgl and self._lvgl_textbox is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_textbox.set_text(value)
            task_handler()
            return

        self._set_text(value)

    @property
    def text_height(self) -> int:
        """Returns the total height of the text content in pixels."""
        if self.use_lvgl and self._lvgl_textbox is not None:
            return self._lvgl_textbox.text_height()
        tl = self.total_lines
        return 0 if tl == 0 else (tl - 1) * self._draw.font_size.y + 2

    def clear(self):
        """Clears the text box content and screen."""
        if self.use_lvgl and self._lvgl_textbox is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_textbox.clear()
            task_handler()
            return

        self._clear()

    def refresh(self):
        """Refreshes the text box display to reflect any changes in content or state."""
        if self.use_lvgl and self._lvgl_textbox is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_textbox.refresh()
            task_handler()
            return

        self.render()

    def set_current_line(self, line: int):
        """Sets the current line index for the text box, which determines the visible portion of the text content."""
        if self.use_lvgl and self._lvgl_textbox is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_textbox.set_current_line(line)
            task_handler()
            return

        self._set_current_line(line)

    def set_text(self, text: str):
        """Updates the text content of the text box and refreshes the display to show the new content."""
        if self.use_lvgl and self._lvgl_textbox is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_textbox.set_text(text)
            task_handler()
            return

        self._set_text(text)

    def scroll_down(self):
        """Scrolls the text box content down by one line"""
        if self.use_lvgl and self._lvgl_textbox is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_textbox.scroll_down()
            task_handler()
            return

        self._scroll_down()

    def scroll_up(self):
        """Scrolls the text box content up by one line"""
        if self.use_lvgl and self._lvgl_textbox is not None:
            from picoware_lvgl import tick, task_handler

            tick(5)
            self._lvgl_textbox.scroll_up()
            task_handler()
            return

        self._scroll_up()
