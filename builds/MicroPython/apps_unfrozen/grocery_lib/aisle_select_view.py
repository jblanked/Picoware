from micropython import const
from picoware.system.vector import Vector
from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_CENTER, BUTTON_BACK, BUTTON_ENTER
from grocery_lib.i18n import translate
from grocery_lib.ui_utils import draw_modal_frame, draw_text_centered, C_BG, C_TEXT, C_PAPER, C_SEL
from grocery_lib.base_view import BaseView
from grocery_lib.config import get_config

_ITEM_H = const(24)

class AisleSelectView(BaseView):
    """Modal dialog for selecting from a list of options."""
    __slots__ = ("callback", "options", "title", "_selected_index", "_scroll_offset", "_max_visible", "_frame")

    def __init__(self, view_manager, app, current_val, callback, options=None, title=None):
        super().__init__(view_manager, app)
        self.callback = callback
        self.title = title if title else translate("sort_category")
        self.options = options if options else get_config("categories")
        if not self.options:
            self.options = ["other"]
        
        self._selected_index = 0
        if current_val in self.options:
            self._selected_index = self.options.index(current_val)
        
        self._scroll_offset = 0
        self._frame = None
        self._max_visible = 5
        self._draw(True)

    def _draw(self, full=False):
        if not self._dirty and not full: return
        
        # Calculate dynamic frame height based on options length and screen size
        max_h = self.draw.size.y - 20
        needed_h = 32 + len(self.options) * _ITEM_H + 32 # Header + Items + Footer
        frame_h = min(max_h, max(120, needed_h))
        
        self._frame = draw_modal_frame(self.draw, self.title, self.draw.size.x - 30, frame_h)
        fx, fy, fw, fh, f_foot_h = self._frame
        
        start_y = fy + 30
        list_h = fh - 30 - f_foot_h
        self._max_visible = list_h // _ITEM_H
        
        new_offset = self.handle_scroll(self._selected_index, self._scroll_offset, self._max_visible)
        if full or new_offset != self._scroll_offset:
            self._scroll_offset = new_offset
            # Redraw frame content background to clear old text
            self.draw.fill_round_rectangle(Vector(fx + 2, fy + 26), Vector(fw - 4, fh - 26 - f_foot_h + 2), 0, C_BG)
        
        # Draw items
        for i in range(self._scroll_offset, min(len(self.options), self._scroll_offset + self._max_visible)):
            idx_in_view = i - self._scroll_offset
            y = start_y + idx_in_view * _ITEM_H
            is_selected = (i == self._selected_index)
            
            if is_selected:
                self.draw.fill_round_rectangle(Vector(fx + 6, y), Vector(fw - 12, _ITEM_H), 4, C_SEL)
            else:
                self.draw.fill_round_rectangle(Vector(fx + 6, y), Vector(fw - 12, _ITEM_H), 4, C_BG)
            
            label = translate(self.options[i])
            self.draw.text(Vector(fx + 12, y + 4), label, C_TEXT, 0)
        
        hint = translate("hint_select")
        draw_text_centered(self.draw, fx, fy + fh - f_foot_h, fw, f_foot_h, hint, C_TEXT, 0)
        
        self.draw.swap()
        self._dirty = False

    def run(self):
        input_manager = self.view_manager.input_manager
        btn = input_manager.button

        if btn == BUTTON_BACK:
            input_manager.reset()
            return "EXIT"
        elif btn in (BUTTON_CENTER, BUTTON_ENTER):
            input_manager.reset()
            self.callback(self.options[self._selected_index])
            return "EXIT"
        elif btn == BUTTON_UP:
            input_manager.reset()
            self._selected_index = (self._selected_index - 1) % len(self.options)
            self._dirty = True
        elif btn == BUTTON_DOWN:
            input_manager.reset()
            self._selected_index = (self._selected_index + 1) % len(self.options)
            self._dirty = True
        
        if self._dirty: self._draw()
        return None
