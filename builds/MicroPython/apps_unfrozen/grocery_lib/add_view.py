from grocery_lib.i18n import translate
from grocery_lib.ui_utils import draw_modal_frame, draw_card, draw_text_centered, C_BG, C_TEXT, C_PAPER, C_SEL
from grocery_lib.base_view import BaseView
from micropython import const
from picoware.system.vector import Vector

_BAR_H = const(24)

class AddView(BaseView):
    """Modal dialog view for text input."""
    __slots__ = ("title", "callback", "input_text", "_frame", "_cursor_pos", "_is_selecting", "is_numeric", "decimal_sep")

    def __init__(self, view_manager, app, title, callback, is_numeric=False):
        super().__init__(view_manager, app)
        self.title = title
        self.callback = callback
        self.input_text = ""
        self._cursor_pos = 0
        self._is_selecting = False # initially empty, but if we had text it would be true
        self._frame = None
        self.is_numeric = is_numeric
        from grocery_lib.config import get_config
        self.decimal_sep = get_config("decimal_separator") or "."
        self._draw()

    def _draw(self):
        if not self._dirty: return
        
        # Frame: x, y, w, h, footer_h
        self._frame = draw_modal_frame(self.draw, self.title, self.draw.size.x - 40, 100)
        fx, fy, fw, fh, f_foot_h = self._frame
        
        # Draw Input Field inside frame
        iw, ih = fw - 20, 32
        ix, iy = fx + 10, fy + 35
        self._scratch_pos.x, self._scratch_pos.y = ix, iy
        draw_card(self.draw, self._scratch_pos, Vector(iw, ih), 4, True)
        
        # Draw Text
        tx, ty = ix + 8, iy + (ih - self.draw.font_size.y) // 2
        
        tw = self.draw.len(self.input_text, 0)
        if self._is_selecting and self.input_text:
            self.draw.fill_rectangle(Vector(tx - 2, iy + 4), Vector(tw + 4, ih - 8), C_SEL)
        
        self.draw.text(Vector(tx, ty), self.input_text, C_TEXT, 0)
        
        if not self._is_selecting and self._cursor_visible:
            # Draw blinking cursor at position
            pre_w = self.draw.len(self.input_text[:self._cursor_pos], 0)
            cx = tx + pre_w
            self.draw.line_custom(Vector(cx, iy + 6), Vector(cx, iy + ih - 6), C_TEXT)
        
        # Footer text inside frame
        hint = translate("hint_add")
        draw_text_centered(self.draw, fx, fy + fh - f_foot_h, fw, f_foot_h, hint, C_TEXT, 0)
        
        self.draw.swap()
        self._dirty = False

    def run(self):
        self._check_cursor()
        from picoware.system.buttons import BUTTON_CENTER, BUTTON_BACK, BUTTON_ENTER, BUTTON_BACKSPACE, BUTTON_DELETE, BUTTON_LEFT, BUTTON_RIGHT
        input_manager = self.view_manager.input_manager
        btn = input_manager.button

        if btn == BUTTON_BACK:
            input_manager.reset()
            return "EXIT"
        elif btn in (BUTTON_CENTER, BUTTON_ENTER):
            input_manager.reset()
            if self.input_text:
                self.callback(self.input_text)
            return "EXIT"
        elif btn == BUTTON_LEFT:
            input_manager.reset()
            if self._is_selecting:
                self._is_selecting = False
                self._cursor_pos = len(self.input_text)
            else:
                self._cursor_pos = max(0, self._cursor_pos - 1)
            self._dirty = True
        elif btn == BUTTON_RIGHT:
            input_manager.reset()
            if self._is_selecting:
                self._is_selecting = False
                self._cursor_pos = len(self.input_text)
            else:
                self._cursor_pos = min(len(self.input_text), self._cursor_pos + 1)
            self._dirty = True
        elif btn in (BUTTON_BACKSPACE, BUTTON_DELETE, 127):
            input_manager.reset()
            if self._is_selecting:
                self.input_text = ""
                self._is_selecting = False
                self._cursor_pos = 0
                self._dirty = True
            elif self._cursor_pos > 0:
                self.input_text = self.input_text[:self._cursor_pos-1] + self.input_text[self._cursor_pos:]
                self._cursor_pos -= 1
                self._dirty = True
        else:
            char = input_manager.button_to_char(btn)
            if char:
                if self.is_numeric:
                    if not (char.isdigit() or char == self.decimal_sep):
                        return None
                
                input_manager.reset()
                if self._is_selecting:
                    self.input_text = char
                    self._is_selecting = False
                    self._cursor_pos = 1
                else:
                    self.input_text = self.input_text[:self._cursor_pos] + char + self.input_text[self._cursor_pos:]
                    self._cursor_pos += 1
                self._dirty = True
        
        if self._dirty: self._draw()
        return None
