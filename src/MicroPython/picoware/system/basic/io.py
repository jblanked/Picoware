class PicowareConsole:
    def __init__(self, view_manager):
        self.vm = view_manager
        self.draw = view_manager.draw
        self.fg = view_manager.foreground_color
        self.bg = view_manager.background_color

        self.font_w = self.draw.font_size.x
        self.font_h = self.draw.font_size.y
        self.screen_w = self.draw.size.x
        self.screen_h = self.draw.size.y
        self.columns = max(self.screen_w // max(self.font_w, 1), 8)
        self.rows = max(self.screen_h // max(self.font_h, 1), 4)

        # Scroll-back buffer
        self.lines = []      # completed lines
        self.cur = ""        # current in-progress line
        self.max_lines = 400
        self.footer = "BACK=exit"
        self.dirty = True
        self._input_active = False


    def output(self, text):
        """Append text; '\\n' flushes lines, a trailing newline opens a fresh
        line, and no trailing newline leaves the line open (PRINT ...;)."""
        parts = text.split("\n")
        for i, part in enumerate(parts):
            self.cur += part
            if i < len(parts) - 1:
                self._flush_line()
            else:
                self._wrap_cur()
        self.dirty = True

    def newline(self):
        self._flush_line()
        self.dirty = True

    def echo(self, ch):
        self.cur += ch
        self._wrap_cur()
        self.dirty = True

    def backspace(self):
        if self.cur:
            self.cur = self.cur[:-1]
            self.dirty = True

    def clear(self):
        self.lines = []
        self.cur = ""
        self.dirty = True

    def pos(self):
        """Current print column (for POS())."""
        return len(self.cur)

    def set_input_active(self, active):
        self._input_active = bool(active)

    def _flush_line(self):
        self.lines.append(self.cur)
        self.cur = ""
        self._trim()

    def _wrap_cur(self):
        while len(self.cur) > self.columns:
            self.lines.append(self.cur[:self.columns])
            self.cur = self.cur[self.columns:]
            self._trim()

    def _trim(self):
        if len(self.lines) > self.max_lines:
            del self.lines[:len(self.lines) - self.max_lines]


    def render(self):
        if not self.dirty:
            return
        draw = self.draw
        try:
            draw.erase()
        except Exception:
            draw.fill_screen(self.bg)

        display = list(self.lines) + [self.cur]
        text_rows = self.rows - (1 if self.footer else 0)
        text_rows = max(text_rows, 1)
        tail = display[-text_rows:]

        y = 0
        for line in tail:
            draw._text(0, y, line, self.fg)
            y += self.font_h
        if self.footer:
            draw._text(0, self.screen_h - self.font_h, self.footer,
                       self.vm.selected_color if hasattr(self.vm, "selected_color")
                       else self.fg)
        draw.swap()
        self.dirty = False


    def log(self, message, level=-1):
        self.vm.log(message, level)
