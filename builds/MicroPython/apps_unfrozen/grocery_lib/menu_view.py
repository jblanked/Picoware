from grocery_lib.i18n import translate
from grocery_lib.ui_utils import draw_header, draw_footer, draw_card, draw_icon, C_BG, C_TEXT, C_PAPER
from grocery_lib.base_view import BaseView
from micropython import const
from picoware.system.vector import Vector

_BAR_H = const(24)
_MARGIN = const(4)
_SPACING = const(4)
_CARD_RADIUS = const(6)

class MenuView(BaseView):
    """Base for simple list-based menus."""
    __slots__ = ("title", "items", "item_keys", "card_h", "_selected_index", "_scroll_offset", "_max_visible", "_card_size", "_hint")

    def __init__(self, view_manager, app, title, items, item_keys, hint="UP/DN: Nav | CENTER: Pick"):
        super().__init__(view_manager, app)
        self.title = title
        self.items = items
        self.item_keys = item_keys
        self._hint = hint
        
        self.card_h = 32
        self._selected_index = 0
        self._scroll_offset = 0
        
        # Calculate how many cards fit on screen
        available_h = self.draw.size.y - (_BAR_H * 2) - (_MARGIN * 2)
        self._max_visible = available_h // (self.card_h + _SPACING)
        
        self._card_size = Vector(self.draw.size.x - (_MARGIN * 2), self.card_h)

    def _draw(self):
        if not self._dirty: return
        
        # Ensure scroll offset is correct for the current index
        self._scroll_offset = self.handle_scroll(self._selected_index, self._scroll_offset, self._max_visible)

        self.draw.fill_screen(C_BG)
        draw_header(self.draw, self.title, _BAR_H)
        
        start_y = _BAR_H + _MARGIN
        end_idx = min(len(self.items), self._scroll_offset + self._max_visible)
        
        for i in range(self._scroll_offset, end_idx):
            is_selected = (i == self._selected_index)
            y = start_y + (i - self._scroll_offset) * (self.card_h + _SPACING)
            
            self._scratch_pos.x, self._scratch_pos.y = _MARGIN, y
            draw_card(self.draw, self._scratch_pos, self._card_size, _CARD_RADIUS, is_selected)
            
            # Icon
            icon_y = y + (self.card_h - 12) // 2
            draw_icon(self.draw, self.item_keys[i], _MARGIN + 12, icon_y)
            
            # Text
            text_y = y + (self.card_h - self.draw.font_size.y) // 2
            self.draw.text(Vector(_MARGIN + 38, text_y), self.items[i], C_TEXT, 0)
            
        draw_footer(self.draw, self._hint, _BAR_H)
        self.draw.swap()
        self._dirty = False

    def run(self):
        from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_CENTER, BUTTON_BACK, BUTTON_F3
        input_manager = self.view_manager.input_manager
        button = input_manager.button

        if button == BUTTON_BACK:
            input_manager.reset()
            return "EXIT"
        elif button == BUTTON_F3:
            input_manager.reset()
            return "HELP"
            
        old_idx = self._selected_index
        if button == BUTTON_UP:
            self._selected_index = (self._selected_index - 1) % len(self.items)
        elif button == BUTTON_DOWN:
            self._selected_index = (self._selected_index + 1) % len(self.items)
        elif button == 58: # BUTTON_LEFT_BRACKET
            self._selected_index = max(0, self._selected_index - self._max_visible)
        elif button == 59: # BUTTON_RIGHT_BRACKET
            self._selected_index = min(len(self.items) - 1, self._selected_index + self._max_visible)
            
        if self._selected_index != old_idx:
            input_manager.reset()
            self._scroll_offset = self.handle_scroll(self._selected_index, self._scroll_offset, self._max_visible)
            self._dirty = True
            self._draw()
        elif button == BUTTON_CENTER:
            input_manager.reset()
            return self.item_keys[self._selected_index]
        return None
