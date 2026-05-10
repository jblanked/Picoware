import utime
from grocery_lib.ui_utils import C_BG, C_TEXT, Vector

class BaseView:
    """Common base for all Grocery views. Proxy for system View."""
    __slots__ = ("app", "_dirty", "draw", "input_manager", "view_manager", "_scratch_pos", "_cursor_tick", "_cursor_visible")

    def __init__(self, view_manager, app):
        self.view_manager = view_manager
        self.draw = view_manager.draw
        self.input_manager = view_manager.input_manager
        self.app = app
        self._dirty = True
        self._scratch_pos = Vector(0, 0)
        self._cursor_tick = utime.ticks_ms()
        self._cursor_visible = True

    def reset_cursor(self):
        self._cursor_tick = utime.ticks_ms()
        self._cursor_visible = True
        self._dirty = True

    def _check_cursor(self):
        """Update cursor blink state. Returns True if redraw needed."""
        now = utime.ticks_ms()
        if utime.ticks_diff(now, self._cursor_tick) > 400:
            self._cursor_tick = now
            self._cursor_visible = not self._cursor_visible
            self._dirty = True
            return True
        return False

    def _draw(self):
        if not self._dirty:
            return
        self.draw.fill_screen(C_BG)
        self.draw.swap()
        self._dirty = False

    def handle_scroll(self, selected_index, current_offset, max_visible):
        """Shared scroll logic for list-based views."""
        if selected_index < current_offset:
            return selected_index
        elif selected_index >= current_offset + max_visible:
            return selected_index - max_visible + 1
        return current_offset
