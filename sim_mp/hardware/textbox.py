class TextBox:
    def __init__(self, y, height, width, chars_per_line, line_spacing, foreground_color, background_color, show_scrollbar=True, show_cursor=False):
        object.__setattr__(self, "y", int(y))
        object.__setattr__(self, "height", int(height))
        object.__setattr__(self, "width", int(width))
        object.__setattr__(self, "chars_per_line", int(chars_per_line) if chars_per_line else 1)
        object.__setattr__(self, "line_spacing", int(line_spacing))
        object.__setattr__(self, "foreground_color", foreground_color)
        object.__setattr__(self, "background_color", background_color)
        object.__setattr__(self, "show_scrollbar", show_scrollbar)
        object.__setattr__(self, "show_cursor", show_cursor)
        object.__setattr__(self, "text", "")
        object.__setattr__(self, "cursor", 0)
        object.__setattr__(self, "current_line", 0)
        object.__setattr__(self, "total_lines", 0)
        object.__setattr__(self, "_lines", [])
        object.__setattr__(self, "_line_starts", [0])
        object.__setattr__(self, "protected_cursor", 0)
        object.__setattr__(self, "lines_per_screen", max(1, int(height) // max(1, int(line_spacing))))

    def __setattr__(self, name, value):
        if name == "text":
            self._set_text(value)
        elif name == "cursor":
            self._set_cursor(value)
        elif name == "current_line":
            self._set_current_line(value)
            self.render()
        else:
            object.__setattr__(self, name, value)

    def _wrap(self):
        lines = []
        starts = []
        pos = 0
        parts = self.text.split("\n")
        for part_index, raw in enumerate(parts):
            line_start = pos
            if raw == "":
                lines.append("")
                starts.append(line_start)
            while len(raw) > self.chars_per_line:
                lines.append(raw[: self.chars_per_line])
                starts.append(line_start)
                raw = raw[self.chars_per_line :]
                line_start += self.chars_per_line
            if raw:
                lines.append(raw)
                starts.append(line_start)
            pos += len(parts[part_index])
            if part_index < len(parts) - 1:
                pos += 1
        if not lines:
            lines = [""]
            starts = [0]
        object.__setattr__(self, "_lines", lines)
        object.__setattr__(self, "_line_starts", starts)
        object.__setattr__(self, "total_lines", len(lines))
        object.__setattr__(self, "lines_per_screen", max(1, self.height // max(1, self.line_spacing)))

    def _cursor_line(self):
        if not self._line_starts:
            return 0
        line = 0
        for i in range(len(self._line_starts)):
            if self._line_starts[i] <= self.cursor:
                line = i
            else:
                break
        return max(0, min(line, max(0, self.total_lines - 1)))

    def _scroll_to_cursor(self):
        line = self._cursor_line()
        first = self.current_line
        last = first + self.lines_per_screen
        if line < first:
            object.__setattr__(self, "current_line", line)
        elif line >= last:
            object.__setattr__(self, "current_line", max(0, line - self.lines_per_screen + 1))

    def _set_text(self, text):
        object.__setattr__(self, "text", str(text))
        object.__setattr__(self, "cursor", len(self.text))
        self._wrap()
        object.__setattr__(self, "current_line", max(0, self.total_lines - self.lines_per_screen))
        self.render()

    def set_text(self, text):
        self._set_text(text)

    def _set_cursor(self, cursor):
        low = max(0, int(getattr(self, "protected_cursor", 0)))
        object.__setattr__(self, "cursor", max(low, min(int(cursor), len(self.text))))
        self._scroll_to_cursor()
        self.render()

    def _set_current_line(self, line):
        if line == 0xFFFF:
            line = self.total_lines - 1
        object.__setattr__(self, "current_line", max(0, min(int(line), max(0, self.total_lines - 1))))

    def set_current_line(self, line):
        self._set_current_line(line)
        self.render()

    def _clear(self):
        object.__setattr__(self, "text", "")
        object.__setattr__(self, "cursor", 0)
        object.__setattr__(self, "current_line", 0)
        self._wrap()
        self.render()

    def clear(self):
        self._clear()
        self.render()

    def _scroll_down(self):
        self._set_current_line(self.current_line + 1)

    def _scroll_up(self):
        self._set_current_line(self.current_line - 1)

    def scroll_down(self):
        self._scroll_down()
        self.render()

    def scroll_up(self):
        self._scroll_up()
        self.render()

    def _insert_char(self, char):
        object.__setattr__(self, "text", self.text[: self.cursor] + char + self.text[self.cursor :])
        object.__setattr__(self, "cursor", self.cursor + len(char))
        self._wrap()
        self._scroll_to_cursor()
        self.render()

    def _delete_char(self):
        if self.cursor > max(0, int(getattr(self, "protected_cursor", 0))):
            object.__setattr__(self, "text", self.text[: self.cursor - 1] + self.text[self.cursor :])
            object.__setattr__(self, "cursor", self.cursor - 1)
            self._wrap()
            self._scroll_to_cursor()
            self.render()

    def _delete_forward(self):
        if self.cursor < len(self.text):
            object.__setattr__(self, "text", self.text[: self.cursor] + self.text[self.cursor + 1 :])
            self._wrap()
            self._scroll_to_cursor()
            self.render()

    def _cursor_home(self):
        line = self._cursor_line()
        self._set_cursor(self._line_starts[line] if self._line_starts else 0)

    def _cursor_end(self):
        line = self._cursor_line()
        if not self._line_starts:
            self._set_cursor(len(self.text))
            return
        start = self._line_starts[line]
        self._set_cursor(start + len(self._lines[line]))

    def _cursor_up(self):
        line = self._cursor_line()
        if line > 0:
            col = self.cursor - self._line_starts[line]
            target = line - 1
            new_pos = self._line_starts[target] + min(col, len(self._lines[target]))
            object.__setattr__(self, "cursor", max(0, min(new_pos, len(self.text))))
            self._scroll_to_cursor()
        self.render()

    def _cursor_down(self):
        line = self._cursor_line()
        if line < self.total_lines - 1:
            col = self.cursor - self._line_starts[line]
            target = line + 1
            new_pos = self._line_starts[target] + min(col, len(self._lines[target]))
            object.__setattr__(self, "cursor", max(0, min(new_pos, len(self.text))))
            self._scroll_to_cursor()
        self.render()

    def jump_to_top(self):
        self._set_cursor(0)

    def jump_to_bottom(self):
        self._set_cursor(len(self.text))

    def load_file(self, filename):
        try:
            import sd_mp

            data = sd_mp.read(filename)
            try:
                text = data.decode()
            except AttributeError:
                text = str(data, "utf-8")
        except Exception as e:
            print("Failed to read file {}: {}".format(filename, e))
            text = ""
        self._set_text(text)

    def refresh(self):
        self.render()

    def render(self):
        draw = getattr(self, "_draw", None)
        if draw is None:
            return
        from picoware.system.vector import Vector

        draw.fill_rectangle(Vector(0, self.y), Vector(self.width, self.height), self.background_color)
        y = self.y
        max_lines = max(1, self.height // max(1, self.line_spacing))
        end = min(len(self._lines), self.current_line + max_lines)
        for i in range(self.current_line, end):
            draw.text(Vector(2, y), self._lines[i], self.foreground_color)
            y += self.line_spacing
        if self.show_cursor:
            line = self._cursor_line()
            if self.current_line <= line < end:
                col = self.cursor - self._line_starts[line]
                cursor_x = 2 + max(0, col) * max(1, self.width // max(1, self.chars_per_line))
                cursor_y = self.y + (line - self.current_line) * self.line_spacing
                draw.fill_rectangle(Vector(cursor_x, cursor_y), Vector(2, max(2, self.line_spacing - 1)), self.foreground_color)
        draw.swap()
