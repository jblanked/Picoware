import sim_runtime


def _get_draw_from_args(args):
    """Extract an LCD-like draw target from variadic args."""
    for item in args:
        if (hasattr(item, "fill_screen") or hasattr(item, "_clear")) and hasattr(item, "swap"):
            return item
    return getattr(sim_runtime, "_lcd", None)


def _line_text(row):
    """Convert a buffer row to a string."""
    try:
        return "".join(row)
    except TypeError:
        return str(row)


def render(buffer, *args):
    """Render-compatible VT shim for native and test signatures."""
    screen_height = int(args[0]) if len(args) > 0 else len(buffer)
    char_height = int(args[2]) if len(args) > 2 else 12
    char_width = int(args[3]) if len(args) > 3 else 7
    draw = _get_draw_from_args(args)
    if draw is None:
        return False

    if len(args) > 4 and isinstance(args[4], int):
        background = args[4]
        foreground = args[5] if len(args) > 5 else 0xFFFF
        cursor_visible = bool(args[6]) if len(args) > 6 else True
        cursor_x = int(args[7]) if len(args) > 7 else 0
        cursor_y = int(args[8]) if len(args) > 8 else 0
        cursor_w = int(args[9]) if len(args) > 9 else 2
        cursor_h = int(args[10]) if len(args) > 10 else max(2, char_height - 1)
        cursor_color = args[11] if len(args) > 11 else foreground
    else:
        foreground = args[5] if len(args) > 5 else 0xFFFF
        background = args[6] if len(args) > 6 else 0
        cursor_x = int(args[7]) if len(args) > 7 else 0
        cursor_y = int(args[8]) if len(args) > 8 else 0
        cursor_visible = bool(args[9]) if len(args) > 9 else True
        cursor_w = 2
        cursor_h = max(2, char_height - 1)
        cursor_color = foreground

    try:
        try:
            from picoware.system.vector import Vector
        except Exception:
            Vector = None

        if hasattr(draw, "fill_screen"):
            draw.fill_screen(background)
        else:
            draw._clear(background)
        y = 0
        rows = min(screen_height, len(buffer))
        for i in range(rows):
            height = draw.size.y if hasattr(draw, "size") else draw.height
            if y >= height:
                break
            if hasattr(draw, "text") and Vector is not None:
                draw.text(Vector(0, y), _line_text(buffer[i]), foreground)
            else:
                draw._text(0, y, _line_text(buffer[i]), foreground)
            y += char_height
        if cursor_visible:
            if hasattr(draw, "fill_rectangle") and Vector is not None:
                draw.fill_rectangle(Vector(cursor_x, cursor_y), Vector(cursor_w, cursor_h), cursor_color)
            else:
                draw._fill_rectangle(cursor_x, cursor_y, cursor_w, cursor_h, cursor_color)
        draw.swap()
        return True
    except Exception as e:
        print("[sim:vt] render failed:", e)
        return False


class TerminalBuffer:
    def __init__(self, cols=40, rows=26):
        """Initialize a terminal buffer with given dimensions."""
        self.cols = int(cols)
        self.rows = int(rows)
        self.cursor_x = 0
        self.cursor_y = 0
        self.buffer = [[" "] * self.cols for _ in range(self.rows)]

    def clear(self):
        """Clear all cells and reset cursor."""
        for y in range(self.rows):
            for x in range(self.cols):
                self.buffer[y][x] = " "
        self.cursor_x = 0
        self.cursor_y = 0

    def write(self, text):
        """Write a string into the terminal buffer with scrolling."""
        for ch in str(text):
            if ch == "\n":
                self.cursor_x = 0
                self.cursor_y += 1
            elif ch == "\r":
                self.cursor_x = 0
            elif ch == "\b":
                self.cursor_x = max(0, self.cursor_x - 1)
                self.buffer[self.cursor_y][self.cursor_x] = " "
            elif ord(ch) >= 32:
                self.buffer[self.cursor_y][self.cursor_x] = ch
                self.cursor_x += 1
            if self.cursor_x >= self.cols:
                self.cursor_x = 0
                self.cursor_y += 1
            if self.cursor_y >= self.rows:
                self.buffer.pop(0)
                self.buffer.append([" "] * self.cols)
                self.cursor_y = self.rows - 1
        return len(str(text))
